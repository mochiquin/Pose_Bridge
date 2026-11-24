"""Scan pose/animation library folders into plain-Python entries (no Blender)."""

from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

KIND_POSE = "pose"
KIND_ANIMATION = "animation"
KIND_UNKNOWN = "unknown"

POSE_FILE_EXTENSION = ".pbpose"
DEFAULT_EXTENSIONS: tuple[str, ...] = (".duf", POSE_FILE_EXTENSION)

_ANIMATION_FOLDER_HINTS = ("animation", "animate", "aniblock", "anibloc")
_POSE_FOLDER_HINTS = ("pose",)


@dataclass(frozen=True)
class LibraryEntry:
    """One pose/animation file found in a library root."""

    name: str
    path: str
    kind: str
    category: str
    root: str
    preview: str = ""
    size: int = 0
    mtime: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryEntry:
        return cls(
            name=str(data["name"]),
            path=str(data["path"]),
            kind=str(data.get("kind", KIND_UNKNOWN)),
            category=str(data.get("category", "")),
            root=str(data.get("root", "")),
            preview=str(data.get("preview", "")),
            size=int(data.get("size", 0)),
            mtime=float(data.get("mtime", 0.0)),
        )


@dataclass(frozen=True)
class ScanResult:
    entries: tuple[LibraryEntry, ...]
    missing_roots: tuple[str, ...]


def guess_kind(parts: Sequence[str]) -> str:
    """Guess pose/animation from folder names; the outermost matching folder wins."""
    for part in parts:
        lowered = part.lower()
        if any(hint in lowered for hint in _ANIMATION_FOLDER_HINTS):
            return KIND_ANIMATION
        if any(hint in lowered for hint in _POSE_FOLDER_HINTS):
            return KIND_POSE
    return KIND_UNKNOWN


def _load_duf_json(path: Path) -> dict[str, Any] | None:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def sniff_duf_kind(path: Path) -> str:
    """Decide pose vs animation by reading the file: animations have channels with several keys."""
    try:
        data = _load_duf_json(Path(path))
    except (OSError, EOFError, gzip.BadGzipFile):
        return KIND_UNKNOWN
    if data is None:
        return KIND_UNKNOWN
    scene = data.get("scene")
    if not isinstance(scene, dict):
        return KIND_UNKNOWN
    animations = scene.get("animations")
    if not isinstance(animations, list) or not animations:
        return KIND_UNKNOWN
    for anim in animations:
        keys = anim.get("keys") if isinstance(anim, dict) else None
        if isinstance(keys, list) and len(keys) > 1:
            return KIND_ANIMATION
    return KIND_POSE


def _find_preview(path: Path, siblings: set[str]) -> str:
    for candidate in (path.name + ".png", path.stem + ".png"):
        if candidate.lower() in siblings:
            return str(path.with_name(candidate))
    return ""


def natural_key(text: str) -> list[Any]:
    """Sort key like a file explorer: symbols first, then numbers by value, then text; case-insensitive."""
    chunks: list[Any] = []
    for part in re.split(r"(\d+)", text):
        if part == "":
            continue
        if part.isdigit():
            chunks.append((1, int(part), ""))
        else:
            chunks.append((0 if not part[0].isalnum() else 2, 0, part.lower()))
    return chunks


def _natural_sort_key(entry: LibraryEntry) -> tuple[str, list[Any]]:
    return (entry.category.lower(), natural_key(entry.name))


def scan_library(roots: Iterable[Path | str], extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> ScanResult:
    """Walk every existing root and describe the matching files."""
    wanted = {ext.lower() for ext in extensions}
    entries: list[LibraryEntry] = []
    missing: list[str] = []
    seen: set[str] = set()

    for raw_root in roots:
        root = Path(raw_root)
        if not root.is_dir():
            missing.append(str(root))
            continue
        files = [p for p in root.rglob("*") if p.is_file()]
        names_by_dir: dict[Path, set[str]] = {}
        for p in files:
            names_by_dir.setdefault(p.parent, set()).add(p.name.lower())
        for p in files:
            if p.suffix.lower() not in wanted:
                continue
            key = str(p).lower()
            if key in seen:
                continue
            seen.add(key)
            rel_parts = p.relative_to(root).parts[:-1]
            stat = p.stat()
            entries.append(
                LibraryEntry(
                    name=p.stem,
                    path=str(p),
                    kind=KIND_POSE
                    if p.suffix.lower() == POSE_FILE_EXTENSION
                    else guess_kind((*root.parts[-1:], *rel_parts)),
                    category="/".join(rel_parts),
                    root=str(root),
                    preview=_find_preview(p, names_by_dir[p.parent]),
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )

    entries.sort(key=_natural_sort_key)
    return ScanResult(entries=tuple(entries), missing_roots=tuple(missing))
