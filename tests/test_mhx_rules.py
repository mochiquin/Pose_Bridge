from __future__ import annotations

import pytest

from core import finger_sides, finger_switches_to_free, fk_switch_values
from core.mhx_rules import FINGER_SWITCH_PREFIX


@pytest.mark.parametrize(
    "name",
    ["f_index.01.L", "f_middle.03.R", "f_ring.02.L", "f_pinky.01.R", "thumb.01.L", "thumb.03.R"],
)
def test_finger_bones_are_recognised(name: str) -> None:
    assert finger_sides([name]) == [name[-1]]


@pytest.mark.parametrize(
    "name",
    ["palm_index.L", "index.L", "hand.fk.L", "forearm.fk.R", "f_index.01", "f_index.01.L.001", "thumb.L", "spine", ""],
)
def test_other_bones_are_not_fingers(name: str) -> None:
    assert finger_sides([name]) == []


def test_sides_are_reported_once_and_in_order() -> None:
    names = ["f_ring.01.R", "spine", "f_index.01.L", "f_index.02.L", "thumb.01.R"]
    assert finger_sides(names) == ["L", "R"]
    assert finger_sides(["f_index.01.R"]) == ["R"]
    assert finger_sides([]) == []


def test_only_switches_that_are_on_are_freed() -> None:
    switches = {f"{FINGER_SWITCH_PREFIX}L": True, f"{FINGER_SWITCH_PREFIX}R": False, "MhaArmIk_L": 0.0}
    assert finger_switches_to_free(["f_index.01.L", "f_index.01.R"], switches) == [f"{FINGER_SWITCH_PREFIX}L"]


def test_missing_switches_and_non_boolean_values_are_ignored() -> None:
    assert finger_switches_to_free(["f_index.01.L"], {}) == []
    assert finger_switches_to_free(["f_index.01.L"], {f"{FINGER_SWITCH_PREFIX}L": 1.0}) == []
    assert finger_switches_to_free(["spine"], {f"{FINGER_SWITCH_PREFIX}L": True}) == []


MHX_DEFAULTS = {
    "MhaArmIk_L": 1.0,
    "MhaArmIk_R": 1.0,
    "MhaLegIk_L": 1.0,
    "MhaLegIk_R": 1.0,
    f"{FINGER_SWITCH_PREFIX}L": True,
    f"{FINGER_SWITCH_PREFIX}R": True,
    "MhaArmHinge_L": 0.0,
    "MhaLimitsOn": True,
}


def test_fk_switches_turn_limbs_to_fk_and_fingers_off_keeping_types() -> None:
    changes = fk_switch_values(MHX_DEFAULTS)
    assert changes == {
        "MhaArmIk_L": 0.0,
        "MhaArmIk_R": 0.0,
        "MhaLegIk_L": 0.0,
        "MhaLegIk_R": 0.0,
        f"{FINGER_SWITCH_PREFIX}L": False,
        f"{FINGER_SWITCH_PREFIX}R": False,
    }
    assert all(isinstance(v, bool) for k, v in changes.items() if k.startswith(FINGER_SWITCH_PREFIX))
    assert all(isinstance(v, float) for k, v in changes.items() if k.startswith("Mha") and "Ik" in k)


def test_fk_switches_leave_other_switches_alone() -> None:
    changes = fk_switch_values(MHX_DEFAULTS)
    assert "MhaArmHinge_L" not in changes
    assert "MhaLimitsOn" not in changes


def test_fk_switches_skip_ones_already_in_fk_or_missing() -> None:
    already = {"MhaArmIk_L": 0.0, f"{FINGER_SWITCH_PREFIX}L": False, "MhaLegIk_R": 1.0}
    assert fk_switch_values(already) == {"MhaLegIk_R": 0.0}
    assert fk_switch_values({}) == {}
    assert fk_switch_values({"MhaArmHinge_L": 1.0}) == {}


def test_partial_ik_values_are_switched_to_fk() -> None:
    assert fk_switch_values({"MhaArmIk_L": 0.4}) == {"MhaArmIk_L": 0.0}
