import os
import json
import re
import urllib.parse
import sqlite3
from config import DB_PATH, IGDB_PATH

GAMES_CACHE = {}
IGDB_POPULARITY = {}
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog.db")

def init_db():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            console     TEXT NOT NULL,
            cover_url   TEXT,
            versions    TEXT,   -- JSON serializado
            popularity  REAL DEFAULT 0
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_console ON games(console)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title   ON games(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pop     ON games(popularity DESC)")
    conn.commit()
    conn.close()

def load_cache():
    global GAMES_CACHE, IGDB_POPULARITY
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            GAMES_CACHE.update(json.load(f))
        print(f"Cargados {len(GAMES_CACHE)} juegos desde games_db.json localmente.")
    else:
        print("games_db.json no encontrado. El catálogo estará vacío.")

    if os.path.exists(IGDB_PATH):
        with open(IGDB_PATH, "r", encoding="utf-8") as f:
            IGDB_POPULARITY.update(json.load(f))
        print(f"Cargados {len(IGDB_POPULARITY)} registros de popularidad IGDB.")
    else:
        print("igdb_popularity.json no encontrado. Orden por popularidad no disponible.")

def migrate_json_to_sqlite():
    init_db()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games")
    count = cursor.fetchone()[0]
    
    if count == 0 and os.path.exists(DB_PATH):
        print("[SQLITE] Migrando games_db.json a catalog.db...", flush=True)
        load_cache()
        
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        insert_data = []
        for base_name, game in data.items():
            key = normalize_popularity_key(base_name)
            igdb_entry = IGDB_POPULARITY.get(key)
            pop = igdb_entry["score"] if igdb_entry else 0
            
            insert_data.append((
                game["title"],
                game["console"],
                game["image"],
                json.dumps(game["versions"], ensure_ascii=False),
                pop
            ))
            
        cursor.executemany("""
            INSERT INTO games (title, console, cover_url, versions, popularity)
            VALUES (?, ?, ?, ?, ?)
        """, insert_data)
        conn.commit()
        print(f"[SQLITE] Migrados {len(insert_data)} juegos con éxito.", flush=True)
        
    conn.close()

def normalize_popularity_key(name: str) -> str:
    n = name.lower()
    n = re.sub(r'\s*\([^)]*\)', '', n)   # strip (USA), (En,Fr,...), etc.
    n = re.sub(r'\s*\[[^\]]*\]', '', n)  # strip [BCES-...] style tags
    n = re.sub(r'[^a-z0-9\s]', ' ', n)   # keep only alphanumeric + space
    n = re.sub(r'\s+', ' ', n).strip()
    if n.startswith('the '):
        n = n[4:] + ' the'
    return n

def obtener_archivos_locales():
    local_files = {}
    if os.path.exists("/roms"):
        EXTENSIONS = (
            ".zip", ".iso", ".chd", ".rvz", ".sfc", ".smc", ".fig", ".swc", 
            ".nes", ".z64", ".n64", ".v64", ".gb", ".gbc", ".gba", ".nds", 
            ".gcm", ".wii", ".wbfs", ".md", ".bin", ".gen", ".smd", ".sms", 
            ".gg", ".cue", ".m3u", ".img", ".cso", ".pbp", ".xiso", ".xex"
        )
        for root, dirs, files in os.walk("/roms"):
            if "Minerva_Myrient" in root:
                continue
            for f in files:
                if f.lower().endswith(EXTENSIONS):
                    local_files[f] = os.path.join(root, f).replace('\\', '/')
        
        for console in os.listdir("/roms"):
            c_path = os.path.join("/roms", console)
            if os.path.isdir(c_path) and console not in ["Minerva_Myrient", "__pycache__", "venv"]:
                for item in os.listdir(c_path):
                    item_path = os.path.join(c_path, item)
                    if os.path.isdir(item_path) and item != "Minerva_Myrient":
                        local_files[item] = item_path.replace('\\', '/')
    return local_files

def find_local_path_for_filename(filename: str, local_files: dict) -> str:
    if not filename:
        return ""
    if filename in local_files:
        return local_files[filename]
    if filename.endswith(".zip") and filename.replace(".zip", ".iso") in local_files:
        return local_files[filename.replace(".zip", ".iso")]
    if filename.endswith(".zip") and filename.replace(".zip", "") in local_files:
        return local_files[filename.replace(".zip", "")]
    return ""

def search_catalog_sqlite(query_str: str = "", console: str = "all", page: int = 1, per_page: int = 50, sort: str = "popularity", titles: list = None):
    init_db()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql = "SELECT id, title, console, cover_url, versions, popularity FROM games WHERE 1=1"
    params = []
    
    if titles is not None:
        if len(titles) == 0:
            conn.close()
            return [], 0
        placeholders = ",".join(["?"] * len(titles))
        sql += f" AND title IN ({placeholders})"
        params.extend(titles)
        
    if console and console != "all":
        sql += " AND console = ?"
        params.append(console)
        
    if query_str:
        sql += " AND title LIKE ?"
        params.append(f"%{query_str}%")
        
    if sort == "name-asc":
        sql += " ORDER BY title ASC"
    elif sort == "name-desc":
        sql += " ORDER BY title DESC"
    else:
        sql += " ORDER BY popularity DESC, title ASC"
        
    limit = per_page
    offset = (page - 1) * per_page
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "title": r["title"],
            "console": r["console"],
            "image": r["cover_url"],
            "versions": json.loads(r["versions"]),
            "popularity_score": r["popularity"]
        })
        
    count_sql = "SELECT COUNT(*) FROM games WHERE 1=1"
    count_params = []
    
    if titles is not None:
        placeholders = ",".join(["?"] * len(titles))
        count_sql += f" AND title IN ({placeholders})"
        count_params.extend(titles)
        
    if console and console != "all":
        count_sql += " AND console = ?"
        count_params.append(console)
        
    if query_str:
        count_sql += " AND title LIKE ?"
        count_params.append(f"%{query_str}%")
        
    cursor.execute(count_sql, count_params)
    total_count = cursor.fetchone()[0]
    
    conn.close()
    return results, total_count

CORE_MAP = {
    "nes": "nestopia",
    "snes": "snes9x",
    "megadrive": "genesis_plus_gx",
    "mastersystem": "genesis_plus_gx",
    "gamegear": "genesis_plus_gx",
    "gb": "gambatte",
    "gbc": "gambatte",
    "gba": "mgba",
    "n64": "mupen64plus_next",
    "ps1": "pcsx_rearmed",
    "ps2": "pcsx2",
    "ps3": "rpcs3",
    "psp": "ppsspp",
    "gamecube": "dolphin",
    "wii": "dolphin",
    "nds": "melonds",
    "xbox": "xemu",
    "xbox360": "xenia",
}
