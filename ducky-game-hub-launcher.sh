#!/usr/bin/env bash
# ==============================================================================
# Lanzador Universal de Ducky Game Hub (Sovereign Game Pass)
# ==============================================================================

# Asegurar directorio de ejecución
CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 || exit 1

echo "[Ducky Game Hub] Iniciando servicios en segundo plano..."

# Levantar el stack de contenedores Docker en segundo plano
if [ -f .env ]; then
    source .env
fi
COMPOSE_CMD=${COMPOSE_CMD:-"docker compose"}

# Derivar el comando base de docker para usar docker wait
DOCKER_CMD=$(echo "$COMPOSE_CMD" | sed 's/ compose//; s/-compose//')

# Levantar el stack
$COMPOSE_CMD up -d

echo "[Ducky Game Hub] ¡Stack de contenedores iniciado con éxito!"
echo "[Ducky Game Hub] Esperando a que se cierre la aplicación..."

# Esperar a que el contenedor de la interfaz (store_front) termine
$DOCKER_CMD wait store_front

echo "[Ducky Game Hub] Cerrando servicios y limpiando contenedores..."
# Detener y remover el stack
$COMPOSE_CMD down

echo "[Ducky Game Hub] Aplicación cerrada de forma limpia."
