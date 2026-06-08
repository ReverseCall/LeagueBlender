"""
Preferências do addon
(Talvez isso nem entre no projeto final.)
"""

from bpy.types import AddonPreferences
from bpy.props import BoolProperty, EnumProperty, FloatProperty


class LeagueBlenderPreferences(AddonPreferences):
    bl_idname = __package__

    # Opções de importação SKN
    # ===========================

    skn_mesh_format: EnumProperty(
        name="Mesh Topology",
        description="Choose whether the mesh should be kept as triangles or converted to quads",
        items=[
            ('TRIS', "Triangles (Default)", "Maintains the original triangle topology"),
            ('QUADS', "Quads (Tris to Quads)", "Attempts to convert triangles to quads"),
        ],
        default='TRIS',
    )

    skn_apply_seams: BoolProperty(
        name="Rebuild Seam (BETA)",
        description="Automatically detects and marks UV seams when importing an SKN",
        default=False,
    )

    skn_merge_by_distance: BoolProperty(
        name="Merge by Distance",
        description="Performs Merge > By Distance on vertices after importing SKN",
        default=False,
    )

    skn_merge_threshold: FloatProperty(
        name="Distance",
        description="Maximum distance to consider two vertices as duplicates when using Merge by Distance",
        default=0.001,
        min=0.00001,
        max=0.1,
        precision=5,
        step=1,
        unit='LENGTH',
    )

    skn_default_material_color: BoolProperty(
        name="Gray Mesh by Default",
        description="Applies the default LeagueBlender gray color to materials created when importing SKN",
        default=True,
    )

    # Opções de importação SKL
    # ===========================

    skl_bone_shape: EnumProperty(
        name="Bone Shape",
        description="Visual shape of bones when importing a Skeleton (.skl)",
        items=[
            ('BLENDER', "Blender (Stick)", "Blender's default bone shape"),
            ('SPHERE',  "Sphere (wire)", "Wire sphere style like glTF"),
        ],
        default='BLENDER',
    )

    skl_show_in_front: BoolProperty(
        name="Show In Front",
        description="Draw the armature on top of other objects (In Front option)",
        default=True,
    )

    # Opções de cena
    # ===========================

    scene_auto_clip_end: BoolProperty(
        name="Auto Clip End",
        description=(
            "Adjusts the viewport and camera Clip End on the first import, "
            "preventing models from being clipped in large scenes"
        ),
        default=True,
    )

    scene_clip_end_distance: FloatProperty(
        name="Clip End Distance",
        description="Clip End value applied to all viewports and the active camera on the first import",
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

        # SKN
        box = layout.box()
        box.label(text="Preferências do SKN", icon='IMPORT')

        col = box.column(align=True)
        col.prop(self, "skn_mesh_format")
        col.prop(self, "skn_apply_seams")
        col.prop(self, "skn_default_material_color")

        col.separator()
        row = col.row(align=True)
        row.prop(self, "skn_merge_by_distance")

        # Threshold so aparece quando Merge esta ativo
        sub = col.row(align=True)
        sub.enabled = self.skn_merge_by_distance
        sub.prop(self, "skn_merge_threshold")

        # SKL
        box = layout.box()
        box.label(text="Preferências do SKL", icon='ARMATURE_DATA')

        col = box.column(align=True)
        col.prop(self, "skl_bone_shape")
        col.prop(self, "skl_show_in_front")

        # Cena
        box = layout.box()
        box.label(text="Preferências de Cena", icon='SCENE_DATA')

        col = box.column(align=True)
        col.prop(self, "scene_auto_clip_end")

        sub = col.row(align=True)
        sub.enabled = self.scene_auto_clip_end
        sub.prop(self, "scene_clip_end_distance")


def get_prefs(context) -> LeagueBlenderPreferences:
    # Atalho para pegar as preferências de qualquer lugar do plugin
    return context.preferences.addons[__package__].preferences