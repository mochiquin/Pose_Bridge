"""MHX switches that an imported pose or animation needs to be visible (the importer only handles the limbs)."""

from __future__ import annotations

import bpy

from ..core import finger_switches_to_free
from ..core.mhx_rules import FINGER_SWITCH_PREFIX


def action_bone_names(action: bpy.types.Action) -> set[str]:
    """Names of the pose bones that an action animates."""
    names: set[str] = set()
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for fcurve in channelbag.fcurves:
                    if fcurve.data_path.startswith('pose.bones["'):
                        names.add(fcurve.data_path.split('"')[1])
    return names


def free_fingers(rig: bpy.types.Object, changed_bones: set[str]) -> tuple[str, ...]:
    """Switch the finger controls of every side whose finger bones were changed to FK; returns the sides ('L', 'R')."""
    switches = {key: rig[key] for key in rig.keys() if key.startswith(FINGER_SWITCH_PREFIX)}
    freed = finger_switches_to_free(changed_bones, switches)
    for name in freed:
        rig[name] = False
    return tuple(name.removeprefix(FINGER_SWITCH_PREFIX) for name in freed)
