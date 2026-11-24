"""Non-destructive adjustment of an imported animation: the animation becomes an NLA base, edits go to a new action."""

from __future__ import annotations

from dataclasses import dataclass

import bpy

from ..core import TRACK_NAME, plan_layers
from .character_history import recorded_change
from .errors import ApplyError


@dataclass(frozen=True)
class AdjustReport:
    base_name: str
    adjust_name: str


def has_adjust(rig: bpy.types.Object | None) -> bool:
    """True when ``rig`` carries a Pose Bridge adjust layer (base on the NLA, edits in the active action)."""
    animation_data = rig.animation_data if rig is not None else None
    return animation_data is not None and any(t.name == TRACK_NAME for t in animation_data.nla_tracks)


def can_start_adjust(rig: bpy.types.Object | None) -> bool:
    animation_data = rig.animation_data if rig is not None else None
    return animation_data is not None and animation_data.action is not None and not has_adjust(rig)


def adjust_action_name(rig: bpy.types.Object | None) -> str:
    """Name of the action that currently collects the user's edits ('' when there is no adjust layer)."""
    if not has_adjust(rig) or rig.animation_data.action is None:
        return ""
    return rig.animation_data.action.name


def start_adjust(context: bpy.types.Context, rig: bpy.types.Object) -> AdjustReport:
    """Layer an empty 'Combine' action on top of the rig's animation (one step of the undo history)."""
    if rig is None or rig.type != "ARMATURE":
        raise ApplyError("Choose an armature as the target rig")
    with recorded_change(context, rig):
        return _start_adjust(context, rig)


def _start_adjust(context: bpy.types.Context, rig: bpy.types.Object) -> AdjustReport:
    if has_adjust(rig):
        raise ApplyError("This rig already has an adjust layer")
    animation_data = rig.animation_data
    if animation_data is None or animation_data.action is None:
        raise ApplyError("Apply an animation first: there is nothing to adjust")

    base = animation_data.action
    base_slot = animation_data.action_slot
    plan = plan_layers(base.name, tuple(base.frame_range), (a.name for a in bpy.data.actions))

    track = animation_data.nla_tracks.new()
    track.name = plan.track_name
    strip = track.strips.new(plan.strip_name, plan.strip_start, base)
    if strip.action_slot is None and base_slot is not None:
        strip.action_slot = base_slot

    adjust = bpy.data.actions.new(plan.adjust_name)
    animation_data.action = adjust
    animation_data.action_slot = adjust.slots.new("OBJECT", rig.name)
    animation_data.action_blend_type = "COMBINE"
    animation_data.action_influence = 1.0

    return AdjustReport(base_name=base.name, adjust_name=adjust.name)


def discard_adjust(context: bpy.types.Context, rig: bpy.types.Object) -> str:
    """Throw the adjustments away and make the original animation the plain active action again.

    The adjust action is only unassigned, so Undo can bring it back during this session; Blender drops it
    for good when the file is saved. Returns the name of the animation that is active again.
    """
    if not has_adjust(rig):
        raise ApplyError("This rig has no adjust layer")
    with recorded_change(context, rig):
        return _discard_adjust(rig)


def _discard_adjust(rig: bpy.types.Object) -> str:
    animation_data = rig.animation_data

    track = next(t for t in animation_data.nla_tracks if t.name == TRACK_NAME)
    strip = track.strips[0]
    base, slot = strip.action, strip.action_slot
    animation_data.action = None
    animation_data.nla_tracks.remove(track)
    animation_data.action_blend_type = "REPLACE"
    animation_data.action = base
    if slot is not None:
        animation_data.action_slot = slot

    return base.name
