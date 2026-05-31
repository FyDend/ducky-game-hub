import urllib.request
import urllib.parse
import re
import json
import os
import time
import html

CONSOLES = {
    "snes": "No-Intro/Nintendo - Super Nintendo Entertainment System",
    "nes": "No-Intro/Nintendo - Nintendo Entertainment System (Headered)",
    "n64": "No-Intro/Nintendo - Nintendo 64 (BigEndian)",
    "gb": "No-Intro/Nintendo - Game Boy",
    "gbc": "No-Intro/Nintendo - Game Boy Color",
    "gba": "No-Intro/Nintendo - Game Boy Advance",
    "megadrive": "No-Intro/Sega - Mega Drive - Genesis",
    "mastersystem": "No-Intro/Sega - Master System - Mark III",
    "gamegear": "No-Intro/Sega - Game Gear",
    "nds": "No-Intro/Nintendo - Nintendo DS (Decrypted)",
    "ps1": "Redump/Sony - PlayStation",
    "ps2": "Redump/Sony - PlayStation 2",
    "ps3": "Redump/Sony - PlayStation 3",
    "psp": "Redump/Sony - PlayStation Portable",
    "gamecube": "Redump/Nintendo - GameCube - NKit RVZ [zstd-19-128k]",
    "xbox": "Redump/Microsoft - Xbox",
    "xbox360": "Redump/Microsoft - Xbox 360",
    "wii": "Redump/Nintendo - Wii - NKit RVZ [zstd-19-128k]"
}

BASE_URL = "https://minerva-archive.org/browse/"

def get_libretro_cover(console, title):
    mapping = {
        "snes": "Nintendo - Super Nintendo Entertainment System",
        "nes": "Nintendo - Nintendo Entertainment System",
        "n64": "Nintendo - Nintendo 64",
        "gb": "Nintendo - Game Boy",
        "gbc": "Nintendo - Game Boy Color",
        "gba": "Nintendo - Game Boy Advance",
        "megadrive": "Sega - Mega Drive - Genesis",
        "mastersystem": "Sega - Master System - Mark III",
        "gamegear": "Sega - Game Gear",
        "nds": "Nintendo - Nintendo DS",
        "ps1": "Sony - PlayStation",
        "ps2": "Sony - PlayStation 2",
        "ps3": "Sony - PlayStation 3",
        "psp": "Sony - PlayStation Portable",
        "gamecube": "Nintendo - GameCube",
        "xbox": "Microsoft - Xbox",
        "xbox360": "Microsoft - Xbox 360",
        "wii": "Nintendo - Wii"
    }
    system_name = mapping.get(console, "")
    # Libretro sometimes uses _ instead of &
    clean_retro_title = title.replace("&", "_")
    return f"https://thumbnails.libretro.com/{urllib.parse.quote(system_name)}/Named_Boxarts/{urllib.parse.quote(clean_retro_title)}.png"

def clean_title(title: str) -> str:
    """Removes (USA), (Europe), [b], etc. to get a clean base name."""
    cleaned = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    return cleaned.strip()

games_db = {}

# Palabras clave para filtrar discos de instalación/demos/basura
JUNK_FILTERS = ["installation disc", "demo disc", "update disc", "bonus disc", "kiosk", "sampler", "preview", "promo", "magazine", "interactive sampler"]

for console_id, console_path in CONSOLES.items():
    print(f"Scraping {console_id}...")
    url = BASE_URL + urllib.parse.quote(console_path) + "/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RetroCloud/1.0"})
    
    try:
        html_content = urllib.request.urlopen(req).read().decode("utf-8")
        
        # Regex captura la URL del archivo y el texto del tamaño en la siguiente etiqueta <span>
        matches = re.findall(r'href="([^"]+\.(?:zip|chd|7z|iso|rvz))"[^>]*>.*?</a>\s*<span>(.*?)</span>', html_content)
        print(f"  Found {len(matches)} games.")
        
        for link, size_str in matches:
            # Primero decodificamos el HTML (&#39; -> ')
            link_unescaped = html.unescape(link)
            
            # Extract real filename from query parameter
            parsed_link = urllib.parse.urlparse(link_unescaped)
            name_param = urllib.parse.parse_qs(parsed_link.query).get('name', [''])[0]
            if not name_param:
                filename = urllib.parse.unquote(link_unescaped.split("/")[-1])
            else:
                filename = os.path.basename(name_param)
            
            # Quitar la extension (.zip, .chd, etc) para el titulo
            full_title = os.path.splitext(filename)[0]
            
            # Filtro de basura
            lower_title = full_title.lower()
            if any(junk in lower_title for junk in JUNK_FILTERS):
                continue

            base_name = clean_title(full_title)
            if not base_name:
                base_name = full_title
                
            download_url = "https://minerva-archive.org" + link_unescaped
            
            if base_name not in games_db:
                games_db[base_name] = {
                    "title": base_name,
                    "console": console_id,
                    "image": get_libretro_cover(console_id, full_title),
                    "versions": []
                }
            
            if "USA" in full_title or "Europe" in full_title or "Japan" in full_title:
                games_db[base_name]["image"] = get_libretro_cover(console_id, full_title)
                
            version_entry = {
                "versionName": full_title,
                "downloadUrl": download_url,
                "filename": filename,
                "size": size_str.strip()
            }
            games_db[base_name]["versions"].append(version_entry)
            
    except Exception as e:
        print(f"Failed to scrape {console_id}: {e}")
        
    time.sleep(1)

# Sort versions and filter out massive DB bloat (Optional)
print(f"Total unique games compiled: {len(games_db)}")

# Save to json
db_path = os.path.join(os.path.dirname(__file__), "games_db.json")
with open(db_path, "w", encoding="utf-8") as f:
    json.dump(games_db, f, ensure_ascii=False)
    
print("Saved games_db.json successfully!")
