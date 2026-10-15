"""Build/export stylized low-poly assets for Imperium: New Era.

Run from the project root:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python assets/blender/build_game_models.py

Every model is authored with bpy, saved as a .blend source, and exported as a self-contained GLB.
The assets use shared palette colors with embedded microdetail maps driving roughness.
"""
import bpy
import math
import os
import random
import sys
from mathutils import Vector

bpy.context.preferences.filepaths.save_version = 0

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLEND_DIR = os.path.join(ROOT, "assets", "blender", "source")
GLB_DIR = os.path.join(ROOT, "assets", "models")
os.makedirs(BLEND_DIR, exist_ok=True)
os.makedirs(GLB_DIR, exist_ok=True)

PALETTE = {
    "plaster": (0.66, 0.48, 0.31, 1),
    "cream": (0.78, 0.67, 0.49, 1),
    "stone": (0.35, 0.32, 0.27, 1),
    "stone_light": (0.57, 0.51, 0.40, 1),
    "wood": (0.20, 0.105, 0.045, 1),
    "wood_light": (0.39, 0.23, 0.10, 1),
    "wood_end": (0.53, 0.34, 0.16, 1),
    "tile": (0.48, 0.105, 0.045, 1),
    "tile_light": (0.68, 0.21, 0.095, 1),
    "tile_dark": (0.31, 0.075, 0.04, 1),
    "glass": (0.07, 0.19, 0.22, 1),
    "iron": (0.105, 0.12, 0.12, 1),
    "gold": (0.67, 0.42, 0.12, 1),
    "canvas": (0.78, 0.67, 0.48, 1),
    "red": (0.55, 0.075, 0.055, 1),
    "leaf_dark": (0.075, 0.23, 0.105, 1),
    "leaf_mid": (0.13, 0.34, 0.12, 1),
    "leaf_light": (0.27, 0.43, 0.13, 1),
    "bark": (0.19, 0.105, 0.055, 1),
    "soil": (0.26, 0.17, 0.095, 1),
    "road_a": (0.48, 0.41, 0.31, 1),
    "road_b": (0.59, 0.51, 0.39, 1),
    "road_c": (0.39, 0.35, 0.29, 1),
    "moss": (0.19, 0.30, 0.12, 1),
    "produce_red": (0.72, 0.14, 0.07, 1),
    "produce_yellow": (0.82, 0.54, 0.07, 1),
    "produce_green": (0.27, 0.46, 0.08, 1),
}
MATS = {}
TEXTURES = {}
TEXTURE_DIR = os.path.join(ROOT, "assets", "materials")
os.makedirs(TEXTURE_DIR, exist_ok=True)


def reset_scene(asset_name):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    MATS.clear()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.world.color = (0.08, 0.08, 0.08)
    root = bpy.data.objects.new(asset_name, None)
    scene.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.2
    return root


def grayscale_texture(category):
    if category in TEXTURES:
        return TEXTURES[category]
    size = 128
    rng = random.Random(9000 + sum(ord(ch) for ch in category))
    pixels = []
    for y in range(size):
        for x in range(size):
            noise = rng.uniform(-0.035, 0.035)
            if category == "plaster":
                value = 0.94 + noise
            elif category == "wood":
                grain = x % 17
                value = 0.68 + noise if grain == 0 else (0.82 + noise if grain < 3 else 0.96 + noise)
                value += 0.025 * math.sin((x + y * 0.08) * 0.18)
            elif category == "tile":
                row = y // 24
                local_x = (x + (row % 2) * 16) % 32
                local_y = y % 24
                value = 0.40 if local_x < 2 or local_y < 2 or (local_y > 21 and 3 < local_x < 29) else 0.88 + noise
                value *= 0.94 + (row % 3) * 0.035
            else:
                row = y // 24
                local_x = (x + (row % 2) * 16) % 32
                local_y = y % 24
                value = 0.38 if local_x < 2 or local_y < 2 else 0.91 + noise
                value *= 0.95 + (row % 2) * 0.04
            value = max(0.0, min(1.0, value))
            pixels.extend((value, value, value, 1.0))
    image = bpy.data.images.new("Imperium_" + category + "_microdetail", width=size, height=size, alpha=False)
    image.pixels.foreach_set(pixels)
    image.file_format = "PNG"
    image.filepath_raw = os.path.join(TEXTURE_DIR, "imperium_" + category + "_microdetail.png")
    image.save()
    image.pack()
    TEXTURES[category] = image
    return image


def mat(name):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new("M_" + name)
    m.diffuse_color = PALETTE[name]
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = PALETTE[name]
    bsdf.inputs["Roughness"].default_value = 0.78 if name in ("glass", "iron", "gold") else 0.88
    if name == "glass":
        bsdf.inputs["Metallic"].default_value = 0.16
    texture_category = None
    if name in ("stone", "stone_light", "road_a", "road_b", "road_c"):
        texture_category = "stone"
    elif name in ("plaster", "cream"):
        texture_category = "plaster"
    elif name in ("wood", "wood_light", "wood_end", "bark"):
        texture_category = "wood"
    elif name in ("tile", "tile_light", "tile_dark"):
        texture_category = "tile"
    if texture_category:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = grayscale_texture(texture_category)
        tex.interpolation = "Linear"
        tex.extension = "REPEAT"
        # Keep each material's authored palette tint. Connecting a grayscale map
        # directly to Base Color makes every stone, plaster and roof tile nearly
        # white in Godot; use the map for surface roughness instead.
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
    MATS[name] = m
    return m


def finish(obj, name, material, parent, bevel=0.0):
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(mat(material))
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    if bevel > 0:
        mod = obj.modifiers.new("Soft hand-cut edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.affect = "EDGES"
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        normal = obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=normal.name)
    return obj


def cube(name, location, scale, material, parent, bevel=0.025, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation:
        obj.rotation_euler = rotation
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return finish(obj, name, material, parent, bevel)


def beam(name, a, b, thickness, material, parent, bevel=0.012):
    mid = (Vector(a) + Vector(b)) * 0.5
    direction = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cube_add(size=1, location=mid)
    obj = bpy.context.object
    obj.dimensions = (thickness, thickness, direction.length)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, material, parent, bevel)


def cylinder(name, location, radius, depth, material, parent, vertices=10, rotation=None, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    if rotation:
        obj.rotation_euler = rotation
    return finish(obj, name, material, parent, bevel)


def uv_sphere(name, location, scale, material, parent, segments=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=location)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return finish(obj, name, material, parent)


def mesh_obj(name, verts, faces, material, parent, bevel=0.0):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat(material))
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer.data[loop_index].uv = (vertex.x * 1.25, vertex.y * 1.25)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    if bevel > 0:
        mod = obj.modifiers.new("Edge highlights", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def roof_slab(name, p1, p2, depth, thickness, material, parent):
    # Four-corner pitched roof plane with real thickness and a faceted eave edge.
    a, b = Vector((p1[0], 0, p1[1])), Vector((p2[0], 0, p2[1]))
    along = b - a
    normal = Vector((-along.z, 0, along.x)).normalized() * thickness * 0.5
    y0, y1 = -depth * 0.5, depth * 0.5
    verts = [
        (a.x + normal.x, y0, a.z + normal.z), (b.x + normal.x, y0, b.z + normal.z),
        (b.x + normal.x, y1, b.z + normal.z), (a.x + normal.x, y1, a.z + normal.z),
        (a.x - normal.x, y0, a.z - normal.z), (b.x - normal.x, y0, b.z - normal.z),
        (b.x - normal.x, y1, b.z - normal.z), (a.x - normal.x, y1, a.z - normal.z),
    ]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_obj(name, verts, faces, material, parent, bevel=0.008)


def gable_mesh(name, width, wall_z, ridge_z, y, depth, material, parent):
    """Create a solid triangular gable in the X/Z plane at a fixed facade depth."""
    w = width * 0.5
    points = [(-w, wall_z), (w, wall_z), (0, ridge_z)]
    verts = [(x, y, z) for x, z in points] + [(x, y + depth, z) for x, z in points]
    faces = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    return mesh_obj(name, verts, faces, material, parent, bevel=0.008)


def house_model():
    root = reset_scene("MedievalHouse")
    # Overall footprint ~1.8 x 1.8 m, base at Z=0; first-floor stone, plaster upper mass.
    cube("Foundation dressed stone", (0, 0, 0.13), (1.64, 1.54, 0.26), "stone", root, 0.045)
    cube("Lower ashlar storey", (0, 0, 0.65), (1.48, 1.38, 0.82), "stone_light", root, 0.035)
    cube("Front plaster infill", (0, -0.706, 0.70), (1.22, 0.035, 0.72), "plaster", root, 0.012)
    cube("Back plaster infill", (0, 0.706, 0.70), (1.22, 0.035, 0.72), "plaster", root, 0.012)
    cube("Left plaster infill", (-0.756, 0, 0.70), (0.035, 1.22, 0.72), "plaster", root, 0.012)
    cube("Right plaster infill", (0.756, 0, 0.70), (0.035, 1.22, 0.72), "cream", root, 0.012)
    # Oak framing and diagonal braces.
    for x in (-0.68, 0.68):
        cube("Oak corner post", (x, -0.735, 0.94), (0.11, 0.10, 1.02), "wood", root, 0.016)
        cube("Side corner post", (x, 0.0, 0.94), (0.10, 1.46, 1.00), "wood", root, 0.015)
    for z in (0.40, 0.96, 1.43):
        cube("Oak cross rail", (0, -0.735, z), (1.40, 0.10, 0.09), "wood", root, 0.015)
    beam("Diagonal timber brace left", (-0.62, -0.79, 0.48), (-0.35, -0.79, 0.88), 0.075, "wood_light", root)
    beam("Diagonal timber brace right", (0.62, -0.79, 0.48), (0.35, -0.79, 0.88), 0.075, "wood_light", root)
    # Recessed entrance: jambs and lintel frame the door, with the leaf behind them.
    cube("Door dark reveal", (0, -0.738, 0.54), (0.47, 0.035, 0.83), "wood", root, 0.015)
    cube("Recessed oak door", (0, -0.765, 0.52), (0.33, 0.035, 0.72), "wood_light", root, 0.012)
    for x in (-0.12, -0.04, 0.04, 0.12):
        cube("Door vertical board", (x, -0.789, 0.52), (0.012, 0.012, 0.64), "wood", root, 0.003)
    for x in (-0.245, 0.245):
        cube("Carved door jamb", (x, -0.805, 0.56), (0.085, 0.105, 0.84), "stone_light", root, 0.018)
        cube("Jamb foot block", (x, -0.812, 0.20), (0.13, 0.13, 0.17), "stone", root, 0.018)
    cube("Door oak lintel", (0, -0.805, 0.99), (0.58, 0.12, 0.12), "wood_end", root, 0.018)
    cube("Door hood dripstone", (0, -0.825, 1.08), (0.68, 0.19, 0.08), "stone_light", root, 0.022)
    cylinder("Iron door handle", (0.105, -0.812, 0.51), 0.026, 0.025, "gold", root, vertices=8, rotation=(math.pi / 2, 0, 0))
    cube("Stone entrance step lower", (0, -0.84, 0.115), (0.70, 0.38, 0.10), "stone", root, 0.025)
    cube("Stone entrance step upper", (0, -0.80, 0.205), (0.54, 0.27, 0.08), "stone_light", root, 0.02)
    # Deep window niches: dark inset, glass set behind a thick four-piece timber frame.
    for wx in (-0.46, 0.46):
        cube("Window recessed shadow", (wx, -0.735, 1.00), (0.31, 0.04, 0.39), "wood", root, 0.012)
        cube("Inset leaded glass", (wx, -0.766, 1.00), (0.215, 0.018, 0.285), "glass", root, 0.008)
        for dx in (-0.155, 0.155):
            cube("Window heavy oak jamb", (wx + dx, -0.793, 1.00), (0.055, 0.10, 0.47), "wood_light", root, 0.012)
        for dz in (0.765, 1.235):
            cube("Projecting stone window sill", (wx, -0.802, dz), (0.39, 0.15, 0.075), "stone_light", root, 0.016)
        cube("Window central mullion", (wx, -0.804, 1.00), (0.027, 0.045, 0.29), "wood_end", root, 0.006)
        cube("Window cross rail", (wx, -0.804, 1.00), (0.21, 0.045, 0.026), "wood_end", root, 0.006)
        for side in (-1, 1):
            shutter_x = wx + side * 0.245
            cube("Open oak shutter", (shutter_x, -0.772, 1.00), (0.095, 0.075, 0.35), "wood_light", root, 0.012, rotation=(0, 0, side * -0.12))
            for row in range(3):
                cube("Shutter raised cross slat", (shutter_x, -0.817, 0.89 + row * 0.105), (0.085, 0.014, 0.025), "wood_end", root, 0.004)
        # A shallow arched hood and keystone give the aperture masonry depth.
        cube("Window lintel stone", (wx, -0.79, 1.275), (0.39, 0.13, 0.075), "stone_light", root, 0.012)
        cube("Window keystone", (wx, -0.812, 1.32), (0.09, 0.12, 0.10), "cream", root, 0.014)
    # Solid front/back gables plus a steep separate two-plane roof.
    gable_mesh("Front plaster gable", 1.48, 1.48, 2.14, -0.68, 0.06, "plaster", root)
    gable_mesh("Rear plaster gable", 1.48, 1.48, 2.14, 0.74, 0.06, "cream", root)
    roof_slab("Left clay roof plane", (-0.91, 1.44), (0, 2.25), 1.82, 0.11, "tile", root)
    roof_slab("Right clay roof plane", (0, 2.25), (0.91, 1.44), 1.82, 0.11, "tile_light", root)
    cube("Ridge cap", (0, 0, 2.29), (0.14, 1.92, 0.13), "tile_dark", root, 0.035)
    for side in (-1, 1):
        for row in range(5):
            t = (row + 0.4) / 5.4
            x = side * (0.80 * (1 - t))
            z = 1.54 + 0.61 * (1 - abs(x) / 0.91)
            for col in range(7):
                y = -0.78 + col * 0.26
                tile_mat = ("tile_light", "tile", "tile_dark")[(row + col) % 3]
                cube("Individual terracotta roof tile", (x, y, z), (0.29, 0.31, 0.045), tile_mat, root, 0.018, rotation=(0, side * 0.64, 0))
        for y in (-0.90, 0.90):
            beam("Exposed carved rafter", (side * 0.86, y, 1.43), (0, y, 2.24), 0.055, "wood", root)
    # Chimney, capstones, little attic vent and two hanging lantern brackets.
    cube("Stone chimney stack", (-0.48, 0.36, 2.12), (0.29, 0.32, 0.92), "stone", root, 0.025)
    cube("Chimney crown", (-0.48, 0.36, 2.61), (0.39, 0.41, 0.10), "stone_light", root, 0.02)
    cube("Chimney flue", (-0.48, 0.36, 2.67), (0.19, 0.20, 0.035), "iron", root, 0.008)
    # Compact centered dormer sits in the roof plane without an oversized box.
    gable_mesh("Dormer plaster gable", 0.20, 1.91, 2.16, -0.52, 0.10, "cream", root)
    roof_slab("Dormer roof left", (0.25, 1.96), (0.47, 2.18), 0.50, 0.06, "tile_light", root)
    roof_slab("Dormer roof right", (0.47, 2.18), (0.69, 1.96), 0.50, 0.06, "tile", root)
    cube("Dormer inset glass", (0.47, -0.584, 1.96), (0.14, 0.025, 0.18), "glass", root, 0.008)
    for x in (0.37, 0.57): cube("Dormer oak jamb", (x, -0.602, 1.96), (0.035, 0.04, 0.23), "wood_light", root, 0.006)
    cube("Dormer sill", (0.47, -0.61, 1.85), (0.25, 0.08, 0.045), "stone_light", root, 0.01)
    # Small timber sign and a hanging amber lantern.
    beam("Lantern bracket", (0.70, -0.78, 1.28), (0.78, -0.94, 1.20), 0.035, "iron", root)
    cube("Lantern housing", (0.78, -0.94, 1.09), (0.13, 0.13, 0.19), "gold", root, 0.025)
    return root


def barrel(name, loc, parent):
    cylinder(name + " body", loc, 0.18, 0.43, "wood_light", parent, vertices=12, bevel=0.012)
    for z in (-0.17, 0.17):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.018, major_segments=12, minor_segments=6, location=(loc[0], loc[1], loc[2] + z))
        finish(bpy.context.object, name + " iron hoop", "iron", parent)
    cylinder(name + " lid", (loc[0], loc[1], loc[2] + 0.225), 0.16, 0.028, "wood_end", parent, vertices=12)


def market_model():
    root = reset_scene("TownMarket")
    cube("Flagstone market pad", (0, 0, 0.07), (2.15, 1.9, 0.14), "stone", root, 0.035)
    # Two open-sided stalls share a strong timber frame and segmented fabric awning.
    for sx in (-0.52, 0.52):
        for y in (-0.57, 0.57):
            cylinder("Turned oak market post", (sx, y, 0.91), 0.065, 1.55, "wood", root, vertices=8, bevel=0.012)
            cylinder("Post capital", (sx, y, 1.70), 0.10, 0.09, "wood_end", root, vertices=8, bevel=0.008)
        cube("Market rear crossbeam", (sx, 0, 1.65), (0.10, 1.35, 0.12), "wood_light", root)
    for y in (-0.61, 0.61):
        cube("Long awning beam", (0, y, 1.67), (1.32, 0.11, 0.11), "wood", root)
    # sloped cloth planes broken into rich alternating strips and scalloped valance
    for i in range(8):
        x = -0.65 + i * 0.185
        cloth = "red" if i % 2 else "canvas"
        cube("Striped canvas awning", (x, 0, 1.81), (0.19, 1.55, 0.075), cloth, root, 0.012, rotation=(0.13, 0, -0.08))
        cube("Scalloped fabric valance", (x, -0.79, 1.70), (0.19, 0.075, 0.18), cloth, root, 0.018)
    # Two counters, display shelves, baskets and fresh produce.
    for y in (-0.36, 0.38):
        cube("Oak market counter", (0, y, 0.50), (1.62, 0.53, 0.66), "wood_light", root, 0.025)
        cube("Carved stall counter rim", (0, y - 0.015, 0.86), (1.70, 0.59, 0.08), "wood_end", root, 0.018)
        for i in range(7):
            x = -0.66 + i * 0.22
            color = ("produce_red", "produce_yellow", "produce_green")[(i + (0 if y < 0 else 1)) % 3]
            uv_sphere("Fresh market produce", (x, y, 0.98), (0.095, 0.09, 0.09), color, root, 8, 5)
    for x in (-0.82, 0.82):
        for y in (-0.72, 0.72):
            cube("Market delivery crate", (x, y, 0.31), (0.34, 0.32, 0.42), "wood_end", root, 0.025)
            for z in (0.20, 0.36, 0.50):
                cube("Crate slat", (x, y - 0.17, z), (0.34, 0.035, 0.045), "wood_light", root, 0.008)
    barrel("Apple barrel", (-0.86, 0.38, 0.35), root)
    barrel("Olive barrel", (0.88, -0.36, 0.35), root)
    return root


def tree_model():
    root = reset_scene("ForestOak")
    rng = random.Random(1928)
    cylinder("Tapered oak trunk", (0, 0, 0.91), 0.23, 1.82, "bark", root, vertices=9, bevel=0.025)
    # Four visible branches, each tapering upward into the crown.
    for idx, angle in enumerate((0.3, 1.9, 3.1, 4.7, 5.5)):
        start = (0, 0, 1.05 + 0.12 * (idx % 2))
        end = (math.cos(angle) * 0.80, math.sin(angle) * 0.80, 2.15 + 0.12 * (idx % 3))
        beam("Forked oak bough", start, end, 0.105, "bark", root, bevel=0.012)
        twig_end = (end[0] * 1.17, end[1] * 1.17, end[2] + 0.38)
        beam("Fine crown branch", end, twig_end, 0.055, "wood_light", root, bevel=0.006)
    foliage = ["leaf_dark", "leaf_mid", "leaf_light"]
    clusters = [
        (0, 0, 2.65, (0.76, 0.80, 0.72)),
        (-0.55, -0.12, 2.45, (0.67, 0.70, 0.62)),
        (0.55, 0.10, 2.48, (0.68, 0.70, 0.64)),
        (-0.25, 0.48, 2.75, (0.70, 0.68, 0.64)),
        (0.32, -0.48, 2.73, (0.72, 0.70, 0.64)),
        (0.10, 0.00, 3.14, (0.58, 0.61, 0.55)),
        (-0.74, 0.34, 2.80, (0.48, 0.54, 0.48)),
        (0.72, 0.36, 2.90, (0.49, 0.55, 0.49)),
        (-0.42, -0.55, 2.97, (0.49, 0.54, 0.49)),
        (0.52, -0.50, 3.03, (0.48, 0.53, 0.48)),
    ]
    for i, (x, y, z, scale) in enumerate(clusters):
        uv_sphere("Faceted oak foliage cluster", (x, y, z), scale, foliage[i % 3], root, 10, 6)
    # Low-poly roots and a scattering of leaf tufts around the trunk base.
    for angle in (0.3, 1.6, 2.8, 4.4, 5.6):
        beam("Surface oak root", (0, 0, 0.18), (math.cos(angle) * 0.55, math.sin(angle) * 0.55, 0.05), 0.10, "bark", root, 0.01)
    return root


def road_model():
    root = reset_scene("StoneRoadTile")
    cube("Packed earth and gravel bed", (0, 0, 0.035), (2.0, 2.0, 0.09), "soil", root, 0.05)
    colors = ("road_a", "road_b", "road_c")
    rng = random.Random(2718)
    # Individually irregular, chamfered paving stones with varied joints and subtle height offsets.
    for row in range(5):
        for col in range(5):
            x = -0.79 + col * 0.39 + (0.08 if row % 2 else 0)
            y = -0.79 + row * 0.39
            sx = rng.uniform(0.31, 0.38)
            sy = rng.uniform(0.28, 0.37)
            stone = cube("Hand-cut cobblestone", (x, y, 0.115 + rng.uniform(-0.012, 0.012)), (sx, sy, rng.uniform(0.11, 0.17)), colors[(row + col + rng.randrange(3)) % 3], root, 0.04, rotation=(0, 0, rng.uniform(-0.06, 0.06)))
            # Chipped corner notches are actual shallow insets via bevelled irregular slabs.
            stone.name = "Bevel-cut paving block"
    # Raised curbs, occasional moss and edge chips make the tile read as a connected road.
    for x in (-0.95, 0.95):
        cube("Set curb stones", (x, 0, 0.13), (0.12, 1.95, 0.19), "road_c", root, 0.035)
    for loc in [(-0.89, -0.58, 0.23), (0.89, 0.32, 0.23), (-0.88, 0.78, 0.22), (0.88, -0.72, 0.22)]:
        uv_sphere("Tiny roadside moss", loc, (0.09, 0.13, 0.025), "moss", root, 7, 4)
    return root


def large_house_model():
    """Overhanging two-storey timber house with balcony and tall tiled roof."""
    root = reset_scene("LargeTimberHouse")
    cube("Broad dressed-stone foundation", (0, 0, 0.14), (1.95, 1.82, 0.28), "stone", root, 0.05)
    cube("Ashlar ground floor", (0, 0, 0.69), (1.80, 1.68, 0.84), "stone_light", root, 0.04)
    cube("Lower front lime plaster", (0, -0.852, 0.70), (1.50, 0.04, 0.70), "cream", root)
    cube("Lower entrance door", (0, -0.89, 0.52), (0.40, 0.08, 0.70), "wood", root, 0.025)
    for x in (-0.18, -0.09, 0, 0.09, 0.18):
        cube("Door oak plank", (x, -0.94, 0.52), (0.018, 0.015, 0.66), "wood_light", root, 0.003)
    for wx in (-0.60, 0.60):
        cube("Ground floor inset window", (wx, -0.89, 0.83), (0.28, 0.045, 0.34), "glass", root, 0.018)
        for dx in (-0.16, 0.16): cube("Stone window jamb", (wx + dx, -0.92, 0.83), (0.045, 0.08, 0.42), "stone", root)
        cube("Stone window lintel", (wx, -0.92, 1.05), (0.38, 0.08, 0.06), "stone_light", root)
    # A wide, slightly cantilevered upper storey creates a distinct silhouette.
    cube("Overhanging upper plaster", (0, 0, 1.68), (1.92, 1.80, 0.94), "plaster", root, 0.025)
    for x in (-0.89, -0.30, 0.30, 0.89):
        cube("Front oak post", (x, -0.94, 1.67), (0.105, 0.09, 1.00), "wood", root, 0.012)
    for z in (1.20, 1.64, 2.12):
        cube("Front oak crossbeam", (0, -0.94, z), (1.86, 0.10, 0.09), "wood", root, 0.012)
    for x in (-0.72, 0.72):
        beam("Carved diagonal timber", (x, -1.00, 1.25), (x * 0.75, -1.00, 1.60), 0.065, "wood_light", root)
        cube("Upper bay window", (x * 0.56, -0.97, 1.76), (0.38, 0.06, 0.38), "glass", root, 0.02)
        for dx in (-0.22, 0.22): cube("Upper window frame", (x * 0.56 + dx, -1.01, 1.76), (0.045, 0.07, 0.48), "wood_light", root)
        cube("Upper window sill", (x * 0.56, -1.02, 1.52), (0.49, 0.14, 0.08), "wood_end", root)
    # Balcony, braces, flower boxes and balusters.
    cube("Balcony oak floor", (0, -1.16, 1.38), (1.92, 0.48, 0.14), "wood_light", root, 0.025)
    for x in (-0.90, -0.60, -0.30, 0, 0.30, 0.60, 0.90):
        cube("Balcony turned baluster", (x, -1.38, 1.63), (0.055, 0.055, 0.42), "wood", root, 0.015)
    cube("Balcony handrail", (0, -1.38, 1.86), (2.02, 0.09, 0.09), "wood_end", root, 0.025)
    for x in (-0.75, 0.75): beam("Balcony carved bracket", (x, -0.91, 1.19), (x, -1.30, 1.42), 0.075, "wood", root)
    # Tall gables and two fully separate roof slopes.
    gable_mesh("Front upper gable", 1.92, 2.14, 3.08, -0.90, 0.06, "cream", root)
    gable_mesh("Rear upper gable", 1.92, 2.14, 3.08, 0.90, 0.06, "plaster", root)
    roof_slab("Large house left tiled pitch", (-1.12, 2.10), (0, 3.08), 2.18, 0.14, "tile", root)
    roof_slab("Large house right tiled pitch", (0, 3.08), (1.12, 2.10), 2.18, 0.14, "tile_light", root)
    cube("Long roof ridge", (0, 0, 3.14), (0.18, 2.32, 0.15), "tile_dark", root, 0.035)
    for y in (-1.08, -0.54, 0, 0.54, 1.08):
        for side in (-1, 1):
            x = side * 0.72
            z = 2.20 + (0.95 * (1 - abs(x) / 1.12))
            cube("Hand-laid roof tile", (x, y, z), (0.38, 0.43, 0.055), "tile_light" if (int(y * 10) + side) % 2 else "tile", root, 0.02, rotation=(0, side * 0.72, 0))
    cube("Tall stone chimney", (-0.62, 0.43, 2.88), (0.34, 0.34, 1.12), "stone", root, 0.025)
    cube("Chimney crown", (-0.62, 0.43, 3.46), (0.43, 0.43, 0.12), "stone_light", root, 0.02)
    return root


def large_house_variant_b_model():
    root = large_house_model()
    root.name = "LargeHouseVariantB"
    # Side workshop wing, little front dormer, and a separate canopy change both massing and roofline.
    cube("Side merchant bay", (1.02, 0.10, 0.53), (0.66, 0.92, 0.86), "cream", root, 0.035)
    cube("Merchant bay plank door", (1.02, -0.39, 0.43), (0.30, 0.07, 0.61), "wood_light", root, 0.018)
    roof_slab("Merchant bay roof left", (0.66, 0.96), (1.02, 1.27), 1.08, 0.09, "tile_dark", root)
    roof_slab("Merchant bay roof right", (1.02, 1.27), (1.38, 0.96), 1.08, 0.09, "tile", root)
    cube("Front dormer cheek", (0.55, -0.78, 2.34), (0.48, 0.25, 0.42), "plaster", root, 0.02)
    roof_slab("Dormer roof left", (0.29, 2.42), (0.55, 2.69), 0.58, 0.06, "tile_light", root)
    roof_slab("Dormer roof right", (0.55, 2.69), (0.81, 2.42), 0.58, 0.06, "tile", root)
    cube("Dormer leadlight", (0.55, -0.93, 2.35), (0.20, 0.045, 0.24), "glass", root, 0.015)
    return root


def large_house_variant_c_model():
    root = large_house_model()
    root.name = "LargeHouseVariantC"
    # A deep shop canopy with carved brackets and a tall vented chimney makes the third type read differently.
    cube("Shopfront timber canopy", (0, -1.37, 1.04), (1.90, 0.55, 0.13), "wood_end", root, 0.03)
    roof_slab("Shop canopy tile skin", (-1.03, 1.17), (1.03, 1.17), 0.72, 0.08, "tile", root)
    for x in (-0.77, 0.77):
        beam("Shop canopy corbel", (x, -0.97, 0.72), (x, -1.62, 1.00), 0.09, "wood", root)
    cube("Tall vent chimney", (0.63, 0.42, 3.14), (0.34, 0.35, 1.38), "stone", root, 0.025)
    for z in (2.95, 3.12, 3.29):
        cube("Chimney vent slit", (0.63, 0.235, z), (0.16, 0.03, 0.055), "iron", root, 0.01)
    cube("Chimney broad cap", (0.63, 0.42, 3.86), (0.44, 0.44, 0.12), "stone_light", root, 0.02)
    return root


def warehouse_model():
    root = reset_scene("TimberWarehouse")
    cube("Raised stone loading platform", (0, 0, 0.16), (2.15, 2.10, 0.32), "stone", root, 0.045)
    cube("Rear limewashed wall", (0, 0.75, -0.92), (1.92, 1.34, 0.12), "cream", root, 0.02)
    cube("Side plaster wall left", (-0.92, 0.75, 0), (0.12, 1.34, 1.78), "plaster", root)
    cube("Side plaster wall right", (0.92, 0.75, 0), (0.12, 1.34, 1.78), "plaster", root)
    for x in (-0.91, -0.48, 0, 0.48, 0.91):
        cube("Massive front oak upright", (x, -0.98, 0.91), (0.13, 0.15, 1.50), "wood", root, 0.02)
    for z in (0.28, 1.53): cube("Warehouse front tie beam", (0, -1.0, z), (2.0, 0.16, 0.14), "wood_light", root, 0.025)
    cube("Double plank loading doors", (0, -1.08, 0.78), (0.78, 0.11, 0.98), "wood_light", root, 0.025)
    for x in (-0.31, -0.15, 0.02, 0.19, 0.34): cube("Door plank seam", (x, -1.145, 0.78), (0.028, 0.02, 0.90), "wood", root, 0.004)
    for x in (-0.22, 0.22):
        beam("Iron-reinforced door brace", (x - 0.18, -1.17, 0.48), (x + 0.18, -1.17, 1.08), 0.055, "iron", root, 0.006)
    # Deep gables, heavy rafters and tiled barn roof.
    gable_mesh("Warehouse front gable", 2.0, 1.54, 2.45, -1.0, 0.08, "plaster", root)
    gable_mesh("Warehouse rear gable", 2.0, 1.54, 2.45, 0.96, 0.08, "cream", root)
    roof_slab("Barn roof west slope", (-1.24, 1.53), (0, 2.45), 2.38, 0.13, "tile", root)
    roof_slab("Barn roof east slope", (0, 2.45), (1.24, 1.53), 2.38, 0.13, "tile_light", root)
    cube("Barn ridge cap", (0, 0, 2.50), (0.18, 2.50, 0.16), "wood", root, 0.03)
    for y in (-1.05, 1.05):
        for side in (-1, 1): beam("Exposed barn rafter", (0, y, 2.42), (side * 1.22, y, 1.52), 0.09, "wood", root)
    # Loft hatch, winch and storage clutter give the silhouette a working character.
    cube("Hayloft hatch", (0.45, -1.10, 1.71), (0.36, 0.06, 0.30), "wood_end", root)
    beam("Loading hoist arm", (0.55, -0.96, 1.45), (0.90, -1.25, 1.72), 0.07, "wood_light", root)
    cylinder("Hoist pulley", (0.90, -1.25, 1.57), 0.14, 0.07, "iron", root, 12, rotation=(math.pi/2, 0, 0))
    for x, y in ((-0.76, -0.58), (0.72, -0.48), (-0.62, 0.28)):
        barrel("Warehouse coopered barrel", (x, y, 0.40), root)
        cube("Warehouse slatted crate", (x * 0.55, y + 0.38, 0.38), (0.38, 0.34, 0.42), "wood_end", root, 0.025)
    return root


def workshop_model():
    root = house_model()
    root.name = "BlacksmithWorkshop"
    cube("Forge lean-to stone bay", (0.72, -0.05, 0.50), (0.62, 0.92, 0.88), "stone", root, 0.035)
    cube("Forge glowing mouth", (0.72, -0.54, 0.53), (0.34, 0.05, 0.35), "red", root, 0.035)
    cube("Forge lintel", (0.72, -0.58, 0.76), (0.46, 0.10, 0.09), "stone_light", root)
    roof_slab("Workshop side shed roof", (0.35, 1.02), (1.10, 0.89), 1.08, 0.10, "tile_dark", root)
    cube("Workshop chimney stack", (-0.47, 0.30, 2.25), (0.28, 0.30, 1.02), "stone", root, 0.025)
    cube("Chimney flared cap", (-0.47, 0.30, 2.78), (0.38, 0.40, 0.11), "stone_light", root, 0.02)
    # Anvil and a large wooden turning wheel identify the craft.
    cube("Blacksmith anvil foot", (0.72, -0.86, 0.24), (0.24, 0.20, 0.20), "iron", root, 0.025)
    cube("Blacksmith anvil block", (0.72, -0.86, 0.39), (0.40, 0.22, 0.12), "iron", root, 0.025)
    cylinder("Workshop water wheel hub", (1.05, -0.83, 0.56), 0.10, 0.08, "wood_end", root, 10, rotation=(math.pi/2, 0, 0))
    for i in range(8):
        a = i * math.tau / 8
        beam("Water wheel spoke", (1.05, -0.88, 0.56), (1.05 + math.cos(a)*0.36, -0.88, 0.56 + math.sin(a)*0.36), 0.04, "wood_light", root)
    return root


def farm_model():
    root = reset_scene("Farmstead")
    cube("Irregular earth yard", (0, 0, 0.055), (2.35, 2.35, 0.11), "soil", root, 0.055)
    # Five raised growing beds leave a broad dirt service lane to the barn.
    for row in range(5):
        x = -0.84 + row * 0.27
        cube("Raised dark furrow", (x, -0.08, 0.15), (0.20, 1.76, 0.09), "road_c", root, 0.025)
        for col in range(7):
            y = -0.76 + col * 0.23
            crop = ("leaf_mid", "leaf_light", "produce_green", "produce_yellow")[(row + col) % 4]
            # Each plant has a central head and several individual swept leaves.
            uv_sphere("Leafy crop head", (x, y, 0.32), (0.075, 0.075, 0.10), crop, root, 8, 5)
            for side in (-1, 1):
                beam("Crop leaf blade", (x, y, 0.23), (x + side * 0.085, y + (0.055 if col % 2 else -0.055), 0.35), 0.035, "leaf_light" if side > 0 else "leaf_mid", root, 0.004)
    # Stepping stones join the gate to the barn's threshing floor.
    for i in range(5):
        y = -0.82 + i * 0.27
        cube("Barnyard stepping stone", (0.49, y, 0.17), (0.25, 0.22, 0.09), "road_b", root, 0.035, rotation=(0, 0, (-1 if i % 2 else 1) * 0.06))
    # A compact timber barn with a stone sill, framed double doors and real gable roof.
    cube("Barn stone sill", (0.70, 0.57, 0.20), (0.94, 0.94, 0.20), "stone", root, 0.035)
    cube("Barn plaster walls", (0.70, 0.57, 0.63), (0.82, 0.82, 0.70), "cream", root, 0.025)
    for x in (0.31, 1.09):
        cube("Barn front timber post", (x, 0.14, 0.67), (0.085, 0.10, 0.78), "wood", root, 0.012)
    for z in (0.30, 1.02):
        cube("Barn front tie beam", (0.70, 0.14, z), (0.88, 0.10, 0.085), "wood_light", root, 0.014)
    cube("Barn double plank door", (0.70, 0.095, 0.56), (0.45, 0.06, 0.55), "wood", root, 0.018)
    for x in (0.52, 0.61, 0.70, 0.79, 0.88):
        cube("Barn door board", (x, 0.055, 0.56), (0.025, 0.018, 0.50), "wood_light", root, 0.004)
    for x in (0.37, 1.03): beam("Barn side brace", (x, 0.05, 0.34), (x + (0.12 if x < 0.7 else -0.12), 0.05, 0.81), 0.045, "wood_end", root)
    gable_mesh("Barn front gable", 0.82, 0.98, 1.38, 0.13, 0.07, "plaster", root)
    gable_mesh("Barn rear gable", 0.82, 0.98, 1.38, 1.01, 0.07, "cream", root)
    roof_slab("Barn roof left pitch", (0.22, 1.00), (0.70, 1.42), 1.10, 0.10, "tile", root)
    roof_slab("Barn roof right pitch", (0.70, 1.42), (1.18, 1.00), 1.10, 0.10, "tile_light", root)
    cube("Barn ridge cap", (0.70, 0.57, 1.47), (0.12, 1.16, 0.11), "wood", root, 0.025)
    for side in (-1, 1):
        for row in range(4):
            x = 0.70 + side * (0.40 - row * 0.095)
            z = 1.06 + 0.32 * (1.0 - abs(x - 0.70) / 0.48)
            for col in range(4):
                y = 0.12 + col * 0.29
                cube("Barn hand-set roof shingle", (x, y, z), (0.22, 0.27, 0.04), ("tile_light", "tile", "tile_dark")[(row + col) % 3], root, 0.012, rotation=(0, side * 0.72, 0))
    cube("Barn loft vent", (0.70, 0.085, 1.20), (0.20, 0.04, 0.12), "wood", root, 0.02)
    # Post-and-rail field fence with an open, braced gate at the front.
    for x in (-1.12, -0.78, -0.44, 0.40, 0.78, 1.12):
        for y in (-1.12, 1.12): cube("Field fence post", (x, y, 0.39), (0.075, 0.075, 0.56), "wood", root, 0.012)
    for y in (-1.12, 1.12):
        for z in (0.28, 0.50):
            for center_x in (-0.76, 0.76): cube("Field fence rail", (center_x, y, z), (0.70, 0.055, 0.055), "wood_light", root)
    for x in (-1.12, 1.12):
        for z in (0.28, 0.50): cube("Side fence rail", (x, 0, z), (0.055, 2.20, 0.055), "wood_light", root)
    beam("Gate diagonal brace", (-0.38, -1.16, 0.25), (0.34, -1.16, 0.55), 0.045, "wood_end", root)
    # A barrel and produce crates give the farmyard a clear working scale.
    barrel("Rainwater barrel", (1.00, 0.05, 0.25), root)
    cube("Apple crate", (0.99, 0.48, 0.30), (0.30, 0.28, 0.25), "wood_end", root, 0.025)
    for x, y in ((-0.90, 0.82), (-0.57, 0.82)):
        cube("Harvested hay bale", (x, y, 0.25), (0.28, 0.30, 0.25), "produce_yellow", root, 0.035)
    return root


def civic_hall_model():
    root = reset_scene("CivicHall")
    cube("Hall foundation", (0, 0, 0.12), (2.35, 2.05, 0.24), "stone", root, 0.045)
    for z, w, d in ((0.27, 2.15, 1.88), (0.43, 1.95, 1.70)):
        cube("Civic hall processional step", (0, 0.02, z), (w, d, 0.14), "stone_light", root, 0.025)
    cube("Civic hall rear chamber", (0, 0.28, 0.12), (1.58, 1.34, 1.42), "cream", root, 0.035)
    cube("Hall ceremonial door", (0, -0.415, 0.94), (0.44, 0.07, 0.92), "wood", root, 0.02)
    for x in (-0.73, -0.25, 0.25, 0.73):
        cylinder("Carved civic column shaft", (x, -0.68, 1.06), 0.105, 1.26, "stone_light", root, 12, bevel=0.01)
        cylinder("Column base", (x, -0.68, 0.43), 0.18, 0.16, "stone", root, 12)
        cube("Column capital", (x, -0.68, 1.72), (0.25, 0.25, 0.13), "cream", root, 0.025)
    cube("Civic entablature", (0, -0.68, 1.84), (1.95, 0.30, 0.20), "stone_light", root, 0.025)
    gable_mesh("Civic hall front pediment", 1.95, 1.94, 2.45, -0.84, 0.10, "cream", root)
    gable_mesh("Civic hall rear pediment", 1.95, 1.94, 2.45, 0.80, 0.10, "cream", root)
    roof_slab("Civic roof left", (-1.10, 1.98), (0, 2.65), 1.95, 0.13, "tile", root)
    roof_slab("Civic roof right", (0, 2.65), (1.10, 1.98), 1.95, 0.13, "tile_light", root)
    cube("Civic roof ridge", (0, 0, 2.72), (0.15, 2.02, 0.12), "tile_dark", root)
    # Heraldic roundel above the entry.
    cylinder("Civic bronze seal", (0, -0.94, 2.18), 0.20, 0.045, "gold", root, 12, rotation=(math.pi/2, 0, 0))
    return root


def temple_model():
    root = reset_scene("TempleSanctuary")
    cube("Temple broad stair plinth", (0, 0, 0.14), (2.55, 2.35, 0.28), "stone", root, 0.05)
    cube("Temple upper platform", (0, 0.02, 0.36), (2.28, 2.08, 0.18), "stone_light", root, 0.03)
    cube("Sanctuary cella", (0, 0.30, 1.18), (1.55, 1.48, 1.48), "cream", root, 0.04)
    cube("Bronze temple doors", (0, -0.47, 0.92), (0.62, 0.09, 1.06), "wood_light", root, 0.025)
    for x in (-0.81, -0.40, 0.40, 0.81):
        cylinder("Temple portico column", (x, -0.80, 1.08), 0.095, 1.45, "stone_light", root, 12, bevel=0.01)
        cylinder("Temple column foot", (x, -0.80, 0.39), 0.16, 0.15, "stone", root, 12)
        cube("Temple capital", (x, -0.80, 1.83), (0.23, 0.23, 0.12), "gold", root, 0.025)
    cube("Temple cornice", (0, -0.80, 1.96), (2.02, 0.28, 0.20), "stone_light", root, 0.03)
    gable_mesh("Temple pediment", 2.02, 2.05, 2.62, -0.95, 0.12, "cream", root)
    roof_slab("Temple roof left", (-0.95, 2.08), (0, 2.72), 1.78, 0.14, "tile_dark", root)
    roof_slab("Temple roof right", (0, 2.72), (0.95, 2.08), 1.78, 0.14, "tile", root)
    cube("Temple ridge", (0, 0.02, 2.79), (0.14, 1.84, 0.12), "gold", root)
    for x in (-0.61, 0.61):
        cube("Sanctuary corner pier", (x, -0.50, 1.20), (0.12, 0.12, 1.44), "stone_light", root)
        cube("Sanctuary side window", (x, -0.02, 1.30), (0.07, 0.28, 0.40), "glass", root, 0.02)
    return root


def watchtower_model():
    root = reset_scene("Watchtower")
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.84, radius2=0.68, depth=2.24, location=(0, 0, 1.12))
    finish(bpy.context.object, "Tapered stone tower shaft", "stone", root, bevel=0.025)
    # Dressed courses, arrow slits and a crenellated crown distinguish the masonry shaft.
    for z in (0.18, 0.54, 1.72, 1.92, 2.14): cylinder("Tower stone string course", (0, 0, z), 0.83 if z < 0.7 else 0.72, 0.075, "stone_light", root, 12)
    for angle in [i * math.tau / 8 for i in range(8)]:
        x, y = 0.72 * math.cos(angle), 0.72 * math.sin(angle)
        cube("Tower merlon", (x, y, 2.34), (0.24, 0.24, 0.42), "stone_light", root, 0.025)
    for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
        x, y = 0.66 * math.cos(angle), 0.66 * math.sin(angle)
        slit = cube("Tower arrow slit recess", (x, y, 1.16), (0.10, 0.035, 0.38), "iron", root, 0.02)
        slit.rotation_euler[2] = angle
    # Timber fighting platform and open framed lookout cabin, rather than a solid perched box.
    cube("Watch gallery deck", (0, 0, 2.56), (1.72, 1.72, 0.14), "wood_light", root, 0.035)
    for x in (-0.73, 0.73):
        for y in (-0.73, 0.73): cube("Lookout corner post", (x, y, 3.00), (0.12, 0.12, 0.90), "wood", root, 0.018)
    for y in (-0.73, 0.73):
        for z in (2.76, 3.37): cube("Lookout front rail", (0, y, z), (1.46, 0.11, 0.10), "wood_light", root, 0.015)
    for x in (-0.73, 0.73):
        for z in (2.76, 3.37): cube("Lookout side rail", (x, 0, z), (0.11, 1.46, 0.10), "wood_light", root, 0.015)
    # Timber wall panels leave tall, dark arrow openings visible on every side.
    for y in (-0.70, 0.70):
        for x in (-0.48, 0.48): cube("Lookout half-timber panel", (x, y, 3.08), (0.42, 0.075, 0.46), "wood_end", root, 0.02)
    for x in (-0.70, 0.70):
        for y in (-0.48, 0.48): cube("Lookout side infill", (x, y, 3.08), (0.075, 0.42, 0.46), "wood_end", root, 0.02)
    for x in (-0.73, -0.25, 0.25, 0.73): cube("Lookout upper tie", (x, -0.76, 3.40), (0.10, 0.11, 0.12), "wood", root, 0.015)
    # A steep, separate gable roof with eaves, ridge and individually laid tiles.
    gable_mesh("Lookout front gable", 1.54, 3.40, 4.10, -0.78, 0.07, "cream", root)
    gable_mesh("Lookout rear gable", 1.54, 3.40, 4.10, 0.71, 0.07, "cream", root)
    roof_slab("Tower roof left slope", (-0.90, 3.43), (0, 4.18), 1.80, 0.12, "tile_dark", root)
    roof_slab("Tower roof right slope", (0, 4.18), (0.90, 3.43), 1.80, 0.12, "tile", root)
    cube("Tower roof ridge", (0, 0, 4.20), (0.14, 1.88, 0.11), "wood", root, 0.025)
    for side in (-1, 1):
        for row in range(4):
            x = side * (0.72 - row * 0.17)
            z = 3.53 + 0.57 * (1.0 - abs(x) / 0.90)
            for col in range(5):
                y = -0.72 + col * 0.36
                cube("Tower roof tile", (x, y, z), (0.23, 0.31, 0.045), ("tile_dark", "tile", "stone_light")[(row + col) % 3], root, 0.012, rotation=(0, side * 0.69, 0))
    cylinder("Tower roof finial socket", (0, 0, 4.25), 0.11, 0.12, "gold", root, 8)
    beam("Tower roof finial", (0, 0, 4.30), (0, 0, 4.62), 0.035, "gold", root, 0.005)
    return root


def pine_tree_model():
    root = reset_scene("PineTree")
    cylinder("Pine trunk", (0, 0, 1.18), 0.17, 2.36, "bark", root, 9)
    for i, (z, radius, height) in enumerate(((0.72, 0.96, 1.45), (1.38, 0.80, 1.42), (2.02, 0.62, 1.35), (2.60, 0.42, 1.18))):
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=radius, radius2=0.04, depth=height, location=(0, 0, z + height*0.5 - 0.25))
        finish(bpy.context.object, "Layered evergreen crown %d" % i, ("leaf_dark", "leaf_mid", "leaf_light")[i % 3], root)
    return root


def young_tree_model():
    root = tree_model()
    root.name = "YoungOak"
    root.scale = (0.58, 0.58, 0.62)
    return root


def rock_cluster_model():
    root = reset_scene("RockCluster")
    for i, (x, y, z, s) in enumerate(((-0.42, -0.08, 0.34, (0.58,0.50,0.62)), (0.30,-0.12,0.30,(0.52,0.60,0.52)), (0.02,0.32,0.25,(0.42,0.44,0.40)), (-0.02,-0.38,0.21,(0.34,0.40,0.34)))):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=(x,y,z))
        obj=bpy.context.object; obj.scale=s
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        finish(obj, "Faceted river boulder %d"%i, "stone_light" if i%2 else "stone", root)
    for i in range(5):
        x=-0.65+i*0.30
        uv_sphere("Moss cushion", (x,0.05,0.08), (0.19,0.16,0.08), "moss", root, 7, 4)
    return root


def stone_bridge_model():
    root = reset_scene("StoneBridge")
    # A swept masonry body follows the arch so the road descends to the banks.
    # This replaces the old high, flat slab that looked like a table over the river.
    span = 4.2
    segments = 20
    def deck_height(x):
        ratio = max(-1.0, min(1.0, x / span))
        return 0.30 + 0.86 * math.sqrt(max(0.0, 1.0 - ratio * ratio))

    verts = []
    faces = []
    for i in range(segments + 1):
        x = -span + 2.0 * span * i / segments
        top = deck_height(x)
        verts.extend(((x, -1.48, top), (x, 1.48, top), (x, -1.48, top - 0.34), (x, 1.48, top - 0.34)))
    for i in range(segments):
        a = i * 4
        b = (i + 1) * 4
        faces.extend(((a, a + 1, b + 1, b), (a + 2, b + 2, b + 3, a + 3),
                      (a, b, b + 2, a + 2), (a + 1, a + 3, b + 3, b + 1)))
    faces.extend(((0, 2, 3, 1), (segments * 4, segments * 4 + 1, segments * 4 + 3, segments * 4 + 2)))
    mesh_obj("Curved bridge spandrel", verts, faces, "stone_light", root, bevel=0.015)

    # Separate paving blocks and parapet sections follow the curved roadway.
    for i in range(18):
        x = -3.98 + i * 0.468
        slope = (deck_height(x + 0.04) - deck_height(x - 0.04)) / 0.08
        angle = -math.atan(slope)
        deck_z = deck_height(x)
        cube("Individual bridge paving slab", (x, 0, deck_z + 0.075), (0.49, 2.66, 0.15), "road_a" if i % 3 else "road_b", root, 0.025, rotation=(0, angle, 0))
        for side in (-1, 1):
            y = side * 1.39
            cube("Curved stone parapet block", (x, y, deck_z + 0.29), (0.51, 0.26, 0.52), "stone", root, 0.035, rotation=(0, angle, 0))
            cube("Parapet capstone", (x, y, deck_z + 0.57), (0.56, 0.34, 0.10), "stone_light", root, 0.025, rotation=(0, angle, 0))

    # Individual voussoirs trace the open arch beneath the curved deck.
    for i in range(17):
        theta=math.pi*(i+0.5)/17
        x=3.65*math.cos(theta); z=0.38+0.82*math.sin(theta)
        block=cube("Arched stone voussoir", (x,0,z), (0.55,3.10,0.33), "stone_light" if i%2 else "stone", root, 0.025)
        block.rotation_euler[1]=-theta+math.pi/2
    for x in (-3.82,3.82):
        cube("Bridge bank abutment", (x,0,0.17), (0.72,3.25,0.34), "stone", root, 0.06)
        for y in (-1.45,1.45): cube("Bridge end pier cap", (x,y,0.40), (0.80,0.42,0.12), "stone_light", root, 0.035)
    return root


def riverbank_model():
    root = reset_scene("RiverbankSection")
    cube("Layered soil bank", (0,0,0.03), (4.0,2.5,0.22), "soil", root, 0.06)
    # A gently stepped stone lip and gravel shelf lead down toward the water edge.
    for i in range(9):
        x=-1.82+i*0.45
        y=-0.86 + 0.10*math.sin(i*0.8)
        cube("Irregular shoreline rock", (x,y,0.19), (0.48,0.42,0.30+(i%3)*0.04), "stone_light" if i%2 else "stone", root, 0.06, rotation=(0,0,(-1 if i%2 else 1)*0.10))
    for i in range(12):
        x=-1.75+(i*0.31)%3.5; y=-0.5-(i%4)*0.20
        uv_sphere("Bank gravel pebble", (x,y,0.14), (0.13,0.12,0.06), "road_b", root, 7, 4)
    for i in range(7):
        x=-1.65+i*0.54; y=0.48+0.18*math.sin(i)
        beam("Bank grass blade", (x,y,0.13),(x+0.06,y,0.43+(i%3)*0.07),0.035,"leaf_mid",root,0.004)
    for x in (-1.45,0.65,1.55):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=(x,-0.12,0.36))
        o=bpy.context.object; o.scale=(0.34,0.38,0.40); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        finish(o,"Bank boulder","stone",root)
    return root


def shrub_cluster_model():
    root = reset_scene("WildShrubCluster")
    # Layered faceted leaves, visible twig structure, blossoms and berries.
    for i, (x, y, z, s) in enumerate(((-0.47,-0.04,0.40,(0.46,0.40,0.38)),(-0.18,0.23,0.48,(0.48,0.45,0.43)),(0.18,-0.20,0.42,(0.50,0.42,0.39)),(0.48,0.08,0.38,(0.42,0.40,0.36)),(0.02,0.02,0.67,(0.42,0.40,0.38)))):
        uv_sphere("Layered wild foliage", (x,y,z), s, ("leaf_dark","leaf_mid","leaf_light")[i%3], root, 9, 5)
    for a in (0.3,1.5,2.7,4.1,5.4):
        beam("Forked shrub twig", (0,0,0.10),(math.cos(a)*0.46,math.sin(a)*0.42,0.57),0.045,"bark",root,0.006)
    for i in range(9):
        a=i*math.tau/9; radius=0.48+(i%3)*0.08
        color=("produce_yellow","produce_red","cream")[i%3]
        uv_sphere("Wildflower or berry",(math.cos(a)*radius,math.sin(a)*radius,0.56+(i%2)*0.10),(0.075,0.075,0.085),color,root,7,4)
    return root


def reed_clump_model():
    root = reset_scene("RiverReedClump")
    for i in range(9):
        a=i*math.tau/9; base_x=math.cos(a)*0.16; base_y=math.sin(a)*0.16
        height=0.62+(i%4)*0.13
        tip=(base_x+math.cos(a)*0.18,base_y+math.sin(a)*0.15,height)
        beam("Reed stem",(base_x,base_y,0.04),tip,0.035,"leaf_mid",root,0.004)
        # Narrow pointed seed head and two lance-shaped leaves make the plant read from a high camera.
        bpy.ops.mesh.primitive_cone_add(vertices=7,radius1=0.055,radius2=0.005,depth=0.20,location=(tip[0],tip[1],tip[2]+0.08))
        finish(bpy.context.object,"Reed seed head","wood_end",root)
        for side in (-1,1):
            beam("Reed blade",(base_x,base_y,0.18),(base_x+side*0.16,base_y+math.sin(a)*0.12,0.44+(i%3)*0.07),0.025,"leaf_light",root,0.003)
    return root


BUILDERS = {
    "medieval_house": house_model,
    "town_market": market_model,
    "oak_tree": tree_model,
    "stone_road": road_model,
    "house_large": large_house_model,
    "house_large_b": large_house_variant_b_model,
    "house_large_c": large_house_variant_c_model,
    "warehouse": warehouse_model,
    "workshop": workshop_model,
    "farm": farm_model,
    "forum": civic_hall_model,
    "temple": temple_model,
    "watchtower": watchtower_model,
    "pine_tree": pine_tree_model,
    "young_tree": young_tree_model,
    "rock_cluster": rock_cluster_model,
    "stone_bridge": stone_bridge_model,
    "riverbank": riverbank_model,
    "shrub_cluster": shrub_cluster_model,
    "reed_clump": reed_clump_model,
}


def join_by_material(root):
    # Join mesh objects by material for low draw-call counts while retaining material variation.
    bpy.ops.object.select_all(action="DESELECT")
    for child in root.children:
        if child.type == "MESH":
            child.select_set(True)
    bpy.context.view_layer.objects.active = next((o for o in root.children if o.type == "MESH"), None)
    if bpy.context.view_layer.objects.active is None:
        return
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = root.name + "_Geometry"
    joined.parent = root
    joined.matrix_parent_inverse = root.matrix_world.inverted()
    # Recalculate face normals after combining separate hand-built components.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def export_asset(asset_name, builder):
    root = builder()
    # Keep the root at the planting/building origin and put all visible geometry above Z=0.
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    # Preserve a genuinely editable source scene before reducing draw calls for GLB.
    collection_names = ("Architecture", "Roofing", "Timber", "Openings", "Ground", "Foliage", "Ornaments")
    collections = {}
    for collection_name in collection_names:
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)
        collections[collection_name] = collection
    for obj in list(root.children):
        if obj.type != "MESH":
            continue
        n = obj.name.lower()
        if any(k in n for k in ("roof", "tile", "ridge", "rafter", "eave", "gable", "awning")):
            target = collections["Roofing"]
        elif any(k in n for k in ("oak", "timber", "wood", "beam", "post", "plank", "barrel", "crate", "balcony", "fence", "wheel", "hay")):
            target = collections["Timber"]
        elif any(k in n for k in ("window", "door", "glass", "shutter", "mullion", "handle")):
            target = collections["Openings"]
        elif any(k in n for k in ("foliage", "leaf", "tree", "bough", "crown", "crop", "grass", "moss", "stalk", "pebble", "gravel")):
            target = collections["Foliage"]
        elif any(k in n for k in ("foundation", "soil", "platform", "pad", "step", "plinth", "road", "paving", "stone", "earth", "bank", "shore", "voussoir", "abutment")):
            target = collections["Ground"]
        elif any(k in n for k in ("ornament", "seal", "lantern", "iron", "gold", "finial", "produce", "scarecrow")):
            target = collections["Ornaments"]
        else:
            target = collections["Architecture"]
        for c in list(obj.users_collection): c.objects.unlink(obj)
        target.objects.link(obj)
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
    blend_path = os.path.join(BLEND_DIR, asset_name + ".blend")
    glb_path = os.path.join(GLB_DIR, asset_name + ".glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    join_by_material(root)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("EXPORTED", asset_name, "blend=", blend_path, "glb=", glb_path)


requested = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()
unknown = requested.difference(BUILDERS)
if unknown:
    raise SystemExit("Unknown asset(s): " + ", ".join(sorted(unknown)))
for name, builder in BUILDERS.items():
    if requested and name not in requested:
        continue
    export_asset(name, builder)

print("BLENDER_MODEL_BUILD_COMPLETE", bpy.app.version_string)
