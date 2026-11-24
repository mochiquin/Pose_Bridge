from __future__ import annotations

from core import default_name, sanitize_filename, split_subfolder, unique_stem


def test_sanitize_removes_illegal_characters_and_collapses_spaces() -> None:
    assert sanitize_filename('A/B\\C:D*E?"F<G>H|I') == "A B C D E F G H I"
    assert sanitize_filename("  many    spaces  ") == "many spaces"
    assert sanitize_filename("坐姿 01") == "坐姿 01"


def test_sanitize_never_returns_an_unusable_name() -> None:
    assert sanitize_filename("") == "Pose"
    assert sanitize_filename("...") == "Pose"
    assert sanitize_filename("???") == "Pose"
    assert sanitize_filename("CON") == "Pose"
    assert sanitize_filename("lpt1") == "Pose"
    assert sanitize_filename("", fallback="x") == "x"


def test_sanitize_limits_length_and_trailing_dots() -> None:
    assert len(sanitize_filename("a" * 300)) == 80
    assert sanitize_filename("name.") == "name"


def test_unique_stem_adds_the_smallest_free_number_case_insensitively() -> None:
    assert unique_stem([], "Sit") == "Sit"
    assert unique_stem(["Sit"], "Sit") == "Sit 2"
    assert unique_stem(["sit", "Sit 2", "SIT 3"], "Sit") == "Sit 4"
    assert unique_stem(["Sit 2"], "Sit") == "Sit"


def test_default_name_skips_used_numbers() -> None:
    assert default_name([]) == "Pose 001"
    assert default_name(["Pose 001", "pose 002"]) == "Pose 003"
    assert default_name(["Pose 002"]) == "Pose 001"
    assert default_name([], prefix="Maria") == "Maria 001"


def test_split_subfolder_is_safe_against_traversal() -> None:
    assert split_subfolder("Maria/Sitting") == ("Maria", "Sitting")
    assert split_subfolder("Maria\\Sitting") == ("Maria", "Sitting")
    assert split_subfolder("../../etc/passwd") == ("etc", "passwd")
    assert split_subfolder("//a///b/") == ("a", "b")
    assert split_subfolder(" . / .. / ") == ()
    assert split_subfolder("") == ()
    assert split_subfolder("a:b/c*d") == ("a b", "c d")
