"""Session state of the browser: the scanned library index and what the current view shows.

Entries live in module memory (never in the .blend). The scene settings only store where the user
is (folder, page, selection), so the panel can recompute what to draw cheaply on every redraw.
"""

from collections.abc import Iterable

from .core import LibraryEntry, LibraryIndex, filter_entries, paginate, parent_of

_entries: list[LibraryEntry] = []
_index: LibraryIndex = LibraryIndex([])


def set_entries(entries: Iterable[LibraryEntry]) -> None:
    global _entries, _index
    _entries = list(entries)
    _index = LibraryIndex(_entries)


def replace_root(root: str, entries: Iterable[LibraryEntry]) -> list[LibraryEntry]:
    """Swap the entries of one library folder (after saving a pose) without rescanning everything."""
    merged = [entry for entry in _entries if entry.root != root] + list(entries)
    set_entries(merged)
    return list(_entries)


def index() -> LibraryIndex:
    return _index


def find(path: str) -> LibraryEntry | None:
    return _index.find(path)


def nav_parts(settings) -> tuple[str, ...]:
    return tuple(part for part in settings.nav_path.split("/") if part)


def is_searching(settings) -> bool:
    return bool(settings.query.strip())


def _kind(settings) -> str | None:
    return None if settings.kind_filter == "ALL" else settings.kind_filter


def current_view(settings):
    return _index.view(settings.nav_root, nav_parts(settings))


def visible_files(settings) -> list[LibraryEntry]:
    """Files to show as thumbnails: search results over the whole library, else the open folder."""
    kind = _kind(settings)
    if is_searching(settings):
        return filter_entries(_entries, query=settings.query.strip(), kind=kind)
    files = current_view(settings).files
    return [entry for entry in files if kind is None or entry.kind == kind]


def page_size(settings) -> int:
    return settings.columns * settings.rows_per_page


def current_page(settings):
    return paginate(visible_files(settings), settings.page, page_size(settings))


def open_folder(scene, root: str, parts: Iterable[str]) -> None:
    settings = scene.pose_bridge
    settings.nav_root = root
    settings.nav_path = "/".join(parts)
    settings.page = 0


def go_up(scene) -> None:
    view = current_view(scene.pose_bridge)
    root, parts = parent_of(view.root, view.parts)
    open_folder(scene, root, parts)


def change_page(scene, delta: int) -> None:
    settings = scene.pose_bridge
    settings.page = paginate(visible_files(settings), settings.page + delta, page_size(settings)).index
