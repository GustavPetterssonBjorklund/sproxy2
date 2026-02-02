import sys
import ctypes
import asyncio
import threading
from pathlib import Path
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "com.yourname.yourapp"
)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from frontend.windows.main_window import MainWindow, MainWindowDependencies
from frontend.tray.tray_app import TrayApp, TrayDependencies
from core.services.proxy_config_service import ConfigService
from core.services.proxy_runner_service import ProxyRunnerService
from core.config.proxy_config_parser import write_default_config

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep app running after main window is closed
    
    icon = QIcon("assets/icon.png")
    app.setWindowIcon(icon)
    
    config_path = Path("config.toml")
    if not config_path.exists():
        write_default_config(config_path)
    
    config_service = ConfigService(config_path)
    proxy_runner = ProxyRunnerService()
    
    # Create and start asyncio event loop in a background thread
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    proxy_runner.set_event_loop(loop)
    
    tray = TrayApp(TrayDependencies(
        app = app,
        icon = icon,
        main_window = None,  # Set after creating main window
        config_service = config_service,
        proxy_runner = proxy_runner,
    ))
    
    # Create main window with tray callbacks
    win = MainWindow(MainWindowDependencies(
        icon=icon,
        tray_show_message=tray.show_message,
        exit_service=tray.exit_app,
        config_service=config_service,
        proxy_runner=proxy_runner,
    ))
    win.hide()  # Start with the main window hidden
    
    tray.deps.main_window = win
    
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())