"""Add-on preferences: library folders, cache location and apply behaviour."""

from pathlib import Path

import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, StringProperty

ADDON_ID = __package__ or "Pose_Bridge"


def _on_undo_steps_changed(self, _context: bpy.types.Context) -> None:
    from .executor import set_undo_limit

    set_undo_limit(self.undo_steps)


class PoseBridgeRoot(bpy.types.PropertyGroup):
    path: StringProperty(name="Folder", subtype="DIR_PATH")


class PoseBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    roots: CollectionProperty(type=PoseBridgeRoot)
    pose_folder: StringProperty(
        name="Saved Poses Folder",
        description="Where 'Save Pose' writes pose files (they also appear in the library). Empty = Blender's config folder",
        subtype="DIR_PATH",
    )
    undo_steps: IntProperty(
        name="Undo Steps",
        description="How many pose changes (imports, T-pose, adjust layers and manual joint edits) are remembered per character (about 0.4 MB per step)",
        min=1,
        max=100,
        default=20,
        update=_on_undo_steps_changed,
    )
    set_frame_range: BoolProperty(
        name="Set Frame Range From Animation",
        description="After importing an animation, set the scene frame range to the animation length",
        default=True,
    )

    def draw(self, _context: bpy.types.Context) -> None:
        layout = self.layout
        layout.label(text="Library folders (poses and animations, searched recursively):")
        for index, root in enumerate(self.roots):
            row = layout.row(align=True)
            row.prop(root, "path", text="")
            op = row.operator("posebridge.remove_root", text="", icon="X")
            op.index = index
        row = layout.row(align=True)
        row.operator("posebridge.add_root", text="Add Folder", icon="ADD")
        row.operator("posebridge.add_daz_roots", text="From DAZ Importer", icon="IMPORT")
        layout.prop(self, "undo_steps")
        layout.prop(self, "pose_folder")
        layout.prop(self, "set_frame_range")


def get_preferences(context: bpy.types.Context) -> PoseBridgePreferences:
    return context.preferences.addons[ADDON_ID].preferences


def saved_poses_folder(context: bpy.types.Context) -> Path:
    custom = get_preferences(context).pose_folder.strip()
    return Path(bpy.path.abspath(custom)) if custom else Path(bpy.utils.user_resource("CONFIG")) / "Pose Bridge Poses"


def configured_roots(context: bpy.types.Context) -> list[Path]:
    """Library folders from the preferences plus the saved-poses folder once it exists."""
    roots = [Path(root.path) for root in get_preferences(context).roots if root.path.strip()]
    saved = saved_poses_folder(context)
    if saved.is_dir() and saved not in roots:
        roots.append(saved)
    return roots


def cache_file() -> Path:
    return Path(bpy.utils.user_resource("CONFIG")) / "pose_bridge_index.json"
