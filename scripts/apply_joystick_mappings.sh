#!/usr/bin/env bash
set -euo pipefail
CONFIG_DIR="$HOME/.config/retroarch"
# Ensure global config has player2 mappings (already present if user followed plan)
# Loop over all core config files (*.cfg) and copy player1 mappings to player2 if missing
for cfg in "$CONFIG_DIR"/cores/*.cfg; do
  [ -e "$cfg" ] || continue
  echo "Processing $cfg"
  # For each line that starts with input_player1_, create a corresponding player2 line
  grep -E '^input_player1_' "$cfg" | while IFS= read -r line; do
    # Transform to player2
    player2_line=$(echo "$line" | sed 's/input_player1_/input_player2_/')
    # If player2 line already exists, skip
    if grep -Fq "${player2_line%%=*}" "$cfg"; then
      continue
    fi
    echo "Adding: $player2_line" >> "$cfg"
  done
  # Ensure joystick index for player2 is set to 1 (second joystick)
  if ! grep -q '^input_player2_joypad_index' "$cfg"; then
    echo 'input_player2_joypad_index = "1"' >> "$cfg"
  fi
done
# Ensure RetroArch loads per‑core config
grep -q '^input_remap_secondary_enable' "$CONFIG_DIR/retroarch.cfg" && sed -i 's/^input_remap_secondary_enable.*/input_remap_secondary_enable = "true"/' "$CONFIG_DIR/retroarch.cfg" || echo 'input_remap_secondary_enable = "true"' >> "$CONFIG_DIR/retroarch.cfg"

echo "Joystick mappings applied to all core configs."
