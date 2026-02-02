from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QComboBox, QCheckBox
)
from core.config.proxy_config_parser import ProxyConfig


class EditProxyDialog(QDialog):
    def __init__(self, proxy_name: str, proxy_config: ProxyConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Proxy: {proxy_name}")
        self.setModal(True)
        self.proxy_name = proxy_name
        self.original_config = proxy_config

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setText(proxy_name)

        self.listen_address_edit = QLineEdit()
        self.listen_address_edit.setText(proxy_config.listen_address)

        self.listen_port_spin = QSpinBox()
        self.listen_port_spin.setRange(1, 65535)
        self.listen_port_spin.setValue(proxy_config.listen_port)

        self.bind_port_spin = QSpinBox()
        self.bind_port_spin.setRange(1, 65535)
        self.bind_port_spin.setValue(proxy_config.bind_port)

        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["socks5", "http"])
        self.proxy_type_combo.setCurrentText(proxy_config.proxy_type)

        self.ssh_username_edit = QLineEdit()
        if proxy_config.ssh_username:
            self.ssh_username_edit.setText(proxy_config.ssh_username)
        self.ssh_username_edit.setPlaceholderText("Optional: SSH username for SOCKS5")

        self.run_on_startup_check = QCheckBox()
        self.run_on_startup_check.setChecked(proxy_config.run_on_startup)

        form.addRow("Name:", self.name_edit)
        form.addRow("Listen Address:", self.listen_address_edit)
        form.addRow("Expose Port:", self.listen_port_spin)
        form.addRow("SSH Port:", self.bind_port_spin)
        form.addRow("Proxy Type:", self.proxy_type_combo)
        form.addRow("SSH Username:", self.ssh_username_edit)
        form.addRow("Run on Startup:", self.run_on_startup_check)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        addr = self.listen_address_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid input", "Name is required.")
            return
        if not addr:
            QMessageBox.warning(self, "Invalid input", "Listen address is required.")
            return

        self.accept()

    def get_values(self) -> tuple[str, str, int, int, str, bool, str | None]:
        """Returns: (name, listen_address, listen_port, bind_port, proxy_type, run_on_startup, ssh_username)"""
        return (
            self.name_edit.text().strip(),
            self.listen_address_edit.text().strip(),
            self.listen_port_spin.value(),
            self.bind_port_spin.value(),
            self.proxy_type_combo.currentText(),
            self.run_on_startup_check.isChecked(),
            self.ssh_username_edit.text().strip() or None,
        )
