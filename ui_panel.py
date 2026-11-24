"""3D Viewport sidebar: folder navigation and a thumbnail grid of the poses/animations."""

import traceback
from pathlib import Path

import bpy
import bpy.utils.previews

from . import library_state
from .core import KIND_ANIMATION
from .executor import adjust_action_name, has_adjust, undo_depth

_previews: bpy.utils.previews.ImagePreviewCollection | None = None
last_error = ""  # traceback of the last failed panel draw (empty when the last draw was fine)


def _preview_icon(path_text: str) -> int:
    """Icon id for a preview png, loaded on demand (0 when unavailable)."""
    if _previews is None or not path_text:
        return 0
    if path_text not in _previews:
        if not Path(path_text).is_file():
            return 0
        try:
            preview = _previews.load(path_text, path_text, "IMAGE")
            # Reading the pixels forces Blender to decode the image now; otherwise the first draw
            # shows a "loading" clock instead of the picture.
            len(preview.icon_pixels)
            len(preview.image_pixels)
        except Exception:
            return 0
    return _previews[path_text].icon_id


def _draw_breadcrumbs(layout, view) -> None:
    # The crumb before the last one is the parent folder: "Back" always goes exactly one level up.
    parent = view.crumbs[-2] if len(view.crumbs) > 1 else None
    back = layout.row(align=True)
    back.enabled = parent is not None
    back.operator("posebridge.up", text=f"Back to {parent.label}" if parent else "Back", icon="BACK")

    row = layout.row(align=True)
    last = len(view.crumbs) - 1
    for index, crumb in enumerate(view.crumbs):
        op = row.operator("posebridge.open_folder", text=crumb.label, depress=index == last)
        op.root = crumb.root
        op.path = "/".join(crumb.parts)


def _draw_folders(layout, view) -> None:
    if not view.folders:
        return
    grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
    for folder in view.folders:
        op = grid.operator("posebridge.open_folder", text=f"{folder.label} ({folder.count})", icon="FILE_FOLDER")
        op.root = folder.root
        op.path = "/".join(folder.parts)


def _draw_thumbnails(layout, settings, page) -> None:
    """Big picture on top, the name below it as the button that selects (and applies) the file."""
    grid = layout.grid_flow(row_major=True, columns=settings.columns, even_columns=True, even_rows=True, align=False)
    for entry in page.items:
        cell = grid.column(align=True)
        icon = _preview_icon(entry.preview)
        if icon:
            cell.template_icon(icon_value=icon, scale=settings.thumb_scale)
        else:
            cell.label(text="", icon="ACTION" if entry.kind == KIND_ANIMATION else "POSE_HLT")
        bar = cell.row(align=True)
        bar.scale_y = 1.6  # a tall name bar is the click target (the picture itself cannot be a button)
        button = bar.operator("posebridge.pick", text=entry.name, depress=entry.path == settings.selected)
        button.path = entry.path


def _draw_pager(layout, page) -> None:
    row = layout.row(align=True)
    prev_row = row.row(align=True)
    prev_row.enabled = page.index > 0
    prev_row.operator("posebridge.page", text="", icon="TRIA_LEFT").delta = -1
    row.label(text=f"Page {page.index + 1} / {page.count}   ({page.total} files)")
    next_row = row.row(align=True)
    next_row.enabled = page.index < page.count - 1
    next_row.operator("posebridge.page", text="", icon="TRIA_RIGHT").delta = 1


def _draw_adjust(layout, settings) -> None:
    rig = settings.target_rig
    box = layout.box()
    row = box.row(align=True)
    row.operator("posebridge.adjust_start", icon="NLA")
    row.operator("posebridge.adjust_discard", icon="TRASH")
    if has_adjust(rig):
        box.label(text=f"Editing layer: {adjust_action_name(rig)}", icon="KEYFRAME")
        box.label(text="Pose bones and press I; the original animation is untouched")


class POSEBRIDGE_PT_main(bpy.types.Panel):
    bl_label = "Pose Bridge"
    bl_idname = "POSEBRIDGE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pose Bridge"

    def draw(self, context):
        global last_error
        try:
            self._draw_body(context)
            last_error = ""
        except Exception:  # keep the panel alive and show what went wrong instead of silently drawing nothing
            last_error = traceback.format_exc()
            self.layout.label(text="Pose Bridge draw error:", icon="ERROR")
            self.layout.label(text=last_error.strip().splitlines()[-1][:80])

    def _draw_body(self, context):
        layout = self.layout
        settings = context.scene.pose_bridge

        layout.prop(settings, "target_rig")
        row = layout.row(align=True)
        row.operator("posebridge.rescan", text="Scan", icon="FILE_REFRESH").force = False
        row.operator("posebridge.rescan", text="Rescan", icon="FILE_REFRESH").force = True

        if len(library_state.index()) == 0:
            layout.label(text="Press Scan to read the library folders", icon="INFO")
            return

        layout.prop(settings, "query", text="", icon="VIEWZOOM")
        layout.prop(settings, "kind_filter", expand=True)

        if not library_state.is_searching(settings):
            view = library_state.current_view(settings)
            _draw_breadcrumbs(layout, view)
            _draw_folders(layout, view)
        else:
            layout.label(text="Search results (whole library)", icon="VIEWZOOM")

        page = library_state.current_page(settings)
        if page.total:
            _draw_thumbnails(layout, settings, page)
            _draw_pager(layout, page)
        elif library_state.is_searching(settings):
            layout.label(text="No matches", icon="INFO")

        layout.separator()
        layout.prop(settings, "apply_on", expand=True)
        row = layout.row(align=True)
        row.operator("posebridge.apply", icon="IMPORT")
        undo_steps, redo_steps = undo_depth(settings.target_rig)
        row.operator("posebridge.undo_apply", text=f"Undo ({undo_steps})" if undo_steps else "Undo", icon="LOOP_BACK")
        row.operator("posebridge.redo", text=f"Redo ({redo_steps})" if redo_steps else "Redo", icon="LOOP_FORWARDS")
        _draw_adjust(layout, settings)
        row = layout.row(align=True)
        row.operator("posebridge.tpose", icon="ARMATURE_DATA")
        row.operator("posebridge.save_pose", text="Save Pose...", icon="FILE_TICK")
        if settings.status:
            layout.label(text=settings.status)


class POSEBRIDGE_PT_display(bpy.types.Panel):
    bl_label = "Display"
    bl_idname = "POSEBRIDGE_PT_display"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Pose Bridge"
    bl_parent_id = "POSEBRIDGE_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        settings = context.scene.pose_bridge
        col = self.layout.column()
        col.prop(settings, "columns")
        col.prop(settings, "rows_per_page")
        col.prop(settings, "thumb_scale")


def register() -> None:
    global _previews
    _previews = bpy.utils.previews.new()


def unregister() -> None:
    global _previews
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
