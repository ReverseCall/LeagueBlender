"""
Operador Blender para importar arquivos SKN do LoL
"""

import os
import bpy
import bmesh
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

from ..preferences import get_prefs
from ..formats.skn import read_skn, SKNFile
from ..utils.mesh_utils import merge_by_distance
from ..utils.scene_setup import apply_clip_end_on_first_import, mark_imported
from ..utils.uv_seams import compute_seam_edges, apply_seams as _apply_seams_to_mesh


# UVs de loops fora da submesh ativa jogadas para fora da janela.
# a um ponto impostor entre nos :3
_UV_STUB = (-10.0, -10.0)


# Material
# ===========

def _srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

_LINEAR_VALUE = _srgb_to_linear(0.158220)


def make_skn_material(mat_name: str, uv_layer_name: str, use_gray: bool = True) -> bpy.types.Material:
    mat = bpy.data.materials.new(name = mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)

    if use_gray:
        color = (_LINEAR_VALUE, _LINEAR_VALUE, _LINEAR_VALUE, 1.0)
    else:
        color = (0.8, 0.8, 0.8, 1.0)   # Branco padrão do Blender

    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0

    uv_node = nodes.new("ShaderNodeUVMap")
    uv_node.location = (-200, -200)
    uv_node.uv_map = uv_layer_name

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = color
    return mat


# WeightedNormal
# -----------------

def _apply_weighted_normal(obj: bpy.types.Object):

    # Aplica o modificador WeightedNormal ao objeto
    wn = obj.modifiers.new(name = "WeightedNormal", type = 'WEIGHTED_NORMAL')
    try:
        if hasattr(wn, "weighting_mode"):
            wn.weighting_mode = 'FACE_AREA'
        elif hasattr(wn, "mode"):
            wn.mode = 'FACE_AREA'

        wn.weight = 50

        if hasattr(wn, "thresh"):
            wn.thresh = 0.01
        elif hasattr(wn, "threshold"):
            wn.threshold = 0.01
    except Exception as e:
        print(f"Aviso: Não foi possivel configurar todas as opções do WeightedNormal: {e}")


# Construção da mesh
# ---------------------

def build_mesh(
    skn: SKNFile,
    name: str,
    apply_weights: bool = True,
    *,
    mesh_format: str | None = None,
    apply_seams: bool | None = None,
    use_gray_material: bool | None = None,
) -> bpy.types.Object:
    """
    Constroi um bpy.Object a partir de um SKNFile ja flipado.

    Os parametros opcionais (mesh_format, apply_seams, use_gray_material)
    sobrescrevem as preferências globais quando fornecidos pelo operador de
    importação. Se forem None, o valor vem das preferências do addon.
    """
    prefs = get_prefs(bpy.context)

    # Resolve cada opção. valor local (operador) > preferência global
    _mesh_format = mesh_format if mesh_format is not None else prefs.skn_mesh_format
    _apply_seams = apply_seams if apply_seams is not None else prefs.skn_apply_seams
    _use_gray_material = use_gray_material if use_gray_material is not None else prefs.skn_default_material_color

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    # ___ Geometria Base (Triangulos) ___
    positions = [(v.position[0], -v.position[2], v.position[1]) for v in skn.vertices]
    faces = [(skn.indices[i], skn.indices[i + 2], skn.indices[i + 1]) for i in range(0, len(skn.indices), 3)]
    mesh.from_pydata(positions, [], faces)
    mesh.update()

    # ___ Atribuição de Materiais Inicial ___
    for sm_idx, sm in enumerate(skn.submeshes):
        mat = make_skn_material(sm.name, sm.name, use_gray = _use_gray_material)
        mesh.materials.append(mat)

        first_face = sm.start_index // 3
        for f in range(sm.face_count):
            if (first_face + f) < len(mesh.polygons):
                mesh.polygons[first_face + f].material_index = sm_idx

    # ___ Conversão para Quads ___
    if _mesh_format == 'QUADS':
        bm = bmesh.new()
        bm.from_mesh(mesh)
        try:
            bmesh.ops.join_triangles(
                bm,
                faces = bm.faces,
                angle_face_threshold = 0.698132,
                angle_shape_threshold = 0.698132
            )
        except:
            pass
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    # ___ UV Layers e Dados de Loops ___
    uv_layers = []
    for sm in skn.submeshes:
        layer = mesh.uv_layers.get(sm.name)
        if not layer:
            layer = mesh.uv_layers.new(name=sm.name)
        uv_layers.append(layer)

    total_loops = len(mesh.loops)

    for sm_idx, (sm, uv_layer) in enumerate(zip(skn.submeshes, uv_layers)):

        # joga todos os loops desta camada para fora da ilha
        for li in range(total_loops):
            uv_layer.data[li].uv = _UV_STUB

        # Escreve os UVs reais apenas nos loops que pertencem a esta submesh
        for poly in mesh.polygons:
            if poly.material_index != sm_idx:
                continue
            for loop_idx in poly.loop_indices:
                vi = mesh.loops[loop_idx].vertex_index
                u, v = skn.vertices[vi].uv
                uv_layer.data[loop_idx].uv = (u, 1.0 - v)

    if mesh.uv_layers:
        mesh.uv_layers[0].active = True

    # ___ Normais Customizadas ___
    loop_normals = []
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            vi = mesh.loops[loop_idx].vertex_index
            n = skn.vertices[vi].normal
            loop_normals.append((n[0], -n[2], n[1]))
    mesh.normals_split_custom_set(loop_normals)
    if hasattr(mesh, "use_auto_smooth"):
        mesh.use_auto_smooth = True

    # ___ WeightedNormal ___
    _apply_weighted_normal(obj)

    # ___ Seams ___
    if _apply_seams:
        seam_edges = compute_seam_edges(skn)
        _apply_seams_to_mesh(mesh, seam_edges)

    # ___ Vertex Groups ___
    if apply_weights:
        bone_groups: dict[int, bpy.types.VertexGroup] = {}
        for vi, v in enumerate(skn.vertices):
            for bi, bw in zip(v.influences, v.weights):
                if bw > 0.0:
                    if bi not in bone_groups:
                        bone_groups[bi] = obj.vertex_groups.new(name = f"bone_{bi:03d}")
                    bone_groups[bi].add([vi], bw, 'ADD')

    mesh.update()
    return obj


# Operador
# -----------

class LEAGUEBLENDER_OT_import_skn(Operator, ImportHelper):

    # Importa um modelo SKN do LoL
    bl_idname = "leagueblender.import_skn"
    bl_label = "League Mesh (.skn)"
    bl_description = "Importa um Skinned Mesh (.skn) do League of Legends"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".skn"
    filter_glob: StringProperty(default = "*.skn", options = {'HIDDEN'})

    # Opções locais - sobrescrevem as preferências globais nesta importação
    # ------------------------------------------------------------------------

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

    skn_apply_vertex_groups: BoolProperty(
        name="Import Vertex Groups",
        description=(
            "Groups of vertices matter with skinning weights."
        ),
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

    def draw(self, context):

        # Painel lateral do file browser com as opções de importação
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_prefs(context)

        col = layout.column(heading = "SKN Options")
        col.prop(self, "skn_mesh_format")
        col.prop(self, "skn_default_material_color")
        col.prop(self, "skn_apply_seams")
        col.prop(self, "skn_apply_vertex_groups")

        col.separator()
        col.prop(self, "skn_merge_by_distance")
        sub = col.row()
        sub.enabled = self.skn_merge_by_distance
        sub.prop(self, "skn_merge_threshold")

        col.separator()
        col.label(text = "Defaults via Addon Preferences", icon = 'PREFERENCES')

    def invoke(self, context, event):

        # Pre preenche as opções locais com os valores das preferências globais
        prefs = get_prefs(context)
        self.skn_mesh_format = prefs.skn_mesh_format
        self.skn_apply_seams = prefs.skn_apply_seams
        self.skn_merge_by_distance = prefs.skn_merge_by_distance
        self.skn_merge_threshold = prefs.skn_merge_threshold
        self.skn_default_material_color = prefs.skn_default_material_color
        return super().invoke(context, event)

    def execute(self, context):
        path = self.filepath
        name = os.path.splitext(os.path.basename(path))[0]

        try:
            skn = read_skn(path)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read SKN: {e}")
            return {'CANCELLED'}

        skn.flip()

        try:
            obj = build_mesh(
                skn,
                name,
                apply_weights = self.skn_apply_vertex_groups,
                mesh_format = self.skn_mesh_format,
                apply_seams = self.skn_apply_seams,
                use_gray_material = self.skn_default_material_color,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Failed to build mesh: {e}")
            return {'CANCELLED'}

        apply_clip_end_on_first_import(context)
        context.collection.objects.link(obj)
        mark_imported(obj)
        bpy.ops.object.select_all(action = 'DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # ___ Merge ___
        if self.skn_merge_by_distance:
            merge_by_distance(obj, threshold = self.skn_merge_threshold)

        self.report({'INFO'},
            f"SKN importado: {name} - "
            f"{len(skn.vertices):,} verts, "
            f"{len(skn.indices) // 3:,} faces, "
            f"{len(skn.submeshes)} submesh(es)"
        )
        return {'FINISHED'}