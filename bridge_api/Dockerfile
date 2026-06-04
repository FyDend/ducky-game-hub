FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install core system packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    gpg \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install emulator utility packages, GPU libs, and python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    retroarch \
    p7zip-full \
    sqlite3 \
    git \
    jq \
    iproute2 \
    socat \
    pulseaudio-utils \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libvulkan1 \
    mesa-vulkan-drivers \
    libxrandr2 \
    libnss3 \
    libnss3-tools \
    libxkbcommon-x11-0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    xvfb \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Xemu AppImage (resolving dynamic filename containing version)
RUN XEMU_URL=$(curl -s https://api.github.com/repos/xemu-project/xemu/releases/latest | grep browser_download_url | grep -E 'xemu-[0-9.]+-x86_64\.AppImage' | head -n 1 | cut -d '"' -f 4) && \
    wget -O /tmp/xemu.AppImage "$XEMU_URL" && \
    chmod +x /tmp/xemu.AppImage && \
    cd /tmp && ./xemu.AppImage --appimage-extract && \
    mv squashfs-root /opt/xemu && \
    ln -s /opt/xemu/AppRun /usr/local/bin/xemu && \
    rm /tmp/xemu.AppImage

# Download and extract DuckStation AppImage
RUN wget -O /tmp/duckstation.AppImage https://github.com/stenzek/duckstation/releases/download/latest/DuckStation-x64.AppImage && \
    chmod +x /tmp/duckstation.AppImage && \
    cd /tmp && ./duckstation.AppImage --appimage-extract && \
    mv squashfs-root /opt/duckstation && \
    ln -s /opt/duckstation/AppRun /usr/local/bin/duckstation && \
    rm /tmp/duckstation.AppImage

# Download and extract RPCS3 AppImage (resolving dynamic filename containing build hashes)
RUN RPCS3_URL=$(curl -s https://api.github.com/repos/RPCS3/rpcs3-binaries-linux/releases/latest | grep browser_download_url | head -n 1 | cut -d '"' -f 4) && \
    wget -O /tmp/rpcs3.AppImage "$RPCS3_URL" && \
    chmod +x /tmp/rpcs3.AppImage && \
    cd /tmp && ./rpcs3.AppImage --appimage-extract && \
    mv squashfs-root /opt/rpcs3 && \
    ln -s /opt/rpcs3/AppRun /usr/local/bin/rpcs3 && \
    rm /tmp/rpcs3.AppImage

# Download and extract Dolphin AppImage
RUN DOLPHIN_URL=$(curl -s https://api.github.com/repos/pkgforge-dev/Dolphin-emu-AppImage/releases | grep browser_download_url | grep anylinux-x86_64.AppImage | head -n 1 | cut -d '"' -f 4) && \
    wget -O /tmp/dolphin.AppImage "$DOLPHIN_URL" && \
    chmod +x /tmp/dolphin.AppImage && \
    cd /tmp && ./dolphin.AppImage --appimage-extract && \
    mv squashfs-root /opt/dolphin && \
    ln -s /opt/dolphin/AppRun /usr/local/bin/dolphin-emu && \
    rm /tmp/dolphin.AppImage

# Download and extract PCSX2 AppImage
RUN PCSX2_URL=$(curl -s https://api.github.com/repos/PCSX2/pcsx2/releases/latest | grep browser_download_url | grep linux-appimage | cut -d '"' -f 4) && \
    wget -O /tmp/pcsx2.AppImage "$PCSX2_URL" && \
    chmod +x /tmp/pcsx2.AppImage && \
    cd /tmp && ./pcsx2.AppImage --appimage-extract && \
    mv squashfs-root /opt/pcsx2 && \
    ln -s /opt/pcsx2/AppRun /usr/local/bin/pcsx2-qt && \
    rm /tmp/pcsx2.AppImage

# Download and install LizardByte Sunshine
RUN wget https://github.com/LizardByte/Sunshine/releases/latest/download/sunshine-ubuntu-22.04-amd64.deb && \
    apt-get update && apt-get install -y ./sunshine-ubuntu-22.04-amd64.deb && \
    rm sunshine-ubuntu-22.04-amd64.deb && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]