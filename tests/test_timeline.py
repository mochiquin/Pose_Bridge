from __future__ import annotations

import pytest

from core import Timeline
from core.timeline import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT, clamp_limit


def _timeline(*states: str, limit: int = 20) -> Timeline[str]:
    timeline = Timeline(states[0], limit)
    for state in states[1:]:
        timeline.record(state)
    return timeline


def test_starts_with_only_the_initial_state() -> None:
    timeline = Timeline("a")
    assert (timeline.current, timeline.undo_depth, timeline.redo_depth) == ("a", 0, 0)


def test_record_makes_the_new_state_current() -> None:
    timeline = _timeline("a", "b", "c")
    assert (timeline.current, timeline.undo_depth, timeline.redo_depth) == ("c", 2, 0)


def test_undo_returns_the_state_before_and_redo_returns_it_again() -> None:
    timeline = _timeline("a", "b", "c")
    assert timeline.undo() == "b"
    assert timeline.undo() == "a"
    assert (timeline.undo_depth, timeline.redo_depth) == (0, 2)
    assert timeline.redo() == "b"
    assert timeline.redo() == "c"
    assert timeline.current == "c"


def test_undo_and_redo_at_the_ends_raise() -> None:
    timeline = _timeline("a", "b")
    with pytest.raises(IndexError):
        timeline.redo()
    timeline.undo()
    with pytest.raises(IndexError):
        timeline.undo()


def test_recording_after_an_undo_discards_the_redo_branch() -> None:
    timeline = _timeline("a", "b", "c")
    timeline.undo()
    timeline.record("x")
    assert (timeline.current, timeline.undo_depth, timeline.redo_depth) == ("x", 2, 0)
    assert timeline.undo() == "b"
    assert timeline.undo() == "a"


def test_the_oldest_steps_are_dropped_beyond_the_limit() -> None:
    timeline = _timeline("s0", "s1", "s2", "s3", "s4", limit=2)
    assert timeline.undo_depth == 2
    assert timeline.undo() == "s3"
    assert timeline.undo() == "s2"
    with pytest.raises(IndexError):
        timeline.undo()


def test_shrinking_the_limit_forgets_the_oldest_steps_but_keeps_redo() -> None:
    timeline = _timeline("a", "b", "c", "d", "e")
    timeline.undo()
    timeline.set_limit(2)
    assert (timeline.current, timeline.undo_depth, timeline.redo_depth) == ("d", 2, 1)
    assert timeline.redo() == "e"


def test_replace_current_changes_only_the_current_state() -> None:
    timeline = _timeline("a", "b")
    timeline.replace_current("b2")
    assert timeline.current == "b2"
    assert timeline.undo() == "a"
    assert timeline.redo() == "b2"
    assert timeline.undo_depth + timeline.redo_depth == 1


def test_skipping_an_unrestorable_undo_target_continues_with_older_steps() -> None:
    timeline = _timeline("a", "broken", "c")
    assert timeline.undo() == "broken"
    timeline.discard_unrestorable("undo")
    assert timeline.current == "c"  # the live state is still the current one
    assert timeline.undo() == "a"


def test_skipping_an_unrestorable_redo_target_continues_with_newer_steps() -> None:
    timeline = _timeline("a", "b", "broken", "d")
    timeline.undo()
    timeline.undo()
    timeline.undo()
    assert timeline.redo() == "b"
    assert timeline.redo() == "broken"
    timeline.discard_unrestorable("redo")
    assert timeline.current == "b"
    assert timeline.redo() == "d"


def test_limit_is_clamped_to_a_sane_range() -> None:
    assert clamp_limit(0) == MIN_LIMIT
    assert clamp_limit(-5) == MIN_LIMIT
    assert clamp_limit(10_000) == MAX_LIMIT
    assert clamp_limit(7) == 7
    assert Timeline("a").limit == DEFAULT_LIMIT
    assert Timeline("a", 0).limit == MIN_LIMIT
