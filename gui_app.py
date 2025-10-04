"""Qt application window for the PlutoSDR GUI."""
from __future__ import annotations

import logging

from PyQt5 import QtCore, QtGui, QtWidgets

from pluto_manager import PlutoManager
from tabs.tab_spectrum import SpectrumAnalyzerTab
from tabs.tab_timevis import TimeVisualizationTab
from tabs.tab_transmitter import TransmitterTab
from tabs.tab_waveform import WaveformGeneratorTab, WaveformConfig

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """Primary application window hosting all tabs."""

    def __init__(self, manager: PlutoManager, dry_run: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("PlutoSDR Control Studio")
        self.resize(1400, 900)
        self.manager = manager
        self.dry_run = dry_run

        self._create_widgets()
        self._populate_devices()
        self._connect_signals()

    def _create_widgets(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setSpacing(12)
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.setMinimumWidth(260)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.status_label = QtWidgets.QLabel("No device connected")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.dry_run_label = QtWidgets.QLabel("Dry-Run" if self.dry_run else "Hardware Mode")
        self.dry_run_label.setStyleSheet("color: #ffaa00; font-weight: bold;" if self.dry_run else "color: #55ff55;")
        top_bar.addWidget(QtWidgets.QLabel("Pluto Device:"))
        top_bar.addWidget(self.device_combo)
        top_bar.addWidget(self.refresh_button)
        top_bar.addWidget(self.connect_button)
        top_bar.addWidget(self.dry_run_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.status_label)
        layout.addLayout(top_bar)

        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget, 1)

        self.waveform_tab = WaveformGeneratorTab()
        self.spectrum_tab = SpectrumAnalyzerTab(self.manager)
        self.transmitter_tab = TransmitterTab(self.manager)
        self.time_tab = TimeVisualizationTab(self.manager)

        self.tab_widget.addTab(self.waveform_tab, "Waveform Generator")
        self.tab_widget.addTab(self.spectrum_tab, "Spectrum Analyzer")
        self.tab_widget.addTab(self.transmitter_tab, "Transmitter")
        self.tab_widget.addTab(self.time_tab, "Time Visualization")

    def _populate_devices(self) -> None:
        devices = self.manager.available_devices()
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem("No Pluto Found")
            self.device_combo.setEnabled(False)
            self.connect_button.setEnabled(False)
        else:
            self.device_combo.addItems(devices)
            self.device_combo.setEnabled(True)
            self.connect_button.setEnabled(True)
        logger.info("Detected devices: %s", devices)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self._populate_devices)
        self.connect_button.clicked.connect(self._connect_device)
        self.waveform_tab.waveform_generated.connect(self._handle_waveform)

    def _connect_device(self) -> None:
        if not self.device_combo.count():
            return
        uri = self.device_combo.currentText()
        device = self.manager.connect(uri if "No Pluto" not in uri else None)
        self.status_label.setText(f"Connected to {device.uri}")

    def _handle_waveform(self, data, config: WaveformConfig) -> None:
        self.transmitter_tab.set_waveform(data)
        self.transmitter_tab.sample_rate_spin.set_value(config.sample_rate)
        self.transmitter_tab.center_spin.set_value(config.center_frequency)
        self.transmitter_tab.bandwidth_spin.set_value(config.bandwidth)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self.manager.stop_rx_stream()
        self.manager.disable_tx()
        super().closeEvent(event)
