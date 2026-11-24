"""Architecture boundary tests enforcing AGENTS.md hard boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "core"
FORBIDDEN_TOP_LEVEL_MODULES = {"bpy", "mathutils", "bmesh", "executor"}


def _violations_in(py_file: Path) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
            if node.level and (node.module or "").split(".")[0] == "executor":
                found.append(f"{py_file.name}:{node.lineno} relative import of executor")
        else:
            continue
        for name in names:
            if name.split(".")[0] in FORBIDDEN_TOP_LEVEL_MODULES:
                found.append(f"{py_file.name}:{node.lineno} imports {name}")
            if name == "os.path":
                found.append(f"{py_file.name}:{node.lineno} imports os.path (use pathlib.Path)")
    return found


def test_core_directory_has_no_forbidden_imports() -> None:
    py_files = sorted(CORE_DIR.rglob("*.py"))
    assert py_files, "Expected core/ to contain Python modules"
    violations = [v for py_file in py_files for v in _violations_in(py_file)]
    assert not violations, f"Architecture violations in core/: {violations}"


def test_executor_does_not_use_os_path() -> None:
    executor_dir = REPO_ROOT / "executor"
    if not executor_dir.exists():
        return
    violations = [v for py_file in executor_dir.rglob("*.py") for v in _violations_in(py_file) if "os.path" in v]
    assert not violations, f"os.path used in executor/: {violations}"
