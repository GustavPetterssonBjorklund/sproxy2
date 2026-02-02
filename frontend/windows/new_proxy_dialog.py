from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDialogButtonBox, QMessageBox, QComboBox, QCheckBox
)

class NewProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Proxy")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Proxy Name")

        self.listen_address_edit = QLineEdit("127.0.0.1")

        self.listen_port_spin = QSpinBox()
        self.listen_port_spin.setRange(1, 65535)
        self.listen_port_spin.setValue(1080)

        self.bind_port_spin = QSpinBox()
        self.bind_port_spin.setRange(1, 65535)
        self.bind_port_spin.setValue(22)

        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["socks5", "http"])

        self.ssh_username_edit = QLineEdit()
        self.ssh_username_edit.setPlaceholderText("Optional: SSH username for SOCKS5")

        self.run_on_startup_check = QCheckBox()

        form.addRow("Name:", self.name_edit)
        form.addRow("Listen Address:", self.listen_address_edit)
        form.addRow("Listen Port:", self.listen_port_spin)
        form.addRow("Bind Port:", self.bind_port_spin)
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

        # TODO: Check here for port collisions, fine for now but annoying UX
        self.accept()

    def get_values(self) -> tuple[str, str, int, int, str, bool, str | None]:
        return (
            self.name_edit.text().strip(),
            self.listen_address_edit.text().strip(),
            self.listen_port_spin.value(),
            self.bind_port_spin.value(),
            self.proxy_type_combo.currentText(),
            self.run_on_startup_check.isChecked(),
            self.ssh_username_edit.text().strip() or None,
        )
