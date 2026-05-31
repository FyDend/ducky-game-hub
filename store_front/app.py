import sys
import os
from PyQt6.QtCore import QUrl, QEvent
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RetroCloud Sovereign Game Pass")
        
        # Iniciar en pantalla completa nativa
        self.showFullScreen()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.showFullScreen()
        super().changeEvent(event)
        
        # Crear la vista de WebEngine y habilitar permisos para consultar la API local
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Configurar almacenamiento persistente de Chromium para cookies, localStorage, etc.
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentStoragePath("/app/data/profile")
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        
        # Cargar index.html a través del servidor FastAPI local en lugar de file:// para evitar bloqueos de seguridad de Chromium
        self.web_view.setUrl(QUrl("http://127.0.0.1:8000/store_front/index.html"))
        
        self.setCentralWidget(self.web_view)

if __name__ == "__main__":
    # Usar Wayland si está disponible, de lo contrario fallback a X11 (xcb)
    if os.environ.get("WAYLAND_DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "wayland"
    else:
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        
    # Desactivar sandbox de Chromium para permitir ejecución como root en Docker
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    sys_args = sys.argv + [
        "--no-sandbox", 
        "--disable-web-security", 
        "--allow-running-insecure-content",
        "--ignore-gpu-blocklist",
        "--enable-gpu-rasterization",
        "--enable-oop-rasterization",
        "--use-gl=desktop"
    ]
    app = QApplication(sys_args)
    
    # Definir nombre de la aplicación para que Hyprland la capture con la clase "retrocloud-app"
    app.setApplicationName("retrocloud-app")
    app.setApplicationDisplayName("RetroCloud")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
