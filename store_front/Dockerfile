FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema para X11, OpenGL, sonido y Chromium/QtWebEngine
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-dri \
    libgl1 \
    libegl1 \
    libglx-mesa0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shm0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxcb-xtest0 \
    libfontconfig1 \
    libfreetype6 \
    libglib2.0-0 \
    libnss3 \
    libasound2 \
    libpulse0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxtst6 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libgbm1 \
    libxkbfile1 \
    libx11-xcb1 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*


# Instalar PyQt6 y PyQt6-WebEngine
RUN pip install --no-cache-dir \
    PyQt6 \
    PyQt6-WebEngine

WORKDIR /app

# Por defecto corre app.py
CMD ["python", "app.py"]
