bl_info = {
    "name": "Pose Bridge",
    "author": "Material Converter project",
    "version": (0, 1, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Pose Bridge",
    "description": "Browse DAZ pose/animation libraries and apply them to an MHX rig (requires DAZ Importer)",
    "category": "Animation",
}

try:
    import bpy
    from bpy.app.handlers import persistent
except ImportError:  # imported outside Blender (pytest): only core/ is usable
    bpy = None

if bpy is not None:
    from . import executor, operators, preferences, properties, ui_panel

    _CLASSES = (
        preferences.PoseBridgeRoot,
        preferences.PoseBridgePreferences,
        properties.PoseBridgeSettings,
        operators.POSEBRIDGE_OT_add_root,
        operators.POSEBRIDGE_OT_remove_root,
        operators.POSEBRIDGE_OT_add_daz_roots,
        operators.POSEBRIDGE_OT_rescan,
        operators.POSEBRIDGE_OT_open_folder,
        operators.POSEBRIDGE_OT_up,
        operators.POSEBRIDGE_OT_page,
        operators.POSEBRIDGE_OT_pick,
        operators.POSEBRIDGE_OT_apply,
        operators.POSEBRIDGE_OT_undo_apply,
        operators.POSEBRIDGE_OT_redo,
        operators.POSEBRIDGE_OT_tpose,
        operators.POSEBRIDGE_OT_save_pose,
        operators.POSEBRIDGE_OT_adjust_start,
        operators.POSEBRIDGE_OT_adjust_discard,
        ui_panel.POSEBRIDGE_PT_main,
        ui_panel.POSEBRIDGE_PT_display,
    )

    def _track_all() -> None:
        for scene in bpy.data.scenes:
            if hasattr(scene, "pose_bridge") and scene.pose_bridge.target_rig is not None:
                executor.track_character(bpy.context, scene.pose_bridge.target_rig)

    def _track_all_once() -> None:
        _track_all()
        return None

    @persistent
    def _on_load_post(_dummy) -> None:
        executor.reset_histories()  # a different .blend: the old characters are gone
        operators.restore_from_cache(bpy.context)
        _track_all()

    def register() -> None:
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
        ui_panel.register()
        bpy.types.Scene.pose_bridge = bpy.props.PointerProperty(type=properties.PoseBridgeSettings)
        bpy.app.handlers.load_post.append(_on_load_post)
        operators.sync_undo_limit(bpy.context)
        # bpy.data is restricted while an add-on registers: start tracking right after it is enabled
        bpy.app.timers.register(_track_all_once, first_interval=0.1, persistent=True)

    def unregister() -> None:
        if _on_load_post in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(_on_load_post)
        executor.reset_histories()
        del bpy.types.Scene.pose_bridge
        ui_panel.unregister()
        for cls in reversed(_CLASSES):
            bpy.utils.unregister_class(cls)
