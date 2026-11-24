"""Apply a library file to an MHX rig: DAZ pose/animation files via DAZ Importer, Pose Bridge pose files directly."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bpy

from ..core import KIND_ANIMATION, KIND_POSE, KIND_UNKNOWN, POSE_EXTENSION, sniff_duf_kind
from .adjust_layer import has_adjust
from .character_history import recorded_change
from .errors import ApplyError
from .group_mount import mounted
from .mhx_switches import action_bone_names, free_fingers
from .pose_file import apply_pose_file
from .pose_state import changed_bone_names, count_changed_bones
from .undo_state import begin_undo, revert


@dataclass(frozen=True)
class ApplyReport:
    kind: str
    bones_changed: int
    action_name: str
    frame_range: tuple[int, int] | None
    fingers_freed: tuple[str, ...] = ()  # sides whose finger controls were switched to FK so the pose shows


def daz_importer_ready() -> bool:
    ops = getattr(bpy.ops, "daz", None)
    return ops is not None and hasattr(ops, "import_pose") and hasattr(ops, "import_action")


def needs_daz_importer(path: Path | str) -> bool:
    """Pose Bridge's own pose files can be applied without DAZ Importer."""
    return Path(path).suffix.lower() != POSE_EXTENSION


def _view3d_override(context: bpy.types.Context) -> dict[str, Any]:
    window = context.window or context.window_manager.windows[0]
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        raise ApplyError("A 3D Viewport is required to import DAZ files")
    region = next(r for r in area.regions if r.type == "WINDOW")
    return {"window": window, "area": area, "region": region}


def _apply_library_file(
    context: bpy.types.Context,
    rig: bpy.types.Object,
    path: Path,
    kind: str,
    *,
    set_frame_range: bool = True,
) -> ApplyReport:
    """Apply ``path`` to ``rig``. The previous state is remembered for ``undo_last_apply``."""
    if rig is None or rig.type != "ARMATURE":
        raise ApplyError("Choose an armature as the target rig")
    if has_adjust(rig):
        raise ApplyError(
            "This rig has an adjust layer: use 'Discard Adjust' (or T-Pose) before applying something else"
        )
    path = Path(path)
    if not path.is_file():
        raise ApplyError(f"File not found: {path}")
    if path.suffix.lower() == POSE_EXTENSION:
        result = apply_pose_file(context, rig, path)
        return ApplyReport(kind=KIND_POSE, bones_changed=result.bones_changed, action_name="", frame_range=None)

    if not daz_importer_ready():
        raise ApplyError("DAZ Importer is not enabled")
    if kind == KIND_UNKNOWN:
        kind = sniff_duf_kind(path)
    if kind == KIND_UNKNOWN:
        raise ApplyError(f"Cannot tell whether {path.name} is a pose or an animation")

    operator = bpy.ops.daz.import_action if kind == KIND_ANIMATION else bpy.ops.daz.import_pose
    state = begin_undo(context, rig)

    with mounted(context, rig):
        view_layer = context.view_layer
        for obj in view_layer.objects:
            obj.select_set(False)
        view_layer.objects.active = rig
        rig.select_set(True)
        override = _view3d_override(context)
        try:
            with context.temp_override(**override, active_object=rig, object=rig, selected_objects=[rig]):
                result = operator(filepath=str(path), files=[{"name": path.name}], directory=str(path.parent) + os.sep)
        except RuntimeError as exc:
            revert(rig, state)
            raise ApplyError(f"DAZ Importer failed: {exc}") from exc
        finally:
            rig.select_set(False)
        if "FINISHED" not in result:
            revert(rig, state)
            raise ApplyError(f"DAZ Importer did not finish ({sorted(result)})")

        action = rig.animation_data.action if rig.animation_data else None
        frame_range: tuple[int, int] | None = None
        if kind == KIND_ANIMATION and action is not None:
            first, last = action.frame_range
            frame_range = (math.floor(first), math.ceil(last))
            if set_frame_range:
                context.scene.frame_start, context.scene.frame_end = frame_range
                context.scene.frame_set(frame_range[0])
        touched = changed_bone_names(rig, state)
        if kind == KIND_ANIMATION and action is not None:
            touched |= action_bone_names(action)
        return ApplyReport(
            kind=kind,
            bones_changed=count_changed_bones(rig, state),
            action_name=action.name if action else "",
            frame_range=frame_range,
            fingers_freed=free_fingers(rig, touched),
        )


def apply_library_file(
    context: bpy.types.Context,
    rig: bpy.types.Object,
    path: Path,
    kind: str,
    *,
    set_frame_range: bool = True,
) -> ApplyReport:
    """Apply ``path`` to ``rig``; the whole application is one step of the character's undo history."""
    if rig is None or rig.type != "ARMATURE":
        raise ApplyError("Choose an armature as the target rig")
    with recorded_change(context, rig):
        return _apply_library_file(context, rig, path, kind, set_frame_range=set_frame_range)
