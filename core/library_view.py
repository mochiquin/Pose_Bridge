"""Folder navigation and pagination for the thumbnail browser (no Blender).

The browser shows one folder of the library at a time: sub-folders as buttons and the files of that
folder as a thumbnail grid. The folders mirror the layout on disk, so an author's poses stay together.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from .library_scan import LibraryEntry, natural_key

T = TypeVar("T")

TOP = ""  # root id of the virtual top level that lists the configured library folders


@dataclass(frozen=True)
class FolderRef:
    """A navigable folder: ``root`` is the library folder (``TOP`` for the top level), ``parts`` the sub-path."""

    label: str
    root: str
    parts: tuple[str, ...]
    count: int


@dataclass(frozen=True)
class FolderView:
    root: str
    parts: tuple[str, ...]
    crumbs: tuple[FolderRef, ...]  # path from the top level down to this folder
    folders: tuple[FolderRef, ...]
    files: tuple[LibraryEntry, ...]


@dataclass(frozen=True)
class Page:
    items: tuple
    index: int
    count: int
    total: int


@dataclass
class _Dir:
    folders: dict[str, int] = field(default_factory=dict)  # child name -> total files below it
    files: list[LibraryEntry] = field(default_factory=list)


def _root_label(root: str) -> str:
    path = Path(root)
    return path.name or str(path)


class LibraryIndex:
    """Entries grouped by folder, built once per scan so navigation is O(1)."""

    def __init__(self, entries: Iterable[LibraryEntry]) -> None:
        self._dirs: dict[tuple[str, tuple[str, ...]], _Dir] = {}
        self._root_counts: dict[str, int] = {}
        self._by_path: dict[str, LibraryEntry] = {}
        for entry in entries:
            self._by_path[entry.path] = entry
            self._root_counts[entry.root] = self._root_counts.get(entry.root, 0) + 1
            parts = tuple(p for p in entry.category.split("/") if p)
            for depth in range(len(parts)):
                parent = self._dirs.setdefault((entry.root, parts[:depth]), _Dir())
                parent.folders[parts[depth]] = parent.folders.get(parts[depth], 0) + 1
            self._dirs.setdefault((entry.root, parts), _Dir()).files.append(entry)
        for node in self._dirs.values():
            node.files.sort(key=lambda e: natural_key(e.name))

    def __len__(self) -> int:
        return len(self._by_path)

    def find(self, path: str) -> LibraryEntry | None:
        return self._by_path.get(path)

    def roots(self) -> tuple[FolderRef, ...]:
        refs = [FolderRef(_root_label(r), r, (), n) for r, n in self._root_counts.items()]
        return tuple(sorted(refs, key=lambda f: natural_key(f.label)))

    def exists(self, root: str, parts: Sequence[str]) -> bool:
        return root == TOP or (root, tuple(parts)) in self._dirs

    def view(self, root: str, parts: Sequence[str] = ()) -> FolderView:
        """The folder at ``root``/``parts``; unknown locations fall back to the top level."""
        parts = tuple(parts)
        top = FolderRef("Library", TOP, (), len(self))
        if root == TOP or not self.exists(root, parts):
            return FolderView(TOP, (), (top,), self.roots(), ())
        node = self._dirs[(root, parts)]
        crumbs = [top, FolderRef(_root_label(root), root, (), self._root_counts[root])]
        for depth in range(len(parts)):
            parent = self._dirs[(root, parts[:depth])]
            crumbs.append(FolderRef(parts[depth], root, parts[: depth + 1], parent.folders[parts[depth]]))
        children = sorted(node.folders.items(), key=lambda item: natural_key(item[0]))
        folders = tuple(FolderRef(name, root, (*parts, name), count) for name, count in children)
        return FolderView(root, parts, tuple(crumbs), folders, tuple(node.files))


def parent_of(root: str, parts: Sequence[str]) -> tuple[str, tuple[str, ...]]:
    """The folder one level up: sub-folder -> parent, library folder -> top level."""
    parts = tuple(parts)
    if parts:
        return root, parts[:-1]
    return TOP, ()


def paginate(items: Sequence[T], page: int, page_size: int) -> Page:
    """Slice ``items``; ``page`` is clamped into the valid range."""
    page_size = max(1, page_size)
    count = max(1, -(-len(items) // page_size))
    index = min(max(0, page), count - 1)
    start = index * page_size
    return Page(items=tuple(items[start : start + page_size]), index=index, count=count, total=len(items))
