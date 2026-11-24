from __future__ import annotations

from pathlib import Path

from core import (
    KIND_ANIMATION,
    KIND_POSE,
    LibraryEntry,
    filter_entries,
    load_cache,
    matches_query,
    roots_signature,
    save_cache,
    top_categories,
)


def _entry(name: str, category: str, kind: str = KIND_POSE, path: str | None = None) -> LibraryEntry:
    return LibraryEntry(
        name=name, path=path or f"/lib/{category}/{name}.duf", kind=kind, category=category, root="/lib"
    )


ENTRIES = [
    _entry("05", "Katana Poses"),
    _entry("Idle", "Havanalibere/Injured", KIND_ANIMATION),
    _entry("Walk", "Havanalibere/Injured", KIND_ANIMATION),
    _entry("Sit", ""),
]


def test_matches_query_requires_all_tokens() -> None:
    assert matches_query("", "anything")
    assert matches_query("katana 05", "05", "Katana Poses")
    assert not matches_query("katana 06", "05", "Katana Poses")
    assert matches_query("IDLE", "Idle", "")


def test_filter_by_kind_category_and_query() -> None:
    assert [e.name for e in filter_entries(ENTRIES, kind=KIND_ANIMATION)] == ["Idle", "Walk"]
    assert [e.name for e in filter_entries(ENTRIES, category_prefix="havanalibere")] == ["Idle", "Walk"]
    assert [e.name for e in filter_entries(ENTRIES, category_prefix="Havanalibere/Injured/")] == ["Idle", "Walk"]
    assert filter_entries(ENTRIES, category_prefix="Hav") == []
    assert [e.name for e in filter_entries(ENTRIES, query="walk")] == ["Walk"]


def test_filter_favorites() -> None:
    favs = frozenset({ENTRIES[0].path})
    assert [e.name for e in filter_entries(ENTRIES, favorites=favs, only_favorites=True)] == ["05"]
    assert len(filter_entries(ENTRIES, favorites=favs)) == 4


def test_top_categories_counts_first_level() -> None:
    assert top_categories(ENTRIES) == [("", 1), ("Havanalibere", 2), ("Katana Poses", 1)]


def test_cache_roundtrip(tmp_path: Path) -> None:
    cache = tmp_path / "sub" / "index.json"
    roots = [tmp_path / "a", tmp_path / "b"]

    save_cache(cache, ENTRIES, roots)
    loaded = load_cache(cache, roots)

    assert loaded == ENTRIES


def test_cache_invalid_when_roots_or_extensions_change(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    save_cache(cache, ENTRIES, [tmp_path / "a"])

    assert load_cache(cache, [tmp_path / "other"]) is None
    assert load_cache(cache, [tmp_path / "a"], extensions=(".duf", ".bvh")) is None
    assert load_cache(cache, [tmp_path / "a"]) is not None


def test_cache_rejects_missing_corrupt_and_wrong_schema(tmp_path: Path) -> None:
    roots = [tmp_path]
    assert load_cache(tmp_path / "missing.json", roots) is None

    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_cache(bad, roots) is None

    wrong = tmp_path / "wrong.json"
    wrong.write_text('{"schema": 999, "signature": "x", "entries": []}')
    assert load_cache(wrong, roots) is None


def test_roots_signature_is_order_independent() -> None:
    assert roots_signature(["/a", "/b"]) == roots_signature(["/b", "/a"])
    assert roots_signature(["/a"]) != roots_signature(["/a", "/b"])
