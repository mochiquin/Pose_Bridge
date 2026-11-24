"""Render a small picture of a rig with a temporary orthographic camera (used as the thumbnail of saved poses)."""

from __future__ import annotations

from pathlib import Path

import bpy
import mathutils

from .group_mount import mounted

THUMBNAIL_SIZE = 256


def _character_bounds(context: bpy.types.Context, rig: bpy.types.Object):
    depsgraph = context.evaluated_depsgraph_get()
    low = mathutils.Vector((1e9, 1e9, 1e9))
    high = mathutils.Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in rig.children_recursive:
        if (
            obj.type != "MESH"
            or obj.name.startswith("GZM_")
            or obj.hide_viewport
            or obj.name not in context.view_layer.objects
        ):
            continue
        for corner in obj.evaluated_get(depsgraph).bound_box:
            world = obj.matrix_world @ mathutils.Vector(corner)
            low = mathutils.Vector(map(min, low, world))
            high = mathutils.Vector(map(max, high, world))
        count += 1
    return (low, high) if count else None


def render_thumbnail(context: bpy.types.Context, rig: bpy.types.Object, out_path: Path) -> bool:
    """Render the character from the front into ``out_path``; False when there is nothing to render.

    Every scene setting that is touched is restored afterwards, and the temporary camera is removed.
    """
    scene = context.scene
    render = scene.render
    shading = scene.display.shading
    with mounted(context, rig):
        bounds = _character_bounds(context, rig)
        if bounds is None:
            return False
        low, high = bounds
        center, size = (low + high) / 2, high - low

        saved = {
            "camera": scene.camera,
            "resolution": (render.resolution_x, render.resolution_y, render.resolution_percentage),
            "transparent": render.film_transparent,
            "shading": (shading.light, shading.color_type, shading.background_type, tuple(shading.background_color)),
            "outline": shading.show_object_outline,
        }
        camera_data = bpy.data.cameras.new("PoseBridgeThumbnail")
        camera = bpy.data.objects.new("PoseBridgeThumbnail", camera_data)
        scene.collection.objects.link(camera)
        try:
            camera_data.type = "ORTHO"
            camera_data.ortho_scale = max(size.z, size.x) * 1.15
            camera.location = (center.x, center.y - 6.0, center.z)
            camera.rotation_euler = (1.5707963, 0.0, 0.0)  # looks along +Y: the front of a DAZ character
            scene.camera = camera
            render.resolution_x = render.resolution_y = THUMBNAIL_SIZE
            render.resolution_percentage = 100
            render.film_transparent = False
            shading.light = "STUDIO"
            shading.color_type = "TEXTURE"
            shading.background_type = "VIEWPORT"
            shading.background_color = (0.30, 0.30, 0.30)
            shading.show_object_outline = False
            context.view_layer.update()
            bpy.ops.render.opengl(view_context=False, write_still=False)
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            bpy.data.images["Render Result"].save_render(str(out_path))
        finally:
            scene.camera = saved["camera"]
            render.resolution_x, render.resolution_y, render.resolution_percentage = saved["resolution"]
            render.film_transparent = saved["transparent"]
            shading.light, shading.color_type, shading.background_type, shading.background_color = saved["shading"]
            shading.show_object_outline = saved["outline"]
            scene.collection.objects.unlink(camera)
            bpy.data.objects.remove(camera)
            bpy.data.cameras.remove(camera_data)
    return Path(out_path).is_file()
