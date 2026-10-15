extends Node3D
## Lightweight, reusable low-poly asset generator used by the individual .tscn assets.
## Every asset is a real Godot scene with separate meshes/materials for its structural parts.

@export_enum("house_small", "house_large", "market", "warehouse", "workshop", "farm", "forum", "tree_oak", "tree_pine", "tree_young", "rock", "road", "bridge", "riverbank") var model_kind := "house_small"
@export var variant := 0

const MAT_STONE: StandardMaterial3D = preload("res://assets/materials/stone.tres")
const MAT_OAK: StandardMaterial3D = preload("res://assets/materials/oak_wood.tres")
const MAT_TILE: StandardMaterial3D = preload("res://assets/materials/terracotta.tres")
const MAT_PLASTER: StandardMaterial3D = preload("res://assets/materials/plaster.tres")
const MAT_GRASS: StandardMaterial3D = preload("res://assets/materials/grass.tres")

var _materials: Dictionary = {}

func _ready() -> void:
	match model_kind:
		"house_small": _house(false)
		"house_large": _house(true)
		"market": _market()
		"warehouse": _warehouse()
		"workshop": _workshop()
		"farm": _farm()
		"forum": _forum()
		"tree_oak": _tree_oak()
		"tree_pine": _tree_pine()
		"tree_young": _tree_young()
		"rock": _rock()
		"road": _road()
		"bridge": _bridge()
		"riverbank": _riverbank()
	_merge_static_meshes()

func _mat(color: Color, roughness := 0.92) -> StandardMaterial3D:
	var key := color.to_html(true) + str(roughness)
	if _materials.has(key): return _materials[key]
	var base: StandardMaterial3D = MAT_STONE
	if color.r > color.g * 1.5 and color.g < 0.40 and color.r > 0.42: base = MAT_TILE
	elif color.g > color.r * 1.08: base = MAT_GRASS
	elif color.r > 0.58 and color.g > 0.43: base = MAT_PLASTER
	elif color.r < 0.45 and color.g < 0.34: base = MAT_OAK
	var m: StandardMaterial3D = base.duplicate()
	m.albedo_color = color
	m.roughness = roughness
	_materials[key] = m
	return m

func _box(label: String, pos: Vector3, size: Vector3, color: Color, rotation := Vector3.ZERO) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	n.name = label
	var mesh := BoxMesh.new()
	mesh.size = size
	n.mesh = mesh
	n.position = pos
	n.rotation = rotation
	n.material_override = _mat(color)
	add_child(n)
	return n

func _cylinder(label: String, pos: Vector3, top: float, bottom: float, height: float, color: Color, sides := 8) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	n.name = label
	var mesh := CylinderMesh.new()
	mesh.top_radius = top
	mesh.bottom_radius = bottom
	mesh.height = height
	mesh.radial_segments = sides
	n.mesh = mesh
	n.position = pos
	n.material_override = _mat(color)
	add_child(n)
	return n

func _ball(label: String, pos: Vector3, scale_value: Vector3, color: Color, sides := 8) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	n.name = label
	var mesh := SphereMesh.new()
	mesh.radial_segments = sides
	mesh.rings = 5
	n.mesh = mesh
	n.position = pos
	n.scale = scale_value
	n.material_override = _mat(color)
	add_child(n)
	return n

func _gable(label: String, width: float, base: float, apex: float, z: float, color: Color) -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.add_vertex(Vector3(-width * 0.5, base, z))
	st.add_vertex(Vector3(width * 0.5, base, z))
	st.add_vertex(Vector3(0, apex, z))
	st.add_vertex(Vector3(0, apex, z - 0.06))
	st.add_vertex(Vector3(width * 0.5, base, z - 0.06))
	st.add_vertex(Vector3(-width * 0.5, base, z - 0.06))
	st.generate_normals()
	var n := MeshInstance3D.new()
	n.name = label
	n.mesh = st.commit()
	n.material_override = _mat(color)
	add_child(n)

func _roof_pair(width: float, depth: float, y: float, color: Color, ridge_y := 0.34) -> void:
	# Thick, separate pitched planes with exposed rafters, fascia and ridge cap.
	var half := width * 0.5
	var run := half + 0.15
	var angle := atan2(ridge_y, run)
	_box("Roof slope left", Vector3(-run * 0.5, y + ridge_y * 0.5, 0), Vector3(sqrt(run * run + ridge_y * ridge_y), 0.16, depth + 0.28), color, Vector3(0, 0, angle))
	_box("Roof slope right", Vector3(run * 0.5, y + ridge_y * 0.5, 0), Vector3(sqrt(run * run + ridge_y * ridge_y), 0.16, depth + 0.28), color.lightened(0.08), Vector3(0, 0, -angle))
	_box("Roof ridge cap", Vector3(0, y + ridge_y + 0.02, 0), Vector3(0.16, 0.13, depth + 0.34), Color(0.34, 0.16, 0.10))
	for z in [-depth * 0.5 - 0.13, depth * 0.5 + 0.13]:
		_box("Gable eave fascia", Vector3(0, y + 0.04, z), Vector3(width + 0.32, 0.11, 0.10), Color(0.33, 0.19, 0.11))
	for side in [-1.0, 1.0]:
		for i in range(5):
			var zpos := -depth * 0.44 + float(i) * depth * 0.22
			var rib := _box("Raised clay tile course", Vector3(side * run * 0.50, y + ridge_y * 0.50 + 0.08, zpos), Vector3(sqrt(run * run + ridge_y * ridge_y) * 0.93, 0.035, 0.045), color.lightened(0.16), Vector3(0, 0, -side * angle))
			# Mesh transform keeps repeated courses attached to their slope.
			rib.rotation.z = side * angle

func _house(large: bool) -> void:
	var w := 1.30 if not large else 1.55
	var d := 1.24 if not large else 1.50
	var h := 0.96 if not large else 1.28
	var plaster: Color = [Color(0.76, 0.65, 0.49), Color(0.77, 0.72, 0.59), Color(0.69, 0.51, 0.37)][variant % 3]
	var roof: Color = [Color(0.62, 0.24, 0.14), Color(0.36, 0.40, 0.47), Color(0.48, 0.20, 0.13)][variant % 3]
	_box("Rough stone plinth", Vector3(0, 0.12, 0), Vector3(w + 0.14, 0.24, d + 0.14), Color(0.40, 0.37, 0.31))
	_box("Front limewashed wall", Vector3(0, 0.24 + h * 0.5, d * 0.5), Vector3(w, h, 0.12), plaster)
	_box("Back limewashed wall", Vector3(0, 0.24 + h * 0.5, -d * 0.5), Vector3(w, h, 0.12), plaster.darkened(0.08))
	_box("Left limewashed wall", Vector3(-w * 0.5, 0.24 + h * 0.5, 0), Vector3(0.12, h, d - 0.18), plaster.darkened(0.05))
	_box("Right limewashed wall", Vector3(w * 0.5, 0.24 + h * 0.5, 0), Vector3(0.12, h, d - 0.18), plaster)
	_gable("Front plaster gable", w, 0.24 + h, 0.24 + h + (0.48 if large else 0.43), d * 0.5 + 0.07, plaster)
	_gable("Rear plaster gable", w, 0.24 + h, 0.24 + h + (0.48 if large else 0.43), -d * 0.5 - 0.07, plaster.darkened(0.06))
	# Timber frame is independent geometry, deliberately thicker than wall trim.
	for x in [-w * 0.47, w * 0.47]:
		_box("Front oak upright", Vector3(x, 0.24 + h * 0.5, d * 0.5 + 0.085), Vector3(0.095, h + 0.06, 0.10), Color(0.29, 0.17, 0.09))
	_box("Front oak crossbeam", Vector3(0, 0.67, d * 0.5 + 0.09), Vector3(w, 0.08, 0.09), Color(0.34, 0.20, 0.11))
	_box("Gable tie beam", Vector3(0, 0.24 + h + 0.12, d * 0.5 + 0.09), Vector3(w, 0.075, 0.08), Color(0.34, 0.20, 0.11))
	_box("Recessed oak door", Vector3(0, 0.49, d * 0.5 + 0.12), Vector3(0.32, 0.66, 0.065), Color(0.24, 0.13, 0.08))
	for i in range(4):
		_box("Door plank seam", Vector3(-0.105 + float(i) * 0.07, 0.49, d * 0.5 + 0.158), Vector3(0.018, 0.59, 0.015), Color(0.42, 0.26, 0.14))
	_box("Door lintel", Vector3(0, 0.85, d * 0.5 + 0.15), Vector3(0.45, 0.09, 0.10), Color(0.38, 0.23, 0.13))
	_ball("Iron door boss", Vector3(0.10, 0.51, d * 0.5 + 0.17), Vector3(0.045, 0.045, 0.035), Color(0.76, 0.58, 0.23), 6)
	var window_positions := [-0.43, 0.43] if large else [-0.41, 0.41]
	for wx in window_positions:
		_box("Dark window recess", Vector3(wx, 0.79, d * 0.5 + 0.10), Vector3(0.34, 0.37, 0.055), Color(0.11, 0.22, 0.25))
		for side in [-1.0, 1.0]: _box("Oak window jamb", Vector3(wx + side * 0.20, 0.79, d * 0.5 + 0.15), Vector3(0.055, 0.44, 0.07), Color(0.36, 0.22, 0.12))
		_box("Window crossbar", Vector3(wx, 0.79, d * 0.5 + 0.16), Vector3(0.35, 0.045, 0.07), Color(0.40, 0.25, 0.13))
		_box("Stone window sill", Vector3(wx, 0.55, d * 0.5 + 0.17), Vector3(0.45, 0.075, 0.13), Color(0.78, 0.69, 0.52))
		_box("Oak shutter left", Vector3(wx - 0.25, 0.79, d * 0.5 + 0.16), Vector3(0.07, 0.32, 0.07), Color(0.36, 0.23, 0.12))
		_box("Oak shutter right", Vector3(wx + 0.25, 0.79, d * 0.5 + 0.16), Vector3(0.07, 0.32, 0.07), Color(0.36, 0.23, 0.12))
	_roof_pair(w, d, 1.37 if not large else 1.58, roof, 0.44 if not large else 0.54)
	if large:
		_box("Stone chimney", Vector3(-0.46, 1.98, -0.48), Vector3(0.27, 0.78, 0.29), Color(0.48, 0.33, 0.24))
		_box("Chimney crown", Vector3(-0.46, 2.39, -0.48), Vector3(0.36, 0.10, 0.37), Color(0.37, 0.27, 0.20))
		_box("Upper timber balcony", Vector3(0.0, 1.30, d * 0.5 + 0.20), Vector3(0.72, 0.11, 0.34), Color(0.43, 0.27, 0.14))
		for x in [-0.34, 0.34]: _box("Balcony bracket", Vector3(x, 1.12, d * 0.5 + 0.20), Vector3(0.08, 0.34, 0.08), Color(0.34, 0.20, 0.11))

func _market() -> void:
	for x in [-0.73, 0.0, 0.73]:
		for z in [-0.62, 0.62]:
			_cylinder("Carved market post", Vector3(x, 0.69, z), 0.055, 0.075, 1.30, Color(0.31, 0.19, 0.10), 6)
			_box("Post capital", Vector3(x, 1.35, z), Vector3(0.15, 0.09, 0.15), Color(0.58, 0.40, 0.22))
	for z in [-0.60, 0.60]: _box("Oak canopy beam", Vector3(0, 1.28, z), Vector3(1.60, 0.12, 0.12), Color(0.35, 0.21, 0.12))
	_box("Stone vendor counter", Vector3(0, 0.36, 0.25), Vector3(1.58, 0.33, 0.55), Color(0.62, 0.51, 0.37))
	_box("Counter slab", Vector3(0, 0.55, 0.25), Vector3(1.68, 0.09, 0.62), Color(0.78, 0.67, 0.50))
	_box("Lower timber stall", Vector3(0, 0.25, -0.50), Vector3(1.28, 0.36, 0.45), Color(0.45, 0.30, 0.17))
	for i in range(7):
		var x := -0.58 + float(i) * 0.19
		var stripe: Color = Color(0.80, 0.69, 0.49) if i % 2 == 0 else Color(0.65, 0.18, 0.13)
		_box("Canvas canopy stripe", Vector3(x, 1.40, -0.02), Vector3(0.20, 0.07, 1.45), stripe, Vector3(-0.12, 0, 0))
		_box("Scalloped canopy valance", Vector3(x, 1.32, 0.68), Vector3(0.19, 0.15, 0.06), stripe)
	for i in range(8):
		var c: Color = [Color(0.82, 0.25, 0.10), Color(0.81, 0.63, 0.14), Color(0.40, 0.61, 0.22)][i % 3]
		_ball("Market fruit", Vector3(-0.63 + float(i) * 0.18, 0.66, 0.23 + 0.10 * float(i % 2)), Vector3(0.13, 0.12, 0.13), c, 7)

func _warehouse() -> void:
	_box("Warehouse cut-stone plinth", Vector3(0, 0.15, 0), Vector3(1.88, 0.30, 1.88), Color(0.40, 0.38, 0.32))
	for x in [-0.82, 0.82]: _box("Warehouse gable wall", Vector3(x, 0.91, 0), Vector3(0.12, 1.24, 1.62), Color(0.69, 0.57, 0.40))
	_box("Warehouse rear wall", Vector3(0, 0.87, -0.82), Vector3(1.64, 1.15, 0.12), Color(0.64, 0.52, 0.37))
	for x in [-0.70, -0.26, 0.26, 0.70]: _box("Exposed oak frame", Vector3(x, 0.86, 0.83), Vector3(0.11, 1.20, 0.12), Color(0.30, 0.18, 0.10))
	_box("Warehouse double doors", Vector3(0, 0.57, 0.85), Vector3(0.78, 0.82, 0.08), Color(0.32, 0.19, 0.10))
	for x in [-0.34, 0.34]:
		_box("Iron strapped door", Vector3(x, 0.57, 0.90), Vector3(0.035, 0.74, 0.025), Color(0.55, 0.41, 0.25))
	for y in [0.30, 0.57, 0.83]: _box("Door cross brace", Vector3(0, y, 0.91), Vector3(0.82, 0.055, 0.04), Color(0.48, 0.31, 0.16))
	_gable("Warehouse front gable", 1.65, 1.50, 2.12, 0.77, Color(0.69, 0.57, 0.40))
	_roof_pair(1.75, 1.70, 1.52, Color(0.39, 0.19, 0.13), 0.50)
	for x in [-0.55, 0.55]:
		_box("Oak storage crate", Vector3(x, 0.39, 0.56), Vector3(0.35, 0.38, 0.32), Color(0.53, 0.34, 0.17))
		_box("Crate top slat", Vector3(x, 0.60, 0.56), Vector3(0.38, 0.05, 0.35), Color(0.64, 0.43, 0.22))

func _workshop() -> void:
	_house(false)
	_box("Workshop lean-to wall", Vector3(0.77, 0.44, -0.28), Vector3(0.46, 0.70, 0.82), Color(0.58, 0.45, 0.31))
	_box("Workshop shed roof", Vector3(0.75, 0.88, -0.28), Vector3(0.73, 0.13, 0.98), Color(0.42, 0.19, 0.12), Vector3(0, 0, -0.16))
	_box("Workshop stone chimney", Vector3(-0.38, 1.92, -0.32), Vector3(0.25, 0.72, 0.26), Color(0.49, 0.31, 0.21))
	_box("Chimney cap", Vector3(-0.38, 2.30, -0.32), Vector3(0.34, 0.10, 0.34), Color(0.35, 0.26, 0.20))
	for i in range(3): _box("Chimney dark opening", Vector3(-0.43 + float(i) * 0.05, 2.36, -0.15), Vector3(0.035, 0.04, 0.015), Color(0.12, 0.10, 0.08))
	_box("Workshop signboard", Vector3(0, 0.99, 0.78), Vector3(0.48, 0.22, 0.08), Color(0.67, 0.45, 0.22))
	for x in [-0.17, 0.17]: _box("Sign hanger", Vector3(x, 1.12, 0.80), Vector3(0.04, 0.17, 0.04), Color(0.29, 0.18, 0.10))

func _farm() -> void:
	_box("Fertile field earth", Vector3(0, 0.08, 0), Vector3(1.82, 0.16, 1.82), Color(0.34, 0.22, 0.13))
	for row in range(5):
		var x := -0.67 + float(row) * 0.34
		_box("Raised furrow", Vector3(x, 0.18, 0), Vector3(0.22, 0.09, 1.48), Color(0.48, 0.32, 0.16))
		for plant in range(5):
			var z := -0.61 + float(plant) * 0.30
			_ball("Crop rosette", Vector3(x, 0.31, z), Vector3(0.17, 0.22, 0.16), Color(0.40 + 0.04 * float(plant % 2), 0.56, 0.21), 7)
	for x in [-0.9, 0.9]:
		for z in [-0.78, 0.78]: _box("Field fence stake", Vector3(x, 0.34, z), Vector3(0.075, 0.58, 0.075), Color(0.30, 0.19, 0.10))
		_box("Field fence rail", Vector3(x, 0.46, 0), Vector3(0.06, 0.07, 1.56), Color(0.39, 0.25, 0.12))
	_box("Farmstead walls", Vector3(0.48, 0.48, -0.44), Vector3(0.54, 0.70, 0.56), Color(0.72, 0.58, 0.39))
	_box("Farmstead door", Vector3(0.48, 0.36, -0.14), Vector3(0.18, 0.47, 0.05), Color(0.30, 0.18, 0.10))
	_roof_pair(0.68, 0.68, 0.87, Color(0.52, 0.23, 0.14), 0.26)

func _forum() -> void:
	_box("Forum foundation step", Vector3(0, 0.12, 0), Vector3(1.9, 0.24, 1.82), Color(0.55, 0.50, 0.41))
	_box("Forum upper step", Vector3(0, 0.29, 0.02), Vector3(1.64, 0.14, 1.56), Color(0.76, 0.67, 0.52))
	_box("Forum cella", Vector3(0, 0.84, -0.29), Vector3(1.34, 0.96, 0.92), Color(0.78, 0.68, 0.52))
	for x in [-0.62, -0.21, 0.21, 0.62]:
		_cylinder("Fluted marble column", Vector3(x, 0.94, 0.47), 0.085, 0.12, 1.20, Color(0.89, 0.81, 0.66), 10)
		_box("Column capital", Vector3(x, 1.58, 0.47), Vector3(0.23, 0.10, 0.23), Color(0.87, 0.77, 0.59))
	_box("Forum entablature", Vector3(0, 1.67, 0.47), Vector3(1.62, 0.18, 0.20), Color(0.79, 0.68, 0.52))
	_gable("Forum pediment", 1.65, 1.76, 2.22, 0.56, Color(0.78, 0.67, 0.50))
	_roof_pair(1.78, 1.48, 1.82, Color(0.46, 0.23, 0.15), 0.43)

func _tree_oak() -> void:
	_cylinder("Forked oak trunk", Vector3(0, 0.88, 0), 0.12, 0.23, 1.76, Color(0.31, 0.19, 0.11), 7)
	for x in [-0.35, 0.35]: _cylinder("Oak branch", Vector3(x * 0.42, 1.48, 0), 0.07, 0.12, 0.92, Color(0.34, 0.21, 0.12), 6).rotation.z = -x * 1.5
	var greens: Array[Color] = [Color(0.17, 0.35, 0.18), Color(0.23, 0.41, 0.20), Color(0.30, 0.44, 0.21), Color(0.20, 0.38, 0.17)]
	_ball("Oak crown core", Vector3(0, 2.20, 0), Vector3(1.72, 1.65, 1.55), greens[variant % greens.size()], 9)
	for point in [Vector3(-0.48, 2.15, -0.20), Vector3(0.47, 2.28, 0.18), Vector3(-0.08, 2.68, 0.23), Vector3(0.10, 1.89, 0.47)]:
		_ball("Leaf cluster", point, Vector3(0.92, 0.88, 0.88), greens[(variant + 1) % greens.size()], 8)

func _tree_pine() -> void:
	_cylinder("Pine trunk", Vector3(0, 0.95, 0), 0.10, 0.16, 1.9, Color(0.32, 0.21, 0.13), 7)
	for tier in range(4):
		var base_y := 1.10 + float(tier) * 0.50
		_cylinder("Layered pine boughs", Vector3(0, base_y + 0.40, 0), 0.04, 0.70 - float(tier) * 0.12, 1.15 - float(tier) * 0.12, Color(0.14 + float(tier) * 0.025, 0.32 + float(tier) * 0.025, 0.20), 8)

func _tree_young() -> void:
	_cylinder("Young tree trunk", Vector3(0, 0.63, 0), 0.08, 0.14, 1.26, Color(0.34, 0.21, 0.12), 6)
	_ball("Young tree crown", Vector3(0, 1.55, 0), Vector3(0.95, 1.0, 0.90), Color(0.31, 0.48, 0.24), 8)
	_ball("Young crown leaf cluster", Vector3(0.23, 1.77, -0.12), Vector3(0.55, 0.58, 0.55), Color(0.39, 0.52, 0.25), 7)

func _rock() -> void:
	_ball("Faceted main boulder", Vector3(0, 0.28, 0), Vector3(0.96, 0.58, 0.78), Color(0.43, 0.43, 0.37), 7)
	_ball("Secondary stone", Vector3(0.48, 0.18, 0.22), Vector3(0.52, 0.34, 0.46), Color(0.52, 0.48, 0.40), 7)
	_ball("Small stone", Vector3(-0.48, 0.12, 0.27), Vector3(0.42, 0.25, 0.36), Color(0.38, 0.39, 0.34), 7)

func _road() -> void:
	_box("Earthen road bed", Vector3(0, 0.035, 0), Vector3(2.0, 0.07, 2.0), Color(0.32, 0.23, 0.15))
	var stone_colors: Array[Color] = [Color(0.67, 0.59, 0.45), Color(0.59, 0.52, 0.40), Color(0.74, 0.65, 0.50)]
	for row in range(4):
		for col in range(4):
			var x := -0.73 + float(col) * 0.49 + (0.12 if row % 2 == 1 else 0.0)
			var z := -0.73 + float(row) * 0.49
			_box("Hand-cut paving slab", Vector3(x, 0.105 + 0.006 * float((col + row) % 2), z), Vector3(0.43, 0.10, 0.43), stone_colors[(col + 2 * row + variant) % 3], Vector3(0, 0.035 * float((col + row) % 3), 0))
	for side in [-1.0, 1.0]:
		_box("Raised road curb", Vector3(side * 0.94, 0.12, 0), Vector3(0.12, 0.16, 1.98), Color(0.48, 0.42, 0.33))

func _bridge() -> void:
	# Arched stone bridge built from a curved deck, voussoirs and parapets.
	for i in range(9):
		var x := -2.0 + float(i) * 0.5
		var y := 0.42 + 0.50 * (1.0 - pow((x / 2.0), 2.0))
		_box("Bridge arch voussoir", Vector3(x, y, 0), Vector3(0.53, 0.34, 2.30), Color(0.59, 0.54, 0.44))
		_box("Bridge paving", Vector3(x, y + 0.20, 0), Vector3(0.48, 0.12, 1.86), Color(0.71, 0.63, 0.49))
	for side in [-1.0, 1.0]:
		for i in range(9):
			var x := -2.0 + float(i) * 0.5
			var y := 0.79 + 0.50 * (1.0 - pow((x / 2.0), 2.0))
			_box("Bridge parapet stone", Vector3(x, y, side * 1.06), Vector3(0.49, 0.24, 0.22), Color(0.51, 0.47, 0.39))
		for x in [-1.7, 1.7]: _box("Bridge end pier", Vector3(x, 0.52, side * 0.75), Vector3(0.55, 0.95, 0.52), Color(0.48, 0.45, 0.37))

func _riverbank() -> void:
	for i in range(7):
		var x := -0.82 + float(i) * 0.27
		var z := 0.18 * sin(float(i) * 0.8)
		_box("Irregular bank sod", Vector3(x, 0.06, z), Vector3(0.38, 0.12, 0.62), Color(0.39, 0.34, 0.22), Vector3(0, 0.12 * sin(float(i)), 0))
		_ball("Bank grass hummock", Vector3(x, 0.18, z), Vector3(0.42, 0.23, 0.58), Color(0.30, 0.42, 0.20))
	for i in range(4):
		_ball("Waterline pebble", Vector3(-0.60 + float(i) * 0.42, 0.12, -0.63), Vector3(0.30, 0.19, 0.28), Color(0.48, 0.44, 0.36), 7)
	for i in range(5):
		_cylinder("Reed stalk", Vector3(-0.70 + float(i) * 0.34, 0.48, -0.52), 0.018, 0.035, 0.72, Color(0.59, 0.59, 0.31), 5).rotation.z = -0.08 + float(i % 3) * 0.07

func _merge_static_meshes() -> void:
	# Combine each model's small static pieces by material: preserves details while
	# keeping draw calls low for the Intel Mac compatibility renderer.
	var groups: Dictionary = {}
	var source_count := 0
	for child in get_children():
		if not child is MeshInstance3D or child.mesh == null: continue
		var source: MeshInstance3D = child
		for surface_idx in range(source.mesh.get_surface_count()):
			var surface_material: Material = source.get_active_material(surface_idx)
			var key: int = surface_material.get_instance_id() if surface_material != null else 0
			if not groups.has(key): groups[key] = {"material": surface_material, "surfaces": []}
			groups[key].surfaces.append({"mesh": source.mesh, "surface": surface_idx, "transform": source.transform})
			source_count += 1
	set_meta("detail_mesh_count", source_count)
	var sources := get_children()
	for child in sources:
		if child is MeshInstance3D: remove_child(child)
	for group in groups.values():
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for piece in group.surfaces:
			st.append_from(piece.mesh, piece.surface, piece.transform)
		var merged := MeshInstance3D.new()
		merged.name = "Batched architectural mesh"
		merged.mesh = st.commit()
		merged.material_override = group.material
		merged.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		add_child(merged)
	for child in sources:
		if child.get_parent() == null: child.free()
