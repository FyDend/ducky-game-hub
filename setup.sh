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

# Cargar wrappers de compatibilidad para Distrobox / dependencias
if [ -f "$WORKSPACE_PATH/scripts/distrobox_helper.sh" ]; then
    source "$WORKSPACE_PATH/scripts/distrobox_helper.sh"
fi

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

# 1.5 Verificar disponibilidad de Docker y Docker Compose
COMPOSE_OK=false
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    COMPOSE_OK=true
elif command -v docker-compose &>/dev/null; then
    COMPOSE_OK=true
elif command -v distrobox-host-exec &>/dev/null; then
    if distrobox-host-exec docker compose version &>/dev/null || distrobox-host-exec docker-compose version &>/dev/null; then
        COMPOSE_OK=true
    fi
fi

if [ "$COMPOSE_OK" = false ]; then
    echo ""
    echo "❌ ERROR: No se encontró Docker Compose."
    echo "   Ducky Game Hub requiere Docker + Docker Compose para levantar sus servicios (API, Sunshine, qBittorrent, etc.)."
    if command -v distrobox-host-exec &>/dev/null; then
        echo "   Por favor, asegúrate de tener instalado Docker y su plugin Compose en tu sistema HOST."
    else
        echo "   Por favor, instala Docker y el plugin 'docker-compose-plugin' (o 'docker-compose') en tu sistema."
    fi
    echo ""
    exit 1
fi

# 2. Asegurar directorios y configuraciones iniciales
mkdir -p "$WORKSPACE_PATH/qbittorrent/config"

# Autodetectar y configurar el archivo .env
if [ ! -f "$WORKSPACE_PATH/.env" ]; then
    echo "📄 Creando archivo .env inicial a partir de .env.example..."
    cp "$WORKSPACE_PATH/.env.example" "$WORKSPACE_PATH/.env"
fi

# Detectar la IP del host en la red de docker. Si existe docker0, usar esa. Si no, buscar la primera ip de interfaces virtuales de docker o fallback a 172.17.0.1
DETECTED_HOST_IP=$(ip -4 addr show docker0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2 | head -n1)
if [ -z "$DETECTED_HOST_IP" ]; then
    DETECTED_HOST_IP=$(docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || echo "172.17.0.1")
fi
if [ -z "$DETECTED_HOST_IP" ]; then
    DETECTED_HOST_IP="172.17.0.1"
fi

echo "⚙️  Configurando archivo .env con valores dinámicos..."
# Reemplazar valores autodetectados utilizando sed
sed -i "s/^HOST_USER=.*/HOST_USER=$HOST_USER/" "$WORKSPACE_PATH/.env"
sed -i "s/^PUID=.*/PUID=$PUID/" "$WORKSPACE_PATH/.env"
sed -i "s/^PGID=.*/PGID=$PGID/" "$WORKSPACE_PATH/.env"
sed -i "s|^TZ=.*|TZ=$TZ|" "$WORKSPACE_PATH/.env"
sed -i "s/^HOST_IP=.*/HOST_IP=$DETECTED_HOST_IP/" "$WORKSPACE_PATH/.env"

# 2.5 Solicitar la ruta de ROMs si no está configurada
source "$WORKSPACE_PATH/.env"
if [ -z "$ROMS_PATH" ] || [ "$ROMS_PATH" = "/mnt/tu_disco/Roms" ]; then
    echo ""
    read -rp "📂 ¿Dónde están tus ROMs? (ej. /mnt/MiDisco/Roms): " USER_ROMS_PATH
    if [ -n "$USER_ROMS_PATH" ]; then
        sed -i "s|^ROMS_PATH=.*|ROMS_PATH=$USER_ROMS_PATH|" "$WORKSPACE_PATH/.env"
        ROMS_PATH="$USER_ROMS_PATH"
    fi
fi

# 2.6 Generar bridge_api/settings.json dinámico (nunca se sube a git)
echo "📝 Generando bridge_api/settings.json..."
SETTINGS_FILE="$WORKSPACE_PATH/bridge_api/settings.json"
if [ ! -f "$SETTINGS_FILE" ]; then
    cat <<SETTINGS_EOF > "$SETTINGS_FILE"
{
  "roms_path": "$ROMS_PATH",
  "host_user": "$HOST_USER",
  "host_ip": "$DETECTED_HOST_IP"
}
SETTINGS_EOF
else
    # Actualizar los campos dinámicos sin perder la configuración existente del usuario
    TMP_SETTINGS=$(mktemp)
    if command -v jq &> /dev/null; then
        jq --arg ru "$ROMS_PATH" --arg hu "$HOST_USER" --arg hi "$DETECTED_HOST_IP" \
           '.roms_path = $ru | .host_user = $hu | .host_ip = $hi' \
           "$SETTINGS_FILE" > "$TMP_SETTINGS" && mv "$TMP_SETTINGS" "$SETTINGS_FILE"
    elif command -v python3 &> /dev/null; then
        python3 -c "
import json
with open('$SETTINGS_FILE', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['roms_path'] = '$ROMS_PATH'
data['host_user'] = '$HOST_USER'
data['host_ip'] = '$DETECTED_HOST_IP'
with open('$TMP_SETTINGS', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" && mv "$TMP_SETTINGS" "$SETTINGS_FILE"
    else
        echo "⚠️  No se encontró 'jq' ni 'python3' para actualizar bridge_api/settings.json sin perder otros campos."
        echo "   Sobrescribiendo archivo con la configuración básica..."
        cat <<SETTINGS_EOF > "$SETTINGS_FILE"
{
  "roms_path": "$ROMS_PATH",
  "host_user": "$HOST_USER",
  "host_ip": "$DETECTED_HOST_IP"
}
SETTINGS_EOF
    fi
fi

# 3. Levantar el stack de contenedores Docker en segundo plano
echo "🐳 Levantando servicios Docker..."
docker compose -f "$WORKSPACE_PATH/docker-compose.yml" up -d


# 4. Instalar el daemon de mandos (joysticks) en el host
if [ -f "$WORKSPACE_PATH/scripts/install-daemon.sh" ]; then
    echo "🎮 Instalando daemon de mandos en el host..."
    bash "$WORKSPACE_PATH/scripts/install-daemon.sh"
fi

# 5. Configurar la pantalla virtual y el sumidero de audio en el host
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
