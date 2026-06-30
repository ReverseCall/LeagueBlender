import os
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

from ..preferences import get_prefs
from ..formats.skn import read_skn, SKNFile
from ..formats.shared_mesh import make_base_material, convert_to_quads, apply_weighted_normal

from ..utils.mesh_utils import merge_by_distance
from ..utils.scene_setup import apply_clip_end_on_first_import, mark_imported
from ..utils.uv_seams import compute_seam_edges, apply_seams as _apply_seams_to_mesh
from ..i18n import t


# UVs de loops fora da submesh ativa jogadas para fora da janela.
# a um ponto impostor entre nos :3
_UV_STUB = (-10.0, -10.0)


# Material
# ===========

def make_skn_material(mat_name: str, uv_layer_name: str, use_gray: bool = True) -> bpy.types.Material:
    return make_base_material(mat_name, uv_layer_name=uv_layer_name, use_gray=use_gray)


# WeightedNormal
# -----------------

def _apply_weighted_normal(obj: bpy.types.Object):
    apply_weighted_normal(obj)


# Pos-processamento
# --------------------

def _convert_to_quads(mesh: bpy.types.Mesh):
    convert_to_quads(mesh)


def _apply_vertex_groups(obj: bpy.types.Object, vertices: list):

    # Cria os vertex groups bone_NNN a partir das influences/weights brutas do SKN
    # vertices[i] precisa corresponder 1:1 com obj.data.vertices[i]
    bone_groups: dict[int, bpy.types.VertexGroup] = {}
    for vi, v in enumerate(vertices):
        for bi, bw in zip(v.influences, v.weights):
            if bw > 0.0:
                if bi not in bone_groups:
                    bone_groups[bi] = obj.vertex_groups.new(name = f"bone_{bi:03d}")
                bone_groups[bi].add([vi], bw, 'ADD')


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
    _mesh_format = mesh_format if mesh_format is not None else prefs.mesh_format
    _apply_seams = apply_seams if apply_seams is not None else prefs.apply_seams
    _use_gray_material = use_gray_material if use_gray_material is not None else prefs.default_material_color

    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    # ___ Geometria Base (Triangulos) ___
    positions = [(v.position[0], -v.position[2], v.position[1]) for v in skn.vertices]
    faces = [(skn.indices[i], skn.indices[i + 2], skn.indices[i + 1]) for i in range(0, len(skn.indices), 3)]
    mesh.from_pydata(positions, [], faces)
    mesh.update()

    # Atribuição de Materiais Inicial
    for sm_idx, sm in enumerate(skn.submeshes):
        mat = make_skn_material(sm.name, sm.name, use_gray = _use_gray_material)
        mesh.materials.append(mat)

        first_face = sm.start_index // 3
        for f in range(sm.face_count):
            if (first_face + f) < len(mesh.polygons):
                mesh.polygons[first_face + f].material_index = sm_idx

    # Conversão para Quads
    if _mesh_format == 'QUADS':
        _convert_to_quads(mesh)

    # UV Layers e Dados de Loops
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

    # Normais Customizadas
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
        _apply_vertex_groups(obj, skn.vertices)

    mesh.update()
    return obj


# Construção por submesh
# -------------------------

def build_submesh_objects(skn: SKNFile, apply_weights: bool = True, *, mesh_format: str | None = None, apply_seams: bool | None = None, use_gray_material: bool | None = None,) -> list:
    
    prefs = get_prefs(bpy.context)

    # Resolve cada opção. valor local
    _mesh_format = mesh_format if mesh_format is not None else prefs.mesh_format
    _apply_seams = apply_seams if apply_seams is not None else prefs.apply_seams
    _use_gray_material = use_gray_material if use_gray_material is not None else prefs.default_material_color

    objs = []

    for sm in skn.submeshes:
        mesh = bpy.data.meshes.new(sm.name)
        obj = bpy.data.objects.new(sm.name, mesh)

        # Fatia local.
        local_verts = skn.vertices[sm.start_vertex: sm.start_vertex + sm.vertex_count]
        local_indices = skn.indices[sm.start_index: sm.start_index + sm.index_count]

        # ___ Geometria Base (Triangulos) ___
        positions = [(v.position[0], -v.position[2], v.position[1]) for v in local_verts]
        faces = [
            (local_indices[i] - sm.start_vertex, local_indices[i + 2] - sm.start_vertex, local_indices[i + 1] - sm.start_vertex)
            for i in range(0, len(local_indices), 3)
        ]
        mesh.from_pydata(positions, [], faces)
        mesh.update()

        # ___ Material ___
        mat = make_skn_material(sm.name, sm.name, use_gray = _use_gray_material)
        mesh.materials.append(mat)

        # Conversão para Quads
        if _mesh_format == 'QUADS':
            _convert_to_quads(mesh)

        # UV Layer
        uv_layer = mesh.uv_layers.new(name = sm.name)
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vi = mesh.loops[loop_idx].vertex_index
                u, v = local_verts[vi].uv
                uv_layer.data[loop_idx].uv = (u, 1.0 - v)
        uv_layer.active = True

        # ___ Normais ___
        loop_normals = []
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vi = mesh.loops[loop_idx].vertex_index
                n = local_verts[vi].normal
                loop_normals.append((n[0], -n[2], n[1]))
        mesh.normals_split_custom_set(loop_normals)
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True

        # ___ WeightedNormal ___
        _apply_weighted_normal(obj)

        # ___ Seams ___
        if _apply_seams:

            # Reusa compute_seam_edges com uma "fatia" local do SKN
            local_skn = SKNFile(
                version_major = skn.version_major,
                version_minor = skn.version_minor,
                vertex_type = skn.vertex_type,
                submeshes = [],
                indices = [idx - sm.start_vertex for idx in local_indices],
                vertices = local_verts,
            )
            seam_edges = compute_seam_edges(local_skn)
            _apply_seams_to_mesh(mesh, seam_edges)

        # ___ Vertex Groups ___
        if apply_weights:
            _apply_vertex_groups(obj, local_verts)

        mesh.update()
        objs.append(obj)

    return objs


# Operador SKN
# -----------

class LEAGUEBLENDER_OT_import_skn(Operator, ImportHelper):

    # Importa um modelo SKN do LoL
    bl_idname = "leagueblender.import_skn"
    bl_label = t("op_import_skn_label")
    bl_description = t("op_import_skn_desc")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".skn"
    filter_glob: StringProperty(default = "*.skn", options = {'HIDDEN'})

    # Opções locais - sobrescrevem as preferências globais nesta importação
    # ------------------------------------------------------------------------

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

    skn_apply_vertex_groups: BoolProperty(
        name=t("prop_skn_apply_vertex_groups_name"),
        description=t("prop_skn_apply_vertex_groups_desc"),
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
        description=t("prop_skn_import_as_collection_desc_skn"),
        default=False,
    )

    def draw(self, context):

        # Painel lateral do file browser com as opções de importação
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_prefs(context)

        col = layout.column(heading = t("ui_skn_options"))
        col.prop(self, "skn_mesh_format")
        col.prop(self, "skn_default_material_color")
        col.prop(self, "skn_apply_seams")
        col.prop(self, "skn_apply_vertex_groups")

        col.separator()
        col.prop(self, "skn_import_as_collection")

        col.separator()
        row = col.row()

        # Merge by Distance não se aplica quando cada submesh vira um objeto separado
        row.enabled = not self.skn_import_as_collection
        row.prop(self, "skn_merge_by_distance")
        sub = col.row()
        sub.enabled = self.skn_merge_by_distance and not self.skn_import_as_collection
        sub.prop(self, "skn_merge_threshold")

        col.separator()
        col.label(text = t("ui_defaults_via_prefs"), icon = 'PREFERENCES')

    def invoke(self, context, event):

        # Pre preenche as opções locais com os valores das preferências globais
        prefs = get_prefs(context)
        self.skn_mesh_format = prefs.mesh_format
        self.skn_apply_seams = prefs.apply_seams
        self.skn_merge_by_distance = prefs.merge_by_distance
        self.skn_merge_threshold = prefs.merge_threshold
        self.skn_default_material_color = prefs.default_material_color
        self.skn_import_as_collection = prefs.skn_import_as_collection
        return super().invoke(context, event)

    def execute(self, context):
        path = self.filepath
        name = os.path.splitext(os.path.basename(path))[0]

        try:
            skn = read_skn(path)
        except Exception as e:
            self.report({'ERROR'}, t("msg_failed_read_skn", e))
            return {'CANCELLED'}

        skn.flip()

        apply_clip_end_on_first_import(context)

        # ___ Modo Collection ___
        if self.skn_import_as_collection:
            try:
                objs = build_submesh_objects(
                    skn,
                    apply_weights = self.skn_apply_vertex_groups,
                    mesh_format = self.skn_mesh_format,
                    apply_seams = self.skn_apply_seams,
                    use_gray_material = self.skn_default_material_color,
                )
            except Exception as e:
                self.report({'ERROR'}, t("msg_failed_build_mesh", e))
                return {'CANCELLED'}

            collection = bpy.data.collections.new(name)
            context.collection.children.link(collection)

            bpy.ops.object.select_all(action = 'DESELECT')
            for obj in objs:
                collection.objects.link(obj)
                mark_imported(obj)
                obj.select_set(True)

            if objs:
                context.view_layer.objects.active = objs[0]

            self.report({'INFO'}, t(
                "msg_skn_imported_collection",
                name,
                len(skn.vertices),
                len(skn.indices) // 3,
                len(skn.submeshes),
            ))
            return {'FINISHED'}

        # Modo padrão
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
            self.report({'ERROR'}, t("msg_failed_build_mesh", e))
            return {'CANCELLED'}

        context.collection.objects.link(obj)
        mark_imported(obj)
        bpy.ops.object.select_all(action = 'DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # ___ Merge ___
        if self.skn_merge_by_distance:
            merge_by_distance(obj, threshold = self.skn_merge_threshold)

        self.report({'INFO'}, t(
            "msg_skn_imported",
            name,
            len(skn.vertices),
            len(skn.indices) // 3,
            len(skn.submeshes),
        ))
        return {'FINISHED'}