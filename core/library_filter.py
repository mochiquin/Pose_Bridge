"""Search and category helpers for library entries (no Blender)."""

from __future__ import annotations

from collections.abc import Iterable

from .library_scan import LibraryEntry


def matches_query(query: str, *fields: str) -> bool:
    """True when every whitespace-separated token of ``query`` occurs in at least one field."""
    tokens = query.lower().split()
    if not tokens:
        return True
    haystack = " ".join(fields).lower()
    return all(token in haystack for token in tokens)


def filter_entries(
    entries: Iterable[LibraryEntry],
    *,
    query: str = "",
    kind: str | None = None,
    category_prefix: str = "",
    favorites: frozenset[str] = frozenset(),
    only_favorites: bool = False,
) -> list[LibraryEntry]:
    """Filter entries, keeping the input order."""
    prefix = category_prefix.strip("/").lower()
    result: list[LibraryEntry] = []
    for entry in entries:
        if kind and entry.kind != kind:
            continue
        if prefix and not (entry.category.lower() == prefix or entry.category.lower().startswith(prefix + "/")):
            continue
        if only_favorites and entry.path not in favorites:
            continue
        if not matches_query(query, entry.name, entry.category):
            continue
        result.append(entry)
    return result


def top_categories(entries: Iterable[LibraryEntry]) -> list[tuple[str, int]]:
    """Return ``(first-level category, entry count)`` sorted by name; root-level files use ``""``."""
    counts: dict[str, int] = {}
    for entry in entries:
        head = entry.category.split("/", 1)[0] if entry.category else ""
        counts[head] = counts.get(head, 0) + 1
    return sorted(counts.items(), key=lambda item: item[0].lower())
