import os

# Configuración básica desde variables de entorno
HOST_USER = os.getenv("HOST_USER", "fydend")
HOST_IP = os.getenv("HOST_IP", "172.18.0.1")
ROMS_PATH = os.getenv("ROMS_PATH", "/mnt/DiscoHDD/RetroCloud-PatoLinux/Roms")
PUID = os.getenv("PUID", "1000")
PGID = os.getenv("PGID", "1000")

TARGET_MONITOR = os.getenv("TARGET_MONITOR", "TV-STREAM")
HOST_MONITOR = os.getenv("HOST_MONITOR", "DP-1")
TARGET_WORKSPACE = os.getenv("TARGET_WORKSPACE", "10")

SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "/root/.ssh/id_ed25519")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "games_db.json")
IGDB_PATH = os.path.join(os.path.dirname(__file__), "igdb_popularity.json")

SAVE_SYNC_HOST = os.getenv("SAVE_SYNC_HOST", "")
SAVE_SYNC_USER = os.getenv("SAVE_SYNC_USER", "")
SAVE_SYNC_PATH = os.getenv("SAVE_SYNC_PATH", "/mnt/saves/retrocloud")
