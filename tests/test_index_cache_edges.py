from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import (
    KIND_ANIMATION,
    KIND_POSE,
    LibraryEntry,
    load_cache,
    natural_key,
    roots_signature,
    save_cache,
)
from core.index_cache import CACHE_SCHEMA


def _entry(name: str = "Sit", **kwargs) -> LibraryEntry:
    return LibraryEntry(name=name, path=f"/lib/{name}.duf", kind=KIND_POSE, category="", root="/lib", **kwargs)


# --- roots_signature -------------------------------------------------------------------------


def test_signature_ignores_case_of_roots_and_extensions_and_their_order() -> None:
    assert roots_signature(["C:/Lib"], (".duf", ".BVH")) == roots_signature(["c:/lib"], (".bvh", ".DUF"))


def test_signature_accepts_path_objects_and_strings_alike() -> None:
    assert roots_signature([Path("/a")]) == roots_signature(["/a"])


def test_signature_differs_for_different_extensions() -> None:
    assert roots_signature(["/a"], (".duf",)) != roots_signature(["/a"], (".duf", ".bvh"))


# --- save_cache / load_cache -----------------------------------------------------------------


def test_empty_library_roundtrips_to_an_empty_list_not_none(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    save_cache(cache, [], [tmp_path])
    assert load_cache(cache, [tmp_path]) == []


def test_unicode_names_survive_the_roundtrip(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    entries = [_entry("坐姿 站立"), _entry("Café")]
    save_cache(cache, entries, [tmp_path])
    assert load_cache(cache, [tmp_path]) == entries
    assert "坐姿" in cache.read_text(encoding="utf-8")  # stored readable, not as \u escapes


def test_all_entry_fields_survive_the_roundtrip(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    entry = LibraryEntry(
        name="Walk", path="/lib/a/Walk.duf", kind=KIND_ANIMATION, category="a", root="/lib", preview="/p.png", size=42
    )
    save_cache(cache, [entry], [tmp_path])
    assert load_cache(cache, [tmp_path]) == [entry]


def test_saving_again_replaces_the_old_cache_and_leaves_no_temp_file(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    save_cache(cache, [_entry("One")], [tmp_path])
    save_cache(cache, [_entry("Two")], [tmp_path])

    assert [e.name for e in load_cache(cache, [tmp_path]) or []] == ["Two"]
    assert [p.name for p in tmp_path.iterdir()] == ["index.json"]


def test_save_creates_missing_parent_folders(tmp_path: Path) -> None:
    cache = tmp_path / "a" / "b" / "index.json"
    save_cache(cache, [_entry()], [tmp_path])
    assert cache.is_file()


def _write_payload(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("payload", [[], "text", 5, None])
def test_non_object_json_is_rejected(tmp_path: Path, payload: object) -> None:
    cache = tmp_path / "index.json"
    _write_payload(cache, payload)
    assert load_cache(cache, [tmp_path]) is None


@pytest.mark.parametrize(
    "bad_entries",
    [
        [{"path": "/lib/x.duf"}],  # no name
        [{"name": "x"}],  # no path
        ["not a dict"],
        [{"name": "x", "path": "/x", "size": "big"}],  # size is not a number
    ],
)
def test_malformed_entries_make_the_whole_cache_unusable(tmp_path: Path, bad_entries: list) -> None:
    cache = tmp_path / "index.json"
    _write_payload(cache, {"schema": CACHE_SCHEMA, "signature": roots_signature([tmp_path]), "entries": bad_entries})
    assert load_cache(cache, [tmp_path]) is None


def test_missing_entries_key_is_an_empty_cache(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    _write_payload(cache, {"schema": CACHE_SCHEMA, "signature": roots_signature([tmp_path])})
    assert load_cache(cache, [tmp_path]) == []


def test_invalid_utf8_file_is_not_a_crash(tmp_path: Path) -> None:
    cache = tmp_path / "index.json"
    cache.write_bytes(b"\xff\xfe\x00bad")
    assert load_cache(cache, [tmp_path]) is None


def test_a_folder_in_place_of_the_cache_file_is_not_a_crash(tmp_path: Path) -> None:
    assert load_cache(tmp_path, [tmp_path]) is None


# --- natural_key -----------------------------------------------------------------------------


def test_numbers_sort_by_value_not_by_text() -> None:
    names = ["pose 10", "pose 2", "pose 1"]
    assert sorted(names, key=natural_key) == ["pose 1", "pose 2", "pose 10"]


def test_sorting_is_case_insensitive() -> None:
    assert sorted(["b", "A", "c"], key=natural_key) == ["A", "b", "c"]


def test_symbols_come_before_numbers_and_numbers_before_letters() -> None:
    assert sorted(["abc", "1", "_x", "-y"], key=natural_key)[-1] == "abc"
    ordered = sorted(["abc", "1", "_x"], key=natural_key)
    assert ordered.index("1") < ordered.index("abc")


def test_empty_and_digit_only_names_do_not_crash() -> None:
    assert natural_key("") == []
    assert sorted(["10", "9", ""], key=natural_key) == ["", "9", "10"]


def test_leading_zeros_compare_by_value() -> None:
    assert natural_key("01") == natural_key("1")
