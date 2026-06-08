"""
LeagueBlender — Blender Plugin
=================================
=-=- NOTAS MENTAIS -=-=
Suporte atual:
  - Import: SKN (Skinned Mesh)
  - Import: SKL (Skeleton + SKN vinculado)
  - Export: SKN (Skinned Mesh)
  - Export: SKL (Skeleton)

Em desenvolvimento:
  - Melhorias no Importe de arquivos SKN e SKL
  - Export: SKN (o arquivo final acaba ficando maior pq algns dados da Uv não batem 100% depos de ser mastigado pelo o codigo)
  - Import: ANM (Animations) | refatorando

Atualizações futuras:
  - Import: SCO (Sla qq e isso meu fi, so quero fazer importar)
  - Import: SCB (Script Compiled Binary)
  -
  - Export: ANM (Animations)
  - Import: SCO (SLA.file)
  - Export: SCB (Script Compiled Binary)
  -

Talvez eu não traga o suporte para MAPGEO. :p
"""

# Informações do plugin
# ------------------------

bl_info = {
    "name": "LeagueBlender",
    "author": "ReverseCall",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "File > Import / File > Export",
    "warning": "Essa jocha pode explodir a qualquer momento",
    "description": "Imports and exports the formats supported by League Of Legends",
    "doc_url": "https://github.com/ReverseCall/LeagueBlender",
    "tracker_url": "https://github.com/ReverseCall/LeagueBlender/issues",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

# Iniciador
# ------------

import bpy

from .preferences import LeagueBlenderPreferences
from .importers.import_skn import LEAGUEBLENDER_OT_import_skn
from .importers.import_skl import LEAGUEBLENDER_OT_import_skl
from .exporters.export_skn import LEAGUEBLENDER_OT_export_skn
from .exporters.export_skl import LEAGUEBLENDER_OT_export_skl


def menu_import(self, context):
    self.layout.operator(
        LEAGUEBLENDER_OT_import_skn.bl_idname,
        text="League Mesh (.skn)",
    )
    self.layout.operator(
        LEAGUEBLENDER_OT_import_skl.bl_idname,
        text="League Skeleton (.skl + .skn)",
    )


def menu_export(self, context):
    self.layout.operator(
        LEAGUEBLENDER_OT_export_skn.bl_idname,
        text="League Mesh (.skn)",
    )
    self.layout.operator(
        LEAGUEBLENDER_OT_export_skl.bl_idname,
        text="League Skeleton (.skl)",
    )


_classes = [
    LeagueBlenderPreferences,
    LEAGUEBLENDER_OT_import_skn,
    LEAGUEBLENDER_OT_import_skl,
    LEAGUEBLENDER_OT_export_skn,
    LEAGUEBLENDER_OT_export_skl,
]

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
