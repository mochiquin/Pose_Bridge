"""A linear state timeline with undo and redo (no Blender).

The timeline always holds the *current* state and the states before and after it. Recording a new state
after an undo discards the states that were undone (the redo branch), like any editor history.
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

T = TypeVar("T")

MIN_LIMIT = 1
MAX_LIMIT = 100
DEFAULT_LIMIT = 20


def clamp_limit(limit: int) -> int:
    return max(MIN_LIMIT, min(MAX_LIMIT, int(limit)))


class Timeline(Generic[T]):
    """States ``s0 .. sn`` with a pointer to the current one; at most ``limit`` undo steps are kept."""

    def __init__(self, initial: T, limit: int = DEFAULT_LIMIT) -> None:
        self._limit = clamp_limit(limit)
        self._states: list[T] = [initial]
        self._index = 0

    @property
    def current(self) -> T:
        return self._states[self._index]

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def undo_depth(self) -> int:
        return self._index

    @property
    def redo_depth(self) -> int:
        return len(self._states) - 1 - self._index

    def set_limit(self, limit: int) -> None:
        """Change the limit; when it shrinks the oldest steps are forgotten."""
        self._limit = clamp_limit(limit)
        self._trim()

    def record(self, state: T) -> None:
        """Make ``state`` the new current state; anything that could have been redone is discarded."""
        del self._states[self._index + 1 :]
        self._states.append(state)
        self._index += 1
        self._trim()

    def replace_current(self, state: T) -> None:
        """Update the current state in place (it changed in a way that does not deserve its own step)."""
        self._states[self._index] = state

    def undo(self) -> T:
        """Step back and return the state to restore; ``IndexError`` when there is nothing to undo."""
        if self._index == 0:
            raise IndexError("nothing to undo")
        self._index -= 1
        return self._states[self._index]

    def redo(self) -> T:
        """Step forward and return the state to restore; ``IndexError`` when there is nothing to redo."""
        if self._index >= len(self._states) - 1:
            raise IndexError("nothing to redo")
        self._index += 1
        return self._states[self._index]

    def discard_unrestorable(self, direction: Literal["undo", "redo"]) -> None:
        """Forget the state that the last ``undo()`` / ``redo()`` pointed at because it cannot be restored.

        The pointer goes back to the state that is still live, so the next ``undo()`` / ``redo()`` continues
        with the step beyond the broken one.
        """
        if direction == "undo":
            del self._states[self._index]  # the live state slides into this position
        else:
            del self._states[self._index]
            self._index -= 1

    def _trim(self) -> None:
        while self._index > self._limit:
            del self._states[0]
            self._index -= 1
