from bpy.types import AddonPreferences
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from .i18n import t, save_language


# Idiomas suportados.
LANGUAGES = [
    ("en", "English", "English"),
    ("pt-br", "Português (Brasil)", "Português (Brasil)"),
]


def _on_language_update(self, context):
    save_language(self.language)

# Geral
# ========

class LeagueBlenderPreferences(AddonPreferences):
    bl_idname = __package__

    language: EnumProperty(
        name=t("prop_language_name"),
        description=t("prop_language_desc"),
        items=LANGUAGES,
        default="en",
        update=_on_language_update,
    )

    # Opções de importação SKN
    # ---------------------------

    skn_mesh_format: EnumProperty(
        name=t("prop_skn_mesh_format_name"),
        description=t("prop_skn_mesh_format_desc"),
        items=[
            ('TRIS', t("prop_skn_mesh_format_tris_name"), t("prop_skn_mesh_format_tris_desc")),
            ('QUADS', t("prop_skn_mesh_format_quads_name"), t("prop_skn_mesh_format_quads_desc")),
        ],
        default='TRIS',
    )

    skn_apply_seams: BoolProperty(
        name=t("prop_skn_apply_seams_name"),
        description=t("prop_skn_apply_seams_desc"),
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

    # Opções de importação SKL
    # ---------------------------

    skl_bone_shape: EnumProperty(
        name=t("prop_skl_bone_shape_name"),
        description=t("prop_skl_bone_shape_desc"),
        items=[
            ('BLENDER', t("prop_skl_bone_shape_blender_name"), t("prop_skl_bone_shape_blender_desc")),
            ('SPHERE',  t("prop_skl_bone_shape_sphere_name"), t("prop_skl_bone_shape_sphere_desc")),
        ],
        default='BLENDER',
    )

    skl_show_in_front: BoolProperty(
        name=t("prop_skl_show_in_front_name"),
        description=t("prop_skl_show_in_front_desc"),
        default=True,
    )

    # Opções de cena
    # -----------------

    scene_auto_clip_end: BoolProperty(
        name=t("prop_scene_auto_clip_end_name"),
        description=t("prop_scene_auto_clip_end_desc"),
        default=True,
    )

    scene_clip_end_distance: FloatProperty(
        name=t("prop_scene_clip_end_distance_name"),
        description=t("prop_scene_clip_end_distance_desc"),
        default=10000.0,
        min=100.0,
        max=1_000_000.0,
        step=100,
        precision=1,
        unit='LENGTH',
    )

    # Desenho do painel de preferências
    # ------------------------------------

    def draw(self, context):
        layout = self.layout

        # Geral / Idioma
        box = layout.box()
        box.label(text=t("prefs_general_section"), icon='WORLD')
        box.prop(self, "language")
        box.label(text=t("prefs_restart_required"), icon='INFO')

        # SKN
        box = layout.box()
        box.label(text=t("prefs_skn_section"), icon='IMPORT')

        col = box.column(align=True)
        col.prop(self, "skn_mesh_format")
        col.prop(self, "skn_apply_seams")
        col.prop(self, "skn_default_material_color")

        col.separator()
        col.prop(self, "skn_import_as_collection")

        col.separator()
        row = col.row(align=True)

        # Merge by Distance não se aplica quando cada submesh vira um objeto separado
        row.enabled = not self.skn_import_as_collection
        row.prop(self, "skn_merge_by_distance")

        # Threshold so aparece quando Merge esta ativo
        sub = col.row(align=True)
        sub.enabled = self.skn_merge_by_distance and not self.skn_import_as_collection
        sub.prop(self, "skn_merge_threshold")

        # SKL
        box = layout.box()
        box.label(text=t("prefs_skl_section"), icon='ARMATURE_DATA')

        col = box.column(align=True)
        col.prop(self, "skl_bone_shape")
        col.prop(self, "skl_show_in_front")

        # Cena
        box = layout.box()
        box.label(text=t("prefs_scene_section"), icon='SCENE_DATA')

        col = box.column(align=True)
        col.prop(self, "scene_auto_clip_end")

        sub = col.row(align=True)
        sub.enabled = self.scene_auto_clip_end
        sub.prop(self, "scene_clip_end_distance")


def get_prefs(context) -> LeagueBlenderPreferences:
    
    # Atalho para pegar as preferências de qualquer lugar do plugin
    return context.preferences.addons[__package__].preferences