import os
import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..i18n import t
from ..formats.skn import write_skn_binary
from .export_skl import dump_skl_from_armature
from ..formats.skl import write_skl_binary
from ..formats.shared_mesh import validate_material_slots, enforce_material_name_limit, triangulate_to_temp_mesh

# UV fora da janela
_UV_STUB_X = -10.0


# Mapeamento de bones
# ======================

def _build_bone_to_idx(arm_obj: bpy.types.Object) -> dict:

    # Agora arm_obj sempre existe
    arm_bones = list(arm_obj.data.bones)

    # Ordena por lol_id se disponivel
    has_lol_id = all("lol_id" in b for b in arm_bones)
    if has_lol_id:
        arm_bones.sort(key=lambda b: int(b["lol_id"]))

    real_id_map = {b.name: i for i, b in enumerate(arm_bones)}

    raw_influences = arm_obj.get("lol_influences")
    if raw_influences and len(raw_influences) > 0:
        real_to_raw = {}
        for raw_id, real_id in enumerate(raw_influences):

            # Mantem so o primeiro raw_id para cada real_id
            if real_id not in real_to_raw:
                real_to_raw[real_id] = raw_id

        bone_to_raw = {}
        for name, real_id in real_id_map.items():
            if real_id in real_to_raw:
                bone_to_raw[name] = real_to_raw[real_id]
            else:

                # Joint fora da tabela influences. usa real_id como fallback
                bone_to_raw[name] = real_id
        return bone_to_raw
    else:

        # Sem tabela de remapeamento. raw_id == real_id
        return real_id_map


def _get_vertex_weights(v_idx: int, mesh_obj: bpy.types.Object, bone_to_idx: dict):

    # Mantem os 4 pesos mais altos, normaliza e empacota como bytes + floats | Nota: Melhore isso no futuro.
    vert = mesh_obj.data.vertices[v_idx]
    valid_groups = []
    for g in vert.groups:
        vg_name = mesh_obj.vertex_groups[g.group].name
        if vg_name in bone_to_idx:
            valid_groups.append((bone_to_idx[vg_name], g.weight))

    valid_groups.sort(key=lambda x: x[1], reverse=True)
    valid_groups = valid_groups[:4]

    influences = [0, 0, 0, 0]
    weights = [0.0, 0.0, 0.0, 0.0]

    for k, (idx, w) in enumerate(valid_groups):
        influences[k] = idx
        weights[k] = w

    total = sum(weights)
    if total > 0.0:
        weights = [w / total for w in weights]
    else:
        weights = [1.0, 0.0, 0.0, 0.0]

    return bytes(influences), tuple(weights)


# Validações de pre-exportação
# -------------------------------

def _sync_uv_layer_names(mesh_obj: bpy.types.Object, warnings: list) -> tuple[bool, str]:

    # ___ Tratamento UV layers ___
    materials = [slot.material for slot in mesh_obj.material_slots if slot.material is not None]
    uv_layers = mesh_obj.data.uv_layers

    if len(uv_layers) == 0:
        return True, ""

    """
    Caso simples: 1 material, 1 UV layer
    Renomeia sempre, mesmo que a UV ja tenha um nome "valido" diferente
    """
    if len(materials) == 1 and len(uv_layers) == 1:
        mat = materials[0]
        uv = uv_layers[0]
        if uv.name != mat.name:
            old_uv_name = uv.name
            uv.name = mat.name
            warnings.append(t("msg_uv_renamed", old_uv_name, mat.name, mesh_obj.name))
        return True, ""

    if len(uv_layers) <= 1:
        return True, ""

    # Caso multi-material + multi-UV
    uv_names = {uv.name for uv in uv_layers}
    mat_names = {mat.name for mat in materials}

    orphan_materials = [mat for mat in materials if mat.name not in uv_names]
    leftover_uvs = [uv for uv in uv_layers if uv.name not in mat_names]

    if not orphan_materials:

        # Todo material ja tem UV
        return True, ""

    if len(orphan_materials) == 1 and len(leftover_uvs) == 1:

        # Unico par possivel -> renomeia por eliminação
        mat = orphan_materials[0]
        uv = leftover_uvs[0]
        old_uv_name = uv.name
        uv.name = mat.name
        warnings.append(t("msg_uv_renamed_elimination", old_uv_name, mat.name, mesh_obj.name))
        return True, ""

    # Bloqueio de exportação caso muitas UVs estiverem erradas
    orphan_names = ", ".join(f"\"{m.name}\"" for m in orphan_materials)
    leftover_names = ", ".join(f"\"{u.name}\"" for u in leftover_uvs) if leftover_uvs else t("msg_no_leftover_uvs")
    return False, t("msg_uv_ambiguous", mesh_obj.name, orphan_names, leftover_names)


def _validate_mesh_for_export(mesh_obj: bpy.types.Object) -> tuple[bool, str]:

    arm_obj = None
    for mod in mesh_obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            arm_obj = mod.object
            break

    if arm_obj is None:
        return False, t("msg_export_no_armature", mesh_obj.name)

    return validate_material_slots(mesh_obj)


# Reconhecimento de submeshes por armature
# --------------------------------------------

def _find_meshes_for_armature(arm_obj: bpy.types.Object, context) -> list:

    # tratamento de doda sas meshs com armatures para união em um unico arquivo
    meshes = []
    for obj in context.scene.objects:
        if obj.type != 'MESH':
            continue
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object == arm_obj:
                meshes.append(obj)
                break

    meshes.sort(key=lambda o: o.name)
    return meshes


# Merge de submeshes por nome
# ------------------------------

def _merge_submeshes_by_name(submeshes: list) -> list:

    # Une submeshes com o mesmo nome em uma unica entrada
    merged = {}
    merged_order = []

    for sm in submeshes:
        name = sm["name"]
        if name not in merged:
            merged[name] = {"name": name, "verts": [], "indices": []}
            merged_order.append(name)

        offset = len(merged[name]["verts"])
        merged[name]["verts"].extend(sm["verts"])
        merged[name]["indices"].extend(idx + offset for idx in sm["indices"])

    return [merged[name] for name in merged_order]


# Extração da Mesh
# -------------------

def dump_skn_from_mesh(mesh_obj: bpy.types.Object, bone_to_idx: dict) -> list:

    # ___ Triangulação ___
    temp_mesh = triangulate_to_temp_mesh(mesh_obj, "_lb_export_temp")

    uv_layers = temp_mesh.uv_layers
    num_materials = max(1, len(mesh_obj.material_slots))
    submesh_verts = [[] for _ in range(num_materials)]
    submesh_indices = [[] for _ in range(num_materials)]
    vert_cache = [{} for _ in range(num_materials)]

    for poly in temp_mesh.polygons:
        mat_idx = min(poly.material_index, num_materials - 1)

        loop_indices = list(poly.loop_indices)

        """
        Inverte a winding order (Blender -> LoL)
        Checa se os 3 vertices são distintos antes de inverter
        sem isso faces degeneradas da triangulização causam alternancia
        de CCW/CW (não buga dentrod do jogo, mas bugou no Ultimate Unwrap3D)
        """
        v0 = temp_mesh.loops[loop_indices[0]].vertex_index
        v1 = temp_mesh.loops[loop_indices[1]].vertex_index
        v2 = temp_mesh.loops[loop_indices[2]].vertex_index

        if v0 != v1 and v1 != v2 and v0 != v2:
            loop_indices = [loop_indices[0], loop_indices[2], loop_indices[1]]

        for loop_idx in loop_indices:
            loop = temp_mesh.loops[loop_idx]
            v_idx = loop.vertex_index
            co = temp_mesh.vertices[v_idx].co

            # Prefere corner_normals sobre loop.normal
            corner_normal = temp_mesh.corner_normals[loop_idx].vector
            normal = (corner_normal.x, corner_normal.y, corner_normal.z)

            # ___ Remontagem de UV ___
            # Prioridade. layer com o nome do material -> qualquer layer valida -> layer 0
            final_u, final_v = 0.0, 0.0
            found_valid_uv = False

            mat_name = ""
            if mat_idx < len(mesh_obj.material_slots) and mesh_obj.material_slots[mat_idx].material:
                mat_name = mesh_obj.material_slots[mat_idx].material.name

            target_layer = uv_layers.get(mat_name)
            if target_layer:
                uv = target_layer.data[loop_idx].uv
                if uv[0] > _UV_STUB_X + 1.0:
                    final_u, final_v = uv[0], 1.0 - uv[1]
                    found_valid_uv = True

            if not found_valid_uv:
                for layer in uv_layers:
                    uv = layer.data[loop_idx].uv
                    if uv[0] > _UV_STUB_X + 1.0:
                        final_u, final_v = uv[0], 1.0 - uv[1]
                        found_valid_uv = True
                        break

            if not found_valid_uv and uv_layers:
                uv = uv_layers[0].data[loop_idx].uv
                final_u, final_v = uv[0], 1.0 - uv[1]

            # Conversão (Blender -> LoL)
            pos_x = -co.x
            pos_y = co.z
            pos_z = -co.y

            norm_x = normal[0]
            norm_y = -normal[1]
            norm_z = normal[2]

            # Cache key baseada em posição + UV. normais são armazenadas no vertice
            key = (v_idx, round(final_u, 4), round(final_v, 4))

            if key in vert_cache[mat_idx]:
                local_idx = vert_cache[mat_idx][key]
            else:
                infl, wts = _get_vertex_weights(v_idx, mesh_obj, bone_to_idx)
                vert_data = {
                    "position": (pos_x, pos_y, pos_z),
                    "influences": infl,
                    "weights": wts,
                    "normal": (norm_x, norm_y, norm_z),
                    "uv": (final_u, final_v),
                }
                local_idx = len(submesh_verts[mat_idx])
                submesh_verts[mat_idx].append(vert_data)
                vert_cache[mat_idx][key] = local_idx

            submesh_indices[mat_idx].append(local_idx)

    bpy.data.meshes.remove(temp_mesh)

    submeshes = []
    for i in range(num_materials):
        if not submesh_verts[i]:
            continue
        name = (mesh_obj.material_slots[i].material.name if mesh_obj.material_slots[i].material else f"mat_{i}")
        submeshes.append({"name": name, "verts": submesh_verts[i], "indices": submesh_indices[i]})

    return submeshes


# Operador
# -----------

class LEAGUEBLENDER_OT_export_skn(Operator, ExportHelper):
    bl_idname = "leagueblender.export_skn"
    bl_label = t("op_export_skn_label")
    filename_ext = ".skn"
    filter_glob: StringProperty(default="*.skn", options={'HIDDEN'})

    def execute(self, context):
        mesh_obj = context.active_object
        if not mesh_obj or mesh_obj.type != 'MESH':
            self.report({'ERROR'}, t("msg_export_select_mesh"))
            return {'CANCELLED'}

        # Verificações basicas antes de triangular uma mesh
        ok, err = _validate_mesh_for_export(mesh_obj)
        if not ok:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}

        # Pega o armature vinculado
        arm_obj = next(
            mod.object for mod in mesh_obj.modifiers
            if mod.type == 'ARMATURE' and mod.object
        )

        # Outras meshes vinculadas ao mesmo armature entram como submeshes
        mesh_objs = _find_meshes_for_armature(arm_obj, context)
        for obj in mesh_objs:
            ok, err = _validate_mesh_for_export(obj)
            if not ok:
                self.report({'ERROR'}, err)
                return {'CANCELLED'}

        try:
            # ___ SKN ___
            bone_to_idx = _build_bone_to_idx(arm_obj)

            # Renomeia materiais com nome > 63 caracteres ANTES de extrair submeshes
            export_warnings = []
            for obj in mesh_objs:
                enforce_material_name_limit(obj, export_warnings)

            # Garante que UV layer e material tenham o mesmo nome
            for obj in mesh_objs:
                ok, err = _sync_uv_layer_names(obj, export_warnings)
                if not ok:
                    self.report({'ERROR'}, err)
                    return {'CANCELLED'}

            submeshes = []
            for obj in mesh_objs:
                submeshes.extend(dump_skn_from_mesh(obj, bone_to_idx))

            # Une submeshes com mesmo nome (varias meshes com o mesmo material)
            submeshes = _merge_submeshes_by_name(submeshes)

            # Limite de submeshes
            submesh_count = len(submeshes)
            if submesh_count > 32:
                raise ValueError(t("msg_too_many_submeshes", submesh_count))

            # Limite de vertices
            total_verts = sum(len(sm["verts"]) for sm in submeshes)
            if total_verts > 65535:
                raise ValueError(t("msg_too_many_verts", total_verts))

            write_skn_binary(submeshes, self.filepath)

            # ___ SKL ___
            skl_path = os.path.splitext(self.filepath)[0] + ".skl"
            joints = dump_skl_from_armature(arm_obj)

            raw_influences = arm_obj.get("lol_influences")
            influences = list(raw_influences) if raw_influences is not None else list(range(len(joints)))

            write_skl_binary(joints, influences, skl_path)

            for w in export_warnings:
                self.report({'WARNING'}, w)

            mesh_names = ", ".join(obj.name for obj in mesh_objs)
            self.report({'INFO'}, t("msg_skn_exported", self.filepath, mesh_names, skl_path))
            return {'FINISHED'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, t("msg_export_generic_error", e))
            return {'CANCELLED'}
        