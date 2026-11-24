"""File and folder naming for saved poses (no Blender)."""

from __future__ import annotations

import re
from collections.abc import Iterable

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
)
MAX_LENGTH = 80


def sanitize_filename(name: str, fallback: str = "Pose") -> str:
    """A safe file name stem for every platform: no separators or illegal characters, never empty."""
    cleaned = _ILLEGAL.sub(" ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = cleaned[:MAX_LENGTH].strip(" .")
    if not cleaned or cleaned.lower() in _RESERVED:
        return fallback
    return cleaned


def unique_stem(existing: Iterable[str], stem: str) -> str:
    """``stem`` itself when free, otherwise ``stem 2``, ``stem 3``... (case-insensitive comparison)."""
    taken = {name.lower() for name in existing}
    if stem.lower() not in taken:
        return stem
    number = 2
    while f"{stem} {number}".lower() in taken:
        number += 1
    return f"{stem} {number}"


def default_name(existing: Iterable[str], prefix: str = "Pose") -> str:
    """The first unused ``Pose 001``-style name."""
    taken = {name.lower() for name in existing}
    number = 1
    while f"{prefix} {number:03d}".lower() in taken:
        number += 1
    return f"{prefix} {number:03d}"


def split_subfolder(text: str) -> tuple[str, ...]:
    """Turn ``Maria/Sitting`` into safe folder names; empty parts, '.' and '..' are dropped."""
    parts: list[str] = []
    for raw in re.split(r"[\\/]+", text):
        raw = raw.strip()
        if raw in ("", ".", ".."):
            continue
        cleaned = sanitize_filename(raw, fallback="")
        if cleaned:
            parts.append(cleaned)
    return tuple(parts)
