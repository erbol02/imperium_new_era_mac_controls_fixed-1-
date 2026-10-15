"""Export selected downloaded Quaternius farm BLEND assets to GLB for Godot.
This script converts supplied models as-is; it does not generate or alter meshes.
Run from the project root with Blender --background --python.
"""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/downloaded/Quaternius_Farm_Buildings/Blend"
DEST = ROOT / "assets/models/downloaded"
MODELS = ("Barn", "BigBarn", "OpenBarn", "Windmill", "TowerWindmill", "ChickenCoop", "Well", "WaterTower", "Silo", "Silo_House")
DEST.mkdir(parents=True, exist_ok=True)
for name in MODELS:
    source = SOURCE / f"{name}.blend"
    if not source.exists():
        continue
    bpy.ops.wm.open_mainfile(filepath=str(source))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    if mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]
    target = DEST / f"{name}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(target), export_format="GLB", use_selection=True,
        export_apply=True, export_materials="EXPORT", export_image_format="AUTO",
        export_yup=True, export_cameras=False, export_lights=False,
    )
    print(f"EXPORTED {name}: {len(mesh_objects)} mesh objects -> {target.relative_to(ROOT)}")
