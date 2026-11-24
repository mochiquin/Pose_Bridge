"""Scene-level properties: browser position, display options and the current target rig."""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty


def _is_armature(_self: bpy.types.PropertyGroup, obj: bpy.types.Object) -> bool:
    return obj.type == "ARMATURE"


def _on_target_rig_changed(self, context: bpy.types.Context) -> None:
    from .executor import track_character

    track_character(context, self.target_rig)


def _back_to_first_page(self, _context: bpy.types.Context) -> None:
    self.page = 0


class PoseBridgeSettings(bpy.types.PropertyGroup):
    target_rig: PointerProperty(
        name="Target Rig",
        description="Armature that receives poses and animations (works for GroupPro characters too)",
        type=bpy.types.Object,
        poll=_is_armature,
        update=_on_target_rig_changed,
    )

    # Browser state: never written into the user's .blend (the library is rebuilt from the cache).
    nav_root: StringProperty(options={"SKIP_SAVE"})
    nav_path: StringProperty(options={"SKIP_SAVE"})
    page: IntProperty(default=0, min=0, options={"SKIP_SAVE"})
    selected: StringProperty(options={"SKIP_SAVE"})
    status: StringProperty(options={"SKIP_SAVE"})

    query: StringProperty(
        name="Search",
        description="Search the whole library by name or folder",
        options={"TEXTEDIT_UPDATE", "SKIP_SAVE"},
        update=_back_to_first_page,
    )
    kind_filter: EnumProperty(
        name="Show",
        items=[("ALL", "All", ""), ("pose", "Poses", ""), ("animation", "Animations", "")],
        default="ALL",
        update=_back_to_first_page,
    )

    columns: IntProperty(name="Columns", min=1, max=6, default=3, update=_back_to_first_page)
    rows_per_page: IntProperty(name="Rows Per Page", min=1, max=12, default=4, update=_back_to_first_page)
    thumb_scale: FloatProperty(
        name="Thumbnail Size",
        description="Size of the pictures (widen the sidebar or use fewer columns for bigger pictures)",
        min=1.5,
        max=14.0,
        default=4.5,
    )
    apply_on: EnumProperty(
        name="Apply On",
        description="How a thumbnail is applied to the rig (Undo Apply reverts it)",
        items=[
            ("DOUBLE", "Double Click", "A click selects, a double click applies"),
            ("SINGLE", "Single Click", "A click selects and applies at once"),
        ],
        default="DOUBLE",
    )
    tpose_fk: BoolProperty(
        name="T-Pose in FK",
        description=(
            "After T-Pose leave the arms and legs in FK and the finger controls off, so every joint can be posed "
            "by hand. Off: MHX defaults (IK on, finger controls on), where FK bones do not move the character"
        ),
        default=True,
    )
