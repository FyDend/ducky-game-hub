#!/usr/bin/env python3
import os
import struct
import select
import selectors
import subprocess
import threading
import time

# Event format for Linux joydev device (/dev/input/jsX)
# struct js_event {
#     __u32 time;     /* event timestamp in milliseconds */
#     __s16 value;    /* value */
#     __u8 type;      /* event type: 1 = button, 2 = axis */
#     __u8 number;    /* axis/button number */
# };
JS_EVENT_FORMAT = "IhBB"
JS_EVENT_SIZE = struct.calcsize(JS_EVENT_FORMAT)

# Keep track of active timers for Select+Start combination on each joystick
active_timers = {}
button_states = {}
opened_devices = {}
last_axis_state = {}
selector = selectors.DefaultSelector()
selector_lock = threading.Lock()

def send_event_bg(action):
    def run():
        try:
            import urllib.request
            import json
            # Envía el evento a la Bridge API local (la cual retransmitirá al Store Front por WebSocket)
            url = "http://127.0.0.1:8000/gamepad_event"
            data = json.dumps({"action": action}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=0.5) as response:
                response.read()
        except Exception:
            pass  # Falla silenciosa para no contaminar logs si la API está reiniciando
    threading.Thread(target=run, daemon=True).start()

def send_raw_event_bg(ev_type, number, value):
    def run():
        try:
            import urllib.request
            import json
            url = "http://127.0.0.1:8000/gamepad_event"
            payload = {
                "action": "raw_event",
                "raw": {
                    "type": ev_type,
                    "number": number,
                    "value": value
                }
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=0.5) as response:
                response.read()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()

def kill_emulators():
    print("[Daemon] Select+Start combo held! Killing active emulator processes...", flush=True)
    process_names = ["pcsx2-qt", "pcsx2", "retroarch", "dolphin-emu", "rpcs3", "xemu", "xenia", "xenia_canary.exe", "xenia_canary"]
    for proc in process_names:
        try:
            # Kill process cleanly using -f to match AppImage/helper command lines
            subprocess.run(["pkill", "-f", proc])
        except Exception as e:
            print(f"[Daemon] Error matando {proc}: {e}", flush=True)

def on_button_change(device_path, button_num, is_pressed):
    if device_path not in button_states:
        button_states[device_path] = {}
    
    button_states[device_path][button_num] = is_pressed
    print(f"[Daemon] Boton {button_num} en {device_path} cambiado a {is_pressed}", flush=True)
    
    # Enviar evento raw de botón en segundo plano
    send_raw_event_bg("button", button_num, is_pressed)
    
    # Xbox controller mapping & Generic Gamepads (Suono X3 / Terios):
    # - Xbox: 6: Select, 7: Start, 8: Home
    # - Generic: 10/8: Select, 11/9: Start, 12: Home
    select_pressed = (button_states[device_path].get(6, 0) == 1) or (button_states[device_path].get(10, 0) == 1) or (button_states[device_path].get(8, 0) == 1)
    start_pressed = (button_states[device_path].get(7, 0) == 1) or (button_states[device_path].get(11, 0) == 1) or (button_states[device_path].get(9, 0) == 1)
    home_pressed = (button_states[device_path].get(8, 0) == 1) or (button_states[device_path].get(12, 0) == 1)
    
    combo_pressed = (select_pressed and start_pressed) or (home_pressed and start_pressed)

    # Start a 2.0‑second timer to quit when combo is held
    if combo_pressed:
        if device_path not in active_timers:
            t = threading.Timer(2.0, kill_emulators)
            t.start()
            active_timers[device_path] = t
    else:
        # Combo released – cancel any pending timer
        t = active_timers.pop(device_path, None)
        if t:
            t.cancel()

    # Enviar evento de botón presionado al Store Front para navegación (solo al presionar: is_pressed == 1)
    if is_pressed == 1:
        # Evitar enviar navegación si están presionados botones de combo (Select/Start/Home) para evitar saltos accidentales al salir del juego
        if not (select_pressed or start_pressed or home_pressed):
            if button_num == 0:
                send_event_bg("select")
            elif button_num == 1:
                send_event_bg("cancel")
            elif button_num in (12, 10): # D-pad Up
                send_event_bg("up")
            elif button_num in (13, 11): # D-pad Down
                send_event_bg("down")
            elif button_num in (14, 12): # D-pad Left
                send_event_bg("left")
            elif button_num in (15, 13): # D-pad Right
                send_event_bg("right")

def on_axis_change(device_path, axis_num, value):
    if device_path not in last_axis_state:
        last_axis_state[device_path] = {}
        
    # Clasificar en estados discretos: -1 (negativo), 0 (centrado), 1 (positivo)
    current_state = 0
    if value < -16000:
        current_state = -1
    elif value > 16000:
        current_state = 1
        
    prev_state = last_axis_state[device_path].get(axis_num, 0)
    if current_state != prev_state:
        last_axis_state[device_path][axis_num] = current_state
        # Solo enviar al presionar (mover hacia extremo, ignorar al volver al centro)
        if current_state != 0:
            if axis_num in (1, 7): # Left stick Y o D-pad Y
                action = "up" if current_state == -1 else "down"
                send_event_bg(action)
            elif axis_num in (0, 6): # Left stick X o D-pad X
                action = "left" if current_state == -1 else "right"
                send_event_bg(action)
            
            # Enviar evento raw del eje en segundo plano si cruza el umbral
            send_raw_event_bg("axis", axis_num, value)

def read_joystick_events(fd, mask):
    device_path = None
    for path, dev_fd in list(opened_devices.items()):
        if dev_fd == fd:
            device_path = path
            break
            
    if not device_path:
        return
        
    try:
        data = os.read(fd, JS_EVENT_SIZE)
        if len(data) < JS_EVENT_SIZE:
            return
            
        time_ms, value, ev_type, number = struct.unpack(JS_EVENT_FORMAT, data[:JS_EVENT_SIZE])
        
        # Tipo de evento: 1 = button, 2 = axis (ignorar eventos de inicialización con bit 0x80)
        is_button = (ev_type & ~0x80) == 1
        is_axis = (ev_type & ~0x80) == 2
        
        if is_button:
            on_button_change(device_path, number, 1 if value else 0)
        elif is_axis:
            on_axis_change(device_path, number, value)
            
    except (IOError, OSError) as e:
        print(f"[Daemon] Error leyendo de {device_path}: {e}. Desregistrando...", flush=True)
        close_device(device_path)

def open_device(path):
    try:
        # Check device name in sysfs to ignore virtual mouse
        js_name = os.path.basename(path)
        sys_name_path = f"/sys/class/input/{js_name}/device/name"
        device_name = ""
        if os.path.exists(sys_name_path):
            try:
                with open(sys_name_path, "r") as f:
                    device_name = f.read().strip()
            except Exception:
                pass

        if "Mouse passthrough" in device_name:
            print(f"[Daemon] Ignorando ratón virtual detectado como joystick: {path} ({device_name})", flush=True)
            return

        # Open in non-blocking read-only binary mode
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with selector_lock:
            selector.register(fd, selectors.EVENT_READ, read_joystick_events)
        opened_devices[path] = fd
        button_states[path] = {}
        print(f"[Daemon] Dispositivo registrado: {path} ({device_name if device_name else 'Desconocido'})", flush=True)
    except Exception as e:
        print(f"[Daemon] No se pudo abrir {path}: {e}", flush=True)

def close_device(path):
    fd = opened_devices.get(path)
    if fd is not None:
        with selector_lock:
            try:
                selector.unregister(fd)
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass
        opened_devices.pop(path, None)
        button_states.pop(path, None)
        # Cancel any active timer
        t = active_timers.pop(path, None)
        if t:
            t.cancel()
        print(f"[Daemon] Dispositivo desregistrado: {path}", flush=True)

def monitor_joystick_devices():
    """Background thread to periodically scan /dev/input for added/removed js devices."""
    while True:
        try:
            available_devices = []
            if os.path.exists("/dev/input"):
                for entry in os.listdir("/dev/input"):
                    if entry.startswith("js"):
                        available_devices.append(os.path.join("/dev/input", entry))
                        
            # Close removed devices
            for path in list(opened_devices.keys()):
                if path not in available_devices:
                    close_device(path)
                    
            # Open newly added devices
            for path in available_devices:
                if path not in opened_devices:
                    open_device(path)
                    
        except Exception as e:
            print(f"[Daemon] Error en escaneo de dispositivos: {e}", flush=True)
            
        time.sleep(3.0)

def main():
    print("[Daemon] Iniciando daemon de monitoreo de controles...", flush=True)
    
    # Start scanning thread
    t = threading.Thread(target=monitor_joystick_devices, daemon=True)
    t.start()
    
    # Selector event loop
    while True:
        try:
            with selector_lock:
                events = selector.select(timeout=1.0)
            for key, mask in events:
                callback = key.data
                callback(key.fd, mask)
        except Exception as e:
            # Handle any selector interruption elegantly
            time.sleep(0.1)

if __name__ == "__main__":
    main()
