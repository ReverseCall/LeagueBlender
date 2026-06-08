"""
Operador Blender para importar SKL + SKN do League of Legends
"""

import os
import bpy
import mathutils
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

from ..preferences import get_prefs
from ..formats.skl import read_skl, SKLFile
from ..formats.skn import read_skn, SKNFile
from ..importers.import_skn import build_mesh
from ..utils.bone_shape import apply_bone_shapes, BoneShapeType
from ..utils.scene_setup import apply_clip_end_on_first_import, mark_imported


# Construtor do armature
# =========================

def build_armature(skl: SKLFile, name: str) -> bpy.types.Object:
    """
    Constroi o Armature a partir de um SKLFile ja flipado.

    IDProperties salvas em cada EditBone (necessarias para exportação/round-trip)
        lol_id       - indice original do joint no SKL
        lol_hash     - hash ELF do nome | deve ajudar a evitar erros no exporte
        lol_radius   - radius/scale do arquivo

        Transforms locais (espaço do LoL, pre flip para re exportação exata)
        lol_local_t   - [x, y, z]
        lol_local_r   - [x, y, z, w]
        lol_local_s   - [x, y, z]

        Inverse Bind Pose RAW (espaço LoL, pre flip obrigatorio para o jogo)
        lol_ig_t   - [x, y, z]
        lol_ig_r   - [x, y, z, w]
        lol_ig_s   - [x, y, z]

    Os iglobals são salvos PRE FLIP (valores diretos do arquivo) porque o LoL
    os consome diretamente ao carregar o SKL - O flip e so para visualização no Blender
    """
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)

    arm_obj.show_in_front = False
    arm_data.display_type = 'STICK'

    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode = 'EDIT')

    edit_bones = arm_data.edit_bones
    global_matrices = [mathutils.Matrix.Identity(4)] * len(skl.joints)

    for i, j in enumerate(skl.joints):
        bone_name = j.name if j.name else f"Joint_{i}"
        eb = edit_bones.new(bone_name)

        # IDProperties para round-trip
        eb["lol_id"] = i
        eb["lol_hash"] = j.hash
        eb["lol_radius"] = j.radius

        # Locais - ja flipados
        lt = j.local_translation
        lr = j.local_rotation
        ls = j.local_scale
        eb["lol_local_t"] = [lt[0], lt[1], lt[2]]
        eb["lol_local_r"] = [lr[0], lr[1], lr[2], lr[3]]
        eb["lol_local_s"] = [ls[0], ls[1], ls[2]]

        """
        Inverse Global - salvo RAW (pre flip) exatamente como veio do arquivo
        O LoL usa esses valores diretamente. O flip so afeta a visualização
        Como flip() ja foi chamado, e preciso desfazr para salvar o raw
            flip desfaz: ig_t.x *= -1 | ig_r.y *= -1 | ig_r.z *= -1
        """
        if j.iglobal_translation is not None:
            ig_tx, ig_ty, ig_tz = j.iglobal_translation
            ig_rx, ig_ry, ig_rz, ig_rw = j.iglobal_rotation
            ig_sx, ig_sy, ig_sz = j.iglobal_scale

            # Desfaz o flip para armazenar os valores originais do arquivo
            eb["lol_ig_t"] = [-ig_tx, ig_ty, ig_tz]
            eb["lol_ig_r"] = [ig_rx, -ig_ry, -ig_rz, ig_rw]
            eb["lol_ig_s"] = [ig_sx, ig_sy, ig_sz]

        # ___ Posição no espaço Blender (Y-up para Z-up) ___
        # flip() ja aplicou: tx = -tx, ry = -ry, rz = -rz
        tx, ty, tz = j.local_translation
        loc = mathutils.Vector((tx, -tz, ty))

        qx, qy, qz, qw = j.local_rotation
        rot = mathutils.Quaternion((qw, qx, -qz, qy))

        sx, sy, sz = j.local_scale
        sca = mathutils.Vector((sx, sz, sy))

        # Matriz local e acumulo global
        m_loc = mathutils.Matrix.Translation(loc)
        m_rot = rot.to_matrix().to_4x4()
        m_sca = mathutils.Matrix.Diagonal(sca.to_4d())
        local_m = m_loc @ m_rot @ m_sca

        if j.parent != -1 and j.parent < i:
            parent_eb = edit_bones.get(skl.joints[j.parent].name)
            if parent_eb:
                eb.parent = parent_eb
            global_matrices[i] = global_matrices[j.parent] @ local_m
        else:
            global_matrices[i] = local_m

        # ___ Head / Tail / Matrix do EditBone ___
        matrix = global_matrices[i]
        eb.matrix = matrix
        eb.head = matrix.to_translation()
        eb.tail = eb.head + matrix.to_3x3().col[1] * 0.5
        eb.use_connect = False

    bpy.ops.object.mode_set(mode = 'OBJECT')

    # Pose de descanso
    for pbone in arm_obj.pose.bones:
        pbone.matrix_basis = mathutils.Matrix.Identity(4)

    return arm_obj


# Skinning
# -----------

def apply_skinning(
    mesh_obj: bpy.types.Object,
    arm_obj: bpy.types.Object,
    skl: SKLFile,
    skn: SKNFile,
):
    """
    Aplica pesos seguindo a logica do LBV9_2025
    O indice bruto do SKN (v.influences[i]) e mapeado para o joint real
    via skl.influences, que e a tabela de remapeamento do arquivo.
    """
    joint_names = [j.name if j.name else f"Joint_{i}" for i, j in enumerate(skl.joints)]
    for gn in joint_names:
        if gn not in mesh_obj.vertex_groups:
            mesh_obj.vertex_groups.new(name = gn)

    use_map = len(skl.influences) > 0

    for v_idx, v in enumerate(skn.vertices):
        for i in range(4):
            weight = v.weights[i]
            if weight > 0.001:
                raw_id = v.influences[i]

                real_id = -1
                if use_map:
                    if raw_id < len(skl.influences):
                        real_id = skl.influences[raw_id]
                else:
                    real_id = raw_id

                if 0 <= real_id < len(joint_names):
                    vg = mesh_obj.vertex_groups.get(joint_names[real_id])
                    if vg:
                        vg.add([v_idx], weight, 'ADD')

    mesh_obj.parent = arm_obj
    mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm_obj
    mod.use_vertex_groups = True
    mesh_obj.data.update()


# Operador
# -----------

class LEAGUEBLENDER_OT_import_skl(Operator, ImportHelper):

    # Importa Skeleton + Mesh (.skl + .skn) do LoL
    bl_idname = "leagueblender.import_skl"
    bl_label = "League Skeleton (.skl)"
    bl_description = (
        "Importa Skeleton (.skl) + Mesh (.skn) do League of Legends. "
        "O .skn deve ter o mesmo nome e estar na mesma pasta."
    )
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".skl"
    filter_glob: StringProperty(default = "*.skl", options = {'HIDDEN'})

    # Opções locais - sobrescrevem as preferências globais nesta importação
    # ------------------------------------------------------------------------

    skl_bone_shape: EnumProperty(
        name="Bone Shape",
        description="Forma visual dos ossos ao importar o Skeleton",
        items=[
            ('BLENDER', "Blender (Stick)", "Forma padrão do Blender"),
            ('SPHERE',  "Sphere (wire)",   "Esfera wire estilo glTF"),
        ],
        default='BLENDER',
    )

    skl_show_in_front: BoolProperty(
        name="Show In Front",
        description="Desenha o armature sobre outros objetos (opção In Front)",
        default=True,
    )

    skl_only: BoolProperty(
        name="Import SKL Only",
        description="Importa apenas o Skeleton, sem carregar o SKN",
        default=False,
    )

    skn_mesh_format: EnumProperty(
        name="Mesh Topology",
        description="Mantem triangulos ou converte para quads",
        items=[
            ('TRIS',  "Triangles (Default)", "Mantem a topologia original em triangulos"),
            ('QUADS', "Quads (Tris to Quads)", "Tenta converter triangulos em quads"),
        ],
        default='TRIS',
    )

    skn_apply_seams: BoolProperty(
        name="Rebuild Seam (BETA)",
        description="Detecta e marca UV seams automaticamente ao importar",
        default=False,
    )

    skn_merge_by_distance: BoolProperty(
        name="Merge by Distance",
        description="Faz Merge > By Distance nos vertices apos importar",
        default=False,
    )

    skn_merge_threshold: FloatProperty(
        name="Distance",
        description="Distancia maxima para considerar dois vertices como duplicados",
        default=0.001,
        min=0.00001,
        max=0.1,
        precision=5,
        step=1,
        unit='LENGTH',
    )

    skn_default_material_color: BoolProperty(
        name="Gray Mesh by Default",
        description="Aplica a cor cinza padrão do LeagueBlender aos materiais criados",
        default=True,
    )

    def draw(self, _context):

        # Painel lateral do file browser com as opções de importação
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(heading = "SKL Options")
        col.prop(self, "skl_bone_shape")
        col.prop(self, "skl_show_in_front")
        col.prop(self, "skl_only")

        col.separator()
        col.label(text = "SKN Options")

        # SKN options ficam desabilitadas quando so importa SKL
        skn_col = col.column()
        skn_col.enabled = not self.skl_only
        skn_col.prop(self, "skn_mesh_format")
        skn_col.prop(self, "skn_default_material_color")
        skn_col.prop(self, "skn_apply_seams")

        col.separator()
        col.prop(self, "skn_merge_by_distance")
        sub = col.row()
        sub.enabled = self.skn_merge_by_distance and not self.skl_only
        sub.prop(self, "skn_merge_threshold")

        col.separator()
        col.label(text = "Defaults via Addon Preferences", icon = 'PREFERENCES')

    def invoke(self, context, event):
        
        # Pre preenche as opções locais com os valores das preferências globais
        prefs = get_prefs(context)
        self.skl_bone_shape = prefs.skl_bone_shape
        self.skl_show_in_front = prefs.skl_show_in_front
        self.skn_mesh_format = prefs.skn_mesh_format
        self.skn_apply_seams = prefs.skn_apply_seams
        self.skn_merge_by_distance = prefs.skn_merge_by_distance
        self.skn_merge_threshold = prefs.skn_merge_threshold
        self.skn_default_material_color = prefs.skn_default_material_color
        return super().invoke(context, event)

    def execute(self, context):
        skl_path = self.filepath
        base = os.path.splitext(skl_path)[0]
        skn_path = base + ".skn"
        name = os.path.basename(base)

        # Parsing do SKL (sempre)
        try:
            skl = read_skl(skl_path)
        except Exception as e:
            self.report({'ERROR'}, f"Error in SKL parsing: {e}")
            return {'CANCELLED'}

        skl.flip()

        # Aplica Clip End no primeiro import (antes de criar qualquer objeto)
        apply_clip_end_on_first_import(context)

        # ___ Armature ___
        try:
            arm_obj = build_armature(skl, name + "_Armature")
        except Exception as e:
            self.report({'ERROR'}, f"Error creating armature: {e}")
            return {'CANCELLED'}

        mark_imported(arm_obj)

        # Salva a influence list original para round-trip no exportador
        arm_obj["lol_influences"] = list(skl.influences)

        # Aplica show_in_front conforme a opção local
        arm_obj.show_in_front = self.skl_show_in_front

        # ___ Bone Shape ___
        apply_bone_shapes(arm_obj, BoneShapeType(self.skl_bone_shape))

        # SKN (opcional)
        if not self.skl_only:
            if not os.path.isfile(skn_path):
                self.report({'ERROR'},
                    f"SKN not found: {skn_path}\n"
                    ".skn must be in the same folder with the same name as .skl."
                )
                return {'CANCELLED'}

            try:
                skn = read_skn(skn_path)
            except Exception as e:
                self.report({'ERROR'}, f"Error in SKN parsing: {e}")
                return {'CANCELLED'}

            skn.flip()

            try:
                mesh_obj = build_mesh(
                    skn,
                    name,
                    apply_weights = False,
                    mesh_format = self.skn_mesh_format,
                    apply_seams = self.skn_apply_seams,
                    use_gray_material = self.skn_default_material_color,
                )
                context.collection.objects.link(mesh_obj)
                mark_imported(mesh_obj)
            except Exception as e:
                self.report({'ERROR'}, f"Error creating mesh: {e}")
                return {'CANCELLED'}

            try:
                apply_skinning(mesh_obj, arm_obj, skl, skn)
            except Exception as e:
                self.report({'ERROR'}, f"Error in skinning: {e}")

            if self.skn_merge_by_distance:
                from ..utils.mesh_utils import merge_by_distance
                merge_by_distance(mesh_obj, threshold = self.skn_merge_threshold)

            bpy.ops.object.select_all(action = 'DESELECT')
            arm_obj.select_set(True)
            mesh_obj.select_set(True)
            context.view_layer.objects.active = arm_obj

            self.report({'INFO'},
                f"Importado: {name} - "
                f"{len(skl.joints)} joints, "
                f"{len(skn.vertices):,} verts"
            )
        else:
            bpy.ops.object.select_all(action = 'DESELECT')
            arm_obj.select_set(True)
            context.view_layer.objects.active = arm_obj

            self.report({'INFO'},
                f"SKL importado: {name} - {len(skl.joints)} joints"
            )

        return {'FINISHED'}