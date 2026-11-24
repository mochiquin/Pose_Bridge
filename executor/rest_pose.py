"""Return a rig to its rest pose (T-pose): every bone at rest, MHX switches at their defaults, no animation."""

from __future__ import annotations

from dataclasses import dataclass

import bpy

from ..core import TRACK_NAME
from .adjust_layer import has_adjust
from .character_history import recorded_change
from .errors import ApplyError
from .pose_state import MHX_PROP_PREFIX, capture_pose, count_changed_bones


@dataclass(frozen=True)
class RestReport:
    bones_changed: int
    switches_reset: int
    kept_actions: tuple[str, ...]  # animations that were unassigned but kept in the file


def _ui_default(rig: bpy.types.Object, key: str):
    try:
        return rig.id_properties_ui(key).as_dict().get("default")
    except (TypeError, KeyError, RuntimeError):
        return None


def _drop_animation(rig: bpy.types.Object) -> tuple[str, ...]:
    """Unassign the active action and Pose Bridge's NLA layers, keeping every dropped action in the file."""
    animation_data = rig.animation_data
    if animation_data is None:
        return ()
    dropped = []
    if has_adjust(rig):
        for track in [t for t in animation_data.nla_tracks if t.name == TRACK_NAME]:
            dropped.extend(s.action for s in track.strips if s.action is not None)
            animation_data.nla_tracks.remove(track)
        animation_data.action_blend_type = "REPLACE"
    if animation_data.action is not None:
        dropped.append(animation_data.action)
        animation_data.action = None

    for action in dropped:
        if action.users == 0 and not action.use_fake_user:
            action.use_fake_user = True  # keep the animation in the file instead of silently losing it
    return tuple(action.name for action in dropped)


def reset_to_tpose(context: bpy.types.Context, rig: bpy.types.Object) -> RestReport:
    """Put ``rig`` back to its rest pose; it is one step of the character's undo history."""
    if rig is None or rig.type != "ARMATURE":
        raise ApplyError("Choose an armature as the target rig")
    with recorded_change(context, rig):
        return _reset_to_tpose(rig)


def _reset_to_tpose(rig: bpy.types.Object) -> RestReport:
    before = capture_pose(rig)
    kept = _drop_animation(rig)

    for pb in rig.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)

    switches_reset = 0
    for key in [k for k in rig.keys() if k.startswith(MHX_PROP_PREFIX)]:
        default = _ui_default(rig, key)
        if default is not None and rig[key] != default:
            rig[key] = default
            switches_reset += 1

    changed = count_changed_bones(rig, before)
    return RestReport(bones_changed=changed, switches_reset=switches_reset, kept_actions=kept)
