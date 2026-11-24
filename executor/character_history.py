"""Per-character undo/redo of the pose, including joints the user moves by hand.

Each character (rig) has its own timeline of pose states. A change is recorded when

* an add-on operation finishes (``recorded_change``: apply, T-pose, adjust layer), or
* the user changed the rig some other way (moved a joint...) and then stopped: a light timer looks at every
  tracked rig every ``POLL_SECONDS`` and records a change once two looks in a row see the same new pose.

Undo/Redo restore only this rig, so anything else in the scene is never touched, and the history is not
affected by what the user does to other objects in between. For a rig that plays an animation the pose is a
function of the frame, so bone transforms are not compared (scrubbing is not an edit); the action, the NLA
layers and the add-on's own operations are still tracked.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import bpy

from ..core import Timeline
from ..core.timeline import DEFAULT_LIMIT, clamp_limit
from .errors import ApplyError
from .pose_state import capture_pose, restore_pose

POLL_SECONDS = 0.3
_TOLERANCE = 1e-6  # DAZ drivers re-evaluate with ~1e-16 noise; real edits are far larger

_timelines: dict[str, Timeline[dict[str, Any]]] = {}
_limit = DEFAULT_LIMIT
_last_live: dict[str, dict[str, Any]] = {}  # a changed pose seen once, waiting to be seen unchanged
_timer_running = False


def _is_animated(rig: bpy.types.Object) -> bool:
    animation_data = rig.animation_data
    return animation_data is not None and (animation_data.action is not None or len(animation_data.nla_tracks) > 0)


def _snapshot(context: bpy.types.Context, rig: bpy.types.Object) -> dict[str, Any]:
    state = capture_pose(rig)
    state["frames"] = (context.scene.frame_start, context.scene.frame_end)
    state["animated"] = _is_animated(rig)
    return state


def _vectors_differ(a: tuple, b: tuple) -> bool:
    return any(abs(x - y) > _TOLERANCE for x, y in zip(a, b, strict=True))


def states_differ(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True when two snapshots are different poses worth separate undo steps."""
    if a["action"] != b["action"] or a["layers"] != b["layers"]:
        return True
    if a["animated"] or b["animated"]:
        return False  # the pose follows the frame; scrubbing the timeline is not an edit
    if a["props"] != b["props"]:
        return True
    for name, bone_a in a["bones"].items():
        bone_b = b["bones"].get(name)
        if bone_b is None or bone_a[4] != bone_b[4]:
            return True
        if any(_vectors_differ(bone_a[i], bone_b[i]) for i in range(4)):
            return True
    return False


def set_limit(limit: int) -> None:
    """How many undo steps are remembered per character (older ones are forgotten first)."""
    global _limit
    _limit = clamp_limit(limit)
    for timeline in _timelines.values():
        timeline.set_limit(_limit)


def track(context: bpy.types.Context, rig: bpy.types.Object | None) -> None:
    """Start recording ``rig`` (its current pose becomes the first state); a no-op if it is already tracked."""
    if rig is not None and rig.type == "ARMATURE" and rig.name not in _timelines:
        _timelines[rig.name] = Timeline(_snapshot(context, rig), _limit)
        _start_polling()


def sync(context: bpy.types.Context, rig: bpy.types.Object) -> bool:
    """Record the rig's live pose as a new step if it differs from the last recorded state."""
    timeline = _timelines.get(rig.name)
    if timeline is None:
        track(context, rig)
        return False
    live = _snapshot(context, rig)
    _last_live.pop(rig.name, None)
    if states_differ(timeline.current, live):
        timeline.record(live)
        return True
    timeline.replace_current(live)
    return False


@contextmanager
def recorded_change(context: bpy.types.Context, rig: bpy.types.Object) -> Iterator[None]:
    """Make an operation exactly one undo step: pending manual edits are closed first, then the operation."""
    sync(context, rig)
    try:
        yield
    finally:
        sync(context, rig)


def depth(rig: bpy.types.Object | None) -> tuple[int, int]:
    """``(undo steps, redo steps)`` available for ``rig``."""
    timeline = _timelines.get(rig.name) if rig is not None else None
    return (timeline.undo_depth, timeline.redo_depth) if timeline is not None else (0, 0)


def has_pending_edit(rig: bpy.types.Object | None) -> bool:
    """True while a manual edit has been noticed but is not yet an undo step (the user may still be moving)."""
    return rig is not None and rig.name in _last_live


def _restore(
    context: bpy.types.Context, rig: bpy.types.Object, target: dict[str, Any], came_from: dict[str, Any]
) -> None:
    restore_pose(rig, target)
    scene = context.scene
    # The timeline range only follows the pose history while the user has not set their own range since.
    if (scene.frame_start, scene.frame_end) == came_from["frames"] and target["frames"] != came_from["frames"]:
        scene.frame_start, scene.frame_end = target["frames"]
    timeline = _timelines[rig.name]
    timeline.replace_current(_snapshot(context, rig))


def _step(context: bpy.types.Context, rig: bpy.types.Object, direction: str) -> int:
    sync(context, rig)  # a manual edit made a moment ago becomes a step first, so it can be undone too
    timeline = _timelines.get(rig.name)
    if timeline is None:
        raise ApplyError("Nothing to undo for this character")
    while True:
        came_from = timeline.current
        try:
            target = timeline.undo() if direction == "undo" else timeline.redo()
        except IndexError:
            raise ApplyError(f"Nothing (more) to {direction}") from None
        try:
            _restore(context, rig, target, came_from)
            return timeline.undo_depth if direction == "undo" else timeline.redo_depth
        except ReferenceError:  # an action of that step was deleted in the meantime: skip the step
            timeline.discard_unrestorable(direction)


def undo(context: bpy.types.Context, rig: bpy.types.Object) -> int:
    """Undo the last change of ``rig``; returns how many more steps can be undone."""
    return _step(context, rig, "undo")


def redo(context: bpy.types.Context, rig: bpy.types.Object) -> int:
    """Redo the last undone change of ``rig``; returns how many more steps can be redone."""
    return _step(context, rig, "redo")


# --- automatic recording of manual edits -----------------------------------------------------------------


def _poll() -> float | None:
    """Timer: record manual edits of the tracked rigs. Returns the delay until the next look, or None to stop."""
    global _timer_running
    if not _timelines:
        _timer_running = False
        return None
    context = bpy.context
    for name in list(_timelines):
        rig = bpy.data.objects.get(name)
        if rig is None:
            _timelines.pop(name, None)
            _last_live.pop(name, None)
            continue
        try:
            live = _snapshot(context, rig)
            timeline = _timelines[name]
            if states_differ(timeline.current, live):
                seen = _last_live.get(name)
                if seen is not None and not states_differ(seen, live):  # unchanged since the last look: settled
                    timeline.record(live)
                    _last_live.pop(name, None)
                else:
                    _last_live[name] = live
            else:
                _last_live.pop(name, None)
                timeline.replace_current(live)
        except ReferenceError:
            _timelines.pop(name, None)
            _last_live.pop(name, None)
    return POLL_SECONDS


def _start_polling() -> None:
    global _timer_running
    if not _timer_running:
        _timer_running = True
        bpy.app.timers.register(_poll, first_interval=POLL_SECONDS, persistent=True)


def reset() -> None:
    """Forget all histories (a different .blend was loaded, or the add-on is being disabled)."""
    global _timer_running
    _timelines.clear()
    _last_live.clear()
    if _timer_running and bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    _timer_running = False
