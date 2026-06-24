import os
import bpy
import mathutils
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

from ..i18n import t
from ..formats.skn import read_skn
from ..preferences import get_prefs
from ..formats.skl import read_skl, SKLFile
from ..utils.bone_shape import apply_bone_shapes, BoneShapeType
from ..importers.import_skn import build_mesh, build_submesh_objects
from ..utils.scene_setup import apply_clip_end_on_first_import, mark_imported


# Construtor do armature
# =========================

def build_armature(skl: SKLFile, name: str, collection: bpy.types.Collection | None = None) -> bpy.types.Object:
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

    target_collection = collection if collection is not None else bpy.context.collection
    target_collection.objects.link(arm_obj)
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
    vertices: list,
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

    for v_idx, v in enumerate(vertices):
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
    bl_label = t("op_import_skl_label")
    bl_description = t("op_import_skl_desc")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".skl"
    filter_glob: StringProperty(default = "*.skl", options = {'HIDDEN'})

    # Opções locais - sobrescrevem as preferências globais nesta importação
    # ------------------------------------------------------------------------

    skl_bone_shape: EnumProperty(
        name=t("prop_skl_bone_shape_name"),
        description=t("prop_skl_bone_shape_desc"),
        items=[
            ('BLENDER', t("prop_skl_bone_shape_blender_name"), t("prop_skl_bone_shape_blender_desc")),
            ('SPHERE',  t("prop_skl_bone_shape_sphere_name"),  t("prop_skl_bone_shape_sphere_desc")),
        ],
        default='BLENDER',
    )

    skl_show_in_front: BoolProperty(
        name=t("prop_skl_show_in_front_name"),
        description=t("prop_skl_show_in_front_desc"),
        default=True,
    )

    skl_only: BoolProperty(
        name=t("prop_skl_only_name"),
        description=t("prop_skl_only_desc"),
        default=False,
    )

    skn_mesh_format: EnumProperty(
        name=t("prop_skn_mesh_format_name"),
        description=t("prop_skn_mesh_format_desc"),
        items=[
            ('TRIS',  t("prop_skn_mesh_format_tris_name"),  t("prop_skn_mesh_format_tris_desc")),
            ('QUADS', t("prop_skn_mesh_format_quads_name"), t("prop_skn_mesh_format_quads_desc")),
        ],
        default='TRIS',
    )

    skn_apply_seams: BoolProperty(
        name=t("prop_skn_apply_seams_name"),
        description=t("prop_skn_apply_seams_desc"),
        default=False,
    )

    skn_merge_by_distance: BoolProperty(
        name=t("prop_skn_merge_by_distance_name"),
        description=t("prop_skn_merge_by_distance_desc"),
        default=False,
    )

    skn_merge_threshold: FloatProperty(
        name=t("prop_skn_merge_threshold_name"),
        description=t("prop_skn_merge_threshold_desc"),
        default=0.001,
        min=0.00001,
        max=0.1,
        precision=5,
        step=1,
        unit='LENGTH',
    )

    skn_default_material_color: BoolProperty(
        name=t("prop_skn_default_material_color_name"),
        description=t("prop_skn_default_material_color_desc"),
        default=True,
    )

    skn_import_as_collection: BoolProperty(
        name=t("prop_skn_import_as_collection_name"),
        description=t("prop_skn_import_as_collection_desc_skl"),
        default=False,
    )

    def draw(self, _context):

        # Painel lateral do file browser com as opções de importação
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(heading = t("ui_skl_options"))
        col.prop(self, "skl_bone_shape")
        col.prop(self, "skl_show_in_front")
        col.prop(self, "skl_only")

        col.separator()
        col.label(text = t("ui_skn_options"))

        # SKN options ficam desabilitadas quando so importa SKL
        skn_col = col.column()
        skn_col.enabled = not self.skl_only
        skn_col.prop(self, "skn_mesh_format")
        skn_col.prop(self, "skn_default_material_color")
        skn_col.prop(self, "skn_apply_seams")

        col.separator()
        col.prop(self, "skn_import_as_collection")

        col.separator()
        row = col.row()

        # Merge by Distance não se aplica quando cada submesh vira um objeto separado
        row.enabled = not self.skn_import_as_collection
        row.prop(self, "skn_merge_by_distance")
        sub = col.row()
        sub.enabled = self.skn_merge_by_distance and not self.skl_only and not self.skn_import_as_collection
        sub.prop(self, "skn_merge_threshold")

        col.separator()
        col.label(text = t("ui_defaults_via_prefs"), icon = 'PREFERENCES')

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
        self.skn_import_as_collection = prefs.skn_import_as_collection
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
            self.report({'ERROR'}, t("msg_skl_parse_error", e))
            return {'CANCELLED'}

        skl.flip()

        # Aplica Clip End no primeiro import (antes de criar qualquer objeto)
        apply_clip_end_on_first_import(context)

        # ___ Modo Collection ___
        if self.skn_import_as_collection:
            try:
                arm_obj = build_armature(skl, name + "_Armature")
            except Exception as e:
                self.report({'ERROR'}, t("msg_armature_create_error", e))
                return {'CANCELLED'}

            mark_imported(arm_obj)
            arm_obj["lol_influences"] = list(skl.influences)
            arm_obj.show_in_front = self.skl_show_in_front
            apply_bone_shapes(arm_obj, BoneShapeType(self.skl_bone_shape))

            if self.skl_only:
                bpy.ops.object.select_all(action = 'DESELECT')
                arm_obj.select_set(True)
                context.view_layer.objects.active = arm_obj

                self.report({'INFO'}, t("msg_skl_imported_container", name, len(skl.joints)))
                return {'FINISHED'}

            if not os.path.isfile(skn_path):
                self.report({'ERROR'}, t("msg_skn_not_found", skn_path))
                return {'CANCELLED'}

            try:
                skn = read_skn(skn_path)
            except Exception as e:
                self.report({'ERROR'}, t("msg_skn_parse_error", e))
                return {'CANCELLED'}

            skn.flip()

            try:
                mesh_objs = build_submesh_objects(
                    skn,
                    apply_weights = False,
                    mesh_format = self.skn_mesh_format,
                    apply_seams = self.skn_apply_seams,
                    use_gray_material = self.skn_default_material_color,
                )
            except Exception as e:
                self.report({'ERROR'}, t("msg_mesh_create_error", e))
                return {'CANCELLED'}

            bpy.ops.object.select_all(action = 'DESELECT')
            for sm, mesh_obj in zip(skn.submeshes, mesh_objs):
                context.collection.objects.link(mesh_obj)
                mark_imported(mesh_obj)

                # Fatia skn.vertices
                local_verts = skn.vertices[sm.start_vertex : sm.start_vertex + sm.vertex_count]
                try:
                    apply_skinning(mesh_obj, arm_obj, skl, local_verts)
                except Exception as e:
                    self.report({'ERROR'}, t("msg_skinning_error_named", mesh_obj.name, e))

                mesh_obj.select_set(True)

            # Merge by Distance não e usado em submesh

            arm_obj.select_set(True)
            context.view_layer.objects.active = arm_obj

            self.report({'INFO'}, t(
                "msg_imported_container",
                name,
                len(skl.joints),
                len(skn.vertices),
                len(mesh_objs),
            ))
            return {'FINISHED'}

        # ___ Armature ___
        try:
            arm_obj = build_armature(skl, name + "_Armature")
        except Exception as e:
            self.report({'ERROR'}, t("msg_armature_create_error", e))
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
                self.report({'ERROR'}, t("msg_skn_not_found", skn_path))
                return {'CANCELLED'}

            try:
                skn = read_skn(skn_path)
            except Exception as e:
                self.report({'ERROR'}, t("msg_skn_parse_error", e))
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
                self.report({'ERROR'}, t("msg_mesh_create_error", e))
                return {'CANCELLED'}

            try:
                apply_skinning(mesh_obj, arm_obj, skl, skn.vertices)
            except Exception as e:
                self.report({'ERROR'}, t("msg_skinning_error", e))

            if self.skn_merge_by_distance:
                from ..utils.mesh_utils import merge_by_distance
                merge_by_distance(mesh_obj, threshold = self.skn_merge_threshold)

            bpy.ops.object.select_all(action = 'DESELECT')
            arm_obj.select_set(True)
            mesh_obj.select_set(True)
            context.view_layer.objects.active = arm_obj

            self.report({'INFO'}, t("msg_imported_full", name, len(skl.joints), len(skn.vertices)))
        else:
            bpy.ops.object.select_all(action = 'DESELECT')
            arm_obj.select_set(True)
            context.view_layer.objects.active = arm_obj

            self.report({'INFO'}, t("msg_skl_imported", name, len(skl.joints)))

        return {'FINISHED'}
    