"""Top-level window wiring together all UI panels."""

from __future__ import annotations

from queue import Queue
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from app.core.config import AppConfig
from app.core.events import GLOBAL_BUS
from app.core.logger import get_logger
from app.core.types import DeviceConn, TxConfig
from app.services.session import SessionManager
from app.services.tx_pipeline import TxPipeline
from app.services.rx_pipeline import RxPipeline
from app.services.profiles import ProfileStore
from .console_panel import ConsolePanel
from .device_panel import DevicePanel
from .spectrum_panel import SpectrumPanel
from .tx_control_panel import TxControlPanel
from .waveform_panel import WaveformPanel
from .device_svg import DeviceSvgWidget

LOGGER = get_logger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """Primary control window for the Pluto+ dual TX station."""

    def __init__(
        self,
        config: AppConfig,
        session: SessionManager,
        gui_queue: Queue,
        use_mock: bool = False,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pluto+ Control Board")
        self.resize(1400, 900)
        self.config = config
        self.session = session
        self.gui_queue = gui_queue
        self.use_mock = use_mock
        self.tx_pipeline: Optional[TxPipeline] = None
        self.rx_pipeline: Optional[RxPipeline] = None
        self.profiles = ProfileStore(config)

        self._build_ui()
        self._connect_signals()
        self._start_timers()
        self.session.start_discovery()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(central)
        self.device_panel = DevicePanel(self.session, self.config, self.use_mock)
        self.waveform_panel = WaveformPanel(self.config)
        self.tx_panel = TxControlPanel(self.config)
        self.console_panel = ConsolePanel()
        self.console_panel.attach_queue(self.gui_queue)
        self.spectrum_panel = SpectrumPanel(self.config)
        self.device_svg = DeviceSvgWidget()

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.device_panel)
        left_layout.addWidget(self.waveform_panel)
        left_layout.addWidget(self.tx_panel)
        left_layout.setStretch(1, 1)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.spectrum_panel)
        right_layout.addWidget(self.console_panel)
        right_layout.setStretch(0, 3)
        right_layout.setStretch(1, 2)

        layout.addLayout(left_layout, 0, 0)
        layout.addLayout(right_layout, 0, 1)
        layout.addWidget(self.device_svg, 1, 0, 1, 2)
        layout.setRowStretch(0, 5)
        layout.setRowStretch(1, 1)

        self.setCentralWidget(central)
        self._load_stylesheet()

    def _load_stylesheet(self) -> None:
        path = QtCore.QFile("resources/style.qss")
        if path.exists():
            if path.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
                stylesheet = bytes(path.readAll()).decode("utf-8")
                self.setStyleSheet(stylesheet)

    def _connect_signals(self) -> None:
        self.device_panel.device_connected.connect(self._on_device_connected)
        self.device_panel.device_disconnected.connect(self._on_device_disconnected)
        self.tx_panel.tx_config_requested.connect(self._on_tx_config)
        self.tx_panel.tx_stop_requested.connect(self._on_tx_stop)
        self.waveform_panel.waveform_generated.connect(self._on_waveform_generated)
        GLOBAL_BUS.subscribe("rx:spectrum", self.spectrum_panel.update_spectrum)
        GLOBAL_BUS.subscribe("waveform:warning", self.waveform_panel.show_warning)

    def _start_timers(self) -> None:
        self._log_timer = QtCore.QTimer(self)
        self._log_timer.timeout.connect(self.console_panel.drain_queue)
        self._log_timer.start(200)

        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self.device_panel.refresh_status)
        self._status_timer.start(2000)

    def _on_device_connected(self, connection: DeviceConn) -> None:
        self.tx_pipeline = TxPipeline(self.session.driver)
        self.rx_pipeline = RxPipeline(self.session.driver, self.config.tx1.sample_rate_sps)
        self.rx_pipeline.start()
        self.tx_panel.set_enabled(True)
        self.waveform_panel.set_enabled(True)
        self.device_svg.set_status(True)

    def _on_device_disconnected(self) -> None:
        if self.tx_pipeline:
            self.tx_pipeline.shutdown()
            self.tx_pipeline = None
        if self.rx_pipeline:
            self.rx_pipeline.stop()
            self.rx_pipeline = None
        self.tx_panel.set_enabled(False)
        self.waveform_panel.set_enabled(False)
        self.device_svg.set_status(False)

    def _on_tx_config(self, config: TxConfig) -> None:
        if not self.tx_pipeline:
            return
        spec = self.tx_pipeline.configure(config)
        self.tx_panel.update_waveform_metadata(config.channel, spec)

    def _on_tx_stop(self, channel: str) -> None:
        if self.tx_pipeline:
            self.tx_pipeline.stop(channel)

    def _on_waveform_generated(self, channel: str, iq, spec) -> None:
        if self.tx_pipeline:
            self.tx_pipeline.push_waveform(channel, iq, spec)
            self.tx_panel.update_waveform_metadata(channel, spec)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.session.stop_discovery()
        if self.tx_pipeline:
            self.tx_pipeline.shutdown()
        if self.rx_pipeline:
            self.rx_pipeline.stop()
        super().closeEvent(event)


__all__ = ["MainWindow"]
