from fastapi import APIRouter
import base64
from config import HOST_USER, HOST_IP
from services.ssh_helper import run_ssh_command
from routers.system import load_settings, aplicar_retroarch_ajustes

router = APIRouter()

@router.get("/steam/bigpicture")
def lanzar_steam_bigpicture():
    settings = load_settings()
    versatility = settings.get("versatility", {})
    target_workspace = versatility.get("target_workspace", "10")
    target_monitor = versatility.get("target_monitor", "TV-STREAM")
    host_monitor = versatility.get("host_monitor", "DP-1")
    
    env_str = (
        "export XDG_RUNTIME_DIR=/run/user/1000 && "
        "export HYPRLAND_INSTANCE_SIGNATURE=$(ls -1 $XDG_RUNTIME_DIR/hypr 2>/dev/null | head -n 1) && "
        "export SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1 && "
        "export DISPLAY=:0 && "
        f"export TARGET_MONITOR=\"{target_monitor}\" && "
        f"export TARGET_WORKSPACE=\"{target_workspace}\" && "
        f"export HOST_MONITOR=\"{host_monitor}\""
    )
    cmd = (
        f"{env_str} && "
        f"/home/fydend/Proyectos/RetroCloud-Patolinux/scripts/setup_virtual_display.sh && "
        f"hyprctl eval 'hl.dispatch(hl.dsp.exec_cmd([=[steam -gamepadui]=]))'"
    )
    try:
        resultado = run_ssh_command(cmd, use_bash=True)
        if resultado.returncode == 0:
            return {"estado": "OK", "mensaje": "Steam Big Picture lanzado con éxito."}
        else:
            return {"estado": "Error SSH", "detalle": resultado.stderr}
    except Exception as e:
        return {"estado": "Error Interno", "detalle": str(e)}

@router.get("/jugar")
def jugar_retroarch(core: str, rom_path: str, console: str = None):
    # Traducir la ruta interna del contenedor (/roms) a la ruta real del Host
    host_rom_path = rom_path.replace("/roms", "/mnt/DiscoHDD/RetroCloud-PatoLinux/Roms", 1)

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

    env_str = (
        "export DISPLAY=:0 && "
        "export XDG_RUNTIME_DIR=/run/user/1000 && "
        "export HYPRLAND_INSTANCE_SIGNATURE=$(ls -1 $XDG_RUNTIME_DIR/hypr 2>/dev/null | head -n 1) && "
        "export SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1 && "
        "export SDL_GAMECONTROLLER_IGNORE_DEVICES=0xbeef/0xdead && "
        "export SDL_VIDEODRIVER=x11 && "
        "export DISABLE_WAYLAND=1 && "
        "export PULSE_SERVER=unix:/run/user/1000/pulse/native && "
        "export PULSE_LATENCY_MSEC=30 && "
        "export PIPEWIRE_LATENCY=\"128/48000\" && "
        "export SDL_AUDIODRIVER=pulse && "
        f"export TARGET_MONITOR=\"{target_monitor}\" && "
        f"export TARGET_WORKSPACE=\"{target_workspace}\" && "
        f"export HOST_MONITOR=\"{host_monitor}\" && "
        f"export SDL_GAMECONTROLLERCONFIG=\"{sdl_config}\""
    )

    emulators_map = settings.get("emulators", {})
    mapped_emu = emulators_map.get(console, "retroarch") if console else "retroarch"

    # Si la consola tiene mapeado un emulador standalone o es uno sin soporte en retroarch
    if mapped_emu == "pcsx2" or (core == "pcsx2" and mapped_emu != "retroarch"):
        emu_cmd = f'pcsx2-qt -batch -fullscreen -- "{host_rom_path}"'
    elif mapped_emu == "dolphin" or (core == "dolphin" and mapped_emu != "retroarch"):
        emu_cmd = f'dolphin-emu -b -e "{host_rom_path}"'
    elif mapped_emu == "duckstation" or (console == "ps1" and mapped_emu == "duckstation"):
        emu_cmd = f'duckstation -fullscreen -- "{host_rom_path}"'
    elif mapped_emu == "ppsspp" or (core == "ppsspp" and mapped_emu != "retroarch"):
        emu_cmd = f'PPSSPPSDL --fullscreen "{host_rom_path}"'
    elif mapped_emu == "xemu" or (core == "xemu" and mapped_emu != "retroarch"):
        if host_rom_path.endswith(".zip"):
            host_rom_path = host_rom_path.replace(".zip", ".iso")
        emu_cmd = f'xemu -dvd_path "{host_rom_path}"'
    elif core == "rpcs3" or mapped_emu == "rpcs3":
        if host_rom_path.endswith(".zip"):
            host_rom_path = host_rom_path.replace(".zip", "")
        emu_cmd = f'rpcs3 --no-gui --fullscreen "{host_rom_path}"'
    elif core == "xenia" or mapped_emu == "xenia":
        env_str += f" && export STEAM_COMPAT_CLIENT_INSTALL_PATH=\"/home/{HOST_USER}/.local/share/Steam\" && export STEAM_COMPAT_DATA_PATH=\"/home/{HOST_USER}/.local/share/Xenia/proton_prefix\" && export STEAM_COMPAT_APP_ID=0 && export WINE_WM_CLASS=\"xenia\""
        emu_cmd = f'"/home/{HOST_USER}/.local/share/Steam/steamapps/common/Proton - Experimental/proton" run "/home/{HOST_USER}/.local/share/Xenia/xenia_canary.exe" "{host_rom_path}"'
    else:
        # Por defecto usar RetroArch con el Core correcto
        actual_core = core
        if mapped_emu == "retroarch" and console:
            from services.catalog_service import CORE_MAP
            actual_core = CORE_MAP.get(console, core)
        
        # Resolver ruta del core física en el host CachyOS
        core_so = actual_core if actual_core.endswith(".so") else f"{actual_core}_libretro.so"
        user_core_path = f"/home/{HOST_USER}/.config/retroarch/cores/{core_so}"
        
        emu_cmd = f'retroarch -L "{user_core_path}" "{host_rom_path}"'

    launcher_content = (
        "#!/usr/bin/env bash\n"
        f"{env_str}\n"
        f"mkdir -p \"/home/{HOST_USER}/.local/share/Xenia/proton_prefix\"\n"
        f"exec {emu_cmd}\n"
    )
    launcher_b64 = base64.b64encode(launcher_content.encode('utf-8')).decode('utf-8')

    cmd_str = (
        f"{env_str} && "
        f"echo '{launcher_b64}' | base64 -d > /tmp/retrocloud_launch.sh && "
        f"chmod +x /tmp/retrocloud_launch.sh && "
        f"/home/{HOST_USER}/Proyectos/RetroCloud-Patolinux/scripts/setup_virtual_display.sh && "
        f"hyprctl eval 'hl.dispatch(hl.dsp.exec_cmd([=[/tmp/retrocloud_launch.sh]=]))'"
    )

    try:
        resultado = run_ssh_command(cmd_str, use_bash=True)
        if resultado.returncode == 0:
            return {"estado": "OK", "mensaje": "¡Juego lanzado en CachyOS!"}
        else:
            return {"estado": "Error SSH", "detalle": resultado.stderr}
    except Exception as e:
        return {"estado": "Error Interno", "detalle": str(e)}
