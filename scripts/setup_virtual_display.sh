#!/usr/bin/env bash

# ducky-game-hub-virtual-display setup script
# Configura una pantalla virtual para transmisión con Sunshine en Hyprland (Lua API)

export XDG_RUNTIME_DIR="/run/user/$(id -u)"

# Helper para ejecutar comandos en el host desde contenedores si es necesario
run_host_cmd() {
    local cmd="$1"
    if command -v "$cmd" &>/dev/null; then
        "$@"
    elif command -v distrobox-host-exec &>/dev/null; then
        distrobox-host-exec "$@"
    else
        echo "⚠️  Advertencia: No se encontró '$cmd' para interactuar con el host." >&2
        return 127
    fi
}
hyprctl() { run_host_cmd hyprctl "$@"; }
pactl() { run_host_cmd pactl "$@"; }
systemctl() { run_host_cmd systemctl "$@"; }
export HYPRLAND_INSTANCE_SIGNATURE=$(ls -1 "$XDG_RUNTIME_DIR/hypr" 2>/dev/null | head -n 1)

if [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
    echo "Error: No se pudo detectar una sesión activa de Hyprland en $XDG_RUNTIME_DIR/hypr" >&2
    exit 1
fi

echo "Detectada instancia de Hyprland: $HYPRLAND_INSTANCE_SIGNATURE"

# 0. Asegurar el dispositivo de audio virtual ducky-game-hub-audio en PipeWire/PulseAudio
if ! pactl list sinks short | grep -q "ducky-game-hub-audio"; then
    echo "Creando sumidero de audio virtual 'ducky-game-hub-audio'..."
    pactl load-module module-null-sink sink_name=ducky-game-hub-audio sink_properties=device.description="Ducky-Game-Hub-Audio" >/dev/null
else
    echo "El sumidero de audio virtual 'ducky-game-hub-audio' ya existe."
fi

# NOTA: Comentamos la redirección manual de audio por defecto para que Sunshine gestione
# de forma nativa su propio sumidero virtual de alto rendimiento ('sink-sunshine-stereo').
# pactl set-default-sink ducky-game-hub-audio

# Redirigir el audio de los sumideros virtuales a la TV física conectada por HDMI/DP
HDMI_SINK=$(pactl list sinks short | grep -E 'hdmi|hdmi-stereo' | awk '{print $2}' | head -n 1)
if [ -n "$HDMI_SINK" ]; then
    echo "Detectada TV física HDMI: $HDMI_SINK. Redirigiendo audio loopback..."
    # Limpiar módulos loopback existentes para evitar duplicación de audio
    for mod in $(pactl list modules short | grep module-loopback | awk '{print $1}'); do
        pactl unload-module "$mod" >/dev/null 2>&1
    done
    pactl load-module module-loopback source=sink-sunshine-stereo.monitor sink="$HDMI_SINK" latency_msec=30 >/dev/null 2>&1
    pactl load-module module-loopback source=ducky-game-hub-audio.monitor sink="$HDMI_SINK" latency_msec=30 >/dev/null 2>&1
else
    echo "No se detectó salida física HDMI para audio loopback."
fi


# Definir variables de monitor y workspace dinámicas (por defecto para Sunshine en TV)
SETTINGS_JSON="$(cd -- "$(dirname -- "$0")" > /dev/null 2>&1 && pwd)/../bridge_api/settings.json"
if [ -f "$SETTINGS_JSON" ]; then
    if [ -z "$TARGET_MONITOR" ] || [ "$TARGET_MONITOR" = "null" ]; then
        TARGET_MONITOR=$(jq -r '.versatility.target_monitor // "TV-STREAM"' "$SETTINGS_JSON" 2>/dev/null)
    fi
    if [ -z "$TARGET_WORKSPACE" ] || [ "$TARGET_WORKSPACE" = "null" ]; then
        TARGET_WORKSPACE=$(jq -r '.versatility.target_workspace // "10"' "$SETTINGS_JSON" 2>/dev/null)
    fi
    if [ -z "$HOST_MONITOR" ] || [ "$HOST_MONITOR" = "null" ]; then
        HOST_MONITOR=$(jq -r '.versatility.host_monitor // "DP-1"' "$SETTINGS_JSON" 2>/dev/null)
    fi
fi

TARGET_MONITOR=${TARGET_MONITOR:-"TV-STREAM"}
TARGET_WORKSPACE=${TARGET_WORKSPACE:-"10"}
HOST_MONITOR=${HOST_MONITOR:-"DP-1"}

# 1. Comprobar si ya existe el monitor fantasma TARGET_MONITOR
MONITOR_EXISTS=$(hyprctl -j monitors | jq -r --arg name "$TARGET_MONITOR" '.[] | select(.name == $name) | .name' 2>/dev/null)

if [ -z "$MONITOR_EXISTS" ]; then
    if [ "$TARGET_MONITOR" = "TV-STREAM" ]; then
        echo "Creando pantalla virtual headless '$TARGET_MONITOR'..."
        hyprctl output create headless "$TARGET_MONITOR"
        sleep 1
    fi
else
    echo "La pantalla virtual '$TARGET_MONITOR' ya existe."
fi

# 2. Configurar resolución (1080p @ 60Hz), posición 10000x10000 (para aislar por completo el mouse) y escala 1.0 en Lua
if [ "$TARGET_MONITOR" = "TV-STREAM" ]; then
    echo "Configurando monitor virtual $TARGET_MONITOR a 1920x1080@60 en posición aislada (10000x10000)..."
    hyprctl eval "hl.monitor({ output = '$TARGET_MONITOR', mode = '1920x1080@60', position = '10000x10000', scale = 1 })"
fi

# 3. Asignar explícitamente los workspaces 1 al 9 al monitor físico principal (HOST_MONITOR)
echo "Vinculando y moviendo workspaces 1-9 a monitor $HOST_MONITOR..."
for i in {1..9}; do
    hyprctl eval "hl.workspace_rule({ workspace = '$i', monitor = '$HOST_MONITOR' })" >/dev/null
    hyprctl eval "hl.dispatch(hl.dsp.workspace.move({ workspace = $i, monitor = '$HOST_MONITOR' }))" >/dev/null
done

# 4. Vincular el Workspace de manera exclusiva a la pantalla virtual o monitor objetivo
echo "Vinculando y moviendo workspace $TARGET_WORKSPACE a monitor $TARGET_MONITOR..."
hyprctl eval "hl.workspace_rule({ workspace = '$TARGET_WORKSPACE', monitor = '$TARGET_MONITOR' })" >/dev/null
hyprctl eval "hl.dispatch(hl.dsp.workspace.move({ workspace = $TARGET_WORKSPACE, monitor = '$TARGET_MONITOR' }))" >/dev/null

# 4.5. Registrar reglas de ventana dinámicas en Hyprland para emuladores (Flatpaks, Wine/Proton, nativos y títulos con regex)
echo "Registrando reglas de ventana en Hyprland para los emuladores..."
EMU_PATTERNS=("xenia" "Xenia" "xemu" "Xemu" "pcsx2" "PCSX2" "rpcs3" "RPCS3" "dolphin" "Dolphin" "retroarch" "RetroArch" "steam" "Steam")

# Registrar regla para evitar salvapantallas y ubicar Ducky Game Hub en el escritorio correcto
if [ "$TARGET_MONITOR" = "TV-STREAM" ]; then
    echo "Modo Streaming activo: vinculando la ventana de Ducky Game Hub al workspace $TARGET_WORKSPACE..."
    hyprctl eval "hl.window_rule({ match = { class = 'python3', title = '.*Ducky Game Hub.*' }, workspace = '$TARGET_WORKSPACE', idle_inhibit = 'always' })" >/dev/null
    hyprctl eval "hl.window_rule({ match = { class = 'ducky-game-hub' }, workspace = '$TARGET_WORKSPACE', idle_inhibit = 'always' })" >/dev/null
    hyprctl eval "hl.dispatch(hl.dsp.window.move({ workspace = $TARGET_WORKSPACE, window = 'class:^python3$' }))" >/dev/null 2>&1
    hyprctl eval "hl.dispatch(hl.dsp.window.move({ workspace = $TARGET_WORKSPACE, window = 'class:^ducky-game-hub$' }))" >/dev/null 2>&1
else
    ACTIVE_WS=$(hyprctl -j activeworkspace | jq -r '.id' 2>/dev/null)
    ACTIVE_WS=${ACTIVE_WS:-"1"}
    echo "Modo Local/Dual activo: asegurando que Ducky Game Hub se mantenga en el workspace $ACTIVE_WS..."
    hyprctl eval "hl.window_rule({ match = { class = 'python3', title = '.*Ducky Game Hub.*' }, workspace = '$ACTIVE_WS', idle_inhibit = 'always' })" >/dev/null
    hyprctl eval "hl.window_rule({ match = { class = 'ducky-game-hub' }, workspace = '$ACTIVE_WS', idle_inhibit = 'always' })" >/dev/null
    hyprctl eval "hl.dispatch(hl.dsp.window.move({ workspace = $ACTIVE_WS, window = 'class:^python3$' }))" >/dev/null 2>&1
    hyprctl eval "hl.dispatch(hl.dsp.window.move({ workspace = $ACTIVE_WS, window = 'class:^ducky-game-hub$' }))" >/dev/null 2>&1
fi
for pat in "${EMU_PATTERNS[@]}"; do
    hyprctl eval "hl.window_rule({ match = { class = '.*'$pat'.*' }, workspace = '$TARGET_WORKSPACE silent', idle_inhibit = 'always' })" >/dev/null
    hyprctl eval "hl.window_rule({ match = { title = '.*'$pat'.*' }, workspace = '$TARGET_WORKSPACE silent', idle_inhibit = 'always' })" >/dev/null
done
# Cubrir casos de Proton genéricos
hyprctl eval "hl.window_rule({ match = { class = 'steam_app_.*' }, workspace = '$TARGET_WORKSPACE silent', idle_inhibit = 'always' })" >/dev/null
hyprctl eval "hl.window_rule({ match = { class = 'steam_proton' }, workspace = '$TARGET_WORKSPACE silent', idle_inhibit = 'always' })" >/dev/null

# 5. Asegurar que el daemon de salida universal por joystick esté activo en segundo plano
if systemctl --user list-unit-files 2>/dev/null | grep -q "ducky-game-hub-gamepad"; then
    echo "Reiniciando daemon de salida universal por joystick a través de systemd..."
    systemctl --user stop ducky-game-hub-gamepad >/dev/null 2>&1 || true
    systemctl --user start ducky-game-hub-gamepad >/dev/null 2>&1 || true
fi

echo "¡Pantalla virtual 'TV-STREAM' configurada y aislada correctamente!"
