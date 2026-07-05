"""
LeagueBlender — Blender Plugin
=================================
=-=- NOTAS MENTAIS -=-=
Suporte atual:
  - Import: SKN (Skinned Mesh)
  - Import: SKL (Skeleton + SKN vinculado)
  - Export: SKN (Skinned Mesh + SKL vinculado)
  - Import/Export: SCB (Static Mesh Binary)

Em desenvolvimento:
  - Melhorias no Importe de arquivos SKN e SKL
  - Export: SKL (o arquivo final acaba ficando menor, por falta de alguns dados que eu tinha cortado para facilizar os testes)
  - Import: ANM (Animations) | refatorando

Atualizações futuras:
  - Export: ANM (Animations)
  - Volta fazendo uma refatoração e adicionando os Byte removidos para simplificação

Talvez eu não traga o suporte para MAPGEO. :p
"""

# Informações do plugin
# ------------------------

bl_info = {
    "name": "LeagueBlender",
    "author": "ReverseCall",
    "version": (0, 4, 1),
    "blender": (5, 0, 0),
    "location": "File > Import / File > Export",
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
from .importers.import_scb import LEAGUEBLENDER_OT_import_scb
from .exporters.export_skn import LEAGUEBLENDER_OT_export_skn
from .exporters.export_scb import LEAGUEBLENDER_OT_export_scb
from .i18n import t


def menu_import(self, context):

    # Importer
    self.layout.operator(
        LEAGUEBLENDER_OT_import_skn.bl_idname,
        text=t("op_import_skn_label"),
    )
    self.layout.operator(
        LEAGUEBLENDER_OT_import_skl.bl_idname,
        text=t("op_import_skl_label"),
    )
    self.layout.operator(
        LEAGUEBLENDER_OT_import_scb.bl_idname,
        text=t("op_import_scb_label"),
    )


def menu_export(self, context):

    # Exporter
    self.layout.operator(
        LEAGUEBLENDER_OT_export_skn.bl_idname,
        text=t("op_export_skn_label"),
    )
    self.layout.operator(
        LEAGUEBLENDER_OT_export_scb.bl_idname,
        text=t("op_export_scb_label"),
    )


_classes = [
    LeagueBlenderPreferences,
    LEAGUEBLENDER_OT_import_skn,
    LEAGUEBLENDER_OT_import_skl,
    LEAGUEBLENDER_OT_import_scb,
    LEAGUEBLENDER_OT_export_skn,
    LEAGUEBLENDER_OT_export_scb,
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
        