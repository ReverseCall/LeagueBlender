"""
Utilitarios de configuração de cena no primeiro importe
"""

import bpy


def _is_first_import() -> bool:
    """
    Procurar por um importer do LB2026 para saber se ele deve ajustar o FOV
    Retorna True caso encontre a propriedade gravada no objeto
    """
    for obj in bpy.context.scene.objects:
        if obj.get("league_imported"):
            return False
    return True


def _set_clip_end(distance: float):

    # Aplica o Clip End em todas as viewports abertas
    for workspace in bpy.data.workspaces:
        for screen in workspace.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.clip_end = distance


def mark_imported(obj: bpy.types.Object):

    # Marca o objeto como importado pelo LB2026
    obj["league_imported"] = True


def apply_clip_end_on_first_import(context: bpy.types.Context):

    # Chama o ajuste de Clip End apenas no primeiro import da sessão de cena.
    from ..preferences import get_prefs

    prefs = get_prefs(context)

    if not prefs.scene_auto_clip_end:
        return

    if not _is_first_import():
        return

    _set_clip_end(prefs.scene_clip_end_distance)



    