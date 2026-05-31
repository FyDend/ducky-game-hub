#!/usr/bin/env bash
# ==============================================================================
# Lanzador Universal de Ducky Game Hub (Sovereign Game Pass)
# ==============================================================================

# Asegurar directorio de ejecución
CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 || exit 1

echo "[Ducky Game Hub] Iniciando servicios en segundo plano..."

# 1. Levantar el stack de contenedores Docker en segundo plano si no están corriendo
docker compose up -d

# 2. Asegurar que la pantalla virtual y el sumidero de audio estén configurados en el host
./scripts/setup_virtual_display.sh

echo "[Ducky Game Hub] ¡Lanzado con éxito en el monitor virtual TV-STREAM (Workspace 10)!"
