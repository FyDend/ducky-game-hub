import os
import json

# Configuración básica desde variables de entorno
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "games_db.json")
IGDB_PATH = os.path.join(os.path.dirname(__file__), "igdb_popularity.json")

# Cargar el JSON de ajustes si existe (prioridad sobre .env)
_settings = {}
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            _settings = json.load(f)
    except Exception:
        pass

# Asignación Dinámica: settings.json > env > default
HOST_USER = _settings.get("host_user", os.getenv("HOST_USER", "fydend"))
HOST_IP = os.getenv("HOST_IP", "172.18.0.1")
ROMS_PATH = _settings.get("roms_path", os.getenv("ROMS_PATH", "/mnt/DiscoHDD/RetroCloud-PatoLinux/Roms"))
PUID = os.getenv("PUID", "1000")
PGID = os.getenv("PGID", "1000")

TARGET_MONITOR = os.getenv("TARGET_MONITOR", "TV-STREAM")
HOST_MONITOR = os.getenv("HOST_MONITOR", "DP-1")
TARGET_WORKSPACE = os.getenv("TARGET_WORKSPACE", "10")

SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "/root/.ssh/id_ed25519")
