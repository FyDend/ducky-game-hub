#!/usr/bin/env python3
"""
Script OPCIONAL para actualizar la base de datos de popularidad de IGDB.

NOTA: Ducky Game Hub ya incluye una base de datos pre-generada con ~14,000 juegos
      y sus scores de popularidad (igdb_popularity.json). Este script solo es
      necesario si querés actualizar esos datos con información más reciente.

REQUISITOS (GRATIS):
  1. Ve a https://dev.twitch.tv/console/apps
  2. Crea una aplicación (cualquier nombre, category: "Application Integration")
  3. Genera un Client Secret
  4. Configurá las credenciales en tu .env:
     IGDB_CLIENT_ID=TU_CLIENT_ID
     IGDB_CLIENT_SECRET=TU_CLIENT_SECRET
  5. Ejecutá setup.sh para que genere el archivo de credenciales

USO:
  docker exec bridge_api python3 /app/fetch_igdb_popularity.py

RESULTADO:
  Actualiza /app/igdb_popularity.json con datos frescos de IGDB.
"""

import requests
import json
import os
import re
import math
import time

# ─── Rutas ──────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(__file__)
OUTPUT_PATH  = os.path.join(BASE_DIR, "igdb_popularity.json")
CREDS_PATHS  = [
    os.path.join(BASE_DIR, "..", ".secrets", "igdb_creds.json"),
    "/run/secrets/igdb_creds.json",
    os.path.join(BASE_DIR, "igdb_creds.json"),
]

# ─── Normalización de nombres ────────────────────────────────────────────────
def normalize(name: str) -> str:
    """Normaliza un nombre para matching fuzzy con nuestro games_db."""
    n = name.lower()
    n = re.sub(r'\s*\([^)]*\)', '', n)    # quitar (USA), (En,Fr,...), etc.
    n = re.sub(r'\s*\[[^\]]*\]', '', n)   # quitar [BCES-...]
    n = re.sub(r'[^a-z0-9\s]', ' ', n)   # solo alfanumérico + espacio
    n = re.sub(r'\s+', ' ', n).strip()
    if n.startswith('the '):
        n = n[4:] + ' the'
    return n

# ─── IGDB API ────────────────────────────────────────────────────────────────
def get_twitch_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id":     client_id,
            "client_secret": client_secret,
            "grant_type":    "client_credentials",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def fetch_page(token: str, client_id: str, offset: int, limit: int = 500) -> list:
    """Obtiene una página de juegos de IGDB ordenados por rating_count desc."""
    body = (
        f"fields name, rating, rating_count, aggregated_rating, aggregated_rating_count; "
        f"limit {limit}; offset {offset}; "
        f"where rating_count > 3; "
        f"sort rating_count desc;"
    )
    resp = requests.post(
        "https://api.igdb.com/v4/games",
        headers={
            "Client-ID":     client_id,
            "Authorization": f"Bearer {token}",
            "Content-Type":  "text/plain",
        },
        data=body,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()

# ─── Score compuesto ─────────────────────────────────────────────────────────
def composite_score(game: dict) -> float:
    """Combina rating de usuarios + crítica ponderado por # de votos."""
    user_r   = game.get("rating", 0) or 0
    user_n   = game.get("rating_count", 0) or 0
    crit_r   = game.get("aggregated_rating", 0) or 0
    crit_n   = game.get("aggregated_rating_count", 0) or 0

    total_n = user_n + crit_n
    if total_n == 0:
        return 0.0

    # Promedio ponderado de ambas fuentes
    if user_n > 0 and crit_n > 0:
        blended = (user_r * user_n + crit_r * crit_n) / total_n
    elif user_n > 0:
        blended = user_r
    else:
        blended = crit_r

    # Escalar por logaritmo de votos totales para bajar juegos con muy pocos votos
    return round(blended * math.log(total_n + 1), 3)

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    # Leer credenciales
    creds = None
    for path in CREDS_PATHS:
        if os.path.exists(path):
            with open(path, "r") as f:
                creds = json.load(f)
            print(f"Credenciales cargadas desde: {path}")
            break

    if not creds:
        # Verificar si ya existe una base de datos pre-generada
        if os.path.exists(OUTPUT_PATH):
            print("\nℹ️  No se encontraron credenciales de IGDB/Twitch, pero ya")
            print(f"   existe una base de datos de popularidad con datos pre-generados.")
            print(f"   Archivo: {OUTPUT_PATH}")
            print("\n   Si querés actualizar los datos, configurá las credenciales en tu .env:")
            print("     IGDB_CLIENT_ID=TU_CLIENT_ID")
            print("     IGDB_CLIENT_SECRET=TU_CLIENT_SECRET")
            print("   Y luego ejecutá setup.sh para generar el archivo de credenciales.")
        else:
            print("\n" + "="*60)
            print("AVISO: No se encontraron credenciales de IGDB/Twitch.")
            print("="*60)
            print("\nEl filtro por popularidad no estará disponible hasta que")
            print("configures las credenciales en tu .env:")
            print("  IGDB_CLIENT_ID=TU_CLIENT_ID")
            print("  IGDB_CLIENT_SECRET=TU_CLIENT_SECRET")
            print("\nPasos para obtener credenciales GRATUITAS:")
            print("  1. Ve a https://dev.twitch.tv/console/apps")
            print("  2. Inicia sesión con tu cuenta de Twitch (o créala gratis)")
            print("  3. Haz clic en 'Register Your Application'")
            print("  4. Pon cualquier nombre, OAuth Redirect URL: http://localhost")
            print("     Category: 'Application Integration'")
            print("  5. Genera un Client Secret")
            print("  6. Ejecutá setup.sh para generar el archivo de credenciales")
            print("\nLuego ejecuta:")
            print("  docker exec bridge_api python3 /app/fetch_igdb_popularity.py")
        return

    print("Obteniendo token OAuth de Twitch...")
    token = get_twitch_token(creds["client_id"], creds["client_secret"])
    print("✓ Token obtenido.\n")

    all_games: dict[str, dict] = {}
    offset    = 0
    limit     = 500
    max_fetch = 15000   # Límite de seguridad (30 peticiones × 500 juegos)

    while offset < max_fetch:
        print(f"  Descargando juegos {offset}–{offset+limit}...", end=" ", flush=True)
        try:
            page = fetch_page(token, creds["client_id"], offset, limit)
        except requests.HTTPError as e:
            print(f"Error HTTP: {e}")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

        if not page:
            print("(fin de resultados)")
            break

        added = 0
        for g in page:
            raw_name = g.get("name", "").strip()
            if not raw_name:
                continue
            score = composite_score(g)
            if score <= 0:
                continue
            key = normalize(raw_name)
            # Guardar el mejor score si el nombre normalizado ya existe
            if key not in all_games or score > all_games[key]["score"]:
                all_games[key] = {
                    "name":         raw_name,
                    "rating":       round(g.get("rating", 0) or 0, 1),
                    "rating_count": g.get("rating_count", 0) or 0,
                    "score":        score,
                }
            added += 1

        print(f"{added} juegos añadidos. Total: {len(all_games)}")
        offset += limit

        if len(page) < limit:
            print("  (última página alcanzada)")
            break

        time.sleep(0.25)   # Respetar rate limit de IGDB (4 req/seg)

    if not all_games:
        print("\nNo se obtuvieron juegos. Revisa tus credenciales.")
        return

    print(f"\n✓ Total final: {len(all_games)} juegos con scores de popularidad.")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_games, f, ensure_ascii=False, indent=2)
    print(f"✓ Guardado en: {OUTPUT_PATH}")
    print("\nReinicia bridge_api para aplicar los cambios:")
    print("  docker restart bridge_api")

if __name__ == "__main__":
    main()
