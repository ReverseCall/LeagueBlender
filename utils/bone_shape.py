"""
Controla o formato visual dos ossos da armature
==================================================

Tipos disponiveis
--------------------
  - BLENDER: formato padrão do Blender (stick)
  - SPHERE: ossos em esfera, parecido com rig glTF
  - CUSTOM: reservado para futuras custom shapes
"""

from enum import Enum
import bpy


class BoneShapeType(str, Enum):
    BLENDER = "BLENDER"
    SPHERE = "SPHERE"


# Shape objects
# ----------------

def _get_or_create_sphere_shape() -> bpy.types.Object:
    """
    Retorna (ou cria) um objeto de esfera wire reutilizavel como custom shape.
    Fica num coleção oculta chamada 'LeagueBlender_Shapes'.
    """
    name = "_LB_BoneShape_Sphere"
    if name in bpy.data.objects:
        return bpy.data.objects[name]

    # Garante coleção auxiliar
    col_name = "LeagueBlender_Shapes"
    if col_name not in bpy.data.collections:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
        col.hide_viewport = True
        col.hide_render = True
    else:
        col = bpy.data.collections[col_name]

    # Cria mesh de esfera UV simplificada (apenas arestas)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)

    import bmesh as bm_mod
    bm = bm_mod.new()
    bm_mod.ops.create_uvsphere(bm, u_segments = 8, v_segments = 6, radius = 1.07)
    bm.to_mesh(mesh)
    bm.free()

    # Transforma em wire
    obj.display_type = 'WIRE'
    obj.hide_render = True

    return obj


# Aplicação
# ------------

def apply_bone_shapes(
    arm_obj: bpy.types.Object,
    shape_type: BoneShapeType = BoneShapeType.BLENDER, # Troque essa opição para trocar o shaper
):
    # Aplica o shape desejado a todos os ossos da armature
    if arm_obj.type != 'ARMATURE':
        return

    arm = arm_obj.data

    if shape_type == BoneShapeType.BLENDER:
        # Remove qualquer custom shape - volta ao padrão do Blender
        for bone in arm.bones:
            pbone = arm_obj.pose.bones.get(bone.name)
            if pbone:
                pbone.custom_shape = None
        return

    if shape_type == BoneShapeType.SPHERE:
        sphere = _get_or_create_sphere_shape()
        for bone in arm.bones:
            pbone = arm_obj.pose.bones.get(bone.name)
            if pbone:
                pbone.custom_shape = sphere
                pbone.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
                pbone.use_custom_shape_bone_size = False