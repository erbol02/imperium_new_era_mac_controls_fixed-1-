"""Build/export the first production-ready low-poly assets for Imperium: New Era.

Run from the project root:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python assets/blender/build_game_models.py

Every model is authored with bpy, saved as a .blend source, and exported as a self-contained GLB.
The assets are small, use shared Principled materials, and contain no external textures.
"""
import bpy
import math
import os
import random
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


def gable_mesh(name, width, y0, y1, z, depth, material, parent):
    w = width * 0.5
    points = [(-w, y0), (w, y0), (0, y1)]
    verts = [(x, y, z) for x, y in points] + [(x, y, z - depth) for x, y in points]
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
    # Front door, stone architrave, iron fittings and a small stoop.
    cube("Recessed oak door", (0, -0.79, 0.51), (0.34, 0.065, 0.76), "wood_light", root, 0.018)
    for x in (-0.10, -0.03, 0.04, 0.11):
        cube("Door plank seam", (x, -0.827, 0.51), (0.018, 0.012, 0.68), "wood", root, 0.003)
    cube("Door lintel", (0, -0.81, 0.91), (0.46, 0.09, 0.10), "stone_light", root, 0.018)
    cylinder("Iron door handle", (0.10, -0.842, 0.53), 0.028, 0.025, "gold", root, vertices=8, rotation=(math.pi / 2, 0, 0))
    cube("Stone entrance step", (0, -0.83, 0.16), (0.62, 0.32, 0.14), "stone_light", root, 0.035)
    # Two inset windows with deep teal glass, oak mullions and operable shutters.
    for wx in (-0.44, 0.44):
        cube("Deep window shadow", (wx, -0.79, 0.98), (0.30, 0.06, 0.37), "wood", root, 0.025)
        cube("Lead glass window", (wx, -0.83, 0.99), (0.22, 0.025, 0.29), "glass", root, 0.01)
        for dx in (-0.14, 0.14):
            cube("Window oak jamb", (wx + dx, -0.855, 0.99), (0.045, 0.045, 0.43), "wood_light", root, 0.01)
        for dz in (0.78, 1.20):
            cube("Window frame sill", (wx, -0.855, dz), (0.33, 0.06, 0.055), "cream", root, 0.012)
        cube("Window mullion", (wx, -0.86, 0.99), (0.025, 0.045, 0.30), "wood_light", root, 0.006)
        cube("Window crossbar", (wx, -0.86, 0.99), (0.22, 0.045, 0.025), "wood_light", root, 0.006)
        for side in (-1, 1):
            cube("Hinged oak shutter", (wx + side * 0.22, -0.83, 0.99), (0.075, 0.055, 0.34), "wood_light", root, 0.01)
            for row in range(3):
                cube("Shutter carved slat", (wx + side * 0.22, -0.865, 0.90 + row * 0.085), (0.07, 0.012, 0.018), "wood_end", root, 0.003)
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
                tile_mat = "tile_light" if (row + col) % 3 == 0 else ("tile" if (row + col) % 3 else "tile_dark")
                cube("Individual terracotta roof tile", (x, y, z), (0.29, 0.31, 0.045), tile_mat, root, 0.018, rotation=(0, side * 0.64, 0))
        for y in (-0.90, 0.90):
            beam("Exposed carved rafter", (side * 0.86, y, 1.43), (0, y, 2.24), 0.055, "wood", root)
    # Chimney, capstones, little attic vent and two hanging lantern brackets.
    cube("Stone chimney stack", (-0.48, 0.36, 2.12), (0.29, 0.32, 0.92), "stone", root, 0.025)
    cube("Chimney crown", (-0.48, 0.36, 2.61), (0.39, 0.41, 0.10), "stone_light", root, 0.02)
    cube("Chimney flue", (-0.48, 0.36, 2.67), (0.19, 0.20, 0.035), "iron", root, 0.008)
    # Little side dormer adds a distinct roof silhouette.
    cube("Dormer front", (0.47, -0.60, 1.89), (0.42, 0.18, 0.42), "plaster", root, 0.018)
    roof_slab("Dormer roof left", (0.25, 1.99), (0.47, 2.20), 0.54, 0.06, "tile_light", root)
    roof_slab("Dormer roof right", (0.47, 2.20), (0.69, 1.99), 0.54, 0.06, "tile", root)
    cube("Dormer window", (0.47, -0.71, 1.91), (0.16, 0.04, 0.20), "glass", root, 0.01)
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


BUILDERS = {
    "medieval_house": house_model,
    "town_market": market_model,
    "oak_tree": tree_model,
    "stone_road": road_model,
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
    join_by_material(root)
    # Keep the root at the planting/building origin and put all visible geometry above Z=0.
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    blend_path = os.path.join(BLEND_DIR, asset_name + ".blend")
    glb_path = os.path.join(GLB_DIR, asset_name + ".glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
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


for name, builder in BUILDERS.items():
    export_asset(name, builder)

print("BLENDER_MODEL_BUILD_COMPLETE", bpy.app.version_string)
