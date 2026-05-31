# Estado de Avance y Progreso — RetroCloud-Patolinux

Este documento contiene un resumen detallado de los cambios realizados, la arquitectura actual, los problemas resueltos y los siguientes pasos para continuar con el desarrollo y la refactorización en la próxima sesión.

---

## 📋 Resumen del Estado de la Tarea

Durante esta sesión de refactorización y mejoras de UX, nos enfocamos en optimizar el asistente de configuración inicial (Wizard), resolver bloqueos de navegación con el gamepad, facilitar la comprensión del sistema de pantallas y agregar atajos rápidos para recuperar el control del sistema (cerrar emuladores).

### 🛠️ Lo que se ha implementado con éxito:

1. **Resolución del Bloqueo del Gamepad en Mapeo de Controles**:
   - Cuando el modal de mapeo de controles (`controls-mapping-modal`) está abierto, la navegación espacial ahora se cancela o cierra correctamente al presionar el botón de retroceso/cancelar (botón B del mando). Esto evita que el mando quede inutilizable o bloqueado en la interfaz.

2. **Cierre Rápido de Emuladores y Steam (Select + Start)**:
   - Se añadió un detector en el bucle de lectura del gamepad (`pollGamepad`) en el frontend que identifica la presión simultánea de **Select (botón 8) + Start (botón 9)**.
   - Al activarse esta combinación, realiza una solicitud `POST /cerrar_emulador` a la API Bridge.
   - **Endpoint Backend (`POST /cerrar_emulador`)**: Implementado en `bridge_api/routers/system.py`. Ejecuta de forma segura en el host a través de SSH comandos de tipo `pkill` para terminar procesos de emuladores y Steam (`retroarch`, `steam`, `pcsx2-qt`, `dolphin-emu`, `rpcs3`, `xemu`, `PPSSPPSDL`, `duckstation`).

3. **Simplificación Drástica del Wizard de Pantallas (Paso 3)**:
   - Se reemplazó la confusa selección de 3 listas desplegables independientes por un selector dinámico (Toggle) en español:
     - **🖥️ UNA SOLA PANTALLA** (Modo Simple): Ejecuta los juegos en la misma pantalla en la que se visualiza RetroCloud. Utiliza inputs ocultos en segundo plano para configurar la misma pantalla de destino sin abrumar al usuario.
     - **📺 PC + TV SEPARADOS** (Modo Dual): Permite elegir por separado la pantalla del host (PC), la pantalla de juegos (TV) y el espacio de trabajo (workspace de Hyprland).
   - Se crearon clases y controles para Couch Mode para que estos botones y desplegables sean 100% interactivos desde el joystick.

4. **Ajuste del Diseño del Wizard (Alineación y Footer)**:
   - El botón **ANTERIOR** ahora usa `visibility: hidden` en lugar de `display: none` o `disabled` cuando se está en el Paso 1. Esto mantiene el botón oculto pero reserva su espacio físico, evitando que el botón **SIGUIENTE** se mueva de lugar y se desalinee visualmente.
   - Se corrigieron los anchos de tarjetas y alineaciones generales para que encajen mejor en pantallas de TV o monitores de juego.

5. **Explicación del Flujo SSH (Paso 2)**:
   - Se rediseñó el Paso 2 del Wizard para explicar detalladamente por qué se necesita la conexión SSH (Docker necesita comunicarse con el sistema host de Hyprland para lanzar los emuladores con aceleración gráfica directa).
   - Se muestra un bloque interactivo con las variables del `.env` (`HOST_IP`, `HOST_USER`) y se incluye un consejo para encontrar la IP del puente de red de Docker en el host (`ip route | grep docker`).

---

## 📂 Archivos Modificados

### 1. `store_front/index.html` (Versión `?v=30`)
- **Paso 2 (SSH)**: Modificado para contener descripciones detalladas, pasos explicativos y solución de problemas.
- **Paso 3 (Pantallas)**: Se estructuró el selector de modo de pantalla dual/simple (`wizard-screen-mode-single`, `wizard-screen-mode-dual`) y paneles condicionales.
- **Footer del Wizard**: Botones alineados y lógica de visualización del botón anterior modificada para estabilidad del layout.

### 2. `store_front/main.js` (Versión `?v=30`)
- **Lógica de Gamepad**: Captura del combo Select+Start y llamada a `/cerrar_emulador`.
- **Navegación**: Cierre automático del modal de controles al presionar cancelar.
- **Wizard Dinámico**:
  - `window._wizardScreenMode` controla qué configuración guardar.
  - Al seleccionar "Una sola pantalla", automáticamente clona el monitor del host al monitor de juegos y establece por defecto el workspace en `1`.
  - Integración de desplegables dinámicos en el menú flotante adaptado para mandos de juego (Couch Mode).

### 3. `bridge_api/routers/system.py`
- Añadido el endpoint de limpieza drástica:
  ```python
  @router.post("/cerrar_emulador")
  async def cerrar_emulador():
      # Ejecuta pkill en cascada para todos los emuladores soportados y Steam
  ```

---

## 💡 Análisis Técnico y Hallazgos Importantes

* **Ruta de Clave SSH**: La ruta de la clave SSH dentro del backend está preestablecida en `/root/.ssh/id_ed25519` en `bridge_api/config.py` (línea 14). Si el usuario requiere cambiar su ruta de clave o utiliza una firma personalizada, de momento no es configurable desde el archivo `.env` del usuario. Sería una mejora ideal hacer configurable `SSH_KEY_PATH` mediante `.env`.
* **Ajustes del Sistema**: La pantalla de Ajustes general del menú principal de la aplicación (`settings-view` en el HTML, líneas 158–198) **aún mantiene** el formato anterior de configuración de pantallas de 3 columnas (Workspace, Pantalla de destino y Pantalla de host). Esta sección no se ha simplificado porque priorizamos el Wizard, pero sigue sincronizándose correctamente con los valores que guarda el asistente.
* **Apertura de Steam**: El usuario reportó que Steam "no abre". Steam Big Picture se invoca mediante el script `scripts/setup_virtual_display.sh` ejecutando `steam -gamepadui` dentro de un entorno virtualizado en Hyprland. Se debe verificar si el backend de Hyprland en el host está permitiendo abrir la aplicación correctamente bajo el usuario del host.

---

## 🚀 Próximos Pasos Recomendados

Cuando reanudes el desarrollo con más tokens, te sugerimos seguir este orden de tareas:

1. **Prueba Completa del Asistente (Wizard End-to-End)**:
   - Iniciar la aplicación y ejecutar el wizard.
   - Probar el modo "🖥️ UNA SOLA PANTALLA" y el modo "📺 PC + TV SEPARADOS".
   - Confirmar que los datos se guarden adecuadamente en el backend y persistan al recargar la página.

2. **Unificar la Configuración de Pantalla en Ajustes**:
   - Replicar el sistema de Toggle ("Una pantalla" vs "PC+TV") en el panel `settings-view` de `index.html` para mantener consistencia y no confundir al usuario tras terminar el wizard.

3. **Diagnosticar el Lanzamiento de Steam**:
   - Verificar los logs de ejecución del comando de lanzamiento de Steam (`lanzar_steam_bigpicture` en `bridge_api/routers/emulator.py`).
   - Comprobar si hay errores de variables de entorno de visualización (`DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`) al hacer SSH desde el Docker del backend hacia el host de Hyprland.

4. **Validación Física de los Botones del Control**:
   - Confirmar que el mapeo de botones 8 (Select) y 9 (Start) corresponda exactamente a tu mando. En mandos de PlayStation, suele ser Share/Options; en Xbox, View/Menu. Si no coinciden, se puede añadir una tolerancia de detección en `pollGamepad()`.

5. **Mejora del `.env` para la Clave SSH**:
   - Hacer que `SSH_KEY_PATH` en `bridge_api/config.py` lea del entorno (usando `os.getenv("SSH_KEY_PATH", "/root/.ssh/id_ed25519")`) para evitar configuraciones rígidas.

---

*¡Progreso guardado de manera exitosa para la siguiente sesión! Puedes cerrar o reiniciar la sesión cuando gustes.*
