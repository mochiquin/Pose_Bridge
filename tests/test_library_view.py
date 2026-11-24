from __future__ import annotations

from core import (
    KIND_ANIMATION,
    KIND_POSE,
    TOP,
    LibraryEntry,
    LibraryIndex,
    paginate,
    parent_of,
)

POSES = "/lib/Genesis 8 Female/Poses"
ANIMS = "/lib/Genesis 8 Female/Animations"


def _entry(root: str, category: str, name: str, kind: str = KIND_POSE) -> LibraryEntry:
    return LibraryEntry(name=name, path=f"{root}/{category}/{name}.duf", kind=kind, category=category, root=root)


ENTRIES = [
    _entry(POSES, "Katana Poses", "10"),
    _entry(POSES, "Katana Poses", "2"),
    _entry(POSES, "Aeon Soul/Sitting", "Sit A"),
    _entry(POSES, "Aeon Soul", "Stand"),
    _entry(POSES, "", "loose"),
    _entry(ANIMS, "Havanalibere/Injured", "Idle", KIND_ANIMATION),
]
INDEX = LibraryIndex(ENTRIES)


def test_top_level_lists_library_folders_with_counts() -> None:
    view = INDEX.view(TOP)
    assert [(f.label, f.count) for f in view.folders] == [("Animations", 1), ("Poses", 5)]
    assert view.files == ()
    assert [c.label for c in view.crumbs] == ["Library"]


def test_library_folder_lists_author_folders_and_its_own_files() -> None:
    view = INDEX.view(POSES)
    assert [(f.label, f.count) for f in view.folders] == [("Aeon Soul", 2), ("Katana Poses", 2)]
    assert [e.name for e in view.files] == ["loose"]
    assert [c.label for c in view.crumbs] == ["Library", "Poses"]


def test_sub_folder_shows_files_in_natural_order_and_nested_folders() -> None:
    katana = INDEX.view(POSES, ["Katana Poses"])
    assert [e.name for e in katana.files] == ["2", "10"]
    aeon = INDEX.view(POSES, ["Aeon Soul"])
    assert [(f.label, f.parts) for f in aeon.folders] == [("Sitting", ("Aeon Soul", "Sitting"))]
    assert [e.name for e in aeon.files] == ["Stand"]
    assert [c.label for c in aeon.crumbs] == ["Library", "Poses", "Aeon Soul"]


def test_crumbs_carry_navigation_targets() -> None:
    sitting = INDEX.view(POSES, ["Aeon Soul", "Sitting"])
    assert [(c.root, c.parts) for c in sitting.crumbs] == [
        (TOP, ()),
        (POSES, ()),
        (POSES, ("Aeon Soul",)),
        (POSES, ("Aeon Soul", "Sitting")),
    ]


def test_unknown_location_falls_back_to_top_level() -> None:
    assert INDEX.view("/nope").root == TOP
    assert INDEX.view(POSES, ["Missing"]).root == TOP


def test_parent_of() -> None:
    assert parent_of(POSES, ("Aeon Soul", "Sitting")) == (POSES, ("Aeon Soul",))
    assert parent_of(POSES, ("Aeon Soul",)) == (POSES, ())
    assert parent_of(POSES, ()) == (TOP, ())
    assert parent_of(TOP, ()) == (TOP, ())


def test_find_by_path_and_len() -> None:
    assert len(INDEX) == 6
    assert INDEX.find(f"{ANIMS}/Havanalibere/Injured/Idle.duf").name == "Idle"
    assert INDEX.find("/missing.duf") is None


def test_same_named_folders_in_different_roots_stay_separate() -> None:
    a = _entry("/r1", "Same", "x")
    b = _entry("/r2", "Same", "y")
    index = LibraryIndex([a, b])
    assert [e.name for e in index.view("/r1", ["Same"]).files] == ["x"]
    assert [e.name for e in index.view("/r2", ["Same"]).files] == ["y"]


def test_empty_index() -> None:
    index = LibraryIndex([])
    assert len(index) == 0
    assert index.view(TOP).folders == ()


def test_paginate_slices_and_counts_pages() -> None:
    items = list(range(10))
    first = paginate(items, 0, 4)
    last = paginate(items, 2, 4)
    assert (first.items, first.index, first.count, first.total) == ((0, 1, 2, 3), 0, 3, 10)
    assert (last.items, last.index) == ((8, 9), 2)


def test_paginate_clamps_page_and_handles_empty() -> None:
    assert paginate(list(range(5)), 99, 2).index == 2
    assert paginate(list(range(5)), -3, 2).index == 0
    empty = paginate([], 0, 4)
    assert (empty.items, empty.index, empty.count, empty.total) == ((), 0, 1, 0)
    assert paginate([1, 2], 0, 0).count == 2  # page size is at least 1
