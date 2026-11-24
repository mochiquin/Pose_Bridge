"""Detect a double click from two separate clicks on the same item (no Blender).

Blender buttons only report single presses, so the second click of a double click is recognised by
comparing the time of two consecutive clicks on the same key.
"""

from __future__ import annotations


class DoubleClickTracker:
    """Remembers the last click; ``register`` says whether the new click completes a double click."""

    def __init__(self) -> None:
        self._key: str | None = None
        self._time = 0.0

    def register(self, key: str, now: float, interval: float) -> bool:
        """Record a click on ``key`` at time ``now`` (seconds); True if it is the second click of a double click.

        A double click is consumed: the click that follows it starts a new sequence, so a third quick
        click does not apply again.
        """
        is_double = interval > 0 and key == self._key and 0 <= now - self._time <= interval
        if is_double:
            self.reset()
        else:
            self._key = key
            self._time = now
        return is_double

    def reset(self) -> None:
        self._key = None
        self._time = 0.0
