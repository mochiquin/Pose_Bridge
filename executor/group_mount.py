"""Temporarily make an object reachable in the view layer (GroupPro collection instances).

A GroupPro group is an empty that *instances* a collection which is not linked into the scene, so the
characters inside are not in the view layer and most operators cannot see them. ``mounted`` links the
collection for the duration of a ``with`` block and ALWAYS restores the original state afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import bpy


def _is_linked_in_scene(scene: bpy.types.Scene, collection: bpy.types.Collection) -> bool:
    return collection.name in {c.name for c in scene.collection.children_recursive}


@contextmanager
def mounted(context: bpy.types.Context, obj: bpy.types.Object) -> Iterator[bpy.types.Object]:
    """Yield ``obj`` after making sure it is in the view layer; undo any temporary change on exit."""
    scene = context.scene
    if obj.name in context.view_layer.objects:
        yield obj
        return

    mounted_collection: bpy.types.Collection | None = None
    hidden_instances: list[bpy.types.Object] = []
    for collection in obj.users_collection:
        if _is_linked_in_scene(scene, collection):
            continue
        scene.collection.children.link(collection)
        mounted_collection = collection
        for inst in bpy.data.objects:
            if inst.instance_type == "COLLECTION" and inst.instance_collection == collection and not inst.hide_viewport:
                inst.hide_viewport = True
                hidden_instances.append(inst)
        break

    try:
        context.view_layer.update()
        if obj.name not in context.view_layer.objects:
            raise RuntimeError(f"'{obj.name}' is not reachable in the view layer (collection excluded or hidden)")
        yield obj
    finally:
        for inst in hidden_instances:
            inst.hide_viewport = False
        if mounted_collection is not None:
            scene.collection.children.unlink(mounted_collection)
        context.view_layer.update()
