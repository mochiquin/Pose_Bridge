"""JSON cache for scanned library entries so large libraries are not rescanned every session."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from .library_scan import DEFAULT_EXTENSIONS, LibraryEntry

CACHE_SCHEMA = 1


def roots_signature(roots: Iterable[Path | str], extensions: Sequence[str] = DEFAULT_EXTENSIONS) -> str:
    """Stable fingerprint of the configured roots and extensions."""
    root_text = sorted(str(Path(r)).lower() for r in roots)
    ext_text = sorted(e.lower() for e in extensions)
    payload = json.dumps({"roots": root_text, "ext": ext_text}, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def save_cache(
    cache_path: Path,
    entries: Iterable[LibraryEntry],
    roots: Iterable[Path | str],
    extensions: Sequence[str] = DEFAULT_EXTENSIONS,
) -> None:
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": CACHE_SCHEMA,
        "signature": roots_signature(roots, extensions),
        "entries": [entry.to_dict() for entry in entries],
    }
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(cache_path)


def load_cache(
    cache_path: Path,
    roots: Iterable[Path | str],
    extensions: Sequence[str] = DEFAULT_EXTENSIONS,
) -> list[LibraryEntry] | None:
    """Return cached entries, or ``None`` when missing, unreadable, outdated or for other roots."""
    cache_path = Path(cache_path)
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # ValueError covers bad JSON and bytes that are not UTF-8
        return None
    if not isinstance(payload, dict) or payload.get("schema") != CACHE_SCHEMA:
        return None
    if payload.get("signature") != roots_signature(roots, extensions):
        return None
    try:
        return [LibraryEntry.from_dict(item) for item in payload.get("entries", [])]
    except (KeyError, TypeError, ValueError):
        return None
