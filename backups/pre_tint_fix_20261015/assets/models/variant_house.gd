extends Node3D
## Selects one of the authored Blender house silhouettes by the placement variant.
@export_range(0, 2, 1) var variant := 0

func _ready() -> void:
	var models := get_children()
	for i in range(models.size()):
		models[i].visible = i == posmod(variant, models.size())
