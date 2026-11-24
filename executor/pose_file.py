"""Save the current pose of a rig to a Pose Bridge pose file and apply such files back."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import bpy

from ..core import (
    POSE_EXTENSION,
    PoseFileError,
    dumps,
    loads,
    make_pose_data,
    match_bones,
    sanitize_filename,
    unique_stem,
)
from .errors import ApplyError
from .pose_state import MHX_PROP_PREFIX, count_changed_bones
from .undo_state import begin_undo, revert


@dataclass(frozen=True)
class PoseApplyResult:
    bones_changed: int
    missing: tuple[str, ...]
    props_applied: int


def capture_pose_data(rig: bpy.types.Object, name: str) -> dict[str, Any]:
    """Describe the current pose of ``rig``: every pose bone's transform and the MHX switches."""
    bones = {
        pb.name: {
            "loc": list(pb.location),
            "quat": list(pb.rotation_quaternion),
            "euler": list(pb.rotation_euler),
            "scale": list(pb.scale),
            "mode": pb.rotation_mode,
        }
        for pb in rig.pose.bones
    }
    props = {
        key: rig[key]
        for key in rig.keys()
        if key.startswith(MHX_PROP_PREFIX) and isinstance(rig[key], (bool, int, float))
    }
    return make_pose_data(name, bones, props, rig_name=rig.name, created=datetime.now().isoformat(timespec="seconds"))


def save_pose_file(rig: bpy.types.Object, folder: Path, name: str, subfolders: tuple[str, ...] = ()) -> Path:
    """Write the pose of ``rig`` into ``folder/subfolders``; an existing file is never overwritten."""
    if rig is None or rig.type != "ARMATURE":
        raise ApplyError("Choose an armature as the target rig")
    target_dir = Path(folder).joinpath(*subfolders)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        taken = [p.stem for p in target_dir.glob(f"*{POSE_EXTENSION}")]
        stem = unique_stem(taken, sanitize_filename(name))
        path = target_dir / f"{stem}{POSE_EXTENSION}"
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(dumps(capture_pose_data(rig, stem)), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        raise ApplyError(f"Could not save the pose: {exc}") from exc
    return path


def apply_pose_data(rig: bpy.types.Object, data: dict[str, Any]) -> PoseApplyResult:
    """Set the transforms of every bone the rig shares with ``data``; other bones are left alone."""
    matched, missing = match_bones(data["bones"], (pb.name for pb in rig.pose.bones))
    if not matched:
        raise ApplyError("None of the bones in this pose exist on the target rig")
    for name in matched:
        record = data["bones"][name]
        pb = rig.pose.bones[name]
        pb.rotation_mode = record["mode"]
        pb.location = record["loc"]
        pb.rotation_quaternion = record["quat"]
        pb.rotation_euler = record["euler"]
        pb.scale = record["scale"]
    props_applied = 0
    for key, value in data["props"].items():
        if key in rig.keys():
            rig[key] = value
            props_applied += 1
    return PoseApplyResult(bones_changed=len(matched), missing=tuple(missing), props_applied=props_applied)


def apply_pose_file(context: bpy.types.Context, rig: bpy.types.Object, path: Path) -> PoseApplyResult:
    """Apply a pose file to ``rig``; on failure the rig is rolled back."""
    try:
        data = loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise ApplyError(f"Could not read {Path(path).name}: {exc}") from exc
    except PoseFileError as exc:
        raise ApplyError(f"{Path(path).name}: {exc}") from exc
    state = begin_undo(context, rig)
    try:
        result = apply_pose_data(rig, data)
    except ApplyError:
        revert(rig, state)
        raise
    return PoseApplyResult(
        bones_changed=count_changed_bones(rig, state), missing=result.missing, props_applied=result.props_applied
    )
