from __future__ import annotations

import gzip
import json
from pathlib import Path

from core import (
    KIND_ANIMATION,
    KIND_POSE,
    KIND_UNKNOWN,
    guess_kind,
    scan_library,
    sniff_duf_kind,
)


def _write_duf(path: Path, scene: dict | None, *, gz: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"scene": scene} if scene is not None else {"asset_info": {}}).encode("utf-8")
    path.write_bytes(gzip.compress(payload) if gz else payload)


def test_guess_kind_uses_outermost_folder_hint() -> None:
    assert guess_kind(("Poses", "Katana Poses")) == KIND_POSE
    assert guess_kind(("Animations", "Havanalibere", "Animation of Injured")) == KIND_ANIMATION
    assert guess_kind(("Poses", "Animation Poses")) == KIND_POSE
    assert guess_kind(("aniBlocks", "aniMate")) == KIND_ANIMATION
    assert guess_kind(("Misc",)) == KIND_UNKNOWN


def test_scan_finds_files_categories_and_previews(tmp_path: Path) -> None:
    root = tmp_path / "Poses"
    (root / "Katana Poses").mkdir(parents=True)
    (root / "Katana Poses" / "05.duf").write_text("{}")
    (root / "Katana Poses" / "05.duf.png").write_bytes(b"png")
    (root / "Katana Poses" / "readme.txt").write_text("x")
    (root / "root_pose.duf").write_text("{}")

    result = scan_library([root])

    assert not result.missing_roots
    by_name = {e.name: e for e in result.entries}
    assert set(by_name) == {"05", "root_pose"}
    assert by_name["05"].category == "Katana Poses"
    assert by_name["05"].kind == KIND_POSE
    assert by_name["05"].preview.endswith("05.duf.png")
    assert by_name["root_pose"].category == ""
    assert by_name["root_pose"].preview == ""


def test_scan_reports_missing_roots_and_skips_them(tmp_path: Path) -> None:
    good = tmp_path / "good"
    good.mkdir()
    (good / "a.duf").write_text("{}")

    result = scan_library([tmp_path / "nope", good])

    assert result.missing_roots == (str(tmp_path / "nope"),)
    assert [e.name for e in result.entries] == ["a"]


def test_scan_sorts_naturally_and_deduplicates_overlapping_roots(tmp_path: Path) -> None:
    root = tmp_path / "Poses"
    root.mkdir()
    for name in ("pose10.duf", "pose2.duf", "pose1.duf"):
        (root / name).write_text("{}")

    result = scan_library([root, root])

    assert [e.name for e in result.entries] == ["pose1", "pose2", "pose10"]


def test_scan_respects_extensions_case_insensitively(tmp_path: Path) -> None:
    (tmp_path / "A.DUF").write_text("{}")
    (tmp_path / "b.pbpose").write_text("{}")

    only_duf = scan_library([tmp_path], extensions=(".duf",))
    both = scan_library([tmp_path], extensions=(".duf", ".pbpose"))

    assert [e.name for e in only_duf.entries] == ["A"]
    assert {e.name for e in both.entries} == {"A", "b"}


def test_pose_files_are_scanned_by_default_and_are_always_poses(tmp_path: Path) -> None:
    (tmp_path / "Saved").mkdir()
    (tmp_path / "Saved" / "my pose.pbpose").write_text("{}")
    (tmp_path / "Saved" / "my pose.pbpose.png").write_bytes(b"png")

    entry = scan_library([tmp_path]).entries[0]

    assert (entry.name, entry.kind, entry.category) == ("my pose", KIND_POSE, "Saved")
    assert entry.preview.endswith("my pose.pbpose.png")


def test_sniff_distinguishes_pose_and_animation(tmp_path: Path) -> None:
    pose = tmp_path / "pose.duf"
    anim = tmp_path / "anim.duf"
    _write_duf(pose, {"animations": [{"url": "x", "keys": [[0, 1.0]]}]})
    _write_duf(anim, {"animations": [{"url": "x", "keys": [[0, 1.0], [0.5, 2.0]]}]}, gz=True)

    assert sniff_duf_kind(pose) == KIND_POSE
    assert sniff_duf_kind(anim) == KIND_ANIMATION


def test_sniff_returns_unknown_for_garbage_or_missing(tmp_path: Path) -> None:
    junk = tmp_path / "junk.duf"
    junk.write_bytes(b"not json at all")
    no_scene = tmp_path / "noscene.duf"
    _write_duf(no_scene, None)

    assert sniff_duf_kind(junk) == KIND_UNKNOWN
    assert sniff_duf_kind(no_scene) == KIND_UNKNOWN
    assert sniff_duf_kind(tmp_path / "missing.duf") == KIND_UNKNOWN
