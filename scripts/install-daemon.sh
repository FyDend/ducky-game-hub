#!/usr/bin/env bash
# ==============================================================================
# Instala el Daemon de Joysticks como un Servicio systemd de Usuario
# ==============================================================================
set -euo pipefail

# Obtener ruta absoluta del proyecto
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
systemctl() { run_host_cmd systemctl "$@"; }

echo "[Daemon Installer] Directorio del proyecto detectado: $PROJECT_DIR"

# Crear directorio de servicios de usuario si no existe
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

# Generar archivo de servicio personalizado
SERVICE_TEMPLATE="$PROJECT_DIR/daemon/ducky-game-hub-gamepad.service"
SERVICE_TARGET="$USER_SYSTEMD_DIR/ducky-game-hub-gamepad.service"

if [ ! -f "$SERVICE_TEMPLATE" ]; then
    echo "[Daemon Installer] ERROR: No se encontró la plantilla del servicio en $SERVICE_TEMPLATE"
    exit 1
fi

echo "[Daemon Installer] Configurando el servicio de systemd..."
# Reemplazar la variable de ruta por la real y escribir al destino
sed "s|WORKSPACE_PATH|$PROJECT_DIR|g" "$SERVICE_TEMPLATE" > "$SERVICE_TARGET"

echo "[Daemon Installer] Recargando systemd de usuario..."
systemctl --user daemon-reload

echo "[Daemon Installer] Habilitando el servicio para que inicie con la sesión..."
systemctl --user enable ducky-game-hub-gamepad.service

echo "[Daemon Installer] Iniciando el servicio..."
systemctl --user restart ducky-game-hub-gamepad.service

echo "[Daemon Installer] ¡Instalación completada con éxito!"
echo "[Daemon Installer] Puedes verificar el estado con: systemctl --user status ducky-game-hub-gamepad.service"
