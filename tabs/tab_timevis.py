"""Time and frequency visualization tab."""
from __future__ import annotations

import queue
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from dsp.analyzer import AnalyzerSettings, compute_fft
from pluto_manager import PlutoManager, StreamConfig
from widgets.controls import FlexFormLayout, LabeledSpinBox


class TimeVisualizationTab(QtWidgets.QWidget):
    """Display live IQ waveform and STFT waterfall."""

    def __init__(self, manager: PlutoManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._data_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=8)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._waterfall_lines = 200
        self._waterfall_data = np.zeros((self._waterfall_lines, 256))

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        control_layout = FlexFormLayout()
        self.center_spin = LabeledSpinBox(50e6, 6e9, 1e6, "Hz", decimals=0)
        self.center_spin.set_value(915e6)
        control_layout.addRow("Center Frequency", self.center_spin)

        self.sample_rate_spin = LabeledSpinBox(1e5, 61.44e6, 1e5, "S/s", decimals=0)
        self.sample_rate_spin.set_value(2.5e6)
        control_layout.addRow("Sample Rate", self.sample_rate_spin)

        self.buffer_spin = LabeledSpinBox(512, 16384, 512, "Samples", decimals=0)
        self.buffer_spin.set_value(4096)
        control_layout.addRow("Buffer", self.buffer_spin)

        self.nfft_spin = LabeledSpinBox(128, 4096, 128, "", decimals=0)
        self.nfft_spin.set_value(512)
        control_layout.addRow("STFT FFT", self.nfft_spin)

        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        control_layout.addRow(button_layout)

        main_layout.addLayout(control_layout)

        self.time_plot = pg.PlotWidget()
        self.time_plot.showGrid(x=True, y=True, alpha=0.3)
        self.time_plot.setBackground("#202020")
        self.time_plot.setLabel("bottom", "Time", units="s")
        self.time_plot.setLabel("left", "Amplitude")
        main_layout.addWidget(self.time_plot, 1)

        self.waterfall = pg.ImageView()
        self.waterfall.setPredefinedGradient("spectrum")
        self.waterfall.ui.histogram.hide()
        self.waterfall.ui.roiBtn.hide()
        self.waterfall.ui.menuBtn.hide()
        self.waterfall.getView().invertY(True)
        self.waterfall.getView().setAspectLocked(False)
        main_layout.addWidget(self.waterfall, 1)
        explanation = QtWidgets.QLabel("Waterfall: frequency (x) vs time (y, latest at bottom)")
        explanation.setStyleSheet("font-size: 12px; color: #dddddd;")
        main_layout.addWidget(explanation)

    def start(self) -> None:
        if self._timer.isActive():
            return
        self._waterfall_data = np.zeros((self._waterfall_lines, self.nfft_spin.value()))
        while not self._data_queue.empty():
            try:
                self._data_queue.get_nowait()
            except queue.Empty:
                break
        config = StreamConfig(
            sample_rate=self.sample_rate_spin.value(),
            center_frequency=self.center_spin.value(),
            bandwidth=self.sample_rate_spin.value(),
            buffer_size=int(self.buffer_spin.value()),
        )
        self.manager.start_rx_stream(config, self._enqueue_samples)
        self._timer.start(80)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop(self) -> None:
        self._timer.stop()
        self.manager.stop_rx_stream()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _enqueue_samples(self, samples: np.ndarray) -> None:
        try:
            self._data_queue.put_nowait(samples)
        except queue.Full:
            pass

    def _process_queue(self) -> None:
        if self._data_queue.empty():
            return
        try:
            data = self._data_queue.get_nowait()
        except queue.Empty:
            return

        sample_rate = self.sample_rate_spin.value()
        t = np.arange(data.size) / sample_rate
        self.time_plot.clear()
        self.time_plot.plot(t, data.real, pen=pg.mkPen("#00ff9f", width=2))
        self.time_plot.plot(t, data.imag, pen=pg.mkPen("#ff6f00", width=2))

        settings = AnalyzerSettings(sample_rate=sample_rate, nfft=int(self.nfft_spin.value()))
        _, magnitude = compute_fft(data, settings)
        norm_mag = (magnitude - magnitude.min()) / max(magnitude.ptp(), 1e-9)
        norm_mag = (norm_mag * 255).astype(np.uint8)
        self._waterfall_data = np.roll(self._waterfall_data, -1, axis=0)
        if norm_mag.size != self._waterfall_data.shape[1]:
            self._waterfall_data = np.zeros((self._waterfall_lines, norm_mag.size))
        self._waterfall_data[-1, :] = norm_mag
        freq_bins = self._waterfall_data.shape[1]
        freq_span = sample_rate
        freq_offset = -freq_span / 2
        row_time = data.size / sample_rate if sample_rate else 0.0
        self.waterfall.setImage(
            self._waterfall_data,
            autoLevels=False,
            pos=[freq_offset, -self._waterfall_lines * row_time],
            scale=[freq_span / max(freq_bins, 1), max(row_time, 1e-6)],
        )
        self.waterfall.setLevels(0, 255)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self.stop()
        super().closeEvent(event)
