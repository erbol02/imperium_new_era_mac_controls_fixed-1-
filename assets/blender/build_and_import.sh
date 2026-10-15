#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}"
GODOT_BIN="${GODOT_BIN:-/Applications/Godot.app/Contents/MacOS/Godot}"

if [ ! -x "$BLENDER_BIN" ]; then
  echo "Blender executable not found: $BLENDER_BIN" >&2
  echo "Set BLENDER_BIN to the installed Blender executable." >&2
  exit 1
fi
if [ ! -x "$GODOT_BIN" ]; then
  echo "Godot executable not found: $GODOT_BIN" >&2
  echo "Set GODOT_BIN to the installed Godot 4 executable." >&2
  exit 1
fi

"$BLENDER_BIN" --background --python "$SCRIPT_DIR/build_game_models.py"
"$GODOT_BIN" --headless --editor --path "$PROJECT_ROOT" --quit
echo "GLB models exported and imported into the Godot project."
