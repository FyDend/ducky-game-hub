from fastapi import APIRouter, BackgroundTasks
import urllib.parse
import os
import subprocess
from services.catalog_service import (
    GAMES_CACHE, IGDB_POPULARITY, normalize_popularity_key,
    obtener_archivos_locales, find_local_path_for_filename, CORE_MAP, load_cache
)

router = APIRouter()

def run_build_db():
    print("[API] Iniciando reconstrucción del catálogo...", flush=True)
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "build_db.py")
        subprocess.run(["python3", script_path], check=True)
        print("[API] Catálogo reconstruido con éxito. Recargando caché...", flush=True)
        load_cache()
    except Exception as e:
        print(f"[API] Error reconstruyendo catálogo: {e}", flush=True)

@router.post("/catalogo/rebuild")
def rebuild_catalog(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_build_db)
    return {"estado": "OK", "mensaje": "Reconstrucción del catálogo iniciada en segundo plano."}


from services.catalog_service import search_catalog_sqlite, SQLITE_DB_PATH
import sqlite3
import json

@router.get("/catalogo")
def obtener_catalogo(q: str = "", console: str = "all", page: int = 1, per_page: int = 50, sort: str = "popularity"):
    local_files = obtener_archivos_locales()
    
    games, total_count = search_catalog_sqlite(query_str=q, console=console, page=page, per_page=per_page, sort=sort)
    
    for game in games:
        downloaded = False
        for v in game["versions"]:
            filename = v.get("filename", "")
            if not filename:
                filename = urllib.parse.unquote(v["downloadUrl"].split('/')[-1])
                
            if find_local_path_for_filename(filename, local_files):
                downloaded = True
                break
        game["downloaded"] = downloaded
        
    return {
        "estado": "OK",
        "resultados": games,
        "total": total_count,
        "page": page,
        "per_page": per_page
    }

@router.get("/libreria")
def obtener_libreria():
    resultados = []
    local_files = obtener_archivos_locales()
    
    if not local_files:
        return resultados
        
    rutas_agregadas = set()
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT title, console, cover_url, versions FROM games")
    rows = cursor.fetchall()
    conn.close()
    
    for r in rows:
        title = r["title"]
        versions = json.loads(r["versions"])
        for v in versions:
            filename = v.get("filename", "")
            if not filename:
                filename = urllib.parse.unquote(v["downloadUrl"].split('/')[-1])
                
            actual_path = find_local_path_for_filename(filename, local_files)
            if actual_path:
                resultados.append({
                    "id": filename,
                    "title": title,
                    "console": r["console"],
                    "path": actual_path,
                    "image": r["cover_url"],
                    "core": CORE_MAP.get(r["console"], "snes9x"),
                    "year": "LOCAL"
                })
                rutas_agregadas.add(actual_path)
                break
                
    for filename, actual_path in local_files.items():
        if actual_path not in rutas_agregadas:
            relative_path = actual_path.replace("/roms/", "", 1)
            parts = relative_path.split("/")
            console = parts[0] if parts else "desconocida"
            clean_title = os.path.splitext(filename)[0]
            core = CORE_MAP.get(console, "snes9x")
            
            resultados.append({
                "id": filename,
                "title": clean_title,
                "console": console,
                "path": actual_path,
                "image": "",
                "core": core,
                "year": "LOCAL"
            })
            rutas_agregadas.add(actual_path)

    return resultados
