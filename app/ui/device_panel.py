"""Device connectivity panel."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.events import EventBus
from app.services.session import SessionManager


class DevicePanel(QGroupBox):  # pragma: no cover - requires Qt runtime
    def __init__(self, session: SessionManager, events: EventBus, parent: Optional[QWidget] = None) -> None:
        super().__init__("Device", parent)
        self._session = session
        self._events = events

        self._uri_edit = QLineEdit("usb:0")
        self._connect_button = QPushButton("Connect")
        self._disconnect_button = QPushButton("Disconnect")
        self._status_label = QLabel("Idle")

        form = QFormLayout()
        form.addRow("URI", self._uri_edit)
        form.addRow("Status", self._status_label)

        button_row = QHBoxLayout()
        button_row.addWidget(self._connect_button)
        button_row.addWidget(self._disconnect_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_row)
        layout.addStretch()

        self._connect_button.clicked.connect(self._connect)
        self._disconnect_button.clicked.connect(self._disconnect)

        events.subscribe("device_connected", self._on_connected)
        events.subscribe("device_disconnected", self._on_disconnected)

    def _connect(self) -> None:
        uri = self._uri_edit.text()
        try:
            self._session.connect(uri)
        except Exception as exc:  # pragma: no cover - shown in GUI
            self._status_label.setText(f"Error: {exc}")

    def _disconnect(self) -> None:
        self._session.disconnect()

    def _on_connected(self, payload: dict[str, object]) -> None:
        uri = payload.get("uri", "?")
        self._status_label.setText(f"Connected to {uri}")

    def _on_disconnected(self, payload: dict[str, object]) -> None:  # noqa: ARG002
        self._status_label.setText("Disconnected")


__all__ = ["DevicePanel"]
