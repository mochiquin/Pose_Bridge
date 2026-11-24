from __future__ import annotations

import math

import pytest

from core import LayerPlan, plan_layers
from core.adjust_plan import ADJUST_SUFFIX, TRACK_NAME


def test_plan_names_the_track_strip_and_adjust_action() -> None:
    plan = plan_layers("AOI G8F Hurting Idle", (1.0, 181.99998474121094), [])
    assert plan == LayerPlan(
        track_name=TRACK_NAME,
        strip_name="AOI G8F Hurting Idle",
        strip_start=1,
        adjust_name="AOI G8F Hurting Idle Adjust",
    )


def test_strip_starts_at_the_floor_of_the_first_frame() -> None:
    assert plan_layers("a", (0.0, 10.0), []).strip_start == 0
    assert plan_layers("a", (12.9, 40.0), []).strip_start == 12
    assert plan_layers("a", (-3.5, 10.0), []).strip_start == -4


def test_adjust_name_is_made_unique_against_existing_actions() -> None:
    existing = ["Walk Adjust", "walk adjust 2", "Other"]
    assert plan_layers("Walk", (1, 20), existing).adjust_name == "Walk Adjust 3"
    assert plan_layers("Run", (1, 20), existing).adjust_name == "Run Adjust"


def test_suffix_constant_matches_the_generated_name() -> None:
    assert plan_layers("x", (1, 2), []).adjust_name == f"x{ADJUST_SUFFIX}"


@pytest.mark.parametrize("bad", [(math.nan, 5.0), (1.0, math.inf), (-math.inf, 3.0)])
def test_non_finite_frame_ranges_are_rejected(bad) -> None:
    with pytest.raises(ValueError):
        plan_layers("a", bad, [])
