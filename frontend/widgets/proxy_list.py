from __future__ import annotations
from enum import Enum
from typing import Callable, TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal

from core.services.proxy_config_service import ConfigService

if TYPE_CHECKING:
    from core.services.proxy_runner_service import ProxyRunnerService


class ProxyStatus(Enum):
    """Status of a proxy instance."""
    STOPPED = "Stopped"
    RUNNING = "Running"
    ERROR = "Error"


class ProxyListItem(QFrame):
    """Individual proxy item showing name, endpoint, and status."""
    
    start_clicked = Signal(str)  # Emits proxy name
    stop_clicked = Signal(str)   # Emits proxy name
    delete_clicked = Signal(str) # Emits proxy name
    
    def __init__(self, name: str, listen_address: str, listen_port: int, parent=None):
        super().__init__(parent)
        self.proxy_name = name
        self.status = ProxyStatus.STOPPED
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)
        
        layout = QHBoxLayout(self)
        
        # Info section
        info_layout = QVBoxLayout()
        self.name_label = QLabel(f"<b>{name}</b>")
        self.endpoint_label = QLabel(f"{listen_address}:{listen_port}")
        self.endpoint_label.setStyleSheet("color: gray; font-size: 10px;")
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.endpoint_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Status label
        self.status_label = QLabel("Stopped")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumWidth(80)
        self._update_status_style()
        layout.addWidget(self.status_label)
        
        # Control buttons
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(lambda: self.start_clicked.emit(self.proxy_name))
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(lambda: self.stop_clicked.emit(self.proxy_name))
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.proxy_name))
        layout.addWidget(self.delete_btn)
    
    def set_status(self, status: ProxyStatus) -> None:
        """Update the status display."""
        self.status = status
        self.status_label.setText(status.value)
        self._update_status_style()
        
        # Update button states
        if status == ProxyStatus.RUNNING:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def _update_status_style(self) -> None:
        """Update status label styling based on current status."""
        if self.status == ProxyStatus.RUNNING:
            color = "green"
        elif self.status == ProxyStatus.ERROR:
            color = "red"
        else:
            color = "gray"
        
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")


class ProxyListWidget(QWidget):
    """Reusable widget displaying all configured proxies."""
    
    proxy_started = Signal(str)  # Emits proxy name
    proxy_stopped = Signal(str)  # Emits proxy name
    proxy_deleted = Signal(str)  # Emits proxy name
    
    def __init__(self, config_service: ConfigService, proxy_runner: ProxyRunnerService | None = None, parent=None):
        super().__init__(parent)
        self.config_service = config_service
        self.proxy_runner = proxy_runner
        self.proxy_items: dict[str, ProxyListItem] = {}
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        
        self.refresh()
    
    def refresh(self) -> None:
        """Refresh the proxy list from config."""
        # Clear existing items
        for item in self.proxy_items.values():
            self.layout.removeWidget(item)
            item.deleteLater()
        self.proxy_items.clear()
        
        # Add current proxies
        for name, proxy in self.config_service.config.proxies.items():
            item = ProxyListItem(name, proxy.listen_address, proxy.listen_port, self)
            item.start_clicked.connect(self._on_start_proxy)
            item.stop_clicked.connect(self._on_stop_proxy)
            item.delete_clicked.connect(self._on_delete_proxy)
            
            # Restore running status if proxy_runner is available
            if self.proxy_runner and self.proxy_runner.is_proxy_running(name):
                item.set_status(ProxyStatus.RUNNING)
            
            self.proxy_items[name] = item
            self.layout.addWidget(item)
        
        # Add empty state if no proxies
        if not self.proxy_items:
            empty_label = QLabel("No proxies configured")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: gray; padding: 20px;")
            self.layout.addWidget(empty_label)
    
    def set_proxy_status(self, name: str, status: ProxyStatus) -> None:
        """Update the status of a specific proxy."""
        if name in self.proxy_items:
            self.proxy_items[name].set_status(status)
    
    def _on_start_proxy(self, name: str) -> None:
        """Handle start button click."""
        self.proxy_started.emit(name)
    
    def _on_stop_proxy(self, name: str) -> None:
        """Handle stop button click."""
        self.proxy_stopped.emit(name)
    
    def _on_delete_proxy(self, name: str) -> None:
        """Handle delete button click."""
        self.proxy_deleted.emit(name)
