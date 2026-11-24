"""Operators: library folders, scanning, folder navigation, picking and applying a pose/animation."""

import time
from pathlib import Path

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

from . import library_state, preferences
from .core import (
    DEFAULT_EXTENSIONS,
    DoubleClickTracker,
    default_name,
    load_cache,
    save_cache,
    scan_library,
    split_subfolder,
)
from .executor import (
    ApplyError,
    apply_library_file,
    can_start_adjust,
    daz_importer_ready,
    discard_adjust,
    has_adjust,
    has_pending_edit,
    needs_daz_importer,
    redo_pose,
    render_thumbnail,
    reset_to_tpose,
    save_pose_file,
    set_undo_limit,
    start_adjust,
    undo_depth,
    undo_pose,
)


def sync_undo_limit(context: bpy.types.Context) -> None:
    """Apply the 'Undo Steps' preference (the history is created with the add-on's default otherwise)."""
    try:
        set_undo_limit(preferences.get_preferences(context).undo_steps)
    except KeyError:  # add-on preferences not available yet
        pass


def restore_from_cache(context: bpy.types.Context) -> bool:
    """Refill the library from the cache (used on file load); False when no valid cache exists."""
    sync_undo_limit(context)
    try:
        roots = preferences.configured_roots(context)
    except KeyError:  # add-on preferences not available yet
        return False
    entries = load_cache(preferences.cache_file(), roots, DEFAULT_EXTENSIONS) if roots else None
    if entries is None:
        return False
    library_state.set_entries(entries)
    return True


class POSEBRIDGE_OT_add_root(bpy.types.Operator):
    bl_idname = "posebridge.add_root"
    bl_label = "Add Library Folder"
    bl_description = "Add a folder that contains pose or animation files"

    directory: StringProperty(subtype="DIR_PATH")

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        folder = Path(self.directory)
        if not folder.is_dir():
            self.report({"ERROR"}, f"Not a folder: {folder}")
            return {"CANCELLED"}
        roots = preferences.get_preferences(context).roots
        if any(Path(r.path) == folder for r in roots):
            self.report({"INFO"}, "Folder is already in the list")
            return {"CANCELLED"}
        roots.add().path = str(folder)
        return {"FINISHED"}


class POSEBRIDGE_OT_remove_root(bpy.types.Operator):
    bl_idname = "posebridge.remove_root"
    bl_label = "Remove Library Folder"

    index: IntProperty()

    def execute(self, context):
        roots = preferences.get_preferences(context).roots
        if 0 <= self.index < len(roots):
            roots.remove(self.index)
        return {"FINISHED"}


class POSEBRIDGE_OT_add_daz_roots(bpy.types.Operator):
    bl_idname = "posebridge.add_daz_roots"
    bl_label = "Add From DAZ Importer"
    bl_description = "Add the 'Poses' and 'Animations' folders found under DAZ Importer's content directories"

    def execute(self, context):
        try:
            from import_daz.settings import GS

            content_dirs = [Path(p) for p in GS.getDazPaths()]
        except Exception as exc:  # DAZ Importer internals differ between versions
            self.report({"ERROR"}, f"Could not read DAZ Importer paths: {exc}")
            return {"CANCELLED"}
        roots = preferences.get_preferences(context).roots
        existing = {Path(r.path) for r in roots}
        added = 0
        for base in content_dirs:
            people = base / "People"
            if not people.is_dir():
                continue
            for figure in sorted(people.iterdir()):
                for sub in ("Poses", "Animations"):
                    folder = figure / sub
                    if folder.is_dir() and folder not in existing and "female" in figure.name.lower():
                        roots.add().path = str(folder)
                        existing.add(folder)
                        added += 1
        self.report({"INFO"}, f"Added {added} folder(s)")
        return {"FINISHED"}


class POSEBRIDGE_OT_rescan(bpy.types.Operator):
    bl_idname = "posebridge.rescan"
    bl_label = "Scan Library"
    bl_description = "Scan the configured library folders (uses a cache unless forced)"

    force: BoolProperty(name="Force", default=False)

    def execute(self, context):
        sync_undo_limit(context)
        roots = preferences.configured_roots(context)
        if not roots:
            self.report(
                {"ERROR"},
                "No library folders configured (Preferences > Add-ons > Pose Bridge). "
                "Or save a pose first: that creates the saved-poses library.",
            )
            return {"CANCELLED"}
        entries = None if self.force else load_cache(preferences.cache_file(), roots, DEFAULT_EXTENSIONS)
        if entries is None:
            result = scan_library(roots, DEFAULT_EXTENSIONS)
            entries = list(result.entries)
            save_cache(preferences.cache_file(), entries, roots, DEFAULT_EXTENSIONS)
            if result.missing_roots:
                self.report({"WARNING"}, f"Missing folders: {', '.join(result.missing_roots)}")
        library_state.set_entries(entries)
        library_state.open_folder(context.scene, "", ())
        context.scene.pose_bridge.status = f"{len(entries)} files"
        return {"FINISHED"}


class POSEBRIDGE_OT_open_folder(bpy.types.Operator):
    bl_idname = "posebridge.open_folder"
    bl_label = "Open Folder"
    bl_options = {"INTERNAL"}

    root: StringProperty()
    path: StringProperty()

    @classmethod
    def description(cls, _context, properties):
        return f"Open {properties.path or properties.root or 'the library top level'}"

    def execute(self, context):
        settings = context.scene.pose_bridge
        settings.query = ""
        library_state.open_folder(context.scene, self.root, [p for p in self.path.split("/") if p])
        return {"FINISHED"}


class POSEBRIDGE_OT_up(bpy.types.Operator):
    bl_idname = "posebridge.up"
    bl_label = "Parent Folder"
    bl_description = "Go up one folder"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        library_state.go_up(context.scene)
        return {"FINISHED"}


class POSEBRIDGE_OT_page(bpy.types.Operator):
    bl_idname = "posebridge.page"
    bl_label = "Change Page"
    bl_options = {"INTERNAL"}

    delta: IntProperty()

    def execute(self, context):
        library_state.change_page(context.scene, self.delta)
        return {"FINISHED"}


_double_clicks = DoubleClickTracker()


def _apply_entry(operator: bpy.types.Operator, context: bpy.types.Context, entry) -> set[str]:
    settings = context.scene.pose_bridge
    if needs_daz_importer(entry.path) and not daz_importer_ready():
        operator.report({"ERROR"}, "Enable the DAZ Importer add-on first")
        return {"CANCELLED"}
    try:
        report = apply_library_file(
            context,
            settings.target_rig,
            Path(entry.path),
            entry.kind,
            set_frame_range=preferences.get_preferences(context).set_frame_range,
        )
    except ApplyError as exc:
        operator.report({"ERROR"}, str(exc))
        return {"CANCELLED"}
    extra = f", frames {report.frame_range[0]}-{report.frame_range[1]}" if report.frame_range else ""
    fingers = f"; fingers set to FK ({', '.join(report.fingers_freed)})" if report.fingers_freed else ""
    settings.status = f"Applied {report.kind} '{entry.name}' ({report.bones_changed} bones changed{extra}{fingers})"
    operator.report({"INFO"}, settings.status)
    return {"FINISHED"}


class POSEBRIDGE_OT_pick(bpy.types.Operator):
    bl_idname = "posebridge.pick"
    bl_label = "Select"
    bl_options = {"INTERNAL"}

    path: StringProperty()

    @classmethod
    def description(cls, context, properties):
        entry = library_state.find(properties.path)
        if entry is None:
            return "Select this pose or animation"
        where = f"{entry.category}/" if entry.category else ""
        how = "Click to apply" if context.scene.pose_bridge.apply_on == "SINGLE" else "Double-click to apply"
        return f"{entry.kind.title()}: {where}{entry.name}\n{how}"

    def execute(self, context):
        settings = context.scene.pose_bridge
        entry = library_state.find(self.path)
        if entry is None:
            self.report({"ERROR"}, "File is no longer in the library; rescan")
            return {"CANCELLED"}
        settings.selected = entry.path
        interval = context.preferences.inputs.mouse_double_click_time / 1000.0  # user's own double-click speed
        is_double = _double_clicks.register(entry.path, time.monotonic(), interval)
        if is_double or settings.apply_on == "SINGLE":
            return _apply_entry(self, context, entry)
        return {"FINISHED"}


class POSEBRIDGE_OT_apply(bpy.types.Operator):
    bl_idname = "posebridge.apply"
    bl_label = "Apply To Rig"
    bl_description = "Apply the selected pose or animation to the target rig (can be undone with 'Undo Apply')"

    @classmethod
    def poll(cls, context):
        settings = context.scene.pose_bridge
        return settings.target_rig is not None and library_state.find(settings.selected) is not None

    def execute(self, context):
        entry = library_state.find(context.scene.pose_bridge.selected)
        if entry is None:
            self.report({"ERROR"}, "Select a pose or animation first")
            return {"CANCELLED"}
        return _apply_entry(self, context, entry)


class POSEBRIDGE_OT_undo_apply(bpy.types.Operator):
    bl_idname = "posebridge.undo_apply"
    bl_label = "Undo"
    bl_description = (
        "Undo the last pose change of the target character: imports, T-pose, adjust layers and joints you moved "
        "by hand. Other objects in the scene are not touched"
    )

    @classmethod
    def poll(cls, context):
        rig = context.scene.pose_bridge.target_rig
        return undo_depth(rig)[0] > 0 or has_pending_edit(rig)

    def execute(self, context):
        settings = context.scene.pose_bridge
        try:
            left = undo_pose(context, settings.target_rig)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.status = f"Undone ({left} more step{'s' if left != 1 else ''} can be undone)"
        return {"FINISHED"}


class POSEBRIDGE_OT_redo(bpy.types.Operator):
    bl_idname = "posebridge.redo"
    bl_label = "Redo"
    bl_description = "Redo the pose change of the target character that was just undone"

    @classmethod
    def poll(cls, context):
        return undo_depth(context.scene.pose_bridge.target_rig)[1] > 0

    def execute(self, context):
        settings = context.scene.pose_bridge
        try:
            left = redo_pose(context, settings.target_rig)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.status = f"Redone ({left} more step{'s' if left != 1 else ''} can be redone)"
        return {"FINISHED"}


class POSEBRIDGE_OT_tpose(bpy.types.Operator):
    bl_idname = "posebridge.tpose"
    bl_label = "T-Pose"
    bl_description = (
        "Return the target rig to its rest pose (T-pose), MHX switches to their defaults, and remove the action"
    )

    @classmethod
    def poll(cls, context):
        return context.scene.pose_bridge.target_rig is not None

    def execute(self, context):
        settings = context.scene.pose_bridge
        try:
            report = reset_to_tpose(context, settings.target_rig)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        kept = f"; kept in the file: {', '.join(report.kept_actions)}" if report.kept_actions else ""
        settings.status = f"T-pose ({report.bones_changed} bones reset, {report.switches_reset} switches reset{kept})"
        self.report({"INFO"}, settings.status)
        return {"FINISHED"}


class POSEBRIDGE_OT_save_pose(bpy.types.Operator):
    bl_idname = "posebridge.save_pose"
    bl_label = "Save Pose"
    bl_description = (
        "Save the current pose of the target rig as a pose file in the saved-poses folder (shown in the library)"
    )

    name: StringProperty(name="Name")
    subfolder: StringProperty(name="Folder", description="Optional sub-folder, for example Maria/Sitting")
    with_preview: BoolProperty(
        name="Preview Picture",
        description="Render a small picture of the character (takes a few seconds)",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return context.scene.pose_bridge.target_rig is not None

    def invoke(self, context, _event):
        folder = preferences.saved_poses_folder(context).joinpath(*split_subfolder(self.subfolder))
        existing = [p.stem for p in folder.glob("*.pbpose")] if folder.is_dir() else []
        self.name = default_name(existing)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "subfolder")
        layout.prop(self, "with_preview")
        folder = preferences.saved_poses_folder(context)
        layout.label(text=f"Saves to: {folder}")
        if not folder.is_dir():
            layout.label(text="(this folder will be created)", icon="INFO")

    def execute(self, context):
        settings = context.scene.pose_bridge
        folder = preferences.saved_poses_folder(context)
        subfolders = split_subfolder(self.subfolder)
        try:
            path = save_pose_file(settings.target_rig, folder, self.name, subfolders)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        preview_note = ""
        if self.with_preview:
            try:
                made = render_thumbnail(context, settings.target_rig, path.with_suffix(path.suffix + ".png"))
                preview_note = "" if made else " (no preview: no visible meshes)"
            except Exception as exc:  # the pose is saved either way; a failed picture must not lose it
                preview_note = f" (no preview: {exc})"

        # show the new file in the library without rescanning everything
        result = scan_library([folder], DEFAULT_EXTENSIONS)
        entries = library_state.replace_root(str(folder), result.entries)
        save_cache(preferences.cache_file(), entries, preferences.configured_roots(context), DEFAULT_EXTENSIONS)
        settings.selected = str(path)
        library_state.open_folder(context.scene, str(folder), subfolders)
        settings.status = f"Saved pose '{path.stem}'{preview_note}"
        self.report({"INFO"}, settings.status)
        return {"FINISHED"}


class POSEBRIDGE_OT_adjust_start(bpy.types.Operator):
    bl_idname = "posebridge.adjust_start"
    bl_label = "Add Adjust Layer"
    bl_description = (
        "Keep the applied animation untouched and add a layer on top of it: pose bones and key them (I) "
        "and the keys are stored as offsets in the new layer"
    )

    @classmethod
    def poll(cls, context):
        return can_start_adjust(context.scene.pose_bridge.target_rig)

    def execute(self, context):
        settings = context.scene.pose_bridge
        try:
            report = start_adjust(context, settings.target_rig)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.status = f"Adjust layer '{report.adjust_name}' added on top of '{report.base_name}'"
        self.report({"INFO"}, settings.status)
        return {"FINISHED"}


class POSEBRIDGE_OT_adjust_discard(bpy.types.Operator):
    bl_idname = "posebridge.adjust_discard"
    bl_label = "Discard Adjust"
    bl_description = "Throw away the adjustments and go back to the plain animation (Undo Apply brings them back)"

    @classmethod
    def poll(cls, context):
        return has_adjust(context.scene.pose_bridge.target_rig)

    def execute(self, context):
        settings = context.scene.pose_bridge
        try:
            base = discard_adjust(context, settings.target_rig)
        except ApplyError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        settings.status = f"Adjustments discarded; '{base}' is the active animation again"
        self.report({"INFO"}, settings.status)
        return {"FINISHED"}
