"""The Pose Bridge pose file: a small JSON document with bone transforms and MHX switches (no Blender).

A pose file is independent of any .blend project: it stores only the transforms of pose bones by name,
so it can be applied to any rig that has bones with the same names (e.g. every MHX-converted Genesis 8).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from typing import Any

FORMAT = "pose_bridge.pose"
VERSION = 1
EXTENSION = ".pbpose"

ROTATION_MODES = frozenset({"QUATERNION", "AXIS_ANGLE", "XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"})
_VECTOR_SIZES = {"loc": 3, "quat": 4, "euler": 3, "scale": 3}


class PoseFileError(ValueError):
    """The text is not a valid, supported pose file."""


def _finite_vector(value: Any, size: int, where: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise PoseFileError(f"{where}: expected {size} numbers")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise PoseFileError(f"{where}: values must be finite numbers")
        result.append(float(item))
    return result


def _clean_bone(name: str, record: Any) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise PoseFileError(f"bone '{name}': expected an object")
    cleaned: dict[str, Any] = {
        key: _finite_vector(record.get(key), size, f"bone '{name}' {key}") for key, size in _VECTOR_SIZES.items()
    }
    mode = record.get("mode", "QUATERNION")
    if mode not in ROTATION_MODES:
        raise PoseFileError(f"bone '{name}': unknown rotation mode {mode!r}")
    cleaned["mode"] = mode
    return cleaned


def _clean_props(props: Any) -> dict[str, bool | int | float]:
    if not isinstance(props, Mapping):
        raise PoseFileError("props: expected an object")
    cleaned: dict[str, bool | int | float] = {}
    for key, value in props.items():
        if isinstance(value, bool):
            cleaned[str(key)] = value
        elif isinstance(value, (int, float)) and math.isfinite(value):
            cleaned[str(key)] = value
        else:
            raise PoseFileError(f"prop '{key}': expected a boolean or a finite number")
    return cleaned


def make_pose_data(
    name: str,
    bones: Mapping[str, Mapping[str, Any]],
    props: Mapping[str, Any] | None = None,
    *,
    rig_name: str = "",
    created: str = "",
) -> dict[str, Any]:
    """Build and validate a pose document from captured bone transforms."""
    return validate(
        {
            "format": FORMAT,
            "version": VERSION,
            "name": name,
            "rig": rig_name,
            "created": created,
            "props": dict(props or {}),
            "bones": {bone: dict(record) for bone, record in bones.items()},
        }
    )


def validate(data: Any) -> dict[str, Any]:
    """Return a cleaned copy of ``data`` or raise :class:`PoseFileError`."""
    if not isinstance(data, Mapping):
        raise PoseFileError("not a pose file")
    if data.get("format") != FORMAT:
        raise PoseFileError("not a Pose Bridge pose file")
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise PoseFileError("missing or invalid version")
    if version > VERSION:
        raise PoseFileError(f"pose file version {version} is newer than this add-on supports ({VERSION})")
    bones = data.get("bones")
    if not isinstance(bones, Mapping) or not bones:
        raise PoseFileError("the pose has no bones")
    return {
        "format": FORMAT,
        "version": version,
        "name": str(data.get("name", "")),
        "rig": str(data.get("rig", "")),
        "created": str(data.get("created", "")),
        "props": _clean_props(data.get("props", {})),
        "bones": {str(name): _clean_bone(str(name), record) for name, record in bones.items()},
    }


def dumps(data: Mapping[str, Any]) -> str:
    return json.dumps(validate(data), ensure_ascii=False, indent=1)


def loads(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PoseFileError(f"not valid JSON: {exc.msg}") from exc
    return validate(data)


def match_bones(file_bones: Iterable[str], rig_bones: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split the bones of a pose file into those the rig has and those it lacks (both in file order)."""
    available = set(rig_bones)
    matched: list[str] = []
    missing: list[str] = []
    for name in file_bones:
        (matched if name in available else missing).append(name)
    return matched, missing
