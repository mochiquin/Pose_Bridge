"""Snapshot of a rig used to roll back an operation that fails half-way.

The user-facing undo/redo (including manual joint edits) lives in ``character_history``.
"""

from __future__ import annotations

from typing import Any

import bpy

from .pose_state import capture_pose, restore_pose


def begin_undo(context: bpy.types.Context, rig: bpy.types.Object) -> dict[str, Any]:
    """Snapshot what an operation may touch: pose, MHX switches, action, NLA layers, frame range, known actions."""
    scene = context.scene
    state = capture_pose(rig)
    state["scene_name"] = scene.name
    state["scene_frames"] = (scene.frame_start, scene.frame_end, scene.frame_current)
    state["known_actions"] = {a.name for a in bpy.data.actions}
    return state


def revert(rig: bpy.types.Object, state: dict[str, Any]) -> None:
    """Roll ``rig`` back to ``state`` and drop actions that the failed operation created and nothing uses."""
    restore_pose(rig, state)
    for action in state.get("fake_user_added", []):
        if action.users > 1:  # used by something besides the keep-alive flag, so the flag is not needed any more
            action.use_fake_user = False
    scene = bpy.data.scenes.get(state.get("scene_name", ""))
    if scene is not None and "scene_frames" in state:
        scene.frame_start, scene.frame_end, current = state["scene_frames"]
        scene.frame_set(current)
    for action in [a for a in bpy.data.actions if a.name not in state.get("known_actions", set())]:
        if action.users == 0 and not action.use_fake_user:
            bpy.data.actions.remove(action)
