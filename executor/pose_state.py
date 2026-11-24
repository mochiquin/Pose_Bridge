"""Capture and restore the pose of a rig: bone transforms, MHX switches, the action and Pose Bridge's NLA layers."""

from __future__ import annotations

from typing import Any

import bpy

from ..core import TRACK_NAME

MHX_PROP_PREFIX = "Mha"


def _capture_layers(rig: bpy.types.Object) -> dict[str, Any] | None:
    animation_data = rig.animation_data
    if animation_data is None:
        return None
    return {
        "blend": animation_data.action_blend_type,
        "influence": animation_data.action_influence,
        "slot": animation_data.action_slot,
        "tracks": [
            [(s.name, s.action, s.action_slot, s.frame_start) for s in track.strips]
            for track in animation_data.nla_tracks
            if track.name == TRACK_NAME
        ],
    }


def capture_pose(rig: bpy.types.Object) -> dict[str, Any]:
    bones = {
        pb.name: (
            tuple(pb.location),
            tuple(pb.rotation_quaternion),
            tuple(pb.rotation_euler),
            tuple(pb.scale),
            pb.rotation_mode,
        )
        for pb in rig.pose.bones
    }
    props = {key: rig[key] for key in rig.keys() if key.startswith(MHX_PROP_PREFIX)}
    animation_data = rig.animation_data
    return {
        "bones": bones,
        "props": props,
        "action": animation_data.action if animation_data else None,
        "layers": _capture_layers(rig),
    }


def _restore_layers(rig: bpy.types.Object, layers: dict[str, Any] | None) -> None:
    """Put Pose Bridge's NLA base track back to what it was (our own tracks only; the user's are never touched)."""
    animation_data = rig.animation_data
    if animation_data is None:
        return
    for track in [t for t in animation_data.nla_tracks if t.name == TRACK_NAME]:
        animation_data.nla_tracks.remove(track)
    if layers is None:
        return
    for strips in layers["tracks"]:
        track = animation_data.nla_tracks.new()
        track.name = TRACK_NAME
        for name, action, slot, start in strips:
            strip = track.strips.new(name, int(start), action)
            if slot is not None and strip.action_slot is None:
                strip.action_slot = slot
    animation_data.action_blend_type = layers["blend"]
    animation_data.action_influence = layers["influence"]


def restore_pose(rig: bpy.types.Object, state: dict[str, Any]) -> None:
    for pb in rig.pose.bones:
        saved = state["bones"].get(pb.name)
        if saved is None:
            continue
        location, quaternion, euler, scale, mode = saved
        pb.rotation_mode = mode
        pb.location = location
        pb.rotation_quaternion = quaternion
        pb.rotation_euler = euler
        pb.scale = scale
    for key, value in state["props"].items():
        rig[key] = value

    wanted = state["action"]
    layers = state.get("layers")
    if wanted is not None and rig.animation_data is None:
        rig.animation_data_create()
    if rig.animation_data is not None:
        _restore_layers(rig, layers)
        if rig.animation_data.action != wanted:
            rig.animation_data.action = wanted
        slot = layers["slot"] if layers else None
        if wanted is not None and slot is not None and rig.animation_data.action_slot != slot:
            rig.animation_data.action_slot = slot


def changed_bone_names(rig: bpy.types.Object, state: dict[str, Any]) -> set[str]:
    """Names of the pose bones whose transform differs from a previously captured state."""
    changed: set[str] = set()
    for pb in rig.pose.bones:
        saved = state["bones"].get(pb.name)
        if saved is not None and (
            (tuple(pb.location), tuple(pb.rotation_quaternion), tuple(pb.rotation_euler), tuple(pb.scale)) != saved[:4]
        ):
            changed.add(pb.name)
    return changed


def count_changed_bones(rig: bpy.types.Object, state: dict[str, Any]) -> int:
    """How many pose bones differ from a previously captured state."""
    changed = 0
    for pb in rig.pose.bones:
        saved = state["bones"].get(pb.name)
        if saved is None:
            continue
        if (tuple(pb.location), tuple(pb.rotation_quaternion), tuple(pb.rotation_euler), tuple(pb.scale)) != saved[:4]:
            changed += 1
    return changed
