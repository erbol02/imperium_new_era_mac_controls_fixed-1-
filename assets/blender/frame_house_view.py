"""Frame the rebuilt cottage in Blender's saved Layout viewport."""
import bpy
import os
from mathutils import Vector

path = os.path.join(os.path.dirname(__file__), 'source', 'medieval_house.blend')
bpy.ops.wm.open_mainfile(filepath=path)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        space = area.spaces.active
        region = space.region_3d
        region.view_location = Vector((0.0, 0.0, 1.30))
        region.view_distance = 4.7
        region.view_rotation = Vector((4.0, -6.0, 3.5)).to_track_quat('Z', 'Y')
        region.view_perspective = 'PERSP'
        space.shading.type = 'MATERIAL'
        space.shading.use_scene_lights = False
        space.shading.use_scene_world = False
        space.shading.show_cavity = True
        space.shading.cavity_type = 'BOTH'
        space.shading.curvature_ridge_factor = 1.25
        space.shading.curvature_valley_factor = 1.1
        space.overlay.show_floor = True
        space.overlay.show_relationship_lines = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = None
bpy.ops.wm.save_as_mainfile(filepath=path)
print('FRAMED_REBUILT_HOUSE', path)
