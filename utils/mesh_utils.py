"""
Utilitarios de pos-processamento de mesh.
"""

import bpy


def merge_by_distance(obj: bpy.types.Object, threshold: float = 0.001):

    # Executa Merge > By Distance no objeto de mesh fornecido.
    if obj.type != 'MESH':
        return

    prev_active = bpy.context.view_layer.objects.active
    prev_mode = obj.mode

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action = 'SELECT')
    bpy.ops.mesh.remove_doubles(threshold = threshold)
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # Restaura o objeto ativo anterior se houver
    if prev_active is not None:
        bpy.context.view_layer.objects.active = prev_active
        