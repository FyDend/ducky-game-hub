import subprocess
from config import HOST_USER, HOST_IP, SSH_KEY_PATH

def run_ssh_command(command_str: str, timeout: float = None, use_bash: bool = False) -> subprocess.CompletedProcess:
    """Ejecuta un comando en el host de CachyOS a través de SSH."""
    if use_bash:
        # Escapamos las comillas simples internas
        cmd_escaped = command_str.replace("'", "'\\''")
        remote_cmd = f"bash -c '{cmd_escaped}'"
    else:
        remote_cmd = command_str

    ssh_cmd = [
        "ssh",
        "-i", SSH_KEY_PATH,
        "-o", "StrictHostKeyChecking=no",
        f"{HOST_USER}@{HOST_IP}",
        remote_cmd
    ]
    
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
