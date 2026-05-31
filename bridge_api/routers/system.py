from fastapi import APIRouter, BackgroundTasks
import os
import json
import re
import subprocess
from config import SETTINGS_FILE, HOST_USER, HOST_IP, SAVE_SYNC_HOST, SAVE_SYNC_USER, SAVE_SYNC_PATH
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
            "target_workspace": "10",
            "target_monitor": "TV-STREAM",
            "host_monitor": "DP-1"
        },
        "audio": {
            "selected_sink": ""
        },
        "controls": {
            "profile": "gamepad",
            "gamepad": {
                "a": "b0",
                "b": "b1",
                "x": "b2",
                "y": "b3",
                "leftshoulder": "b4",
                "rightshoulder": "b5",
                "lefttrigger": "b6",
                "righttrigger": "b7",
                "back": "b10",
                "start": "b11",
                "guide": "b12",
                "leftstick": "b8",
                "rightstick": "b9",
                "dpup": "h0.1",
                "dpdown": "h0.4",
                "dpleft": "h0.8",
                "dpright": "h0.2",
                "leftx": "a0",
                "lefty": "a1",
                "rightx": "a2",
                "righty": "a5"
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
    if controls.get("profile") == "keyboard":
        kb = controls.get("keyboard", {{}})
        kb_map = {{
            "up": "input_player1_up",
            "down": "input_player1_down",
            "left": "input_player1_left",
            "right": "input_player1_right",
            "a": "input_player1_a",
            "b": "input_player1_b",
            "x": "input_player1_x",
            "y": "input_player1_y",
            "l1": "input_player1_l",
            "r1": "input_player1_r",
            "l2": "input_player1_l2",
            "r2": "input_player1_r2",
            "select": "input_player1_select",
            "start": "input_player1_start",
            "guide": "input_player1_menu_toggle"
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
    return load_settings()

@router.post("/ajustes")
def guardar_ajustes(ajustes: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, indent=2)
        aplicar_retroarch_ajustes(ajustes)
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
def wizard_complete(ajustes: dict):
    try:
        ajustes["first_run"] = False
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ajustes, f, indent=2)
        aplicar_retroarch_ajustes(ajustes)
        return {"estado": "OK", "mensaje": "Setup inicial completado."}
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}

def execute_saves_sync(direction: str):
    if not SAVE_SYNC_HOST:
        print("[API] Sync de saves abortado: SAVE_SYNC_HOST no configurado.", flush=True)
        return
        
    user_part = f"{SAVE_SYNC_USER}@" if SAVE_SYNC_USER else ""
    remote_target = f"{user_part}{SAVE_SYNC_HOST}:{SAVE_SYNC_PATH}"
    
    local_saves = f"/home/{HOST_USER}/.config/retroarch/saves/"
    
    if direction == "push":
        cmd = f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' '{local_saves}' '{remote_target}/saves/'"
    else:
        cmd = f"rsync -avz -e 'ssh -o StrictHostKeyChecking=no' '{remote_target}/saves/' '{local_saves}'"
        
    print(f"[API] Iniciando rsync de saves ({direction})...", flush=True)
    res = run_ssh_command(cmd)
    if res.returncode == 0:
        print(f"[API] Sync de saves ({direction}) completado con éxito.", flush=True)
    else:
        print(f"[API] Error en sync de saves ({direction}): {res.stderr}", flush=True)

@router.post("/saves/sync")
def sync_saves(direction: str, background_tasks: BackgroundTasks):
    if not SAVE_SYNC_HOST:
        return {"estado": "Error", "detalle": "SAVE_SYNC_HOST no está configurado en el archivo .env"}
    if direction not in ["push", "pull"]:
        return {"estado": "Error", "detalle": "Dirección inválida. Debe ser 'push' o 'pull'"}
        
    background_tasks.add_task(execute_saves_sync, direction)
    return {"estado": "OK", "mensaje": f"Sincronización de partidas ({direction}) iniciada en segundo plano."}

@router.post("/salir")
def salir_retrocloud(background_tasks: BackgroundTasks):
    """Cierra la aplicación RetroCloud en el host."""
    def _cerrar():
        import time
        time.sleep(0.5)
        run_ssh_command("pkill -f 'retrocloud-app' || pkill -f 'store_front/app.py' || pkill -f 'python3.*app.py'; echo done", use_bash=True, timeout=5)
    background_tasks.add_task(_cerrar)
    return {"estado": "OK", "mensaje": "Cerrando RetroCloud..."}
