"""Rules about MHX rigs that decide which switches an imported pose needs (no Blender).

An imported DAZ pose writes rotations into the FK finger bones. MHX only shows them when the finger controls
of that side are switched off, otherwise a Copy Rotation constraint on every finger bone follows the control
bones instead and the pose is invisible.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_FINGER_BONE = re.compile(r"^(?:f_(?:index|middle|ring|pinky)\.\d+|thumb\.\d+)\.(?P<side>[LR])$")

FINGER_SWITCH_PREFIX = "MhaFingerControl_"


def finger_sides(bone_names: Iterable[str]) -> list[str]:
    """The sides (``'L'``/``'R'``) that have at least one finger bone among ``bone_names``, in L, R order."""
    found = {match.group("side") for name in bone_names if (match := _FINGER_BONE.match(name))}
    return [side for side in ("L", "R") if side in found]


def finger_switches_to_free(changed_bones: Iterable[str], switches: dict[str, object]) -> list[str]:
    """Names of the finger-control switches that must be turned off so the changed finger bones show.

    ``switches`` maps switch names to their current value; only switches that exist and are currently
    on are returned.
    """
    names = [f"{FINGER_SWITCH_PREFIX}{side}" for side in finger_sides(changed_bones)]
    return [name for name in names if switches.get(name) is True]
