#!/usr/bin/env python3
import os
import urllib.request
import zipfile
import io
import re

cores_dir = os.path.expanduser("~/.config/retroarch/cores")
os.makedirs(cores_dir, exist_ok=True)

cores_to_download = [
    "mupen64plus_next_libretro.so.zip",   # N64
    "nestopia_libretro.so.zip",           # NES
    "genesis_plus_gx_libretro.so.zip",    # Sega Genesis / Mega Drive
    "gambatte_libretro.so.zip",           # Game Boy / Color
    "mgba_libretro.so.zip",               # Game Boy Advance
    "melonds_libretro.so.zip",             # Nintendo DS
    "pcsx_rearmed_libretro.so.zip"        # PS1 (ARM/x86_64 interpreter)
]

base_url = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/"

print("=== INSTALADOR AUTOMÁTICO DE CORES PARA RETROARCH ===")
print(f"Directorio de destino: {cores_dir}")

for core_zip in cores_to_download:
    url = base_url + core_zip
    core_name = core_zip.replace(".so.zip", "")
    print(f"\nDescargando core: {core_name}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            zip_data = response.read()
            
        print(f"Descomprimiendo {core_zip}...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            z.extractall(cores_dir)
        print(f"✓ ¡Core {core_name} instalado con éxito!")
    except Exception as e:
        print(f"⚠ Error descargando/instalando {core_name}: {e}")

# Ahora modificar retroarch.cfg para apuntar al directorio local de cores
config_path = os.path.expanduser("~/.config/retroarch/retroarch.cfg")
if os.path.exists(config_path):
    print("\nModificando retroarch.cfg para usar la carpeta de cores local...")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Reemplazar libretro_directory
    pattern = re.compile(r'^libretro_directory\s*=\s*".*"', re.MULTILINE)
    new_line = f'libretro_directory = "{cores_dir}"'
    if pattern.search(content):
        content = pattern.sub(new_line, content)
    else:
        content += f'\n{new_line}\n'

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ retroarch.cfg actualizado correctamente.")

print("\n=== ¡PROCESO DE CORES COMPLETADO! ===")
