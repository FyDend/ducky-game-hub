# 🎮 RetroCloud (Sovereign Game Pass)

> Ecosistema privado y autocontenido de emulación y streaming de baja latencia "Couch Mode" para tu televisor.

**RetroCloud** replica la experiencia fluida de plataformas comerciales como Steam Big Picture o Xbox Game Pass pero enfocado en la emulación retro premium. Elimina por completo la fricción manual: navega por tu catálogo visual desde la TV, solicita un juego, y el sistema se encargará de buscar, descargar, organizar y lanzar la emulación de forma 100% automatizada e independiente de la sesión de tu PC.

---

## 🏛️ Arquitectura del Sistema

El ecosistema está diseñado bajo un modelo desacoplado de cliente/servidor:

```
+-----------------------------+             +-------------------------------+
|       CLIENTE (Smart TV)    |             |       SERVIDOR (Host PC)      |
|                             |             |                               |
|   +---------------------+   |  Sunshine   |   +-----------------------+   |
|   |      Moonlight      |<====================|     Sunshine Host     |   |
|   +---------------------+   |  (Video/Audio)  +-----------------------+   |
|                             |             |               |               |
|   +---------------------+   |             |   +-----------------------+   |
|   | Store Front (PyQt6) |<------------------->|  Bridge API (FastAPI) |   |
|   +---------------------+   |  HTTP/Websocket |   +-----------------------+   |
+-----------------------------+             +-------------------------------+
                                                            |
                                                +-----------+-----------+
                                                |                       |
                                    +-----------------------+ +-------------------+
                                    | qBittorrent (Torrents)| | RomM/DB (Metadata)|
                                    +-----------------------+ +-------------------+
```

1. **Store Front (Capa de Presentación)**: Una aplicación visual embebida en PyQt6 que funciona de forma independiente al navegador convencional y lee mandos físicos de forma nativa a través de la HTML5 Gamepad API.
2. **Bridge API (FastAPI - Docker)**: El orquestador central del sistema. Gestiona descargas con qBittorrent, consulta metadatos, interactúa con el sistema operativo mediante un puente cifrado SSH y despacha comandos de Hyprland.
3. **Daemon de Salida Segura (`retrocloud_gamepad_daemon`)**: Un daemon persistente que lee directamente en `/dev/input/js*`. Permite cerrar cualquier emulador activo en pantalla sosteniendo `Select + Start` (o `Home + Start`) por 2 segundos enteros.
4. **Pantalla Virtual Headless (TV-STREAM)**: Configuración en Hyprland de una salida fantasma de 1080p@60Hz en las coordenadas lejanas `10000x10000` (Workspace 10), garantizando que las sesiones de juego en la TV no interrumpan ni interfieran con el monitor físico principal de tu PC.

---

## 📁 Estructura del Directorio

```
RetroCloud-Patolinux/
├── .secrets/                     # Identidades criptográficas y llaves SSH (ignoradas)
├── bridge_api/                   # FastAPI backend orquestador (Dockerizado)
│   ├── routers/                  # Controladores por dominio (catalog, downloads, system...)
│   ├── services/                 # Servicios auxiliares (ssh_helper, catalog_service)
│   ├── config.py                 # Origen centralizado de configuración de entornos
│   ├── main.py                   # Inicialización y middleware FastAPI
│   └── Dockerfile
├── daemon/                       # Daemon de monitoreo de gamepad
│   ├── retrocloud_gamepad_daemon.py
│   └── retrocloud-gamepad.service # Plantilla de unidad de systemd
├── scripts/                      # Utilidades de automatización del Host
│   ├── setup_virtual_display.sh  # Pantalla virtual en Hyprland y sinks de audio
│   ├── apply_joystick_mappings.sh # Inyección de mandos P1 y P2 en RetroArch
│   ├── setup_xbox_joystick.sh    # Mapeo universal de botones Xbox
│   └── install-daemon.sh         # Registro automatizado de systemd
├── store_front/                  # Interfaz Couch Mode Premium (PyQt6 / HTML5 / CSS)
│   ├── app.py                    # Ventana standalone PyQt6
│   └── index.html / main.js
├── docker-compose.yml            # Definición del stack de servicios Docker
├── .env.example                  # Plantilla de configuración local
└── README.md
```

---

## 🚀 Requisitos e Instalación

### Requisitos Previos

- **Host OS**: Linux (optimizado para CachyOS / Arch con Hyprland).
- **GPU**: NVIDIA (con aceleración NVENC y Sunshine configurado).
- **Dependencias**: Docker, Docker Compose y Python 3 instalado en el Host.

### Instalación Paso a Paso

1. **Configurar Variables de Entorno**:
   Copia el archivo de plantilla `.env.example` como `.env` y edita los valores con las rutas y usuarios de tu sistema:
   ```bash
   cp .env.example .env
   nano .env
   ```

2. **Levantar el Stack de Contenedores**:
   Levanta la API del Bridge, qBittorrent y servicios auxiliares en segundo plano:
   ```bash
   docker compose up -d
   ```

3. **Instalar el Daemon de Mandos (systemd)**:
   Registra y activa el daemon de salida segura como un servicio de usuario systemd:
   ```bash
   chmod +x scripts/install-daemon.sh
   ./scripts/install-daemon.sh
   ```

4. **Lanzar la Aplicación**:
   Ejecuta el launcher principal para preparar el monitor virtual virtual de Hyprland e iniciar los servicios gráficos:
   ```bash
   chmod +x retrocloud-launcher.sh
   ./retrocloud-launcher.sh
   ```

---

## 🎮 Controles e Interacción Couch Mode

- **Navegación en Store Front**: Puedes navegar en 2D de forma espacial usando las flechas de tu control remoto, teclado o joystick físico (D-Pad).
- **Cierre Rápido de Emulador**: Sostén `Select + Start` (o `Home + Start`) por **2 segundos** continuos en tu mando para matar de forma segura y ordenada el emulador actual y retornar al Store Front.
- **Doble Mando Cooperativo**: El sistema inyecta en caliente variables de entorno SDL para omitir dispositivos virtuales e identificar mandos físicos, asegurando juego multijugador plug-and-play perfecto sin interferencia en la Smart TV.
