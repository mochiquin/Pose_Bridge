from __future__ import annotations

import json
import math

import pytest

from core import PoseFileError, dumps, loads, make_pose_data, match_bones
from core.pose_schema import EXTENSION, FORMAT, VERSION, validate


def _bone(**overrides):
    record = {"loc": [0, 0, 0], "quat": [1, 0, 0, 0], "euler": [0, 0, 0], "scale": [1, 1, 1], "mode": "QUATERNION"}
    record.update(overrides)
    return record


def _pose(**overrides):
    data = {
        "format": FORMAT,
        "version": VERSION,
        "name": "Sit",
        "bones": {"hip": _bone(), "spine": _bone(loc=[0.1, 0, 0])},
        "props": {"MhaArmIk_L": 0.0, "MhaLimitsOn": True},
    }
    data.update(overrides)
    return data


def test_extension_constant() -> None:
    assert EXTENSION == ".pbpose"


def test_roundtrip_keeps_every_value() -> None:
    data = make_pose_data(
        "Katana",
        {"hip": _bone(mode="XYZ", euler=[0.1, 0.2, 0.3])},
        {"MhaArmIk_L": 1.0},
        rig_name="Lady Maira",
        created="2026-11-23",
    )
    again = loads(dumps(data))
    assert again == data
    assert again["bones"]["hip"]["euler"] == [0.1, 0.2, 0.3]
    assert again["rig"] == "Lady Maira"


def test_dumps_is_valid_utf8_json_with_non_ascii_names() -> None:
    text = dumps(make_pose_data("坐姿", {"hip": _bone()}))
    assert json.loads(text)["name"] == "坐姿"
    assert "坐姿" in text


def test_validate_fills_defaults_and_coerces_numbers_to_float() -> None:
    cleaned = validate(
        _pose(bones={"hip": {"loc": [1, 2, 3], "quat": [1, 0, 0, 0], "euler": [0, 0, 0], "scale": [1, 1, 1]}})
    )
    assert cleaned["bones"]["hip"]["mode"] == "QUATERNION"
    assert all(isinstance(v, float) for v in cleaned["bones"]["hip"]["loc"])
    assert cleaned["rig"] == "" and cleaned["created"] == ""


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(format="something else"),
        lambda d: d.pop("format"),
        lambda d: d.update(version=0),
        lambda d: d.update(version="1"),
        lambda d: d.update(version=True),
        lambda d: d.update(bones={}),
        lambda d: d.update(bones=[]),
        lambda d: d["bones"].update(hip=_bone(loc=[0, 0])),
        lambda d: d["bones"].update(hip=_bone(quat=[1, 0, 0])),
        lambda d: d["bones"].update(hip=_bone(loc=[0, 0, math.nan])),
        lambda d: d["bones"].update(hip=_bone(scale=[1, math.inf, 1])),
        lambda d: d["bones"].update(hip=_bone(loc=["a", 0, 0])),
        lambda d: d["bones"].update(hip=_bone(loc=[True, 0, 0])),
        lambda d: d["bones"].update(hip=_bone(mode="SPIN")),
        lambda d: d["bones"].update(hip="not an object"),
        lambda d: d.update(props={"x": "text"}),
        lambda d: d.update(props={"x": math.nan}),
        lambda d: d.update(props=[1]),
    ],
)
def test_invalid_documents_are_rejected(mutation) -> None:
    data = _pose()
    mutation(data)
    with pytest.raises(PoseFileError):
        validate(data)


def test_newer_version_is_rejected_with_a_helpful_message() -> None:
    with pytest.raises(PoseFileError, match="newer"):
        validate(_pose(version=VERSION + 1))


def test_loads_rejects_non_json_and_non_objects() -> None:
    with pytest.raises(PoseFileError, match="JSON"):
        loads("{broken")
    with pytest.raises(PoseFileError):
        loads("[1, 2]")


def test_match_bones_splits_in_file_order() -> None:
    matched, missing = match_bones(["hip", "tail", "spine", "wing"], ["spine", "hip", "head"])
    assert matched == ["hip", "spine"]
    assert missing == ["tail", "wing"]
    assert match_bones([], ["hip"]) == ([], [])
