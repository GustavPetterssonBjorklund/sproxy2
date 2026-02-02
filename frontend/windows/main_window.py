from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from frontend.windows.new_proxy_dialog import NewProxyDialog
from frontend.windows.edit_proxy_dialog import EditProxyDialog
from frontend.widgets.proxy_list import ProxyListWidget, ProxyStatus
from core.services.proxy_config_service import ConfigService
from core.services.proxy_runner_service import ProxyRunnerService

@dataclass
class MainWindowDependencies:
    icon: QIcon
    tray_show_message: Callable[[str, str], None]
    exit_service: Callable[[], None]
    config_service: ConfigService
    proxy_runner: ProxyRunnerService

class MainWindow(QWidget):
    def __init__(self, deps: MainWindowDependencies):
        super().__init__()
        self.deps = deps

        self.setWindowTitle("SProxy2")
        self.setWindowIcon(deps.icon)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        
        # Header with add button
        header_layout = QVBoxLayout()
        header_layout.addWidget(QLabel("<h2>Simple Proxy 2</h2>"))
        
        new_proxy_btn = QPushButton("Add New Proxy")
        new_proxy_btn.clicked.connect(self._open_new_proxy_dialog)
        header_layout.addWidget(new_proxy_btn)
        
        layout.addLayout(header_layout)
        
        # Proxy list in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        self.proxy_list = ProxyListWidget(deps.config_service, deps.proxy_runner)
        self.proxy_list.proxy_started.connect(self._on_start_proxy)
        self.proxy_list.proxy_stopped.connect(self._on_stop_proxy)
        self.proxy_list.proxy_edited.connect(self._on_edit_proxy)
        
        scroll.setWidget(self.proxy_list)
        layout.addWidget(scroll)
    
    def _on_start_proxy(self, name: str) -> None:
        """Handle proxy start request."""
        try:
            proxy_config = self.deps.config_service.config.proxies.get(name)
            if not proxy_config:
                QMessageBox.warning(self, "Error", f"Proxy '{name}' not found")
                return
            
            self.deps.proxy_runner.start_proxy(name, proxy_config)
            self.proxy_list.set_proxy_status(name, ProxyStatus.RUNNING)
            self.deps.tray_show_message("Proxy Started", f"Started proxy '{name}'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start proxy: {e}")
    
    def _on_stop_proxy(self, name: str) -> None:
        """Handle proxy stop request."""
        try:
            self.deps.proxy_runner.stop_proxy(name)
            self.proxy_list.set_proxy_status(name, ProxyStatus.STOPPED)
            self.deps.tray_show_message("Proxy Stopped", f"Stopped proxy '{name}'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop proxy: {e}")
    
    def _on_edit_proxy(self, name: str) -> None:
        """Handle proxy edit request."""
        proxy_config = self.deps.config_service.config.proxies.get(name)
        if not proxy_config:
            QMessageBox.warning(self, "Error", f"Proxy '{name}' not found")
            return
        
        dialog = EditProxyDialog(name, proxy_config, self)
        if dialog.exec():
            new_name, addr, listen_port, bind_port, proxy_type, run_on_startup, ssh_username = dialog.get_values()
            try:
                # If name changed, remove old and add new
                if new_name != name:
                    self.deps.config_service.remove_proxy(name)
                    self.deps.config_service.add_proxy(
                        new_name, addr, listen_port, bind_port,
                        proxy_type=proxy_type,
                        run_on_startup=run_on_startup,
                        ssh_username=ssh_username
                    )
                else:
                    # Update existing proxy
                    self.deps.config_service.remove_proxy(name)
                    self.deps.config_service.add_proxy(
                        new_name, addr, listen_port, bind_port,
                        proxy_type=proxy_type,
                        run_on_startup=run_on_startup,
                        ssh_username=ssh_username
                    )
                
                self.proxy_list.refresh()
                self.deps.tray_show_message("Success", f"Proxy '{new_name}' updated successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to edit proxy: {e}")

    def _open_new_proxy_dialog(self):
        dialog = NewProxyDialog(self.deps.config_service, self)
        if dialog.exec():
            name, addr, listen_port, bind_port, proxy_type, run_on_startup, ssh_username = dialog.get_values()
            try:
                self.deps.config_service.add_proxy(
                    name, addr, listen_port, bind_port,
                    proxy_type=proxy_type,
                    run_on_startup=run_on_startup,
                    ssh_username=ssh_username
                )
                self.proxy_list.refresh()  # Refresh the list
                self.deps.tray_show_message("Success", f"Proxy '{name}' added successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add proxy: {e}")

    def closeEvent(self, event):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Exit SProxy2?")
        box.setText("Close the service completely or just hide the window?")
        box.setInformativeText("If you hide it, the service keeps running in the background (tray).")

        hide_btn = box.addButton("Hide to tray", QMessageBox.AcceptRole)
        exit_btn = box.addButton("Exit service", QMessageBox.DestructiveRole)  # FIXED
        box.addButton("Cancel", QMessageBox.RejectRole)

        box.setDefaultButton(hide_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked == hide_btn:
            event.ignore()
            self.hide()
            self.deps.tray_show_message(
                "SProxy2",
                "Still running in the background. Use the tray menu to quit.",
            )
        elif clicked == exit_btn:
            event.accept()
            self.deps.exit_service()
        else:
            event.ignore()