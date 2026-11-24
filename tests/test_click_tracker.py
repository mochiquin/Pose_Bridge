from __future__ import annotations

from core import DoubleClickTracker

INTERVAL = 0.35


def test_first_click_is_never_a_double_click() -> None:
    assert DoubleClickTracker().register("a", 10.0, INTERVAL) is False


def test_two_quick_clicks_on_the_same_item_are_a_double_click() -> None:
    tracker = DoubleClickTracker()
    assert tracker.register("a", 10.0, INTERVAL) is False
    assert tracker.register("a", 10.2, INTERVAL) is True


def test_slow_second_click_is_not_a_double_click_but_starts_a_new_sequence() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    assert tracker.register("a", 10.6, INTERVAL) is False
    assert tracker.register("a", 10.8, INTERVAL) is True


def test_clicks_on_different_items_are_not_a_double_click() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    assert tracker.register("b", 10.1, INTERVAL) is False
    assert tracker.register("b", 10.2, INTERVAL) is True


def test_a_double_click_is_consumed_so_a_third_click_does_not_repeat_it() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    assert tracker.register("a", 10.1, INTERVAL) is True
    assert tracker.register("a", 10.2, INTERVAL) is False
    assert tracker.register("a", 10.3, INTERVAL) is True


def test_interval_boundary_is_inclusive_and_zero_interval_disables_double_click() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    assert tracker.register("a", 10.0 + INTERVAL, INTERVAL) is True
    tracker.register("a", 20.0, 0)
    assert tracker.register("a", 20.0, 0) is False


def test_clock_going_backwards_is_not_a_double_click() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    assert tracker.register("a", 9.9, INTERVAL) is False


def test_reset_forgets_the_last_click() -> None:
    tracker = DoubleClickTracker()
    tracker.register("a", 10.0, INTERVAL)
    tracker.reset()
    assert tracker.register("a", 10.1, INTERVAL) is False
