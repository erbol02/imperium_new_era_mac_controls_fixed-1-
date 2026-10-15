extends Node3D

# Imperium: New Era — small, self-contained 3D city-builder prototype.
# All art is made from simple meshes so the project runs without external assets.

const GRID_SIZE := 2.0
const MAP_CELLS := 30
const MAP_HALF_EXTENT := 30.0
const RIVER_CENTER_X := -26.0
const RIVER_HALF_WIDTH := 3.1
const PLAZA_HALF_EXTENT := 3.9
const AUTO_TEST_ARG := "--auto-test"
const MODEL_SMOKE_ARG := "--model-smoke-test"
const BUILDING_SCENES := {
	"house": preload("res://scenes/buildings/house_small.tscn"),
	"house_large": preload("res://scenes/buildings/house_large.tscn"),
	"farm": preload("res://scenes/buildings/farm.tscn"),
	"market": preload("res://scenes/buildings/market.tscn"),
	"warehouse": preload("res://scenes/buildings/warehouse.tscn"),
	"workshop": preload("res://scenes/buildings/workshop.tscn"),
	"forum": preload("res://scenes/buildings/forum.tscn"),
	"road": preload("res://scenes/environment/stone_road.tscn")
}
const TREE_SCENES := [preload("res://scenes/environment/tree_oak.tscn"), preload("res://scenes/environment/tree_pine.tscn"), preload("res://scenes/environment/tree_young.tscn")]
const ROCK_SCENE: PackedScene = preload("res://scenes/environment/rock_cluster.tscn")
const BRIDGE_SCENE: PackedScene = preload("res://scenes/environment/stone_bridge.tscn")
const RIVERBANK_SCENE: PackedScene = preload("res://scenes/environment/riverbank.tscn")
const RIVER_MATERIAL: StandardMaterial3D = preload("res://assets/materials/river_water.tres")
const GRASS_MATERIAL: StandardMaterial3D = preload("res://assets/materials/grass.tres")

var camera: Camera3D
var camera_pivot: Node3D
var ground_body: StaticBody3D
var ui_layer: CanvasLayer
var hud_label: Label
var message_label: Label
var selected_label: Label
var money := 1200
var population := 0
var food := 30
var day := 1
var selected_building := "house"
var placed := {}
var placed_footprints := {}
var preview_mesh: MeshInstance3D
var preview_material: StandardMaterial3D
var preview_cell := Vector2i.ZERO
var preview_valid := false
var build_rotation := 0
var elapsed := 0.0
var drag_orbit := false
var orbit_button := MOUSE_BUTTON_RIGHT
var last_mouse := Vector2.ZERO
var yaw := 0.65
var pitch := 0.82
var camera_distance := 34.0
var camera_target := Vector3.ZERO
var auto_test_enabled := false
var model_smoke_enabled := false
var auto_test_finished := false
var auto_test_success := false
var auto_test_log: Array[String] = []
var shared_materials: Dictionary = {}

func _ready() -> void:
	auto_test_enabled = OS.get_cmdline_user_args().has(AUTO_TEST_ARG)
	model_smoke_enabled = OS.get_cmdline_user_args().has(MODEL_SMOKE_ARG)
	_setup_world()
	_setup_camera()
	_setup_ui()
	_update_hud()
	_show_message("Добро пожаловать! Выбери здание и щёлкни по земле, чтобы построить.")
	if model_smoke_enabled:
		call_deferred("_run_model_smoke_test")
	elif auto_test_enabled:
		call_deferred("_run_auto_test")

func _process(delta: float) -> void:
	_update_build_preview(get_viewport().get_mouse_position())
	elapsed += delta
	if elapsed >= 20.0:
		elapsed -= 20.0
		day += 1
		# Simple economy tick: each house contributes taxes; population consumes food.
		var houses := _count_type("house")
		var farms := _count_type("farm")
		money += houses * 12 - _count_type("market") * 3
		food += farms * 5 - int(ceil(float(population) / 8.0))
		food = max(food, 0)
		_update_hud()
		if food == 0 and population > 0:
			_show_message("Запасы еды закончились! Построй ферму.")

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		# Orbit: right-drag, middle-drag, or Control + left-drag (useful on Mac trackpads).
		if event.button_index == MOUSE_BUTTON_RIGHT or event.button_index == MOUSE_BUTTON_MIDDLE:
			drag_orbit = event.pressed
			orbit_button = event.button_index
			last_mouse = event.position
		elif event.button_index == MOUSE_BUTTON_LEFT and event.pressed and event.ctrl_pressed:
			drag_orbit = true
			orbit_button = MOUSE_BUTTON_LEFT
			last_mouse = event.position
		elif event.button_index == orbit_button and not event.pressed and drag_orbit:
			drag_orbit = false
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			if event.shift_pressed: _rotate_building(1)
			else:
				camera_distance = max(12.0, camera_distance - 2.0)
				_update_camera_transform()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			if event.shift_pressed: _rotate_building(-1)
			else:
				camera_distance = min(60.0, camera_distance + 2.0)
				_update_camera_transform()
		elif event.button_index == MOUSE_BUTTON_LEFT and event.pressed and not event.ctrl_pressed:
			_place_at_mouse(event.position)
	elif event is InputEventMagnifyGesture:
		# Trackpad pinch gesture on macOS: pinch out to zoom in, pinch in to zoom out.
		if event.factor > 0.0:
			camera_distance = clamp(camera_distance / event.factor, 12.0, 60.0)
			_update_camera_transform()
	elif event is InputEventMouseMotion and drag_orbit and _orbit_button_is_held(event.button_mask):
		var mouse_delta: Vector2 = event.position - last_mouse
		yaw -= mouse_delta.x * 0.008
		pitch = clamp(pitch + mouse_delta.y * 0.006, 0.35, 1.25)
		last_mouse = event.position
		_update_camera_transform()
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_1: _select_building("house")
		elif event.keycode == KEY_2: _select_building("farm")
		elif event.keycode == KEY_3: _select_building("market")
		elif event.keycode == KEY_4: _select_building("road")
		elif event.keycode == KEY_5: _select_building("warehouse")
		elif event.keycode == KEY_6: _select_building("workshop")
		elif event.keycode == KEY_7: _select_building("forum")
		elif event.keycode == KEY_8: _select_building("house_large")
		elif event.keycode == KEY_ESCAPE: _select_building("select")
		elif event.keycode == KEY_R: _rotate_building(1)
		elif event.keycode == KEY_W:
			camera_target.z -= 2.0
			_move_camera_target()
		elif event.keycode == KEY_S:
			camera_target.z += 2.0
			_move_camera_target()
		elif event.keycode == KEY_A:
			camera_target.x -= 2.0
			_move_camera_target()
		elif event.keycode == KEY_D:
			camera_target.x += 2.0
			_move_camera_target()

func _move_camera_target() -> void:
	camera_target.x = clamp(camera_target.x, -MAP_HALF_EXTENT, MAP_HALF_EXTENT)
	camera_target.z = clamp(camera_target.z, -MAP_HALF_EXTENT, MAP_HALF_EXTENT)
	_update_camera_transform()

func _orbit_button_is_held(button_mask: int) -> bool:
	if orbit_button == MOUSE_BUTTON_LEFT:
		return (button_mask & MOUSE_BUTTON_MASK_LEFT) != 0
	if orbit_button == MOUSE_BUTTON_MIDDLE:
		return (button_mask & MOUSE_BUTTON_MASK_MIDDLE) != 0
	return (button_mask & MOUSE_BUTTON_MASK_RIGHT) != 0

func _setup_world() -> void:
	var world_env := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.12, 0.20, 0.34)
	sky_material.sky_horizon_color = Color(0.76, 0.61, 0.43)
	sky_material.ground_bottom_color = Color(0.12, 0.16, 0.13)
	sky_material.ground_horizon_color = Color(0.42, 0.38, 0.29)
	sky_material.sun_angle_max = 18.0
	env.sky.sky_material = sky_material
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.72, 0.76, 0.82)
	env.ambient_light_energy = 0.65
	world_env.environment = env
	add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -32, 0)
	sun.light_color = Color(1.0, 0.88, 0.68)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	add_child(sun)

	ground_body = StaticBody3D.new()
	ground_body.name = "Ground"
	var ground_mesh := MeshInstance3D.new()
	ground_mesh.mesh = _build_terrain_mesh()
	var grass: StandardMaterial3D = GRASS_MATERIAL.duplicate()
	grass.albedo_color = Color.WHITE
	grass.vertex_color_use_as_albedo = true
	grass.roughness = 1.0
	grass.cull_mode = BaseMaterial3D.CULL_DISABLED
	ground_mesh.material_override = grass
	ground_body.add_child(ground_mesh)
	var collision := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = Vector3(MAP_CELLS * GRID_SIZE, 0.2, MAP_CELLS * GRID_SIZE)
	collision.shape = box_shape
	collision.position.y = -0.1
	ground_body.add_child(collision)
	add_child(ground_body)

	# A low-poly water ribbon and raised, irregular banks follow a shallow meander.
	_add_river_meshes()
	var bridge := BRIDGE_SCENE.instantiate() as Node3D
	bridge.name = "River crossing"
	bridge.position = Vector3(RIVER_CENTER_X, 0.08, -8.0)
	add_child(bridge)
	# A simple central plaza gives the empty map a clear starting point.
	_add_box("Starting plaza", Vector3(0, 0.025, 0), Vector3(7.8, 0.08, 7.8), Color(0.66, 0.59, 0.43), false)
	_add_scenic_rocks_and_trees()
	_setup_build_preview()
	if auto_test_enabled:
		for node in get_children():
			if node.name == "Starting plaza": node.visible = false

func _terrain_height(x: float, z: float) -> float:
	if abs(x - RIVER_CENTER_X) < 4.0:
		return 0.0
	var edge_fade: float = clampf(maxf(absf(x), absf(z)) / 8.0, 0.0, 1.0)
	return (sin(x * 0.17) * cos(z * 0.14) * 0.34 + sin((x - z) * 0.29) * 0.12 + cos(z * 0.21) * 0.05) * edge_fade

func _build_terrain_mesh() -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cells := 64
	var step := MAP_HALF_EXTENT * 2.0 / float(cells)
	for z_index in range(cells):
		for x_index in range(cells):
			var x0 := -MAP_HALF_EXTENT + float(x_index) * step
			var x1 := x0 + step
			var z0 := -MAP_HALF_EXTENT + float(z_index) * step
			var z1 := z0 + step
			var p00 := Vector3(x0, _terrain_height(x0, z0), z0)
			var p10 := Vector3(x1, _terrain_height(x1, z0), z0)
			var p01 := Vector3(x0, _terrain_height(x0, z1), z1)
			var p11 := Vector3(x1, _terrain_height(x1, z1), z1)
			_add_terrain_triangle(surface, p00, p01, p10)
			_add_terrain_triangle(surface, p10, p01, p11)
	surface.generate_normals()
	return surface.commit()

func _add_terrain_triangle(surface: SurfaceTool, a: Vector3, b: Vector3, c: Vector3) -> void:
	for vertex in [a, b, c]:
		var variation := sin(vertex.x * 0.41 + vertex.z * 0.27) * 0.025 + cos(vertex.z * 0.33 - vertex.x * 0.19) * 0.018
		var tint := Color(0.32 + variation, 0.45 + variation, 0.24 + variation * 0.6, 1.0)
		surface.set_color(tint)
		surface.add_vertex(vertex)

func _add_river_meshes() -> void:
	var water := SurfaceTool.new()
	water.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bank := SurfaceTool.new()
	bank.begin(Mesh.PRIMITIVE_TRIANGLES)
	var segments := 48
	for i in range(segments):
		var z0 := -MAP_HALF_EXTENT + float(i) * (MAP_HALF_EXTENT * 2.0 / float(segments))
		var z1 := -MAP_HALF_EXTENT + float(i + 1) * (MAP_HALF_EXTENT * 2.0 / float(segments))
		var bend0 := RIVER_CENTER_X + sin(z0 * 0.105) * 0.58 + sin(z0 * 0.27) * 0.16
		var bend1 := RIVER_CENTER_X + sin(z1 * 0.105) * 0.58 + sin(z1 * 0.27) * 0.16
		var width0 := 1.85 + 0.28 * sin(z0 * 0.21) + 0.12 * cos(z0 * 0.43)
		var width1 := 1.85 + 0.28 * sin(z1 * 0.21) + 0.12 * cos(z1 * 0.43)
		var l0 := Vector3(bend0 - width0, 0.08 + 0.025 * sin(z0 * 0.6), z0)
		var r0 := Vector3(bend0 + width0, 0.08 + 0.022 * cos(z0 * 0.5), z0)
		var l1 := Vector3(bend1 - width1, 0.08 + 0.025 * sin(z1 * 0.6), z1)
		var r1 := Vector3(bend1 + width1, 0.08 + 0.022 * cos(z1 * 0.5), z1)
		var center0 := Color(0.07 + 0.02 * sin(z0 * 0.17), 0.32 + 0.025 * cos(z0 * 0.15), 0.40 + 0.02 * sin(z0 * 0.12))
		var center1 := Color(0.07 + 0.02 * sin(z1 * 0.17), 0.32 + 0.025 * cos(z1 * 0.15), 0.40 + 0.02 * sin(z1 * 0.12))
		var shore0 := Color(0.14 + 0.02 * cos(z0 * 0.12), 0.46 + 0.02 * sin(z0 * 0.14), 0.49)
		var shore1 := Color(0.14 + 0.02 * cos(z1 * 0.12), 0.46 + 0.02 * sin(z1 * 0.14), 0.49)
		_add_colored_triangle(water, l0, l1, r0, shore0, shore1, center0)
		_add_colored_triangle(water, r0, l1, r1, center0, shore1, center1)
		for side_value in [-1.0, 1.0]:
			var side: float = side_value
			var inner0: float = bend0 + side * width0
			var inner1: float = bend1 + side * width1
			var outer0: float = bend0 + side * (width0 + 0.60 + 0.18 * sin(z0 * 0.38))
			var outer1: float = bend1 + side * (width1 + 0.60 + 0.18 * sin(z1 * 0.38))
			var a := Vector3(inner0, 0.10, z0)
			var b := Vector3(inner1, 0.10, z1)
			var c := Vector3(outer0, 0.12 + 0.05 * sin(z0 * 0.32), z0)
			var d := Vector3(outer1, 0.12 + 0.05 * sin(z1 * 0.32), z1)
			_add_colored_triangle(bank, a, b, c, Color(0.46, 0.40, 0.28), Color(0.44, 0.39, 0.27), Color(0.38, 0.36, 0.25))
			_add_colored_triangle(bank, c, b, d, Color(0.38, 0.36, 0.25), Color(0.44, 0.39, 0.27), Color(0.48, 0.43, 0.30))
	water.generate_normals()
	bank.generate_normals()
	var water_node := MeshInstance3D.new()
	water_node.name = "Meandering river water"
	water_node.mesh = water.commit()
	var water_mat: StandardMaterial3D = RIVER_MATERIAL.duplicate()
	water_mat.vertex_color_use_as_albedo = true
	water_mat.albedo_color = Color.WHITE
	water_mat.roughness = 0.28
	water_mat.metallic = 0.08
	water_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	water_node.material_override = water_mat
	add_child(water_node)
	var bank_node := MeshInstance3D.new()
	bank_node.name = "Natural river banks"
	bank_node.mesh = bank.commit()
	var bank_mat := StandardMaterial3D.new()
	bank_mat.vertex_color_use_as_albedo = true
	bank_mat.roughness = 1.0
	bank_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	bank_node.material_override = bank_mat
	add_child(bank_node)
	# Reeds and rounded boulders break up the waterline without cluttering the build area.
	for i in range(24):
		var z := -27.0 + float(i) * 2.3
		var center := RIVER_CENTER_X + sin(z * 0.105) * 0.58
		var side := -1.0 if i % 2 == 0 else 1.0
		var x := center + side * (2.1 + 0.12 * sin(z * 0.21))
		if i % 3 == 0:
			_add_scenic_shrub(Vector2(x, z), 0.55)
		else:
			_add_box("River reed", Vector3(x, 0.34, z), Vector3(0.055, 0.52, 0.055), Color(0.58, 0.58, 0.28), false)

func _add_riverbank_props() -> void:
	for i in range(14):
		var z := -24.0 + float(i) * 3.6
		var center := RIVER_CENTER_X + sin(z * 0.105) * 0.58 + sin(z * 0.27) * 0.16
		var side := -1.0 if i % 2 == 0 else 1.0
		var shoreline: Node3D = RIVERBANK_SCENE.instantiate()
		shoreline.name = "Grassy river margin"
		shoreline.position = Vector3(center + side * 2.55, 0.0, z)
		shoreline.rotation.y = float(i % 4) * 0.22
		shoreline.scale = Vector3(0.95, 0.8, 1.1)
		add_child(shoreline)

func _add_colored_triangle(surface: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, ca: Color, cb: Color, cc: Color) -> void:
	for entry in [[a, ca], [b, cb], [c, cc]]:
		surface.set_color(entry[1])
		surface.add_vertex(entry[0])

func _setup_camera() -> void:
	camera_pivot = Node3D.new()
	camera_pivot.position = camera_target
	add_child(camera_pivot)
	camera = Camera3D.new()
	camera.current = true
	camera_pivot.add_child(camera)
	_update_camera_transform()

func _update_camera_transform() -> void:
	if not is_instance_valid(camera): return
	camera_pivot.position = camera_target
	var horizontal := camera_distance * cos(pitch)
	camera.position = Vector3(sin(yaw) * horizontal, camera_distance * sin(pitch), cos(yaw) * horizontal)
	camera.look_at(camera_target, Vector3.UP)

func _setup_ui() -> void:
	ui_layer = CanvasLayer.new()
	add_child(ui_layer)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_PASS
	ui_layer.add_child(root)

	var top := PanelContainer.new()
	top.position = Vector2(16, 14)
	top.custom_minimum_size = Vector2(410, 92)
	root.add_child(top)
	var top_col := VBoxContainer.new()
	top.add_child(top_col)
	var title := Label.new()
	title.text = "IMPERIUM: NEW ERA  |  ПРОТОТИП"
	title.add_theme_font_size_override("font_size", 18)
	top_col.add_child(title)
	hud_label = Label.new()
	top_col.add_child(hud_label)

	var panel := PanelContainer.new()
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -230
	panel.offset_right = -16
	panel.offset_top = 14
	panel.offset_bottom = 430
	root.add_child(panel)
	var controls := VBoxContainer.new()
	controls.add_theme_constant_override("separation", 8)
	panel.add_child(controls)
	var heading := Label.new()
	heading.text = "СТРОИТЕЛЬСТВО"
	heading.add_theme_font_size_override("font_size", 17)
	controls.add_child(heading)
	_add_build_button(controls, "Дом — 100", "house", "1")
	_add_build_button(controls, "Ферма — 160", "farm", "2")
	_add_build_button(controls, "Рынок — 220", "market", "3")
	_add_build_button(controls, "Дорога — 10", "road", "4")
	_add_build_button(controls, "Склад — 180", "warehouse", "5")
	_add_build_button(controls, "Мастерская — 200", "workshop", "6")
	_add_build_button(controls, "Форум — 300", "forum", "7")
	_add_build_button(controls, "Большой дом — 150", "house_large", "8")
	_add_build_button(controls, "Выбор / отмена", "select", "Esc")
	selected_label = Label.new()
	selected_label.text = "Выбрано: дом"
	selected_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	controls.add_child(selected_label)

	var bottom := PanelContainer.new()
	bottom.anchor_top = 1.0
	bottom.anchor_bottom = 1.0
	bottom.offset_left = 16
	bottom.offset_top = -82
	bottom.offset_right = 650
	bottom.offset_bottom = -16
	root.add_child(bottom)
	var bottom_col := VBoxContainer.new()
	bottom.add_child(bottom_col)
	message_label = Label.new()
	message_label.text = "Готово к строительству."
	message_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bottom_col.add_child(message_label)
	var help := Label.new()
	help.text = "ЛКМ — построить  |  R — повернуть постройку  |  Колесо / щипок — масштаб  |  ПКМ/средняя кнопка + движение или Ctrl + ЛКМ — вращение  |  WASD — сдвиг камеры"
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bottom_col.add_child(help)

func _add_build_button(parent: VBoxContainer, text_value: String, kind: String, shortcut: String) -> void:
	var button := Button.new()
	button.text = text_value + "  [" + shortcut + "]"
	button.custom_minimum_size.y = 34
	button.pressed.connect(_select_building.bind(kind))
	parent.add_child(button)

func _select_building(kind: String) -> void:
	selected_building = kind
	build_rotation = 0
	var names := {"house":"дом", "house_large":"большой дом", "farm":"ферма", "market":"рынок", "road":"дорога", "warehouse":"склад", "workshop":"мастерская", "forum":"форум", "select":"ничего"}
	if is_instance_valid(selected_label): selected_label.text = "Выбрано: " + names.get(kind, kind)
	if kind == "select": _show_message("Строительство отменено.")
	else: _show_message("Выбрано: " + names.get(kind, kind) + ". Щёлкни по свободной клетке.")
	_update_preview_visibility()

func _rotate_building(direction: int) -> void:
	if selected_building == "select": return
	build_rotation = posmod(build_rotation + direction, 4)
	_show_message("Поворот постройки: %d° (R — повернуть)." % (build_rotation * 90))
	_update_build_preview(get_viewport().get_mouse_position())

func _setup_build_preview() -> void:
	preview_mesh = MeshInstance3D.new()
	preview_mesh.name = "BuildPreview"
	var mesh := BoxMesh.new()
	mesh.size = Vector3(GRID_SIZE, 0.035, GRID_SIZE)
	preview_mesh.mesh = mesh
	preview_material = StandardMaterial3D.new()
	preview_material.albedo_color = Color(0.2, 0.9, 0.3, 0.42)
	preview_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	preview_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	preview_material.no_depth_test = true
	preview_mesh.material_override = preview_material
	preview_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(preview_mesh)
	_update_preview_visibility()

func _update_preview_visibility() -> void:
	if is_instance_valid(preview_mesh):
		preview_mesh.visible = selected_building != "select"

func _update_build_preview(screen_pos: Vector2) -> void:
	if not is_instance_valid(preview_mesh) or selected_building == "select": return
	var cell := _cell_at_screen(screen_pos)
	if not cell.get("valid_hit", false):
		preview_mesh.visible = false
		return
	preview_cell = cell.get("cell", Vector2i.ZERO)
	preview_valid = _can_place_at(preview_cell.x, preview_cell.y, selected_building)
	var center := Vector3(float(preview_cell.x) * GRID_SIZE, 0.035, float(preview_cell.y) * GRID_SIZE)
	preview_mesh.position = center
	preview_mesh.rotation.y = float(build_rotation) * PI * 0.5
	preview_mesh.visible = true
	preview_material.albedo_color = Color(0.2, 0.9, 0.3, 0.42) if preview_valid else Color(0.95, 0.16, 0.12, 0.5)

func _cell_at_screen(screen_pos: Vector2) -> Dictionary:
	var origin := camera.project_ray_origin(screen_pos)
	var direction := camera.project_ray_normal(screen_pos)
	var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 500.0)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or hit.collider != ground_body:
		return {"valid_hit": false}
	var world_pos: Vector3 = hit.position
	return {"valid_hit": true, "cell": Vector2i(roundi(world_pos.x / GRID_SIZE), roundi(world_pos.z / GRID_SIZE))}

func _building_footprint(kind: String, rotation: int) -> Vector2:
	var footprint := Vector2(GRID_SIZE, GRID_SIZE)
	match kind:
		"house": footprint = Vector2(1.55, 1.45)
		"house_large": footprint = Vector2(1.9, 1.75)
		"farm": footprint = Vector2(1.75, 1.75)
		"market": footprint = Vector2(1.75, 1.55)
		"road": footprint = Vector2(GRID_SIZE, GRID_SIZE)
		"warehouse": footprint = Vector2(1.85, 1.85)
		"workshop": footprint = Vector2(1.85, 1.85)
		"forum": footprint = Vector2(1.85, 1.85)
	if rotation % 2 == 1:
		footprint = Vector2(footprint.y, footprint.x)
	return footprint

func _can_place_at(gx: int, gz: int, kind: String) -> bool:
	var center_x := float(gx) * GRID_SIZE
	var center_z := float(gz) * GRID_SIZE
	var footprint := _building_footprint(kind, build_rotation)
	var half_x := footprint.x * 0.5
	var half_z := footprint.y * 0.5
	if abs(center_x) + half_x > MAP_HALF_EXTENT or abs(center_z) + half_z > MAP_HALF_EXTENT:
		return false
	if abs(center_x - RIVER_CENTER_X) < RIVER_HALF_WIDTH + half_x:
		return false
	if abs(center_x) < PLAZA_HALF_EXTENT + half_x and abs(center_z) < PLAZA_HALF_EXTENT + half_z:
		return false
	for key in placed_footprints:
		var existing: Dictionary = placed_footprints[key]
		if abs(center_x - float(existing.center_x)) < half_x + float(existing.half_x) and abs(center_z - float(existing.center_z)) < half_z + float(existing.half_z):
			return false
	return true

func _place_at_mouse(screen_pos: Vector2) -> void:
	if selected_building == "select": return
	var cell := _cell_at_screen(screen_pos)
	if not cell.get("valid_hit", false): return
	var coords: Vector2i = cell.cell
	var gx := coords.x
	var gz := coords.y
	if not _can_place_at(gx, gz, selected_building):
		_show_message(_placement_error(gx, gz, selected_building))
		return
	_try_place_building(gx, gz, selected_building, true)

func _try_place_building(gx: int, gz: int, kind: String, charge_cost: bool) -> bool:
	if not _can_place_at(gx, gz, kind): return false
	var key := str(gx) + "," + str(gz)
	var cost := _cost_for(kind)
	if charge_cost and money < cost:
		_show_message("Недостаточно денег. Нужно: " + str(cost) + ".")
		return false
	if charge_cost: money -= cost
	var position := Vector3(float(gx) * GRID_SIZE, 0.0, float(gz) * GRID_SIZE)
	_create_building(kind, position)
	placed[key] = kind
	var footprint := _building_footprint(kind, build_rotation)
	placed_footprints[key] = {"center_x": position.x, "center_z": position.z, "half_x": footprint.x * 0.5, "half_z": footprint.y * 0.5}
	if kind == "house": population += 5
	elif kind == "house_large": population += 8
	_update_hud()
	if charge_cost: _show_message("Построено: " + kind + ". Стоимость: " + str(cost) + ".")
	return true

func _placement_error(gx: int, gz: int, kind: String) -> String:
	var center_x := float(gx) * GRID_SIZE
	var center_z := float(gz) * GRID_SIZE
	var footprint := _building_footprint(kind, build_rotation)
	var half_x := footprint.x * 0.5
	var half_z := footprint.y * 0.5
	if abs(center_x) + half_x > MAP_HALF_EXTENT or abs(center_z) + half_z > MAP_HALF_EXTENT:
		return "Здесь нельзя строить: постройка выйдет за границу карты."
	if abs(center_x - RIVER_CENTER_X) < RIVER_HALF_WIDTH + half_x:
		return "Здесь нельзя строить: место пересекает реку."
	if abs(center_x) < PLAZA_HALF_EXTENT + half_x and abs(center_z) < PLAZA_HALF_EXTENT + half_z:
		return "Здесь нельзя строить: место занимает центральная площадь."
	return "Место занято другой постройкой."

func _cost_for(kind: String) -> int:
	return {"house":100, "house_large":150, "farm":160, "market":220, "road":10, "warehouse":180, "workshop":200, "forum":300}.get(kind, 0)

func _create_building(kind: String, pos: Vector3) -> void:
	if not BUILDING_SCENES.has(kind):
		push_error("Unknown building scene: " + kind)
		return
	var asset: Node3D = (BUILDING_SCENES[kind] as PackedScene).instantiate()
	asset.name = kind.capitalize()
	asset.position = Vector3(pos.x, _terrain_height(pos.x, pos.z), pos.z)
	asset.rotation.y = float(build_rotation) * PI * 0.5
	if kind == "house" or kind == "house_large":
		asset.set("variant", posmod(roundi(pos.x / GRID_SIZE) + roundi(pos.z / GRID_SIZE), 3))
	elif kind == "road":
		asset.set("variant", posmod(roundi(pos.x / GRID_SIZE) + roundi(pos.z / GRID_SIZE), 3))
	add_child(asset)

func _build_house_model(root: Node3D, pos: Vector3) -> void:
	var variant := posmod(roundi(pos.x / GRID_SIZE) + roundi(pos.z / GRID_SIZE), 3)
	var width: float = [1.24, 1.38, 1.30][variant]
	var depth: float = [1.18, 1.30, 1.22][variant]
	var wall_height: float = [0.96, 1.08, 1.0][variant]
	var wall_color: Color = [Color(0.72, 0.60, 0.42), Color(0.76, 0.69, 0.54), Color(0.66, 0.49, 0.34)][variant]
	var roof_color: Color = [Color(0.55, 0.19, 0.12), Color(0.43, 0.18, 0.13), Color(0.58, 0.25, 0.14)][variant]
	_add_box_to(root, "Stone foundation", Vector3(0, 0.12, 0), Vector3(width + 0.14, 0.24, depth + 0.14), Color(0.39, 0.37, 0.31))
	_add_box_to(root, "Front plaster wall", Vector3(0, 0.24 + wall_height * 0.5, depth * 0.5), Vector3(width, wall_height, 0.10), wall_color)
	_add_box_to(root, "Rear plaster wall", Vector3(0, 0.24 + wall_height * 0.5, -depth * 0.5), Vector3(width, wall_height, 0.10), wall_color.darkened(0.08))
	_add_box_to(root, "Left plaster wall", Vector3(-width * 0.5, 0.24 + wall_height * 0.5, 0), Vector3(0.10, wall_height, depth - 0.14), wall_color.darkened(0.04))
	_add_box_to(root, "Right plaster wall", Vector3(width * 0.5, 0.24 + wall_height * 0.5, 0), Vector3(0.10, wall_height, depth - 0.14), wall_color)
	# Visible half-timbering, stone sill, and a true gabled end silhouette.
	for x in [-width * 0.48, width * 0.48]:
		_add_box_to(root, "Oak corner post", Vector3(x, 0.24 + wall_height * 0.5, depth * 0.5 + 0.06), Vector3(0.10, wall_height + 0.06, 0.09), Color(0.29, 0.17, 0.09))
	_add_box_to(root, "Front crossbeam", Vector3(0, 0.66, depth * 0.5 + 0.065), Vector3(width, 0.075, 0.07), Color(0.34, 0.20, 0.11))
	_add_box_to(root, "Front gable beam", Vector3(0, 0.24 + wall_height + 0.16, depth * 0.5 + 0.065), Vector3(width, 0.07, 0.07), Color(0.34, 0.20, 0.11))
	_add_triangle_to(root, "Plaster gable", [Vector3(-width * 0.5, 0.24 + wall_height, depth * 0.5 + 0.035), Vector3(width * 0.5, 0.24 + wall_height, depth * 0.5 + 0.035), Vector3(0, 1.72, depth * 0.5 + 0.035)], wall_color)
	_add_box_to(root, "Entrance door", Vector3(0, 0.49, depth * 0.5 + 0.10), Vector3(0.31, 0.64, 0.055), Color(0.27, 0.15, 0.08))
	_add_box_to(root, "Door lintel", Vector3(0, 0.84, depth * 0.5 + 0.14), Vector3(0.43, 0.09, 0.09), Color(0.34, 0.21, 0.12))
	_add_sphere_to(root, "Bronze door latch", Vector3(0.095, 0.50, depth * 0.5 + 0.14), Vector3(0.035, 0.035, 0.025), Color(0.77, 0.57, 0.22))
	var window_count := 2 if variant != 2 else 1
	for i in range(window_count):
		var wx := -0.40 + float(i) * 0.80 if window_count == 2 else 0.38
		_add_box_to(root, "Deep window recess", Vector3(wx, 0.77, depth * 0.5 + 0.09), Vector3(0.31, 0.34, 0.045), Color(0.12, 0.23, 0.26))
		_add_box_to(root, "Window frame left", Vector3(wx - 0.18, 0.77, depth * 0.5 + 0.13), Vector3(0.045, 0.40, 0.055), Color(0.36, 0.22, 0.11))
		_add_box_to(root, "Window frame right", Vector3(wx + 0.18, 0.77, depth * 0.5 + 0.13), Vector3(0.045, 0.40, 0.055), Color(0.36, 0.22, 0.11))
		_add_box_to(root, "Window mullion", Vector3(wx, 0.77, depth * 0.5 + 0.14), Vector3(0.035, 0.32, 0.06), Color(0.42, 0.27, 0.14))
		_add_box_to(root, "Carved stone sill", Vector3(wx, 0.55, depth * 0.5 + 0.15), Vector3(0.42, 0.07, 0.12), Color(0.74, 0.66, 0.50))
	# Pitched panels are parallelogram meshes with a raised ridge and overhanging eaves.
	_add_roof_panel(root, "Left terracotta roof", Vector3(-0.34, 1.49, 0), Vector3(0.87, 0.12, depth + 0.24), -0.58, roof_color)
	_add_roof_panel(root, "Right terracotta roof", Vector3(0.34, 1.49, 0), Vector3(0.87, 0.12, depth + 0.24), 0.58, roof_color.lightened(0.09))
	_add_box_to(root, "Ridge cap", Vector3(0, 1.77, 0), Vector3(0.14, 0.13, depth + 0.3), Color(0.36, 0.15, 0.10))
	_add_box_to(root, "Front eave fascia", Vector3(0, 1.20, depth * 0.5 + 0.14), Vector3(width + 0.38, 0.09, 0.10), Color(0.34, 0.19, 0.11))
	if variant == 1:
		_add_box_to(root, "Rear chimney stack", Vector3(width * 0.30, 1.77, -depth * 0.30), Vector3(0.22, 0.52, 0.24), Color(0.48, 0.31, 0.22))
		_add_box_to(root, "Chimney cap", Vector3(width * 0.30, 2.04, -depth * 0.30), Vector3(0.30, 0.08, 0.31), Color(0.37, 0.25, 0.19))
	elif variant == 2:
		_add_box_to(root, "Timber side awning", Vector3(width * 0.5 + 0.20, 0.82, -0.1), Vector3(0.46, 0.09, 0.82), roof_color)
		_add_box_to(root, "Awning brace", Vector3(width * 0.5 + 0.24, 0.56, 0.13), Vector3(0.06, 0.50, 0.06), Color(0.30, 0.18, 0.10))

func _add_roof_panel(parent: Node3D, label: String, center: Vector3, size: Vector3, angle: float, color: Color) -> void:
	var panel := _add_box_to(parent, label, center, size, color)
	panel.rotation.z = angle
	# Narrow ribs read as handmade terracotta courses while staying low-poly.
	for i in range(5):
		var z := center.z - size.z * 0.42 + float(i) * size.z * 0.21
		var rib := _add_box_to(parent, "Raised roof course", center + Vector3(0, 0.065, z - center.z), Vector3(size.x * 0.92, 0.035, 0.035), color.lightened(0.15))
		rib.rotation.z = angle

func _build_farm_model(root: Node3D) -> void:
	_add_box_to(root, "Dark furrow soil", Vector3(0, 0.08, 0), Vector3(1.76, 0.14, 1.76), Color(0.34, 0.22, 0.13))
	for i in range(5):
		var x := -0.68 + float(i) * 0.34
		_add_box_to(root, "Raised crop bed", Vector3(x, 0.17, 0), Vector3(0.20, 0.09, 1.48), Color(0.47, 0.33, 0.17))
		for j in range(4):
			var z := -0.53 + float(j) * 0.35
			_add_sphere_to(root, "Leafy crop tuft", Vector3(x, 0.29, z), Vector3(0.15, 0.20, 0.14), Color(0.43 + 0.04 * float(j % 2), 0.55, 0.22))
	for x in [-0.87, 0.87]:
		for z in [-0.75, 0.75]: _add_box_to(root, "Field fence post", Vector3(x, 0.34, z), Vector3(0.08, 0.58, 0.08), Color(0.30, 0.19, 0.10))
	_add_box_to(root, "Farm hut walls", Vector3(0.46, 0.47, -0.43), Vector3(0.50, 0.72, 0.55), Color(0.70, 0.56, 0.37))
	_add_box_to(root, "Hut door", Vector3(0.46, 0.34, -0.142), Vector3(0.17, 0.43, 0.035), Color(0.30, 0.18, 0.10))
	_add_roof_panel(root, "Hut roof left", Vector3(0.30, 0.93, -0.43), Vector3(0.38, 0.10, 0.72), -0.62, Color(0.49, 0.22, 0.14))
	_add_roof_panel(root, "Hut roof right", Vector3(0.62, 0.93, -0.43), Vector3(0.38, 0.10, 0.72), 0.62, Color(0.55, 0.26, 0.16))

func _build_market_model(root: Node3D) -> void:
	for x in [-0.68, 0.68]:
		for z in [-0.58, 0.58]:
			_add_box_to(root, "Market oak post", Vector3(x, 0.66, z), Vector3(0.10, 1.22, 0.10), Color(0.30, 0.18, 0.10))
	_add_box_to(root, "Market back beam", Vector3(0, 1.15, -0.58), Vector3(1.48, 0.11, 0.10), Color(0.34, 0.20, 0.11))
	_add_box_to(root, "Market counter", Vector3(0, 0.37, 0.28), Vector3(1.46, 0.32, 0.52), Color(0.61, 0.48, 0.32))
	_add_box_to(root, "Counter stone top", Vector3(0, 0.56, 0.28), Vector3(1.56, 0.08, 0.60), Color(0.76, 0.66, 0.49))
	# Striped awning fabric is built as alternating sloped panels with a scalloped front edge.
	for i in range(5):
		var stripe_color := Color(0.80, 0.68, 0.49) if i % 2 == 0 else Color(0.62, 0.18, 0.13)
		_add_roof_panel(root, "Striped market awning", Vector3(-0.60 + float(i) * 0.30, 1.34, -0.02), Vector3(0.30, 0.06, 1.42), -0.06, stripe_color)
		_add_box_to(root, "Awning scallop", Vector3(-0.60 + float(i) * 0.30, 1.27, 0.72), Vector3(0.24, 0.13, 0.09), stripe_color)
	for i in range(5):
		_add_sphere_to(root, "Market produce", Vector3(-0.54 + float(i) * 0.27, 0.69, 0.28), Vector3(0.14, 0.13, 0.14), [Color(0.75, 0.29, 0.11), Color(0.82, 0.65, 0.16), Color(0.46, 0.61, 0.22)][i % 3])

func _build_warehouse_model(root: Node3D) -> void:
	_add_box_to(root, "Warehouse stone footings", Vector3(0, 0.14, 0), Vector3(1.78, 0.28, 1.78), Color(0.40, 0.38, 0.32))
	_add_box_to(root, "Warehouse plaster back", Vector3(0, 0.83, -0.78), Vector3(1.62, 1.12, 0.12), Color(0.68, 0.58, 0.42))
	_add_box_to(root, "Warehouse plaster left", Vector3(-0.78, 0.83, 0), Vector3(0.12, 1.12, 1.5), Color(0.70, 0.61, 0.45))
	_add_box_to(root, "Warehouse plaster right", Vector3(0.78, 0.83, 0), Vector3(0.12, 1.12, 1.5), Color(0.65, 0.54, 0.38))
	for x in [-0.70, -0.27, 0.27, 0.70]: _add_box_to(root, "Warehouse timber frame", Vector3(x, 0.82, 0.80), Vector3(0.10, 1.15, 0.10), Color(0.30, 0.18, 0.10))
	_add_box_to(root, "Warehouse double doors", Vector3(0, 0.61, 0.82), Vector3(0.70, 0.82, 0.06), Color(0.34, 0.21, 0.12))
	for x in [-0.17, 0.17]: _add_box_to(root, "Door brace", Vector3(x, 0.60, 0.86), Vector3(0.035, 0.70, 0.035), Color(0.55, 0.37, 0.20))
	_add_roof_panel(root, "Warehouse long roof A", Vector3(-0.42, 1.62, 0), Vector3(1.10, 0.16, 1.95), -0.62, Color(0.43, 0.18, 0.12))
	_add_roof_panel(root, "Warehouse long roof B", Vector3(0.42, 1.62, 0), Vector3(1.10, 0.16, 1.95), 0.62, Color(0.52, 0.23, 0.14))
	_add_box_to(root, "Warehouse ridge", Vector3(0, 1.99, 0), Vector3(0.18, 0.16, 2.0), Color(0.33, 0.17, 0.10))
	for x in [-0.53, 0.53]: _add_box_to(root, "Storage crate", Vector3(x, 0.40, 0.48), Vector3(0.32, 0.32, 0.28), Color(0.53, 0.35, 0.18))

func _build_workshop_model(root: Node3D) -> void:
	_build_house_model(root, Vector3(0, 0, 0))
	_add_box_to(root, "Workshop lean-to walls", Vector3(0.70, 0.40, -0.34), Vector3(0.52, 0.65, 0.76), Color(0.55, 0.43, 0.30))
	_add_roof_panel(root, "Workshop shed roof", Vector3(0.70, 0.83, -0.34), Vector3(0.68, 0.11, 0.94), -0.18, Color(0.39, 0.18, 0.12))
	_add_box_to(root, "Workshop chimney", Vector3(-0.40, 1.91, -0.37), Vector3(0.23, 0.64, 0.24), Color(0.48, 0.30, 0.21))
	_add_box_to(root, "Chimney stone cap", Vector3(-0.40, 2.25, -0.37), Vector3(0.31, 0.09, 0.31), Color(0.35, 0.26, 0.20))
	_add_box_to(root, "Workshop timber sign", Vector3(0.0, 1.02, 0.76), Vector3(0.40, 0.18, 0.07), Color(0.62, 0.41, 0.20))

func _build_forum_model(root: Node3D) -> void:
	_add_box_to(root, "Forum broad steps", Vector3(0, 0.11, 0.10), Vector3(1.78, 0.22, 1.72), Color(0.58, 0.53, 0.43))
	_add_box_to(root, "Forum upper step", Vector3(0, 0.28, 0.05), Vector3(1.50, 0.18, 1.42), Color(0.72, 0.64, 0.49))
	_add_box_to(root, "Forum cella", Vector3(0, 0.83, -0.25), Vector3(1.30, 0.92, 0.90), Color(0.76, 0.67, 0.52))
	for x in [-0.58, -0.20, 0.20, 0.58]:
		var column := CylinderMesh.new()
		column.top_radius = 0.09
		column.bottom_radius = 0.12
		column.height = 1.14
		column.radial_segments = 8
		var col_node := MeshInstance3D.new()
		col_node.name = "Forum marble column"
		col_node.mesh = column
		col_node.material_override = _material(Color(0.88, 0.79, 0.61))
		col_node.position = Vector3(x, 0.91, 0.48)
		root.add_child(col_node)
		_add_box_to(root, "Column capital", Vector3(x, 1.51, 0.48), Vector3(0.21, 0.10, 0.21), Color(0.85, 0.76, 0.59))
	_add_box_to(root, "Forum entablature", Vector3(0, 1.62, 0.48), Vector3(1.50, 0.20, 0.22), Color(0.81, 0.71, 0.54))
	_add_triangle_to(root, "Forum pediment", [Vector3(-0.76, 1.72, 0.50), Vector3(0.76, 1.72, 0.50), Vector3(0, 2.25, 0.50)], Color(0.79, 0.67, 0.49))
	_add_roof_panel(root, "Forum roof left", Vector3(-0.42, 1.90, -0.20), Vector3(1.00, 0.12, 1.50), -0.48, Color(0.47, 0.23, 0.15))
	_add_roof_panel(root, "Forum roof right", Vector3(0.42, 1.90, -0.20), Vector3(1.00, 0.12, 1.50), 0.48, Color(0.53, 0.27, 0.17))

func _material(color: Color) -> StandardMaterial3D:
	var key := color.to_html(true)
	if shared_materials.has(key): return shared_materials[key]
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.92
	shared_materials[key] = material
	return material

func _add_triangle_to(parent: Node3D, label: String, points: Array[Vector3], color: Color) -> void:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for point in points: surface.add_vertex(point)
	for point in [points[2], points[1], points[0]]: surface.add_vertex(point + Vector3(0, 0.008, 0))
	surface.generate_normals()
	var mesh_node := MeshInstance3D.new()
	mesh_node.name = label
	mesh_node.mesh = surface.commit()
	mesh_node.material_override = _material(color)
	parent.add_child(mesh_node)

func _add_sphere_to(parent: Node3D, label: String, pos: Vector3, scale_value: Vector3, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = label
	var mesh := SphereMesh.new()
	mesh.radius = 0.5
	mesh.height = 1.0
	mesh.radial_segments = 8
	mesh.rings = 5
	node.mesh = mesh
	node.scale = scale_value
	node.position = pos
	node.material_override = _material(color)
	parent.add_child(node)
	return node

func _add_box_to(parent: Node3D, object_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = object_name
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.92
	node.material_override = material
	node.position = pos
	parent.add_child(node)
	return node

func _add_box(object_name: String, pos: Vector3, size: Vector3, color: Color, with_collision: bool) -> void:
	var node := MeshInstance3D.new()
	node.name = object_name
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.92
	node.material_override = material
	node.position = pos
	add_child(node)
	if with_collision:
		var body := StaticBody3D.new()
		var shape_node := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		shape_node.shape = shape
		body.position = pos
		body.add_child(shape_node)
		add_child(body)

func _add_box_material(object_name: String, pos: Vector3, size: Vector3, material: Material) -> void:
	var node := MeshInstance3D.new()
	node.name = object_name
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.material_override = material
	node.position = pos
	add_child(node)

func _add_scenic_rocks_and_trees() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7319
	for i in range(52):
		var side := i % 4
		var along := rng.randf_range(-27.0, 27.0)
		var edge := rng.randf_range(29.45, 29.85)
		var rock_pos := Vector2(edge, along)
		if side == 1: rock_pos.x = -edge
		elif side == 2: rock_pos = Vector2(along, edge)
		elif side == 3: rock_pos = Vector2(along, -edge)
		var rock_size := rng.randf_range(0.25, 0.55)
		_add_rock_cluster(rock_pos, rock_size)
	for tree_pos in [Vector2(-29, -24), Vector2(-29, -16), Vector2(-29, -7), Vector2(-29, 3), Vector2(-29, 12), Vector2(-29, 22), Vector2(29, -24), Vector2(29, -15), Vector2(29, -5), Vector2(29, 5), Vector2(29, 15), Vector2(29, 24), Vector2(-22, -29), Vector2(-10, -29), Vector2(4, -29), Vector2(18, -29), Vector2(-17, 29), Vector2(-3, 29), Vector2(11, 29), Vector2(24, 29)]:
		_add_low_poly_tree(tree_pos, rng.randi_range(0, 3))
	for i in range(46):
		var x := rng.randf_range(-28.0, 28.0)
		var z := rng.randf_range(-28.0, 28.0)
		if abs(x - RIVER_CENTER_X) < 4.5 or (abs(x) < 6.0 and abs(z) < 6.0): continue
		if abs(x) < 21.0 and abs(z) < 21.0: continue
		_add_scenic_shrub(Vector2(x, z), rng.randf_range(0.35, 0.70))
	for i in range(22):
		var x := rng.randf_range(-10.0, 23.0)
		var z := rng.randf_range(-23.0, 23.0)
		if abs(x) < 11.0 and abs(z) < 11.0: continue
		if abs(x - RIVER_CENTER_X) < 5.0: continue
		if x < -9.0 and abs(z) < 9.0: continue
		if i % 3 == 0:
			_add_low_poly_tree(Vector2(x, z), rng.randi_range(0, 2))
		else:
			_add_scenic_shrub(Vector2(x, z), rng.randf_range(0.45, 0.8))

func _add_low_poly_tree(tree_pos: Vector2, variant: int = 0) -> void:
	var ground_y := _terrain_height(tree_pos.x, tree_pos.y)
	var tree_scene: PackedScene = TREE_SCENES[posmod(variant, TREE_SCENES.size())]
	var tree: Node3D = tree_scene.instantiate()
	tree.name = "Scenic tree"
	tree.position = Vector3(tree_pos.x, ground_y, tree_pos.y)
	tree.set("variant", variant)
	add_child(tree)

func _add_rock_cluster(position: Vector2, size: float) -> void:
	var y := _terrain_height(position.x, position.y)
	var rocks: Node3D = ROCK_SCENE.instantiate()
	rocks.name = "Scenic rock cluster"
	rocks.position = Vector3(position.x, y, position.y)
	rocks.scale = Vector3.ONE * maxf(size, 0.45)
	add_child(rocks)

func _add_scenic_shrub(position: Vector2, size: float) -> void:
	var y := _terrain_height(position.x, position.y)
	_add_sphere_world("Wild shrub", Vector3(position.x, y + size * 0.28, position.y), Vector3(size, size * 0.62, size * 0.76), Color(0.25, 0.37, 0.18))
	_add_sphere_world("Shrub leaves", Vector3(position.x + size * 0.22, y + size * 0.36, position.y - size * 0.16), Vector3(size * 0.68, size * 0.58, size * 0.65), Color(0.31, 0.42, 0.20))

func _add_sphere_world(label: String, pos: Vector3, scale_value: Vector3, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = label
	var mesh := SphereMesh.new()
	mesh.radius = 0.5
	mesh.height = 1.0
	mesh.radial_segments = 8
	mesh.rings = 5
	node.mesh = mesh
	node.scale = scale_value
	node.position = pos
	node.material_override = _material(color)
	add_child(node)
	return node

func _add_cylinder_world(label: String, pos: Vector3, top: float, bottom: float, height: float, color: Color, rotation: Vector3) -> void:
	var node := MeshInstance3D.new()
	node.name = label
	var mesh := CylinderMesh.new()
	mesh.top_radius = top
	mesh.bottom_radius = bottom
	mesh.height = height
	mesh.radial_segments = 6
	node.mesh = mesh
	node.position = pos
	node.rotation = rotation
	node.material_override = _material(color)
	add_child(node)

func _run_auto_test() -> void:
	placed.clear()
	placed_footprints.clear()
	money = 1200
	population = 0
	food = 30
	day = 1
	elapsed = 0.0
	auto_test_finished = false
	auto_test_success = true
	auto_test_log.clear()
	_record_auto_test("Начало: пустой город, казна 1200, еда 30.")
	build_rotation = 0
	_update_hud()
	if DisplayServer.get_name() != "headless":
		selected_building = "select"
		_update_preview_visibility()
		camera_target = Vector3(-18.0, 0.0, -3.0)
		camera_distance = 22.0
		_update_camera_transform()
		_show_message("Автотест: готовлю пустую карту и планирую город…")
		await _auto_test_pause()
	var road_plan: Array[Vector2i] = []
	for gx in range(-12, 13):
		var candidate := Vector2i(gx, -1)
		if _can_place_at(candidate.x, candidate.y, "road"):
			road_plan.append(candidate)
			if road_plan.size() == 5: break
		else:
			road_plan.clear()
	if road_plan.size() < 5:
		_auto_test_fail("Не удалось найти место для связанной дороги из пяти клеток.")
		return
	var actions: Array[Dictionary] = []
	for cell in road_plan:
		actions.append({"cell": cell, "kind": "road"})
	var building_kinds: Array[String] = ["house", "house", "farm", "market"]
	for i in range(building_kinds.size()):
		var kind := building_kinds[i]
		var road_cell := road_plan[i]
		var candidates := [Vector2i(road_cell.x, road_cell.y - 1), Vector2i(road_cell.x, road_cell.y + 1)]
		var found_site := false
		for cell in candidates:
			if _can_place_at(cell.x, cell.y, kind):
				actions.append({"cell": cell, "kind": kind})
				found_site = true
				break
		if not found_site:
			_auto_test_fail("Планировщик не нашёл место для %s рядом с дорогой." % kind)
	if actions.size() != 9:
		_auto_test_fail("План содержит %d действий вместо 9." % actions.size())
	for action in actions:
		var cell: Vector2i = action.cell
		var kind: String = action.kind
		if not _can_place_at(cell.x, cell.y, kind):
			_auto_test_fail("Проверка занятости отказала для запланированного %s в %s." % [kind, cell])
			continue
		if not _try_place_building(cell.x, cell.y, kind, true):
			_auto_test_fail("Общая функция строительства не смогла поставить %s в %s." % [kind, cell])
			continue
		var progress := placed.size()
		var progress_line := "ПОСТРОЕНО %d/9: %s в клетке %s." % [progress, kind, cell]
		_record_auto_test(progress_line)
		_show_message("Автотест %d/9 — %s построено. Казна: %d." % [progress, kind, money])
		await _auto_test_pause()
	var roads_connected := true
	for i in range(1, road_plan.size()):
		var step := road_plan[i] - road_plan[i - 1]
		if abs(step.x) + abs(step.y) != 1:
			roads_connected = false
			_auto_test_fail("Дорожные клетки не соединены.")
	var adjacent_buildings := 0
	for action in actions:
		var kind: String = action.kind
		if kind == "road": continue
		var cell: Vector2i = action.cell
		if _is_adjacent_to_road(cell): adjacent_buildings += 1
		else: _auto_test_fail("%s в %s не примыкает к дороге." % [kind, cell])
	var rejection_checks := [
		{"cell": Vector2i(15, 0), "kind": "house", "label": "граница карты"},
		{"cell": Vector2i(-13, 0), "kind": "house", "label": "река"},
		{"cell": Vector2i(0, 0), "kind": "house", "label": "центральная площадь"},
		{"cell": road_plan[0], "kind": "house", "label": "занятая дорога"}
	]
	var rejected := 0
	for check in rejection_checks:
		var cell: Vector2i = check.cell
		var kind: String = check.kind
		var placement_valid := _can_place_at(cell.x, cell.y, kind)
		var placement_created := _try_place_building(cell.x, cell.y, kind, false)
		if not placement_valid and not placement_created:
			rejected += 1
			_record_auto_test("ОТКЛОНЕНО КОРРЕКТНО: %s." % check.label)
		else:
			_auto_test_fail("Система разрешила недопустимое место: %s." % check.label)
	var built := placed.size()
	if built != 9: _auto_test_fail("Ожидалось 9 объектов, создано %d." % built)
	if _count_type("road") != 5 or _count_type("house") != 2 or _count_type("farm") != 1 or _count_type("market") != 1:
		_auto_test_fail("Итоговый состав города отличается от плана.")
	if money != 570 or population != 10: _auto_test_fail("Баланс после строительства неверен: деньги=%d, жители=%d." % [money, population])
	if rejected != rejection_checks.size(): _auto_test_fail("Проверки отказа прошли %d/%d." % [rejected, rejection_checks.size()])
	if adjacent_buildings != 4: _auto_test_fail("К дороге примыкают %d из 4 зданий." % adjacent_buildings)
	auto_test_finished = true
	if auto_test_success:
		_record_auto_test("RESULT: SUCCESS | 9 зданий/дорог, %d/4 блокировок проверено, дорога связана, %d/4 здания примыкают." % [rejected, adjacent_buildings])
	else:
		_record_auto_test("RESULT: FAILURE | построено %d объектов." % built)
	selected_building = "select"
	_update_preview_visibility()
	if is_instance_valid(selected_label): selected_label.text = "Автотест завершён: " + ("успех" if auto_test_success else "ошибка")
	_show_message("Автотест: " + ("УСПЕХ" if auto_test_success else "ОШИБКА") + " — %d объектов. Город оставлен на экране." % built)
	if DisplayServer.get_name() == "headless":
		get_tree().quit(0 if auto_test_success else 1)
	else:
		await get_tree().create_timer(1.0).timeout
		await RenderingServer.frame_post_draw
		var screenshot := get_viewport().get_texture().get_image()
		var screenshot_error := screenshot.save_png(ProjectSettings.globalize_path("res://auto_test_city_after.png"))
		if screenshot_error == OK: _record_auto_test("SCREENSHOT: res://auto_test_city_after.png сохранён.")
		else: _record_auto_test("SCREENSHOT ERROR: код %d." % screenshot_error)

func _run_model_smoke_test() -> void:
	var kinds: Array[String] = ["house", "house_large", "market", "warehouse", "workshop", "farm", "forum", "road"]
	var successes := 0
	for kind in kinds:
		var placed_at := Vector2i(999, 999)
		for gz in range(5, 16):
			for gx in range(4, 16):
				if _can_place_at(gx, gz, kind):
					placed_at = Vector2i(gx, gz)
					break
			if placed_at.x != 999: break
		if placed_at.x == 999:
			push_error("MODEL-SMOKE: no safe test cell for " + kind)
			continue
		if not _try_place_building(placed_at.x, placed_at.y, kind, false):
			push_error("MODEL-SMOKE: build path rejected " + kind)
			continue
		var instance: Node = get_child(get_child_count() - 1)
		var meshes := _count_mesh_instances(instance)
		if meshes < 4:
			push_error("MODEL-SMOKE: %s has only %d mesh parts." % [kind, meshes])
			continue
		successes += 1
		print("[MODEL-SMOKE] BUILT %s at %s | %d mesh parts" % [kind, placed_at, meshes])
	var distance_before := camera_distance
	var wheel := InputEventMouseButton.new()
	wheel.button_index = MOUSE_BUTTON_WHEEL_UP
	wheel.pressed = true
	_unhandled_input(wheel)
	var zoom_ok := camera_distance < distance_before
	camera_distance = distance_before
	selected_building = "house"
	var rotate_event := InputEventKey.new()
	rotate_event.keycode = KEY_R
	rotate_event.pressed = true
	_unhandled_input(rotate_event)
	var rotation_ok := build_rotation == 1
	build_rotation = 0
	if successes == kinds.size() and zoom_ok and rotation_ok:
		print("[MODEL-SMOKE] RESULT: SUCCESS | %d buildable scenes, wheel zoom and R rotation." % successes)
	else:
		push_error("MODEL-SMOKE: scenes=%d/%d zoom=%s rotation=%s" % [successes, kinds.size(), zoom_ok, rotation_ok])
	if DisplayServer.get_name() == "headless": get_tree().quit(0 if successes == kinds.size() and zoom_ok and rotation_ok else 1)

func _count_mesh_instances(root: Node) -> int:
	var count := 1 if root is MeshInstance3D else 0
	for child in root.get_children(): count += _count_mesh_instances(child)
	return count

func _record_auto_test(line: String) -> void:
	auto_test_log.append(line)
	print("[AUTO-TEST] " + line)

func _auto_test_pause() -> void:
	if DisplayServer.get_name() != "headless":
		await get_tree().create_timer(0.7).timeout

func _auto_test_fail(reason: String) -> void:
	auto_test_success = false
	_record_auto_test("ОШИБКА: " + reason)
	push_error("AUTO-TEST: " + reason)

func _is_adjacent_to_road(cell: Vector2i) -> bool:
	for offset in [Vector2i.UP, Vector2i.DOWN, Vector2i.LEFT, Vector2i.RIGHT]:
		var neighbor: Vector2i = cell + offset
		if placed.get(str(neighbor.x) + "," + str(neighbor.y), "") == "road":
			return true
	return false

func _count_type(kind: String) -> int:
	var total := 0
	for value in placed.values():
		if value == kind: total += 1
	return total

func _update_hud() -> void:
	if not is_instance_valid(hud_label): return
	hud_label.text = "День %d   |   Казна: %d   |   Жители: %d   |   Еда: %d" % [day, money, population, food]

func _show_message(text_value: String) -> void:
	if is_instance_valid(message_label): message_label.text = text_value
