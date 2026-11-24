"""Plan the non-destructive adjustment layer of an animation (no Blender).

The imported animation becomes a strip on an NLA track named ``TRACK_NAME`` and a new, empty action is
layered on top of it with 'Combine' blending: whatever the user keys afterwards is stored as an offset
in that new action, so the original animation is never modified.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .pose_naming import unique_stem

TRACK_NAME = "PB Base"
ADJUST_SUFFIX = " Adjust"


@dataclass(frozen=True)
class LayerPlan:
    track_name: str
    strip_name: str
    strip_start: int
    adjust_name: str


def plan_layers(base_name: str, frame_range: tuple[float, float], existing_actions: Iterable[str]) -> LayerPlan:
    """Names and start frame for layering ``base_name``; the adjust action never reuses an existing name."""
    first, last = frame_range
    if not (math.isfinite(first) and math.isfinite(last)):
        raise ValueError("frame range must be finite")
    return LayerPlan(
        track_name=TRACK_NAME,
        strip_name=base_name,
        strip_start=math.floor(first),
        adjust_name=unique_stem(existing_actions, f"{base_name}{ADJUST_SUFFIX}"),
    )
