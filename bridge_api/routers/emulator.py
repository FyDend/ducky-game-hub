from fastapi import APIRouter
import os
import subprocess
from routers.system import load_settings, aplicar_retroarch_ajustes
from services.hyprland_helper import setup_virtual_display_hyprland

router = APIRouter()

def resolve_core_path(core_so: str) -> str:
    paths_to_check = [
        f"/root/.config/retroarch/cores/{core_so}",
        f"/usr/lib/x86_64-linux-gnu/libretro/{core_so}",
        f"/usr/lib/libretro/{core_so}"
    ]
    for path in paths_to_check:
        if os.path.exists(path):
            return path
    return f"/root/.config/retroarch/cores/{core_so}" # Fallback

@router.get("/steam/bigpicture")
def lanzar_steam_bigpicture():
    settings = load_settings()
    versatility = settings.get("versatility", {})
    target_workspace = versatility.get("target_workspace", "10")
    target_monitor = versatility.get("target_monitor", "TV-STREAM")
    host_monitor = versatility.get("host_monitor", "DP-1")
    
    try:
        setup_virtual_display_hyprland(target_monitor, target_workspace, host_monitor)
    except Exception as e:
        print(f"[Emulator Router] Hyprland display setup failed: {e}", flush=True)
        
    env = os.environ.copy()
    env["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    env["DISPLAY"] = ":0"
    
    try:
        subprocess.Popen(["steam", "-gamepadui"], env=env)
        return {"estado": "OK", "mensaje": "Steam Big Picture lanzado con éxito."}
    except Exception as e:
        return {"estado": "Error Interno", "detalle": str(e)}

@router.get("/jugar")
def jugar_retroarch(core: str, rom_path: str, console: str = None):
    # En modo Zero-Footprint con emuladores corriendo dentro del contenedor,
    # abrimos la ruta de la ROM directamente (/roms) sin traducir al host
    settings = load_settings()
    aplicar_retroarch_ajustes(settings)
    
    versatility = settings.get("versatility", {})
    target_workspace = versatility.get("target_workspace", "10")
    target_monitor = versatility.get("target_monitor", "TV-STREAM")
    host_monitor = versatility.get("host_monitor", "DP-1")
    
    controls = settings.get("controls", {})
    gp_configs = []
    
    # Gamepad 1 (gamepad)
    gp = controls.get("gamepad", {})
    if gp:
        gp_parts = [f"{sdl_name}:{physical}" for sdl_name, physical in gp.items()]
        gp_configs.append(f"0500a5d049190000b08cbd08fd7f0000,Gamepad1,platform:Linux,{','.join(gp_parts)},")
        
    # Gamepad 2
    gp2 = controls.get("gamepad2", {})
    if gp2:
        gp2_parts = [f"{sdl_name}:{physical}" for sdl_name, physical in gp2.items()]
        gp_configs.append(f"0500a5d049190000b08cbd08fd7f0001,Gamepad2,platform:Linux,{','.join(gp2_parts)},")
        
    # Gamepad 3
    gp3 = controls.get("gamepad3", {})
    if gp3:
        gp3_parts = [f"{sdl_name}:{physical}" for sdl_name, physical in gp3.items()]
        gp_configs.append(f"0500a5d049190000b08cbd08fd7f0002,Gamepad3,platform:Linux,{','.join(gp3_parts)},")
        
    # Gamepad 4
    gp4 = controls.get("gamepad4", {})
    if gp4:
        gp4_parts = [f"{sdl_name}:{physical}" for sdl_name, physical in gp4.items()]
        gp_configs.append(f"0500a5d049190000b08cbd08fd7f0003,Gamepad4,platform:Linux,{','.join(gp4_parts)},")
        
    sdl_config = "\n".join(gp_configs)

    puid = os.getenv("PUID", "1000")
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    env["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    env["SDL_GAMECONTROLLER_IGNORE_DEVICES"] = "0xbeef/0xdead"
    env["SDL_VIDEODRIVER"] = "x11"
    env["DISABLE_WAYLAND"] = "1"
    env["PULSE_SERVER"] = f"unix:/run/user/{puid}/pulse/native"
    env["PULSE_LATENCY_MSEC"] = "30"
    env["PIPEWIRE_LATENCY"] = "128/48000"
    env["SDL_AUDIODRIVER"] = "pulse"
    env["SDL_GAMECONTROLLERCONFIG"] = sdl_config

    emulators_map = settings.get("emulators", {})
    mapped_emu = emulators_map.get(console, "retroarch") if console else "retroarch"

    if mapped_emu == "pcsx2" or (core == "pcsx2" and mapped_emu != "retroarch"):
        emu_cmd = ["pcsx2-qt", "-batch", "-fullscreen", "--", rom_path]
    elif mapped_emu == "dolphin" or (core == "dolphin" and mapped_emu != "retroarch"):
        emu_cmd = ["dolphin-emu", "-b", "-e", rom_path]
    elif mapped_emu == "duckstation" or (console == "ps1" and mapped_emu == "duckstation"):
        emu_cmd = ["duckstation", "-fullscreen", "--", rom_path]
    elif mapped_emu == "ppsspp" or (core == "ppsspp" and mapped_emu != "retroarch"):
        emu_cmd = ["PPSSPPSDL", "--fullscreen", rom_path]
    elif mapped_emu == "xemu" or (core == "xemu" and mapped_emu != "retroarch"):
        if rom_path.endswith(".zip"):
            rom_path = rom_path.replace(".zip", ".iso")
        emu_cmd = ["xemu", "-dvd_path", rom_path]
    elif core == "rpcs3" or mapped_emu == "rpcs3":
        if rom_path.endswith(".zip"):
            rom_path = rom_path.replace(".zip", "")
        emu_cmd = ["rpcs3", "--no-gui", "--fullscreen", rom_path]
    else:
        # Por defecto usar RetroArch con el Core correcto
        actual_core = core
        if mapped_emu == "retroarch" and console:
            from services.catalog_service import CORE_MAP
            actual_core = CORE_MAP.get(console, core)
        
        core_so = actual_core if actual_core.endswith(".so") else f"{actual_core}_libretro.so"
        core_path = resolve_core_path(core_so)
        emu_cmd = ["retroarch", "-L", core_path, rom_path]

    try:
        # Configurar la pantalla virtual en Hyprland antes de lanzar el emulador
        setup_virtual_display_hyprland(target_monitor, target_workspace, host_monitor)
    except Exception as e:
        print(f"[Emulator Router] Hyprland display setup failed: {e}", flush=True)

    try:
        print(f"[Emulator Router] Launching emu process locally: {emu_cmd}", flush=True)
        subprocess.Popen(emu_cmd, env=env)
        return {"estado": "OK", "mensaje": "¡Juego lanzado en el contenedor!"}
    except Exception as e:
        return {"estado": "Error Interno", "detalle": str(e)}
