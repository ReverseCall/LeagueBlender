import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..formats.skl import elf_hash, write_skl_binary_modern


# Conversão de espaço
# ======================

def _blender_to_lol_local(b_bone: bpy.types.Bone):

    # Calcula T/R/S local no espaço LoL a partir da geometria do EditBone
    # Usado como fallback quando o bone não tem lol_local_* armazenado
    if b_bone.parent:
        m_local = b_bone.parent.matrix_local.inverted() @ b_bone.matrix_local
    else:
        m_local = b_bone.matrix_local

    loc, rot, sca = m_local.decompose()

    tx = -loc.x
    ty = loc.z
    tz = -loc.y

    qx = rot.x
    qy = -rot.z
    qz = rot.y
    qw = rot.w

    sx = sca.x
    sy = sca.z
    sz = sca.y

    return (tx, ty, tz), (qx, qy, qz, qw), (sx, sy, sz)


def _restore_local_from_stored(stored_t, stored_r, stored_s):

    # Desfaz o flip() aplicado na importação para recuperar os valores RAW do LoL
    raw_t = (-stored_t[0], stored_t[1], stored_t[2])
    raw_r = (stored_r[0], -stored_r[1], -stored_r[2], stored_r[3])
    raw_s = tuple(stored_s)
    return raw_t, raw_r, raw_s


# Extração do Armature
# -----------------------

def dump_skl_from_armature(arm_obj: bpy.types.Object) -> list:
    arm_data = arm_obj.data
    bone_list = list(arm_data.bones)

    # Ordena por lol_id se disponivel
    has_lol_id = all("lol_id" in b for b in bone_list)
    if has_lol_id:
        bone_list.sort(key=lambda b: int(b["lol_id"]))

    bone_to_idx = {b.name: i for i, b in enumerate(bone_list)}

    joints = []
    for _i, b in enumerate(bone_list):
        j = {
            "name": b.name,
            "parent": bone_to_idx.get(b.parent.name, -1) if b.parent else -1,
            "hash": int(b["lol_hash"]) if "lol_hash" in b else elf_hash(b.name),
            "radius": float(b["lol_radius"]) if "lol_radius" in b else 2.1,
        }

        # ___ Transformação local ___
        if "lol_local_t" in b:

            # Round trip. recupera os valores originais do arquivo
            raw_t, raw_r, raw_s = _restore_local_from_stored(b["lol_local_t"], b["lol_local_r"], b["lol_local_s"])
            j["local_t"] = raw_t
            j["local_r"] = raw_r
            j["local_s"] = raw_s
        else:
            # Bone novo. calcula a partir da geometria Blender
            j["local_t"], j["local_r"], j["local_s"] = _blender_to_lol_local(b)

        # ___ Inverse Global ___
        if "lol_ig_t" in b:
            j["ig_t"] = tuple(b["lol_ig_t"])
            j["ig_r"] = tuple(b["lol_ig_r"])
            j["ig_s"] = tuple(b["lol_ig_s"])
        else:

            # Fallback. calcula a partir da matriz global do bone
            world_mat = b.matrix_local.copy()
            try:
                inv = world_mat.inverted()
                loc, rot, sca = inv.decompose()
                ig_tx = -loc.x; ig_ty = loc.z; ig_tz = -loc.y
                ig_rx = rot.x; ig_ry = -rot.z; ig_rz = rot.y; ig_rw = rot.w
                ig_sx = sca.x; ig_sy = sca.z; ig_sz = sca.y
                j["ig_t"] = (ig_tx, ig_ty, ig_tz)
                j["ig_r"] = (ig_rx, ig_ry, ig_rz, ig_rw)
                j["ig_s"] = (ig_sx, ig_sy, ig_sz)
            except Exception:
                j["ig_t"] = (0.0, 0.0, 0.0)
                j["ig_r"] = (0.0, 0.0, 0.0, 1.0)
                j["ig_s"] = (1.0, 1.0, 1.0)

        joints.append(j)

    return joints


# Operador
# -----------

class LEAGUEBLENDER_OT_export_skl(Operator, ExportHelper):
    bl_idname = "leagueblender.export_skl"
    bl_label = "League Skeleton (.skl)"
    filename_ext = ".skl"
    filter_glob: StringProperty(default="*.skl", options={'HIDDEN'})

    def execute(self, context):
        arm_obj = context.active_object
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an ARMATURE before exporting.")
            return {'CANCELLED'}

        try:
            joints = dump_skl_from_armature(arm_obj)

            # Recupera a influence list original gravada na importação
            # Se não existir (armature novo), usa sequência identidade 0..N-1
            raw_influences = arm_obj.get("lol_influences")
            influences = list(raw_influences) if raw_influences is not None else list(range(len(joints)))

            write_skl_binary_modern(joints, influences, self.filepath)
            self.report({'INFO'}, f"SKL exportado: {len(joints)} joints -> {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Erro: {e}")
            return {'CANCELLED'}
        
