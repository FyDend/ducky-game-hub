#!/usr/bin/env bash
# ==============================================================================
# Instalador Inteligente de Ducky Game Hub (Kubernetes Zero-Configuration)
# ==============================================================================
set -e

# 1. Autodetectar el entorno del Host local
export HOST_USER=$(whoami)
export PUID=$(id -u)
export PGID=$(id -g)
export WORKSPACE_PATH=$(cd -- "$(dirname -- "$0")" > /dev/null 2>&1 && pwd)

# Autodetectar la Zona Horaria del sistema operativo
if [ -f /etc/localtime ]; then
    export TZ=$(readlink /etc/localtime | sed 's#.*/zoneinfo/##')
else
    export TZ="America/Argentina/Buenos_Aires"
fi

echo "===================================================="
echo "🦆 INICIANDO INSTALACION DE DUCKY GAME HUB:"
echo "👤 Usuario detectado: $HOST_USER (UID: $PUID / GID: $PGID)"
echo "📅 Zona Horaria: $TZ"
echo "📂 Ruta del Proyecto: $WORKSPACE_PATH"
echo "===================================================="

# 2. Asegurar directorios y configuraciones iniciales
mkdir -p "$WORKSPACE_PATH/qbittorrent/config"

# 3. Levantar el stack de contenedores Docker en segundo plano
echo "🐳 Levantando servicios Docker..."
docker compose -f "$WORKSPACE_PATH/docker-compose.yml" up -d

# 4. Configurar la pantalla virtual y el sumidero de audio en el host
if [ -f "$WORKSPACE_PATH/scripts/setup_virtual_display.sh" ]; then
    echo "🖥️  Configurando pantalla virtual..."
    bash "$WORKSPACE_PATH/scripts/setup_virtual_display.sh"
fi

# 5. Crear el Lanzador de Escritorio (.desktop) dinámico para el usuario
echo "🖥️  Integrando Ducky Game Hub con el buscador de aplicaciones (Super + Space)..."
DESKTOP_DIR="/home/$HOST_USER/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat <<EOF > "$DESKTOP_DIR/ducky-game-hub.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Ducky Game Hub
Comment=Tu Sovereign Game Pass de Emulación
Exec=$WORKSPACE_PATH/ducky-game-hub-launcher.sh
Icon=$WORKSPACE_PATH/store_front/assets/logo.png
Terminal=false
Categories=Game;Emulator;
EOF

chmod +x "$DESKTOP_DIR/ducky-game-hub.desktop"

echo "===================================================="
echo "✅ ¡Instalación Completada con Éxito!"
echo "✨ Ya puedes presionar 'Super + Space', buscar 'Ducky Game Hub' y jugar."
echo "===================================================="
