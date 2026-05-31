#!/usr/bin/env bash

# Script para configurar joysticks de Xbox en CachyOS (desactivar ERTM y preparar Bluetooth)
# RetroCloud sovereign game pass system helper

echo "=== CONFIGURADOR DE JOYSTICKS XBOX EN CACHYOS ==="
echo ""

# 1. Desactivar ERTM temporalmente
echo "[1/4] Desactivando ERTM en caliente..."
echo 1 | sudo tee /sys/module/bluetooth/parameters/disable_ertm

# Desactivar ERTM permanentemente para que persista tras reiniciar
echo "[2/4] Configurando desactivación permanente de ERTM..."
echo "options bluetooth disable_ertm=1" | sudo tee /etc/modprobe.d/xbox_bt.conf

# 2. Reiniciar el servicio Bluetooth para destrabar cualquier operación atascada
echo "[3/4] Reiniciando servicio Bluetooth para limpiar estados colgados..."
sudo systemctl restart bluetooth
sleep 2

# 3. Preguntar si se desea instalar xpadneo (driver avanzado y recomendado)
echo ""
echo "--------------------------------------------------------"
echo "CONSEJO: Se recomienda instalar 'xpadneo' (driver avanzado de Xbox para Linux)."
echo "Esto soluciona mapeos incorrectos y caídas de conexión por Bluetooth."
echo "--------------------------------------------------------"
read -p "¿Deseas instalar el driver xpadneo desde el AUR ahora? (s/n): " instalar_xpadneo

if [[ "$instalar_xpadneo" =~ ^[sS]$ ]]; then
    echo "[4/4] Instalando xpadneo-dkms..."
    yay -S --noconfirm xpadneo-dkms
else
    echo "[4/4] Omitiendo instalación de xpadneo. Se usará el driver nativo xpad."
fi

echo ""
echo "=== ¡PROCESO COMPLETADO! ==="
echo "Ahora sigue estos pasos en tu tele/PC:"
echo "1. Pon tu mando de Xbox en modo sincronización (mantén pulsado el botón pequeño superior hasta que el logo parpadee rápido)."
echo "2. Ejecuta en tu consola: bluetoothctl"
echo "3. Dentro de bluetoothctl escribe los siguientes comandos:"
echo "   power on"
echo "   agent on"
echo "   default-agent"
echo "   scan on"
echo "4. Espera a que aparezca 'Xbox Wireless Controller' con su dirección MAC (ej. 1A:2B:3C:4D:5E:6F)."
echo "5. Copia esa MAC y escribe:"
echo "   pair TU_DIRECCION_MAC"
echo "   trust TU_DIRECCION_MAC"
echo "   connect TU_DIRECCION_MAC"
echo "6. ¡Repite para el segundo mando!"
