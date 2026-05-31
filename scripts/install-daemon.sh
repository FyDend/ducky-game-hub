#!/usr/bin/env bash
# ==============================================================================
# Instala el Daemon de Joysticks como un Servicio systemd de Usuario
# ==============================================================================
set -euo pipefail

# Obtener ruta absoluta del proyecto
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[Daemon Installer] Directorio del proyecto detectado: $PROJECT_DIR"

# Crear directorio de servicios de usuario si no existe
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

# Generar archivo de servicio personalizado
SERVICE_TEMPLATE="$PROJECT_DIR/daemon/retrocloud-gamepad.service"
SERVICE_TARGET="$USER_SYSTEMD_DIR/retrocloud-gamepad.service"

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
systemctl --user enable retrocloud-gamepad.service

echo "[Daemon Installer] Iniciando el servicio..."
systemctl --user restart retrocloud-gamepad.service

echo "[Daemon Installer] ¡Instalación completada con éxito!"
echo "[Daemon Installer] Puedes verificar el estado con: systemctl --user status retrocloud-gamepad.service"
