# ==============================================================================
# Distrobox and Dependency Compatibility Helper for Ducky Game Hub
# ==============================================================================

# Helper para ejecutar comandos en el host desde distrobox si no existen en el contenedor
run_host() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null && command -v distrobox-host-exec &> /dev/null; then
        distrobox-host-exec "$@"
    else
        command "$@"
    fi
}

# Wrappers de comandos interactivos con el Host
docker() {
    if ! command -v docker &> /dev/null && command -v distrobox-host-exec &> /dev/null; then
        if [ "$1" = "compose" ] && ! distrobox-host-exec docker compose version &> /dev/null && distrobox-host-exec docker-compose version &> /dev/null; then
            shift
            distrobox-host-exec docker-compose "$@"
        else
            distrobox-host-exec docker "$@"
        fi
    else
        command docker "$@"
    fi
}

systemctl() { run_host systemctl "$@"; }
hyprctl() { run_host hyprctl "$@"; }
pactl() { run_host pactl "$@"; }

# Wrapper minimalista de jq utilizando python3 como fallback
jq() {
    if command -v jq &> /dev/null; then
        command jq "$@"
    elif command -v python3 &> /dev/null; then
        python3 -c "
import sys, json, os

args = sys.argv[1:]
query = ''
file_path = None

for arg in args:
    if arg.startswith('.'):
        query = arg
    elif os.path.exists(arg):
        file_path = arg

try:
    if file_path:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
except Exception:
    sys.exit(1)

parts = query.split('//')
path_str = parts[0].strip().strip('.')
fallback = parts[1].strip().strip('\"\'') if len(parts) > 1 else ''

val = data
try:
    if path_str:
        for p in path_str.split('.'):
            if p:
                val = val[p]
        print(val)
    else:
        print(data)
except Exception:
    print(fallback if fallback else '')
" "$@"
    else
        echo "❌ Error: ni 'jq' ni 'python3' están disponibles para procesar JSON." >&2
        return 1
    fi
}
