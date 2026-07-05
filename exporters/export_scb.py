import bpy
import unicodedata

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..i18n import t
from ..formats.scb import (
    write_scb_binary,
    unflip_point,
    invert_winding,
    SCB_FLAG_HAS_LOCAL_ORIGIN_LOCATOR_PIVOT,
    SCB_FLAG_HAS_VCP,
)

from ..formats.shared_mesh import (
    read_vertex_color_layer,
    read_alpha_attribute,
    merge_alpha,
    find_main_color_attribute,
    find_vcp_attribute,
    read_vcp_corner,
    enforce_material_name_limit,
    triangulate_to_temp_mesh,
    flip_uv,
    PLACEHOLDER_MATERIAL_NAME,
    is_placeholder_material,
    )


# Validações de pre exportação
# ===============================

_MAX_SCB_NAME_LEN = 127


def _sanitize_scb_name(name: str) -> tuple[str, str | None]:

    # Tratamento dos nomes de ColorAttribute
    if not name:
        return "", None

    sem_acento = unicodedata.normalize('NFKD', name).encode('ascii', errors='ignore').decode('ascii')
    ascii_name = "_".join(sem_acento.split())

    if not ascii_name:
        return "", t("msg_scb_name_dropped_non_ascii", name)

    if len(ascii_name) > _MAX_SCB_NAME_LEN:
        truncated = ascii_name[:_MAX_SCB_NAME_LEN]
        return truncated, t("msg_scb_name_truncated", name, len(name), _MAX_SCB_NAME_LEN, truncated)

    if ascii_name != name:
        return ascii_name, t("msg_scb_name_non_ascii_stripped", name, ascii_name)

    return ascii_name, None


def classify_scb_export_materials(mesh_obj: bpy.types.Object) -> tuple[set, bool]:

    # Analisa os poligonos da mesh
    real_names: set = set()
    has_no_material = False

    mesh = mesh_obj.data
    num_slots = len(mesh_obj.material_slots)

    for poly in mesh.polygons:
        mat = None
        if 0 <= poly.material_index < num_slots:
            mat = mesh_obj.material_slots[poly.material_index].material

        if mat is None or is_placeholder_material(mat):
            has_no_material = True
        else:
            real_names.add(mat.name)

    return real_names, has_no_material


def _validate_mesh_for_export_scb(mesh_obj: bpy.types.Object) -> tuple[bool, str]:

    # Validador dos materiais aplicados a mesh para proteger o usuario do usuario
    real_names, has_no_material = classify_scb_export_materials(mesh_obj)

    if len(real_names) > 1:
        return False, t("msg_scb_export_multi_material", mesh_obj.name, len(real_names))

    if real_names and has_no_material:
        return False, t("msg_scb_export_mixed_material", mesh_obj.name)

    return True, ""


# Extração da Mesh
# -------------------

def dump_scb_from_mesh(mesh_obj: bpy.types.Object) -> tuple[list, list, list | None, str, bool]:

    # ___ Triangulação ___
    temp_mesh = triangulate_to_temp_mesh(mesh_obj, "_lb_export_temp_scb")

    uv_layer = temp_mesh.uv_layers.active or (temp_mesh.uv_layers[0] if temp_mesh.uv_layers else None)
    num_materials = max(1, len(mesh_obj.material_slots))

    # ___ VCP ___
    vcp_layer = find_vcp_attribute(temp_mesh)
    has_vcp_data = vcp_layer is not None

    # ___ Pivô ___
    lx, ly, lz = mesh_obj.location

    # Unflip para o espaço do LoL
    vertices = [unflip_point(v.co.x + lx, v.co.y + ly, v.co.z + lz) for v in temp_mesh.vertices]

    faces = []
    for poly in temp_mesh.polygons:
        mat_idx = min(poly.material_index, num_materials - 1)

        mat_name = ""
        if mat_idx < len(mesh_obj.material_slots):
            mat = mesh_obj.material_slots[mat_idx].material
            if mat is not None and not is_placeholder_material(mat):
                mat_name = mat.name

        loop_indices = list(invert_winding(tuple(poly.loop_indices)))
        idxs = tuple(temp_mesh.loops[li].vertex_index for li in loop_indices)

        uvs = []
        for li in loop_indices:
            if uv_layer is not None:
                u, v = uv_layer.data[li].uv
                uvs.append(flip_uv(u, v))
            else:
                uvs.append((0.0, 0.0))

        vcp = None
        if vcp_layer is not None:
            vcp = tuple(read_vcp_corner(temp_mesh, vcp_layer, li) for li in loop_indices)

        faces.append({"indices": idxs, "material": mat_name, "uvs": tuple(uvs), "vcp": vcp})

    # ___ Vertex Colors ___
    color_layer = find_main_color_attribute(temp_mesh)
    vertex_colors = read_vertex_color_layer(temp_mesh, color_layer)
    color_name = color_layer.name if color_layer is not None else ""

    # ___ Alpha ___
    alphas = read_alpha_attribute(temp_mesh)
    if alphas is not None:
        if vertex_colors is None:
            vertex_colors = [(255, 255, 255, 255)] * len(temp_mesh.vertices)
        vertex_colors = merge_alpha(vertex_colors, alphas)

    bpy.data.meshes.remove(temp_mesh)

    return vertices, faces, vertex_colors, color_name, has_vcp_data


# Operador
# -----------

class LEAGUEBLENDER_OT_export_scb(Operator, ExportHelper):
    bl_idname = "leagueblender.export_scb"
    bl_label = t("op_export_scb_label")
    filename_ext = ".scb"
    filter_glob: StringProperty(default="*.scb", options={'HIDDEN'})

    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'ERROR'}, t("msg_export_select_mesh"))
            return {'CANCELLED'}

        ok, err = _validate_mesh_for_export_scb(mesh_obj)
        if not ok:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}

        try:
            export_warnings = []

            # Renomeia materiais com nome > 63 caracteres
            enforce_material_name_limit(mesh_obj, export_warnings)

            vertices, faces, vertex_colors, color_name, has_vcp_data = dump_scb_from_mesh(mesh_obj)

            color_name, name_warning = _sanitize_scb_name(color_name)
            if name_warning:
                export_warnings.append(name_warning)

            # ___ Central point ___
            lx, ly, lz = mesh_obj.location
            central_point = unflip_point(lx, ly, lz)

            flags = SCB_FLAG_HAS_LOCAL_ORIGIN_LOCATOR_PIVOT
            if has_vcp_data:
                flags |= SCB_FLAG_HAS_VCP

            write_scb_binary(
                vertices,
                faces,
                self.filepath,
                central_point = central_point,
                flags = flags,
                vertex_colors = vertex_colors,
                name = color_name,
            )

            for w in export_warnings:
                self.report({'WARNING'}, w)

            self.report({'INFO'}, t("msg_scb_exported", self.filepath, len(vertices), len(faces), mesh_obj.name))

            return {'FINISHED'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, t("msg_export_generic_error", e))
            return {'CANCELLED'}
        
