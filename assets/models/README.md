# Blender-authored game models

Source `.blend` scenes live in `assets/blender/source/`; the automated low-poly authoring and GLB exporter is `assets/blender/build_game_models.py`. Run `assets/blender/build_and_import.sh` from anywhere to regenerate every source and export and ask Godot to import the GLBs.

| Asset | Blender source | Godot export/use |
|---|---|---|
| Small timber-and-plaster house | `source/medieval_house.blend` | `medieval_house.glb` → `scenes/assets/medieval_house.tscn` |
| Large house, 3 silhouettes | `source/house_large*.blend` | `house_large*.glb` → `scenes/buildings/house_large.tscn` |
| Market stalls | `source/town_market.blend` | `town_market.glb` → `scenes/buildings/market.tscn` |
| Warehouse | `source/warehouse.blend` | `warehouse.glb` → `scenes/buildings/warehouse.tscn` |
| Blacksmith workshop | `source/workshop.blend` | `workshop.glb` → `scenes/buildings/workshop.tscn` |
| Farm plot and shed | `source/farm.blend` | `farm.glb` → `scenes/buildings/farm.tscn` |
| Civic hall / forum | `source/forum.blend` | `forum.glb` → `scenes/buildings/forum.tscn` |
| Temple, watchtower | `source/temple.blend`, `source/watchtower.blend` | matching GLBs in `assets/models/` |
| Oak, pine, young tree | matching `.blend` sources | matching GLBs in environment scenes |
| Stone road, arched bridge, riverbank, boulder cluster, shrub cluster, river reeds | matching `.blend` sources | matching GLBs in environment scenes |

Each `.blend` retains the named, editable mesh parts grouped into collections by architecture, roofing, timber, openings, ground, foliage, and ornaments. GLBs are joined by material to keep draw calls modest. Principled material palette colors are preserved; small embedded microdetail maps drive roughness so stone, wood, and tiles keep their color in Godot.

Run `assets/blender/build_and_import.sh` to regenerate Blender sources and GLBs and import them into Godot. Run Godot with `-- --building-gallery-test` to place every buildable type (including all large-house variants) through the normal placement code and save an overview plus close-ups under `screenshots/`. The normal-budget city bot is `-- --auto-test`; it saves `auto_test_city_after.png` when launched with the graphical display.
