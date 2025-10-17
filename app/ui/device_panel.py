"""Panel providing device connection controls and telemetry."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6 import QtCore, QtWidgets

from app.core.config import AppConfig
from app.core.logger import get_logger
from app.core.types import DeviceConn
from app.services.session import SessionManager

LOGGER = get_logger(__name__)


class DevicePanel(QtWidgets.QGroupBox):
    device_connected = QtCore.pyqtSignal(DeviceConn)
    device_disconnected = QtCore.pyqtSignal()

    def __init__(self, session: SessionManager, config: AppConfig, use_mock: bool, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Device", parent)
        self.session = session
        self.config = config
        self.use_mock = use_mock
        default_uri = os.getenv("PLUTO_URI", "usb:0")
        self.uri_edit = QtWidgets.QLineEdit(default_uri)
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.status_label = QtWidgets.QLabel("Disconnected")
        self.temp_label = QtWidgets.QLabel("-- °C")
        self.ext_ref_checkbox = QtWidgets.QCheckBox("External Reference")
        self.ext_ref_checkbox.setEnabled(False)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(QtWidgets.QLabel("URI"), 0, 0)
        layout.addWidget(self.uri_edit, 0, 1, 1, 2)
        layout.addWidget(self.connect_button, 1, 0)
        layout.addWidget(self.disconnect_button, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addWidget(QtWidgets.QLabel("Temperature"), 2, 0)
        layout.addWidget(self.temp_label, 2, 1)
        layout.addWidget(self.ext_ref_checkbox, 2, 2)

        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button.clicked.connect(self._disconnect)
        self.disconnect_button.setEnabled(False)
        self.ext_ref_checkbox.toggled.connect(self._set_external_reference)

    def _connect(self) -> None:
        uri = self.uri_edit.text()
        try:
            conn = self.session.connect(uri, use_mock=self.use_mock)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection Error", str(exc))
            return
        self.status_label.setText(f"Connected to {conn.serial or conn.uri}")
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.ext_ref_checkbox.setEnabled(True)
        self.device_connected.emit(conn)

    def _disconnect(self) -> None:
        self.session.disconnect()
        self.status_label.setText("Disconnected")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.ext_ref_checkbox.setEnabled(False)
        self.device_disconnected.emit()

    def refresh_status(self) -> None:
        if not self.session.connection:
            return
        temperature = self.session.driver.read_temperature()
        if temperature is not None:
            self.temp_label.setText(f"{temperature:.1f} °C")

    def _set_external_reference(self, enabled: bool) -> None:
        if not self.session.connection:
            return
        success = self.session.driver.set_external_reference(enabled)
        if not success:
            QtWidgets.QMessageBox.warning(self, "External Reference", "Failed to toggle external reference")


__all__ = ["DevicePanel"]
