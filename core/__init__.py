"""Pure Python logic layer for Pose_Bridge.

This package MUST remain strictly decoupled from Blender runtime APIs
(no bpy, mathutils, bmesh, or executor imports).
"""

from .adjust_plan import TRACK_NAME, LayerPlan, plan_layers
from .click_tracker import DoubleClickTracker
from .index_cache import load_cache, roots_signature, save_cache
from .library_filter import filter_entries, matches_query, top_categories
from .library_scan import (
    DEFAULT_EXTENSIONS,
    KIND_ANIMATION,
    KIND_POSE,
    KIND_UNKNOWN,
    LibraryEntry,
    ScanResult,
    guess_kind,
    natural_key,
    scan_library,
    sniff_duf_kind,
)
from .library_view import TOP, FolderRef, FolderView, LibraryIndex, Page, paginate, parent_of
from .mhx_rules import finger_sides, finger_switches_to_free
from .pose_naming import default_name, sanitize_filename, split_subfolder, unique_stem
from .pose_schema import EXTENSION as POSE_EXTENSION
from .pose_schema import PoseFileError, dumps, loads, make_pose_data, match_bones
from .timeline import Timeline

__all__ = [
    "DEFAULT_EXTENSIONS",
    "DoubleClickTracker",
    "LayerPlan",
    "TRACK_NAME",
    "Timeline",
    "plan_layers",
    "POSE_EXTENSION",
    "PoseFileError",
    "default_name",
    "dumps",
    "loads",
    "make_pose_data",
    "match_bones",
    "sanitize_filename",
    "split_subfolder",
    "unique_stem",
    "KIND_ANIMATION",
    "KIND_POSE",
    "KIND_UNKNOWN",
    "FolderRef",
    "FolderView",
    "LibraryEntry",
    "LibraryIndex",
    "Page",
    "ScanResult",
    "TOP",
    "filter_entries",
    "finger_sides",
    "finger_switches_to_free",
    "guess_kind",
    "load_cache",
    "matches_query",
    "natural_key",
    "paginate",
    "parent_of",
    "roots_signature",
    "save_cache",
    "scan_library",
    "sniff_duf_kind",
    "top_categories",
]
