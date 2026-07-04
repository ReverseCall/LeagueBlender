""""
Talvez eu tenha exagerado um pouquinho nas verificações .w. como analisei apenas 7 arquivos SCB,
preferi assumir o pior cenario e preservar o maximo de informação possível. Isso deve tornar o codigo
mais resistente a variações e surpresas que eu possa ter deixado passar
"""

import os
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty

from ..preferences import get_prefs
from ..formats.scb import invert_winding
from ..utils.mesh_utils import merge_by_distance
from ..utils.scene_setup import apply_clip_end_on_first_import, mark_imported
from ..utils.uv_seams import compute_seam_edges_scb, apply_seams as _apply_seams_to_mesh

from ..formats.shared_mesh import (
    make_base_material,
    convert_to_quads,
    apply_weighted_normal,
    create_vertex_color_layer,
    create_alpha_attribute,
    flip_uv
)
from ..i18n import t

_DEFAULT_VCOLOR_NAME = "VertexColor"
_FALLBACK_UV_LAYER_NAME = "UVMap"


def _resolve_scb_uv_layer_name(scb) -> str:
    stripped_name = scb.name.strip() if scb.name else ""
    if stripped_name:
        return stripped_name

    materials = {f.material.strip() for f in scb.faces if f.material and f.material.strip()}
    if len(materials) == 1:
        return next(iter(materials))

    return _FALLBACK_UV_LAYER_NAME


# Leitor
# =========

# UVs devem ser buscados pelo vertex_index de cada loop (via dicionário)
# nunca pela posição/ordem do loop, pois o Blender pode reordenar os vértices
# da face ao normalizar o winding em from_pydata.

def _write_uvs_scb(mesh: bpy.types.Mesh, faces_orig, uv_layer):
    for _fi, (poly, face) in enumerate(zip(mesh.polygons, faces_orig)):

        # Monta mapa vertex_index -> uv para esta face
        uv_by_vert = {
            face.indices[k]: face.uvs[k]
            for k in range(3)
        }
        for loop_idx in poly.loop_indices:
            vi = mesh.loops[loop_idx].vertex_index
            uv = uv_by_vert.get(vi)
            if uv is not None:
                uv_layer.data[loop_idx].uv = flip_uv(*uv)


# Construção SCB
# -------------------

def build_mesh_from_scb(scb, name: str, *, mesh_format: str | None = None, use_gray_material: bool | None = None, apply_seams: bool | None = None) -> bpy.types.Object:

    #Constrói um bpy.Object a partir de um SCBFile já flipado, filtrando faces degeneradas
    prefs = get_prefs(bpy.context)

    _mesh_format = mesh_format if mesh_format is not None else prefs.mesh_format
    _apply_seams = apply_seams if apply_seams is not None else prefs.apply_seams

    mesh = bpy.data.meshes.new(name)
    obj  = bpy.data.objects.new(name, mesh)

    # ___ Pivô (central_point) ___
    cx, cy, cz = scb.central_point
    positions = [(px - cx, py - cy, pz - cz) for px, py, pz in (v.position for v in scb.vertices)]
    n_verts = len(positions)

    valid_faces = [
        f for f in scb.faces
        if f.indices[0] != f.indices[1]
        and f.indices[1] != f.indices[2]
        and f.indices[0] != f.indices[2]
        and f.indices[0] < n_verts
        and f.indices[1] < n_verts
        and f.indices[2] < n_verts
    ]

    faces_idx = [invert_winding(f.indices) for f in valid_faces]

    mesh.from_pydata(positions, [], faces_idx)
    mesh.update()

    # ___ Nome da UV Layer ___
    uv_layer_name = _resolve_scb_uv_layer_name(scb)

    # Materiais
    mat_name_to_idx: dict = {}
    for fi, face in enumerate(valid_faces):
        m = face.material
        if m not in mat_name_to_idx:
            mat = make_base_material(m, uv_layer_name=uv_layer_name, use_gray=use_gray_material)
            mesh.materials.append(mat)
            mat_name_to_idx[m] = len(mesh.materials) - 1
        mesh.polygons[fi].material_index = mat_name_to_idx[m]

    uv_layer = mesh.uv_layers.new(name=uv_layer_name)
    _write_uvs_scb(mesh, valid_faces, uv_layer)
    uv_layer.active = True

    # ___ Vertex Colors ___
    if scb.vertex_colors:
        rgb_values = {(b, g, r) for b, g, r, a in scb.vertex_colors}
        has_real_color = rgb_values != {(255, 255, 255)}

        if has_real_color:
            stripped_name = scb.name.strip() if scb.name else ""

            if stripped_name and stripped_name != _DEFAULT_VCOLOR_NAME:
                color_name = stripped_name
            else:
                color_name = _DEFAULT_VCOLOR_NAME
            create_vertex_color_layer(mesh, color_name, scb.vertex_colors)

        # Alpha separado numa color attribute "Alpha" (tom de cinza), editavel no Vertex Paint
        alphas = [c[3] for c in scb.vertex_colors]  # (b, g, r, a) -> a
        create_alpha_attribute(mesh, alphas)

    mesh.update()

    # ___ Seams ___
    if _apply_seams:
        seam_edges = compute_seam_edges_scb(valid_faces)
        _apply_seams_to_mesh(mesh, seam_edges)

    # Conversão para Quads
    if _mesh_format == 'QUADS':
        convert_to_quads(mesh)

    # ___ WeightedNormal ___
    apply_weighted_normal(obj)

    obj.location = (cx, cy, cz)

    return obj


# Operador SCB
# ----------------

class LEAGUEBLENDER_OT_import_scb(Operator, ImportHelper):

    bl_idname = "leagueblender.import_scb"
    bl_label = t("op_import_scb_label")
    bl_description = t("op_import_scb_desc")
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".scb"
    filter_glob: StringProperty(default="*.scb", options={'HIDDEN'})

    # Opções locais - sobrescrevem as preferências globais nesta importação
    # ------------------------------------------------------------------------

    scb_mesh_format: EnumProperty(
        name=t("prop_scb_mesh_format_name"),
        description=t("prop_scb_mesh_format_desc"),
        items=[
            ('TRIS',  t("prop_skn_mesh_format_tris_name"),  t("prop_skn_mesh_format_tris_desc")),
            ('QUADS', t("prop_skn_mesh_format_quads_name"), t("prop_skn_mesh_format_quads_desc")),
        ],
        default='TRIS',
    )

    scb_default_material_color: BoolProperty(
        name=t("prop_skn_default_material_color_name"),
        description=t("prop_skn_default_material_color_desc"),
        default=True,
    )

    scb_apply_seams: BoolProperty(
        name=t("prop_skn_apply_seams_name"),
        description=t("prop_skn_apply_seams_desc"),
        default=False,
    )

    scb_merge_by_distance: BoolProperty(
        name=t("prop_skn_merge_by_distance_name"),
        description=t("prop_skn_merge_by_distance_desc"),
        default=False,
    )

    scb_merge_threshold: FloatProperty(
        name=t("prop_skn_merge_threshold_name"),
        description=t("prop_skn_merge_threshold_desc"),
        default=0.001,
        min=0.00001,
        max=0.1,
        precision=5,
        step=1,
        unit='LENGTH',
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(heading=t("ui_scb_options"))
        col.prop(self, "scb_mesh_format")
        col.prop(self, "scb_default_material_color")
        col.prop(self, "scb_apply_seams")

        col.separator()
        row = col.row()
        row.prop(self, "scb_merge_by_distance")
        sub = col.row()
        sub.enabled = self.scb_merge_by_distance
        sub.prop(self, "scb_merge_threshold")

        col.separator()
        col.label(text=t("ui_defaults_via_prefs"), icon='PREFERENCES')

    def invoke(self, context, event):

        # globais compartilhadas com o SKN
        prefs = get_prefs(context)
        self.scb_mesh_format = prefs.mesh_format
        self.scb_default_material_color = prefs.default_material_color
        self.scb_apply_seams = prefs.apply_seams
        self.scb_merge_by_distance = prefs.merge_by_distance
        self.scb_merge_threshold = prefs.merge_threshold
        return super().invoke(context, event)

    def execute(self, context):
        path = self.filepath
        ext = os.path.splitext(path)[1].lower()
        name = os.path.splitext(os.path.basename(path))[0]

        apply_clip_end_on_first_import(context)

        if ext == '.scb':
            obj = self._import_scb(path, name, context)
        else:
            self.report({'ERROR'}, t("msg_scb_unknown_ext", ext))
            return {'CANCELLED'}

        if obj is None:
            return {'CANCELLED'}

        context.collection.objects.link(obj)
        mark_imported(obj)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # ___ Merge ___
        if self.scb_merge_by_distance:
            merge_by_distance(obj, threshold=self.scb_merge_threshold)

        return {'FINISHED'}


    # Helpers internos
    # ------------------

    def _import_scb(self, path: str, name: str, context) -> bpy.types.Object | None:
        from ..formats.scb import read_scb

        try:
            scb = read_scb(path)
        except Exception as e:
            self.report({'ERROR'}, t("msg_failed_read_scb", e))
            return None

        scb.flip()

        try:
            obj = build_mesh_from_scb(
                scb,
                name,
                mesh_format = self.scb_mesh_format,
                use_gray_material = self.scb_default_material_color,
                apply_seams = self.scb_apply_seams,
            )
        except Exception as e:
            self.report({'ERROR'}, t("msg_failed_build_mesh_scb", e))
            return None

        self.report({'INFO'}, t("msg_scb_imported", name, len(scb.vertices), len(scb.faces), scb.version_str))

        # ___ VCP (cor por face-corner) ___
        # Não achei nem uma referencia disso nos binarios analizados. Por isso vou deixar um aviso para caso alguem achar
        # me passar para eu analizar
        vcp_face_count = sum(1 for f in scb.faces if f.vcp is not None)
        if vcp_face_count > 0:
            self.report({'WARNING'}, t("msg_scb_vcp_unsupported", vcp_face_count))

        return obj
    
