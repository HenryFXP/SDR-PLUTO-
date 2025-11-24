from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dsp import concatenate_buffers
from pluto_controller import PlutoController
from rx_worker import RxWorker
from sigmf_io import load_sigmf, save_sigmf
from tx_worker import TxWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pluto SDR Toolkit")
        self.controller = PlutoController()
        self.rx_worker: Optional[RxWorker] = None
        self.tx_worker: Optional[TxWorker] = None
        self.tx_data: np.ndarray = np.array([], dtype=np.complex64)

        self._build_ui()
        self._update_connection_state(False)
        self._refresh_contexts()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout()
        central.setLayout(layout)
        layout.addWidget(self._build_device_bar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_rx_tab(), "RX Spectrum/Record")
        self.tabs.addTab(self._build_tx_tab(), "TX Replay")
        layout.addWidget(self.tabs)

        self.setCentralWidget(central)

    def _build_device_bar(self) -> QWidget:
        bar = QWidget()
        hbox = QHBoxLayout()
        bar.setLayout(hbox)

        hbox.addWidget(QLabel("Device:"))
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_contexts)
        hbox.addWidget(self.refresh_button)

        self.uri_combo = QComboBox()
        hbox.addWidget(self.uri_combo, 1)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect)
        hbox.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self._disconnect)
        hbox.addWidget(self.disconnect_button)
        return bar

    def _build_rx_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        form = QGridLayout()
        self.rx_freq = QDoubleSpinBox()
        self.rx_freq.setSuffix(" Hz")
        self.rx_freq.setMaximum(6e9)
        self.rx_freq.setValue(1e9)
        form.addWidget(QLabel("Center Freq"), 0, 0)
        form.addWidget(self.rx_freq, 0, 1)

        self.rx_samplerate = QDoubleSpinBox()
        self.rx_samplerate.setSuffix(" sps")
        self.rx_samplerate.setMaximum(61.44e6)
        self.rx_samplerate.setValue(1e6)
        form.addWidget(QLabel("Sample Rate"), 1, 0)
        form.addWidget(self.rx_samplerate, 1, 1)

        self.rx_bandwidth = QDoubleSpinBox()
        self.rx_bandwidth.setSuffix(" Hz")
        self.rx_bandwidth.setMaximum(61.44e6)
        self.rx_bandwidth.setValue(self.rx_samplerate.value())
        form.addWidget(QLabel("RF Bandwidth"), 2, 0)
        form.addWidget(self.rx_bandwidth, 2, 1)

        self.gain_mode = QComboBox()
        self.gain_mode.addItems(["slow_attack", "fast_attack", "manual"])
        form.addWidget(QLabel("Gain Mode"), 3, 0)
        form.addWidget(self.gain_mode, 3, 1)

        self.rx_gain = QDoubleSpinBox()
        self.rx_gain.setRange(-10.0, 70.0)
        self.rx_gain.setValue(10.0)
        self.rx_gain.setSuffix(" dB")
        form.addWidget(QLabel("Manual Gain"), 4, 0)
        form.addWidget(self.rx_gain, 4, 1)

        self.rx_buffer = QSpinBox()
        self.rx_buffer.setRange(1024, 1024 * 1024)
        self.rx_buffer.setValue(8192)
        form.addWidget(QLabel("Buffer Size"), 5, 0)
        form.addWidget(self.rx_buffer, 5, 1)

        layout.addLayout(form)

        self.start_rx_button = QPushButton("Start RX")
        self.start_rx_button.clicked.connect(self._start_rx)
        self.stop_rx_button = QPushButton("Stop RX")
        self.stop_rx_button.clicked.connect(self._stop_rx)

        button_bar = QHBoxLayout()
        button_bar.addWidget(self.start_rx_button)
        button_bar.addWidget(self.stop_rx_button)

        self.record_toggle = QPushButton("Record")
        self.record_toggle.setCheckable(True)
        self.record_toggle.toggled.connect(self._toggle_recording)
        button_bar.addWidget(self.record_toggle)

        self.save_button = QPushButton("Save SigMF")
        self.save_button.clicked.connect(self._save_recording)
        button_bar.addWidget(self.save_button)

        layout.addLayout(button_bar)

        self.spectrum_plot = pg.PlotWidget(title="RX Spectrum")
        self.spectrum_plot.setLabel("bottom", "Frequency", units="Hz")
        self.spectrum_plot.setLabel("left", "Power", units="dB")
        self.spectrum_curve = self.spectrum_plot.plot([], [])
        layout.addWidget(self.spectrum_plot, 1)

        return tab

    def _build_tx_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        form = QGridLayout()
        self.tx_freq = QDoubleSpinBox()
        self.tx_freq.setSuffix(" Hz")
        self.tx_freq.setMaximum(6e9)
        self.tx_freq.setValue(1e9)
        form.addWidget(QLabel("Center Freq"), 0, 0)
        form.addWidget(self.tx_freq, 0, 1)

        self.tx_samplerate = QDoubleSpinBox()
        self.tx_samplerate.setSuffix(" sps")
        self.tx_samplerate.setMaximum(61.44e6)
        self.tx_samplerate.setValue(1e6)
        form.addWidget(QLabel("Sample Rate"), 1, 0)
        form.addWidget(self.tx_samplerate, 1, 1)

        self.tx_bandwidth = QDoubleSpinBox()
        self.tx_bandwidth.setSuffix(" Hz")
        self.tx_bandwidth.setMaximum(61.44e6)
        self.tx_bandwidth.setValue(self.tx_samplerate.value())
        form.addWidget(QLabel("RF Bandwidth"), 2, 0)
        form.addWidget(self.tx_bandwidth, 2, 1)

        self.tx_attenuation = QDoubleSpinBox()
        self.tx_attenuation.setRange(-90, 0)
        self.tx_attenuation.setValue(-10)
        self.tx_attenuation.setSuffix(" dB")
        form.addWidget(QLabel("Attenuation"), 3, 0)
        form.addWidget(self.tx_attenuation, 3, 1)

        self.tx_cyclic = QCheckBox("Cyclic")
        form.addWidget(QLabel("Mode"), 4, 0)
        form.addWidget(self.tx_cyclic, 4, 1)

        layout.addLayout(form)

        file_bar = QHBoxLayout()
        self.meta_path_edit = QLineEdit()
        self.meta_path_edit.setPlaceholderText("SigMF .sigmf-meta path")
        file_bar.addWidget(self.meta_path_edit, 1)
        load_button = QPushButton("Load SigMF")
        load_button.clicked.connect(self._load_sigmf)
        file_bar.addWidget(load_button)
        layout.addLayout(file_bar)

        tx_buttons = QHBoxLayout()
        self.tx_once_button = QPushButton("Play Once")
        self.tx_once_button.clicked.connect(self._play_once)
        tx_buttons.addWidget(self.tx_once_button)

        self.tx_cyclic_button = QPushButton("Play Cyclic")
        self.tx_cyclic_button.clicked.connect(self._play_cyclic)
        tx_buttons.addWidget(self.tx_cyclic_button)
        layout.addLayout(tx_buttons)
        return tab

    def _refresh_contexts(self) -> None:
        self.uri_combo.clear()
        self.uri_combo.addItem("auto")
        contexts = self.controller.scan_contexts()
        for uri in contexts.keys():
            self.uri_combo.addItem(uri)

    def _connect(self) -> None:
        uri = self.uri_combo.currentText()
        try:
            self.controller.connect(uri if uri else None)
            self._update_connection_state(True)
        except Exception as exc:
            self._show_error(str(exc))

    def _disconnect(self) -> None:
        self._stop_rx()
        if self.tx_worker and self.tx_worker.isRunning():
            self.tx_worker.terminate()
        self.controller.disconnect()
        self._update_connection_state(False)

    def _update_connection_state(self, connected: bool) -> None:
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.tabs.setTabEnabled(0, connected)
        self.tabs.setTabEnabled(1, connected)

    def _collect_rx_settings(self) -> Dict[str, float]:
        bw = self.rx_bandwidth.value() or self.rx_samplerate.value()
        return {
            "center_frequency": self.rx_freq.value(),
            "sample_rate": self.rx_samplerate.value(),
            "rf_bandwidth": bw,
            "gain_mode": self.gain_mode.currentText(),
            "gain": self.rx_gain.value(),
            "buffer_size": self.rx_buffer.value(),
        }

    def _start_rx(self) -> None:
        if not self.controller.connected:
            self._show_error("Pluto not connected")
            return
        if self.rx_worker and self.rx_worker.isRunning():
            return
        settings = self._collect_rx_settings()
        self.rx_worker = RxWorker(self.controller, settings)
        self.rx_worker.spectrum_ready.connect(self._update_spectrum)
        self.rx_worker.error.connect(self._show_error)
        self.rx_worker.data_ready.connect(lambda _: None)
        self.rx_worker.start()

    def _stop_rx(self) -> None:
        if self.rx_worker:
            self.rx_worker.stop()
            self.rx_worker = None

    def _toggle_recording(self, enabled: bool) -> None:
        if not self.rx_worker:
            self.record_toggle.setChecked(False)
            return
        if enabled:
            self.rx_worker.clear_buffers()
        self.rx_worker.set_recording(enabled)

    def _save_recording(self) -> None:
        if not self.rx_worker or not self.rx_worker.buffers:
            self._show_error("No recorded data to save")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SigMF", filter="SigMF Meta (*.sigmf-meta)"
        )
        if not file_path:
            return
        iq = concatenate_buffers(self.rx_worker.buffers)
        try:
            save_sigmf(
                Path(file_path),
                iq,
                center_frequency=self.rx_freq.value(),
                sample_rate=self.rx_samplerate.value(),
                gain=self.rx_gain.value(),
            )
        except Exception as exc:
            self._show_error(str(exc))

    def _update_spectrum(self, freqs: np.ndarray, psd: np.ndarray) -> None:
        self.spectrum_curve.setData(freqs, psd)

    def _load_sigmf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open SigMF", filter="SigMF Meta (*.sigmf-meta)")
        if not path:
            return
        self.meta_path_edit.setText(path)
        try:
            data, info = load_sigmf(Path(path))
        except Exception as exc:
            self._show_error(str(exc))
            return
        self.tx_data = data
        if info.get("center_frequency"):
            self.tx_freq.setValue(info["center_frequency"])
        if info.get("sample_rate"):
            self.tx_samplerate.setValue(info["sample_rate"])
            self.tx_bandwidth.setValue(info["sample_rate"])
        if info.get("gain"):
            self.tx_attenuation.setValue(info["gain"])

    def _collect_tx_settings(self) -> Dict[str, float]:
        bw = self.tx_bandwidth.value() or self.tx_samplerate.value()
        return {
            "center_frequency": self.tx_freq.value(),
            "sample_rate": self.tx_samplerate.value(),
            "rf_bandwidth": bw,
            "attenuation": self.tx_attenuation.value(),
            "cyclic": self.tx_cyclic.isChecked(),
        }

    def _play_once(self) -> None:
        self._start_tx(cyclic=False)

    def _play_cyclic(self) -> None:
        self._start_tx(cyclic=True)

    def _start_tx(self, cyclic: bool) -> None:
        if not self.controller.connected:
            self._show_error("Pluto not connected")
            return
        if self.tx_worker and self.tx_worker.isRunning():
            return
        settings = self._collect_tx_settings()
        chosen_cyclic = cyclic or settings.pop("cyclic", False)
        self.tx_worker = TxWorker(self.controller, settings, self.tx_data, chosen_cyclic)
        self.tx_worker.error.connect(self._show_error)
        self.tx_worker.finished_once.connect(self._on_tx_finished)
        self.tx_worker.start()

    def _on_tx_finished(self) -> None:
        QMessageBox.information(self, "TX", "Playback finished")

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message or "Unknown error")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._disconnect()
        super().closeEvent(event)
