from __future__ import annotations
from dataclasses import dataclass

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject

from core.services.proxy_config_service import ConfigService
from .menu_builder import build_tray_menu
from .actions import create_tray_actions

@dataclass
class TrayDependencies:
    app: QApplication
    icon: QIcon
    main_window: QObject
    config_service: ConfigService
    
class TrayApp(QObject):
    def __init__(self, deps: TrayDependencies):
        super().__init__()
        self.deps = deps
        
        self.tray = QSystemTrayIcon(deps.icon, self)
        self.tray.setToolTip("SProxy2")
        
        self.actions = create_tray_actions(deps)
        
        self.menu = build_tray_menu(self.actions)
        self.tray.setContextMenu(self.menu)
        
        # Rebuild menu when shown to reflect current proxy list
        self.tray.activated.connect(self._on_tray_activated)
        
        self.tray.show()
    
    def _on_tray_activated(self, reason) -> None:
        """Rebuild menu when tray icon is interacted with."""
        if reason == QSystemTrayIcon.Context:
            self._rebuild_menu()
    
    def _rebuild_menu(self) -> None:
        """Rebuild the tray menu with current proxy list."""
        self.menu.clear()
        
        # Add proxy submenu
        proxies = self.deps.config_service.config.proxies
        if proxies:
            proxy_menu = self.menu.addMenu("Proxies")
            for name, proxy in proxies.items():
                proxy_action = QAction(f"{name} ({proxy.listen_address}:{proxy.listen_port})", self)
                proxy_action.setEnabled(False)  # Just for display
                proxy_menu.addAction(proxy_action)
        else:
            no_proxies = QAction("No proxies configured", self)
            no_proxies.setEnabled(False)
            self.menu.addAction(no_proxies)
        
        self.menu.addSeparator()
        self.menu.addAction(self.actions["show"])
        self.menu.addSeparator()
        self.menu.addAction(self.actions["quit"])
    
    def show_message(self, title: str, message: str) -> None:
        """Show a message in the system tray."""
        self.tray.showMessage(title, message)
    
    def exit_app(self) -> None:
        """Exit the application."""
        self.deps.app.quit() 