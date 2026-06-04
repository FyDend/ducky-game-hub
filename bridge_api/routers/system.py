from fastapi import APIRouter, BackgroundTasks
import os
import json
import re
import subprocess
from config import SETTINGS_FILE

router = APIRouter()

@router.get("/health")
def health_check():
    return {"estado": "OK"}


def load_settings():
    settings = {
        "video": {
            "crt_shader": False,
            "bilinear_filtering": True,
            "aspect_ratio": "auto",
            "show_fps": False
        },
        "versatility": {
            "target_workspace": "1",
            "target_monitor": "DP-1",
            "host_monitor": "DP-1"
        },
        "audio": {
            "selected_sink": ""
        },
        "controls": {
            "profile": "gamepad",
            "gamepad": {
                "a": "b0", "b": "b1", "x": "b2", "y": "b3",
                "leftshoulder": "b4", "rightshoulder": "b5", "lefttrigger": "b6", "righttrigger": "b7",
                "back": "b10", "start": "b11", "guide": "b12",
                "leftstick": "b8", "rightstick": "b9",
                "dpup": "h0.1", "dpdown": "h0.4", "dpleft": "h0.8", "dpright": "h0.2",
                "leftx": "a0", "lefty": "a1", "rightx": "a2", "righty": "a5"
            },
            "gamepad2": {
                "a": "b0", "b": "b1", "x": "b2", "y": "b3",
                "leftshoulder": "b4", "rightshoulder": "b5", "lefttrigger": "b6", "righttrigger": "b7",
                "back": "b10", "start": "b11", "guide": "b12",
                "leftstick": "b8", "rightstick": "b9",
                "dpup": "h0.1", "dpdown": "h0.4", "dpleft": "h0.8", "dpright": "h0.2",
                "leftx": "a0", "lefty": "a1", "rightx": "a2", "righty": "a5"
            },
            "gamepad3": {
                "a": "b0", "b": "b1", "x": "b2", "y": "b3",
                "leftshoulder": "b4", "rightshoulder": "b5", "lefttrigger": "b6", "righttrigger": "b7",
                "back": "b10", "start": "b11", "guide": "b12",
                "leftstick": "b8", "rightstick": "b9",
                "dpup": "h0.1", "dpdown": "h0.4", "dpleft": "h0.8", "dpright": "h0.2",
                "leftx": "a0", "lefty": "a1", "rightx": "a2", "righty": "a5"
            },
            "gamepad4": {
                "a": "b0", "b": "b1", "x": "b2", "y": "b3",
                "leftshoulder": "b4", "rightshoulder": "b5", "lefttrigger": "b6", "righttrigger": "b7",
                "back": "b10", "start": "b11", "guide": "b12",
                "leftstick": "b8", "rightstick": "b9",
                "dpup": "h0.1", "dpdown": "h0.4", "dpleft": "h0.8", "dpright": "h0.2",
                "leftx": "a0", "lefty": "a1", "rightx": "a2", "righty": "a5"
            },
            "keyboard": {
                "up": "up",
                "down": "down",
                "left": "left",
                "right": "right",
                "a": "x",
                "b": "z",
                "x": "s",
                "y": "a",
                "l1": "q",
                "r1": "w",
                "l2": "e",
                "r2": "r",
                "select": "shift",
                "start": "enter",
                "guide": "escape"
            }
        },
        "first_run": True,
        "screen_mode": "single",
        "emulators": {
            "ps1": "retroarch",
            "ps2": "pcsx2",
            "gamecube": "dolphin",
            "wii": "dolphin",
            "xbox": "xemu",
            "psp": "ppsspp",
            "default": "retroarch"
        }
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if isinstance(v, dict) and k in settings:
                        settings[k].update(v)
                    else:
                        settings[k] = v
        except Exception as e:
            print(f"[API] Error cargando settings: {e}", flush=True)
    return settings

def aplicar_retroarch_ajustes(ajustes: dict):
    # En el contenedor, el archivo de configuración está en /root/.config/retroarch/retroarch.cfg
    config_path = os.path.expanduser("~/.config/retroarch/retroarch.cfg")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# RetroArch config\n")
            
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        video = ajustes.get("video", {})
        
        def set_option(key, value):
            nonlocal content
            pattern = re.compile(rf'^{key}\s*=.*$', re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f'{key} = "{value}"', content)
            else:
                content += f'\n{key} = "{value}"\n'
                
        if "crt_shader" in video:
            shader_val = "true" if video["crt_shader"] else "false"
            set_option("video_shader_enable", shader_val)
            if video["crt_shader"]:
                posibles_shaders = [
                    "/usr/share/libretro/shaders/shaders_glsl/crt/crt-pi.glslp",
                    os.path.expanduser("~/.config/retroarch/shaders/shaders_glsl/crt/crt-pi.glslp"),
                    "/usr/share/libretro/shaders/shaders_glsl/crt/crt-lonescreen.glslp"
                ]
                shader_path = posibles_shaders[0]
                for path in posibles_shaders:
                    if os.path.exists(path):
                        shader_path = path
                        break
                set_option("video_shader", shader_path)
                
        if "bilinear_filtering" in video:
            smooth_val = "true" if video["bilinear_filtering"] else "false"
            set_option("video_smooth", smooth_val)
            
        if "show_fps" in video:
            fps_val = "true" if video["show_fps"] else "false"
            set_option("fps_show", fps_val)
            
        if "aspect_ratio" in video:
            ar = video["aspect_ratio"]
            if ar == "16:9":
                set_option("aspect_ratio_index", "1")
            elif ar == "4:3":
                set_option("aspect_ratio_index", "0")
            else:
                set_option("aspect_ratio_index", "21")
                
        controls = ajustes.get("controls", {})
        for player_num in range(1, 5):
            player_profile = controls.get(f"player{player_num}_profile", "gamepad" if player_num == 1 else f"gamepad{player_num}")
            if player_profile == "keyboard":
                kb = controls.get("keyboard", {})
                kb_map = {
                    "up": f"input_player{player_num}_up",
                    "down": f"input_player{player_num}_down",
                    "left": f"input_player{player_num}_left",
                    "right": f"input_player{player_num}_right",
                    "a": f"input_player{player_num}_a",
                    "b": f"input_player{player_num}_b",
                    "x": f"input_player{player_num}_x",
                    "y": f"input_player{player_num}_y",
                    "l1": f"input_player{player_num}_l",
                    "r1": f"input_player{player_num}_r",
                    "l2": f"input_player{player_num}_l2",
                    "r2": f"input_player{player_num}_r2",
                    "select": f"input_player{player_num}_select",
                    "start": f"input_player{player_num}_start",
                    "guide": f"input_player{player_num}_menu_toggle"
                }
                for key_name, cfg_name in kb_map.items():
                    if key_name in kb:
                        set_option(cfg_name, kb[key_name])
                    
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[API] RetroArch config actualizada con éxito localmente.", flush=True)
    except Exception as e:
        print(f"[API] Error aplicando ajustes locales de RetroArch: {e}", flush=True)

@router.get("/foco")
def enfocar_browser():
    return {"estado": "OK"}

@router.get("/ajustes")
def obtener_ajustes():
    from config import HOST_USER, HOST_IP
    ajustes = load_settings()
    ajustes["host_user"] = HOST_USER
    ajustes["host_ip"] = HOST_IP
    return ajustes

@router.post("/ajustes")
def guardar_ajustes(ajustes: dict, background_tasks: BackgroundTasks):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, indent=2)
        aplicar_retroarch_ajustes(ajustes)
        
        # Aplicar workspaces de Hyprland localmente
        def _aplicar_pantalla():
            try:
                from services.hyprland_helper import setup_virtual_display_hyprland
                versatility = ajustes.get("versatility", {})
                target_workspace = versatility.get("target_workspace", "10")
                target_monitor = versatility.get("target_monitor", "TV-STREAM")
                host_monitor = versatility.get("host_monitor", "DP-1")
                setup_virtual_display_hyprland(target_monitor, target_workspace, host_monitor)
            except Exception as e:
                print(f"[API] Error configurando pantalla virtual: {e}", flush=True)
                
        background_tasks.add_task(_aplicar_pantalla)
        return {"estado": "OK", "mensaje": "Ajustes guardados y aplicados correctamente."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/pantallas")
def obtener_pantallas():
    try:
        from services.hyprland_helper import send_hyprland_cmd
        monitors_json = send_hyprland_cmd("j/monitors")
        monitors_data = json.loads(monitors_json)
        names = [m["name"] for m in monitors_data]
        if "TV-STREAM" not in names:
            names.append("TV-STREAM")
        return {"estado": "OK", "pantallas": names}
    except Exception as e:
        print(f"[API] Error obteniendo pantallas via Hyprland socket: {e}", flush=True)
        return {"estado": "OK", "pantallas": ["DP-1", "HDMI-A-1", "TV-STREAM"]}

@router.get("/explorar")
def explorar_directorios(ruta: str = None):
    """Lista las subcarpetas de una ruta en el contenedor para el explorador de archivos Couch Mode."""
    try:
        if not ruta or not os.path.exists(ruta):
            ruta = "/roms"
        
        ruta = os.path.abspath(ruta)
        directorios = []
        for item in os.listdir(ruta):
            full_path = os.path.join(ruta, item)
            if os.path.isdir(full_path) and not item.startswith("."):
                directorios.append(item)
                
        directorios.sort()
        padre = os.path.dirname(ruta) if ruta != "/" else "/"
        return {
            "estado": "OK",
            "ruta_actual": ruta,
            "padre": padre,
            "directorios": directorios
        }
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/audio/dispositivos")
def obtener_dispositivos_audio():
    try:
        resultado = subprocess.run(["pactl", "list", "sinks"], capture_output=True, text=True, timeout=5)
        if resultado.returncode != 0:
            return {"estado": "Error", "detalle": resultado.stderr}
            
        dispositivos = []
        current_name = None
        for line in resultado.stdout.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("Name:"):
                current_name = line_strip.split("Name:", 1)[1].strip()
            elif line_strip.startswith("Description:") and current_name:
                desc = line_strip.split("Description:", 1)[1].strip()
                dispositivos.append({
                    "name": current_name,
                    "description": desc.replace('"', '').replace("'", "")
                })
                current_name = None
                
        return {"estado": "OK", "dispositivos": dispositivos}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/audio/seleccionar")
def seleccionar_dispositivo_audio(sink_name: str):
    try:
        cmd = ["pactl", "set-default-sink", sink_name]
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if resultado.returncode != 0:
            return {"estado": "Error", "detalle": resultado.stderr}
        return {"estado": "OK", "mensaje": f"Dispositivo cambiado a {sink_name}"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/estado_emulador")
def estado_emulador():
    try:
        resultado = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, timeout=5)
        if resultado.returncode != 0:
            return {"activo": False, "error": resultado.stderr}
            
        process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "xenia_canary", "xenia-canary-bin", "xenia_canary.exe", "xenia_canary.ex", "xenia", "steam"]
        
        for line in resultado.stdout.splitlines():
            line_lower = line.lower()
            if any(x in line_lower for x in ["ps -eo", "grep"]):
                continue
                
            for name in process_names:
                if name in line_lower:
                    print(f"[API] Detectado emulador activo: {line.strip()}", flush=True)
                    return {"activo": True}
                    
        return {"activo": False}
    except Exception as e:
        return {"activo": False, "error": str(e)}

@router.post("/cerrar_emulador")
def cerrar_emulador():
    """Mata los procesos de emuladores/Steam locales en el contenedor."""
    process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "PPSSPPSDL", "duckstation", "steam"]
    for proc in process_names:
        try:
            subprocess.run(["pkill", "-f", proc])
        except Exception:
            pass
    return {"estado": "OK", "mensaje": "Señal de cierre enviada localmente."}

@router.post("/pausar_emulador")
def pausar_emulador():
    """Pausa temporalmente los procesos de emuladores y devuelve el foco a RetroCloud."""
    process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "PPSSPPSDL", "duckstation", "xenia", "xenia_canary", "xenia_canary.exe", "steam"]
    for proc in process_names:
        try:
            subprocess.run(["pkill", "-STOP", "-f", proc])
        except Exception:
            pass
            
    # Devuelve el foco a la ventana de la UI en Hyprland
    try:
        from services.hyprland_helper import send_hyprland_cmd
        send_hyprland_cmd("eval hl.dispatch(hl.dsp.focus({ window = 'class:ducky-game-hub' }))")
        send_hyprland_cmd("eval hl.dispatch(hl.dsp.focus({ window = 'title:.*Ducky Game Hub.*' }))")
    except Exception as e:
        print(f"[API] Error de foco al pausar emulador: {e}", flush=True)
        
    return {"estado": "OK", "mensaje": "Emulador pausado y foco devuelto a RetroCloud."}

@router.post("/reanudar_emulador")
def reanudar_emulador():
    """Reanuda los procesos de emuladores previamente pausados."""
    process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "PPSSPPSDL", "duckstation", "xenia", "xenia_canary", "xenia_canary.exe", "steam"]
    for proc in process_names:
        try:
            subprocess.run(["pkill", "-CONT", "-f", proc])
        except Exception:
            pass
            
    # Intentar enfocar el emulador reanudado en Hyprland
    classes = [
        "class:retroarch",
        "class:pcsx2",
        "class:dolphin",
        "class:rpcs3",
        "class:xemu",
        "class:xenia",
        "class:duckstation",
        "class:steam_app_.*",
        "class:steam"
    ]
    try:
        from services.hyprland_helper import send_hyprland_cmd
        for cls in classes:
            send_hyprland_cmd(f"eval hl.dispatch(hl.dsp.focus({{ window = '{cls}' }}))")
    except Exception as e:
        print(f"[API] Error de foco al reanudar emulador: {e}", flush=True)
        
    return {"estado": "OK", "mensaje": "Emulador reanudado."}


@router.get("/ssh/test")
def test_ssh():
    # En modo Zero-Footprint, validamos la conectividad al socket de Hyprland local
    try:
        from services.hyprland_helper import get_hyprland_socket
        socket_path = get_hyprland_socket()
        if os.path.exists(socket_path):
            return {"estado": "OK", "mensaje": "Conexión a Hyprland socket exitosa."}
        else:
            return {"estado": "Error", "detalle": "Socket de Hyprland no encontrado."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/ajustes/wizard-complete")
def wizard_complete(ajustes: dict, background_tasks: BackgroundTasks):
    try:
        ajustes["first_run"] = False
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, indent=2)
        aplicar_retroarch_ajustes(ajustes)
        
        # Aplicar workspaces de Hyprland localmente
        def _aplicar_pantalla():
            try:
                from services.hyprland_helper import setup_virtual_display_hyprland
                versatility = ajustes.get("versatility", {})
                target_workspace = versatility.get("target_workspace", "10")
                target_monitor = versatility.get("target_monitor", "TV-STREAM")
                host_monitor = versatility.get("host_monitor", "DP-1")
                setup_virtual_display_hyprland(target_monitor, target_workspace, host_monitor)
            except Exception as e:
                print(f"[API] Error configurando pantalla virtual: {e}", flush=True)
                
        background_tasks.add_task(_aplicar_pantalla)
        return {"estado": "OK", "mensaje": "Setup inicial completado."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}


@router.post("/salir")
def salir_retrocloud(background_tasks: BackgroundTasks):
    """Cierra la aplicación RetroCloud en el host cerrando la ventana en Hyprland."""
    def _cerrar():
        import time
        time.sleep(0.5)
        try:
            from services.hyprland_helper import send_hyprland_cmd
            send_hyprland_cmd("eval hl.dispatch(hl.dsp.window.close({ window = 'class:ducky-game-hub' }))")
        except Exception as e:
            print(f"[API] Error cerrando aplicación: {e}", flush=True)
    background_tasks.add_task(_cerrar)
    return {"estado": "OK", "mensaje": "Cerrando RetroCloud..."}
