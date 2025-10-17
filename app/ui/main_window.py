"""Main window wiring the panels together for the Windows GUI."""

from __future__ import annotations

from queue import Queue

from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QWidget

from app.core.config import AppConfig
from app.core.events import EventBus
from app.core.logger import get_logger
from app.services.session import SessionManager
from app.ui.console_panel import ConsolePanel
from app.ui.device_panel import DevicePanel
from app.ui.spectrum_panel import SpectrumPanel
from app.ui.tx_control_panel import TxControlPanel
from app.ui.waveform_panel import WaveformPanel

LOGGER = get_logger(__name__)


class MainWindow(QMainWindow):  # pragma: no cover - heavy GUI component
    def __init__(self, *, config: AppConfig, log_queue: Queue) -> None:
        super().__init__()
        self.setWindowTitle("Pluto+ Windows Control Board")
        self.resize(1600, 900)
        self._events = EventBus()
        self._session = SessionManager(config, events=self._events)
        self._log_queue = log_queue

        self._device_panel = DevicePanel(self._session, self._events)
        self._console_panel = ConsolePanel(log_queue)
        self._waveform_panel = WaveformPanel(self._session, self._events, config)
        self._tx_panel = TxControlPanel(self._session, self._events)
        self._spectrum_panel = SpectrumPanel(self._events)

        central = QWidget(self)
        layout = QHBoxLayout(central)
        layout.addWidget(self._device_panel, stretch=1)
        layout.addWidget(self._waveform_panel, stretch=2)
        layout.addWidget(self._tx_panel, stretch=2)
        layout.addWidget(self._spectrum_panel, stretch=3)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Ready")
        self._events.subscribe("device_connected", self._on_device_connected)
        self._events.subscribe("device_disconnected", self._on_device_disconnected)
        self._events.subscribe("tx_error", self._on_error)
        self._events.subscribe("rx_error", self._on_error)

    def _on_device_connected(self, payload: dict[str, object]) -> None:
        uri = payload.get("uri", "unknown")
        self.statusBar().showMessage(f"Connected to {uri}")

    def _on_device_disconnected(self, payload: dict[str, object]) -> None:  # noqa: ARG002
        self.statusBar().showMessage("Disconnected")

    def _on_error(self, payload: dict[str, object]) -> None:
        message = payload.get("message", "An error occurred")
        QMessageBox.critical(self, "Pluto+ Error", str(message))


__all__ = ["MainWindow"]
