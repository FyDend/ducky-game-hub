from fastapi import APIRouter, BackgroundTasks
import os
import json
import re
import subprocess
from config import SETTINGS_FILE, HOST_USER, HOST_IP
from services.ssh_helper import run_ssh_command

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
    from services.ssh_helper import run_ssh_command
    import base64
    import json
    
    ajustes_json = json.dumps(ajustes)
    script_content = f"""
import os, re, json
config_path = os.path.expanduser("~/.config/retroarch/retroarch.cfg")
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    ajustes = json.loads(r'''{ajustes_json}''')
    video = ajustes.get("video", {{}})
    
    def set_option(key, value):
        global content
        pattern = re.compile(rf'^{{key}}\\s*=.*$', re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f'{{key}} = "{{value}}"', content)
        else:
            content += f'\\n{{key}} = "{{value}}"\\n'
            
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
            
    controls = ajustes.get("controls", {{}})
    for player_num in range(1, 5):
        player_profile = controls.get(f"player{{player_num}}_profile", "gamepad" if player_num == 1 else f"gamepad{{player_num}}")
        if player_profile == "keyboard":
            kb = controls.get("keyboard", {{}})
            kb_map = {{
                "up": f"input_player{{player_num}}_up",
                "down": f"input_player{{player_num}}_down",
                "left": f"input_player{{player_num}}_left",
                "right": f"input_player{{player_num}}_right",
                "a": f"input_player{{player_num}}_a",
                "b": f"input_player{{player_num}}_b",
                "x": f"input_player{{player_num}}_x",
                "y": f"input_player{{player_num}}_y",
                "l1": f"input_player{{player_num}}_l",
                "r1": f"input_player{{player_num}}_r",
                "l2": f"input_player{{player_num}}_l2",
                "r2": f"input_player{{player_num}}_r2",
                "select": f"input_player{{player_num}}_select",
                "start": f"input_player{{player_num}}_start",
                "guide": f"input_player{{player_num}}_menu_toggle"
            }}
            for key_name, cfg_name in kb_map.items():
                if key_name in kb:
                    set_option(cfg_name, kb[key_name])
                
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS")
else:
    print("CONFIG_NOT_FOUND")
"""
    try:
        b64_script = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
        cmd = f"echo '{b64_script}' | base64 -d > /tmp/retroarch_sync.py && python /tmp/retroarch_sync.py && rm /tmp/retroarch_sync.py"
        resultado = run_ssh_command(cmd, use_bash=True)
        if resultado.returncode == 0:
            output = resultado.stdout.strip()
            if "SUCCESS" in output:
                print("[API] RetroArch config actualizada con éxito en el HOST.", flush=True)
            else:
                print(f"[API] Warning al aplicar ajustes en HOST: {output}", flush=True)
        else:
            print(f"[API] Error ejecutando script de sync en HOST: {resultado.stderr}", flush=True)
    except Exception as e:
        print(f"[API] Error de SSH aplicando ajustes de RetroArch: {e}", flush=True)

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
        
        # Aplicar workspaces de Hyprland sobre el host en segundo plano
        def _aplicar_pantalla():
            run_ssh_command("/home/fydend/Proyectos/RetroCloud-Patolinux/scripts/setup_virtual_display.sh", timeout=10)
        background_tasks.add_task(_aplicar_pantalla)
        
        return {"estado": "OK", "mensaje": "Ajustes guardados y aplicados correctamente."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/pantallas")
def obtener_pantallas():
    try:
        resultado = run_ssh_command("hyprctl monitors -j", timeout=5)
        if resultado.returncode == 0:
            monitors_data = json.loads(resultado.stdout)
            names = [m["name"] for m in monitors_data]
            if "TV-STREAM" not in names:
                names.append("TV-STREAM")
            return {"estado": "OK", "pantallas": names}
        else:
            return {"estado": "OK", "pantallas": ["DP-1", "HDMI-A-1", "TV-STREAM"]}
    except Exception:
        return {"estado": "OK", "pantallas": ["DP-1", "HDMI-A-1", "TV-STREAM"]}

@router.get("/explorar")
def explorar_directorios(ruta: str = None):
    """Lista las subcarpetas de una ruta en el host para el explorador de archivos Couch Mode."""
    try:
        from services.ssh_helper import run_ssh_command
        import json
        import base64
        import os

        # Script a ejecutar en el HOST via SSH
        script = f"""
import os, json
ruta = {repr(ruta)}
if not ruta:
    ruta = os.path.expanduser("~")
ruta = os.path.expanduser(ruta)
if not os.path.exists(ruta) or not os.path.isdir(ruta):
    ruta = os.path.expanduser("~")
ruta = os.path.abspath(ruta)

directorios = []
try:
    for item in os.listdir(ruta):
        full_path = os.path.join(ruta, item)
        try:
            if os.path.isdir(full_path) and not item.startswith("."):
                directorios.append(item)
        except Exception:
            pass
    directorios.sort()
except Exception:
    pass

padre = os.path.dirname(ruta) if ruta != "/" else "/"
print(json.dumps({{
    "estado": "OK",
    "ruta_actual": ruta,
    "padre": padre,
    "directorios": directorios
}}))
"""
        b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
        cmd = f"echo '{b64_script}' | base64 -d | python3"
        resultado = run_ssh_command(cmd, use_bash=True)
        if resultado.returncode == 0:
            return json.loads(resultado.stdout)
        else:
            print(f"[API] SSH explorar falló, usando local: {resultado.stderr}", flush=True)
    except Exception as e:
        print(f"[API] Error de SSH en explorar, usando fallback local: {e}", flush=True)

    # Fallback local (dentro del contenedor)
    try:
        import os
        if not ruta or not os.path.exists(ruta):
            ruta = "/roms"  # Fallback a la carpeta montada si no hay SSH o ruta inválida
        
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
    except Exception as local_err:
        return {"estado": "Error", "detalle": str(local_err)}

@router.get("/audio/dispositivos")
def obtener_dispositivos_audio():
    try:
        resultado = run_ssh_command("pactl list sinks", timeout=5)
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
    cmd = f"pactl set-default-sink {sink_name}"
    if "retrocloud-audio" not in sink_name and "sunshine" not in sink_name:
        cmd += f" && for mod in \$(pactl list modules short | grep module-loopback | awk '{{print \$1}}'); do pactl unload-module \$mod >/dev/null 2>&1; done && pactl load-module module-loopback source=retrocloud-audio.monitor sink={sink_name} latency_msec=30 >/dev/null 2>&1"
        
    try:
        resultado = run_ssh_command(cmd, timeout=5, use_bash=True)
        if resultado.returncode != 0:
            return {"estado": "Error", "detalle": resultado.stderr}
        return {"estado": "OK", "mensaje": f"Dispositivo cambiado a {sink_name}"}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.get("/estado_emulador")
def estado_emulador():
    comando = f"ps -u {HOST_USER} -o args="
    try:
        resultado = run_ssh_command(comando, timeout=5)
        if resultado.returncode != 0:
            return {"activo": False, "error": resultado.stderr}
            
        process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "xenia_canary", "xenia-canary-bin", "xenia_canary.exe", "xenia_canary.ex", "xenia", "steam"]
        
        for line in resultado.stdout.splitlines():
            line_lower = line.lower()
            
            if any(x in line_lower for x in ["ssh", "ps -u", "grep", "retrocloud_gamepad_daemon"]):
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
    """Mata los procesos de emuladores/Steam en el host via SSH.
    Usado por el combo Select+Start del gamepad para volver a RetroCloud."""
    kill_cmd = (
        "pkill -x retroarch; pkill -x steam; pkill -x pcsx2-qt; pkill -x dolphin-emu; "
        "pkill -x rpcs3; pkill -x xemu; pkill -x PPSSPPSDL; pkill -x duckstation; "
        "echo done"
    )
    try:
        run_ssh_command(kill_cmd, timeout=5)
        return {"estado": "OK", "mensaje": "Señal de cierre enviada."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/pausar_emulador")
def pausar_emulador():
    """Pausa temporalmente los procesos de emuladores y devuelve el foco a RetroCloud."""
    stop_cmd = (
        "pkill -STOP -x retroarch; pkill -STOP -x steam; pkill -STOP -f pcsx2-qt; "
        "pkill -STOP -x dolphin-emu; pkill -STOP -x rpcs3; pkill -STOP -x xemu; "
        "pkill -STOP -x PPSSPPSDL; pkill -STOP -x duckstation; pkill -STOP -f xenia; "
        "pkill -STOP -f xenia_canary; pkill -STOP -f xenia_canary.exe; "
        "hyprctl dispatch focuswindow class:retrocloud-app; echo done"
    )
    try:
        run_ssh_command(stop_cmd, timeout=5)
        return {"estado": "OK", "mensaje": "Emulador pausado y foco devuelto a RetroCloud."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/reanudar_emulador")
def reanudar_emulador():
    """Reanuda los procesos de emuladores previamente pausados."""
    cont_cmd = (
        "pkill -CONT -x retroarch; pkill -CONT -x steam; pkill -CONT -f pcsx2-qt; "
        "pkill -CONT -x dolphin-emu; pkill -CONT -x rpcs3; pkill -CONT -x xemu; "
        "pkill -CONT -x PPSSPPSDL; pkill -CONT -x duckstation; pkill -CONT -f xenia; "
        "pkill -CONT -f xenia_canary; pkill -CONT -f xenia_canary.exe; "
        "hyprctl dispatch focuswindow class:retroarch; "
        "hyprctl dispatch focuswindow class:pcsx2; "
        "hyprctl dispatch focuswindow class:dolphin; "
        "hyprctl dispatch focuswindow class:rpcs3; "
        "hyprctl dispatch focuswindow class:xemu; "
        "hyprctl dispatch focuswindow class:xenia; "
        "hyprctl dispatch focuswindow class:duckstation; "
        "hyprctl dispatch focuswindow class:steam_app_.*; "
        "echo done"
    )
    try:
        run_ssh_command(cont_cmd, timeout=5)
        return {"estado": "OK", "mensaje": "Emulador reanudado."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}


@router.get("/ssh/test")
def test_ssh():
    try:
        resultado = run_ssh_command("echo OK", timeout=5)
        if resultado.returncode == 0:
            return {"estado": "OK", "mensaje": "Conexión SSH exitosa."}
        else:
            return {"estado": "Error", "detalle": resultado.stderr}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

@router.post("/ajustes/wizard-complete")
def wizard_complete(ajustes: dict, background_tasks: BackgroundTasks):
    try:
        ajustes["first_run"] = False
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, indent=2)
        aplicar_retroarch_ajustes(ajustes)
        
        # Aplicar workspaces de Hyprland sobre el host en segundo plano
        def _aplicar_pantalla():
            run_ssh_command("/home/fydend/Proyectos/RetroCloud-Patolinux/scripts/setup_virtual_display.sh", timeout=10)
        background_tasks.add_task(_aplicar_pantalla)
        
        return {"estado": "OK", "mensaje": "Setup inicial completado."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}





@router.post("/salir")
def salir_retrocloud(background_tasks: BackgroundTasks):
    """Cierra la aplicación RetroCloud en el host."""
    def _cerrar():
        import time
        time.sleep(0.5)
        run_ssh_command("docker stop store_front || pkill -f 'retrocloud-app' || pkill -f 'store_front/app.py' || pkill -f 'python3.*app.py'; echo done", use_bash=True, timeout=5)
    background_tasks.add_task(_cerrar)
    return {"estado": "OK", "mensaje": "Cerrando RetroCloud..."}
