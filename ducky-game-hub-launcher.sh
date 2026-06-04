#!/usr/bin/env bash
# ==============================================================================
# Lanzador Universal de Ducky Game Hub (Sovereign Game Pass)
# ==============================================================================

# Asegurar directorio de ejecución
CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 || exit 1

echo "[Ducky Game Hub] Iniciando servicios en segundo plano..."

# Levantar el stack de contenedores Docker en segundo plano
docker compose up -d

echo "[Ducky Game Hub] ¡Stack de contenedores iniciado con éxito!"
