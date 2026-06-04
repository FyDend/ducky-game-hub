import os
import socket
import json
import time

def get_hyprland_socket() -> str:
    puid = os.getenv("PUID", "1000")
    runtime_dir = f"/run/user/{puid}"
    
    instance_sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not instance_sig:
        hypr_dir = os.path.join(runtime_dir, "hypr")
        if os.path.exists(hypr_dir):
            for entry in os.listdir(hypr_dir):
                entry_path = os.path.join(hypr_dir, entry)
                if os.path.isdir(entry_path):
                    instance_sig = entry
                    break
                    
    if not instance_sig:
        raise Exception("No active Hyprland instance signature found")
        
    return f"{runtime_dir}/hypr/{instance_sig}/.socket.sock"

def send_hyprland_cmd(cmd: str) -> str:
    socket_path = get_hyprland_socket()
    if not os.path.exists(socket_path):
        raise Exception(f"Hyprland socket does not exist at {socket_path}")
        
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(socket_path)
        client.sendall(cmd.encode("utf-8"))
        response = b""
        while True:
            data = client.recv(4096)
            if not data:
                break
            response += data
        return response.decode("utf-8")
    finally:
        client.close()

def setup_virtual_display_hyprland(target_monitor="TV-STREAM", target_workspace="10", host_monitor="DP-1"):
    print(f"[Hyprland Helper] Setting up virtual display. Target: {target_monitor}, WS: {target_workspace}, Host Mon: {host_monitor}", flush=True)
    
    # 1. Check if target_monitor exists
    try:
        monitors_json = send_hyprland_cmd("j/monitors")
        monitors = json.loads(monitors_json)
    except Exception as e:
        print(f"[Hyprland Helper] Failed to query monitors: {e}", flush=True)
        monitors = []
        
    exists = any(m.get("name") == target_monitor for m in monitors)
    if not exists:
        if target_monitor == "TV-STREAM":
            print(f"[Hyprland Helper] Creating headless output {target_monitor}...", flush=True)
            send_hyprland_cmd(f"output create headless {target_monitor}")
            time.sleep(1.0)
    else:
        print(f"[Hyprland Helper] Monitor {target_monitor} already exists.", flush=True)
        
    # 2. Configure resolution and position if TV-STREAM
    if target_monitor == "TV-STREAM":
        send_hyprland_cmd(f"eval hl.monitor({{ output = '{target_monitor}', mode = '1920x1080@60', position = '10000x10000', scale = 1 }})")
        
    # 3. Bind workspaces 1-9 to host monitor
    for i in range(1, 10):
        send_hyprland_cmd(f"eval hl.workspace_rule({{ workspace = '{i}', monitor = '{host_monitor}' }})")
        send_hyprland_cmd(f"eval hl.dispatch(hl.dsp.workspace.move({{ workspace = {i}, monitor = '{host_monitor}' }}))")
        
    # 4. Bind target workspace to target monitor
    send_hyprland_cmd(f"eval hl.workspace_rule({{ workspace = '{target_workspace}', monitor = '{target_monitor}' }})")
    send_hyprland_cmd(f"eval hl.dispatch(hl.dsp.workspace.move({{ workspace = {target_workspace}, monitor = '{target_monitor}' }}))")
    
    # 5. Set up window rules for emulators
    emu_patterns = ["xenia", "Xenia", "xemu", "Xemu", "pcsx2", "PCSX2", "rpcs3", "RPCS3", "dolphin", "Dolphin", "retroarch", "RetroArch", "steam", "Steam", "sunshine", "Sunshine"]
    
    # Python / Ducky Game Hub app window rule
    send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ class = 'python3', title = '.*Ducky Game Hub.*' }}, workspace = '{target_workspace}', idle_inhibit = 'always' }})")
    send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ class = 'ducky-game-hub' }}, workspace = '{target_workspace}', idle_inhibit = 'always' }})")
    send_hyprland_cmd(f"eval hl.dispatch(hl.dsp.window.move({{ workspace = {target_workspace}, window = 'class:^python3$' }}))")
    send_hyprland_cmd(f"eval hl.dispatch(hl.dsp.window.move({{ workspace = {target_workspace}, window = 'class:^ducky-game-hub$' }}))")
    
    for pat in emu_patterns:
        send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ class = '.*{pat}.*' }}, workspace = '{target_workspace} silent', idle_inhibit = 'always' }})")
        send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ title = '.*{pat}.*' }}, workspace = '{target_workspace} silent', idle_inhibit = 'always' }})")
        
    # Proton rules
    send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ class = 'steam_app_.*' }}, workspace = '{target_workspace} silent', idle_inhibit = 'always' }})")
    send_hyprland_cmd(f"eval hl.window_rule({{ match = {{ class = 'steam_proton' }}, workspace = '{target_workspace} silent', idle_inhibit = 'always' }})")
    
    print("[Hyprland Helper] Virtual display setup complete!", flush=True)
