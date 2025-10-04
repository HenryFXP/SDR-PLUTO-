"""Spectrum Analyzer tab implementation."""
from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from dsp.analyzer import (
    AnalyzerSettings,
    compute_psd,
    update_max_hold,
    update_min_hold,
)
from pluto_manager import PlutoManager, StreamConfig
from widgets.controls import FlexFormLayout, LabeledSpinBox


@dataclass
class Marker:
    line: pg.InfiniteLine
    label: QtWidgets.QLabel


class SpectrumAnalyzerTab(QtWidgets.QWidget):
    """Live FFT/PSD visualization with markers and hold modes."""

    def __init__(self, manager: PlutoManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._data_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=10)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._max_hold: Optional[np.ndarray] = None
        self._min_hold: Optional[np.ndarray] = None
        self._avg_accum: Optional[np.ndarray] = None
        self._current_freqs: Optional[np.ndarray] = None
        self._current_psd: Optional[np.ndarray] = None
        self._markers: List[Marker] = []

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        control_widget = QtWidgets.QWidget()
        control_layout = FlexFormLayout(control_widget)
        control_widget.setLayout(control_layout)

        self.center_spin = LabeledSpinBox(50e6, 6e9, 1e6, "Hz", decimals=0)
        self.center_spin.set_value(915e6)
        control_layout.addRow("Center Frequency", self.center_spin)

        self.sample_rate_spin = LabeledSpinBox(1e5, 61.44e6, 1e5, "S/s", decimals=0)
        self.sample_rate_spin.set_value(2.5e6)
        control_layout.addRow("Sample Rate", self.sample_rate_spin)

        self.span_spin = LabeledSpinBox(1e5, 20e6, 1e5, "Hz", decimals=0)
        self.span_spin.set_value(2.5e6)
        control_layout.addRow("Span", self.span_spin)

        self.rbw_spin = LabeledSpinBox(100, 100_000, 100, "Hz", decimals=0)
        self.rbw_spin.set_value(5_000)
        control_layout.addRow("RBW", self.rbw_spin)

        self.average_spin = LabeledSpinBox(1, 32, 1, "", decimals=0)
        self.average_spin.set_value(4)
        control_layout.addRow("Averages", self.average_spin)

        detector_layout = QtWidgets.QHBoxLayout()
        detector_layout.setContentsMargins(0, 0, 0, 0)
        detector_layout.setSpacing(8)
        self.detector_combo = QtWidgets.QComboBox()
        self.detector_combo.addItems(["Sample", "Positive", "Negative"])
        detector_layout.addWidget(QtWidgets.QLabel("Detector"))
        detector_layout.addWidget(self.detector_combo)
        control_layout.addRow(detector_layout)

        holds_layout = QtWidgets.QHBoxLayout()
        holds_layout.setContentsMargins(0, 0, 0, 0)
        holds_layout.setSpacing(16)
        self.max_hold_check = QtWidgets.QCheckBox("Max Hold")
        self.min_hold_check = QtWidgets.QCheckBox("Min Hold")
        self.average_check = QtWidgets.QCheckBox("Averaging")
        self.average_check.setChecked(True)
        holds_layout.addWidget(self.max_hold_check)
        holds_layout.addWidget(self.min_hold_check)
        holds_layout.addWidget(self.average_check)
        control_layout.addRow(holds_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        control_layout.addRow(buttons_layout)

        main_layout.addWidget(control_widget)

        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Frequency Offset", units="Hz")
        self.plot.setLabel("left", "Power", units="dBFS")
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setBackground("#202020")
        main_layout.addWidget(self.plot, 1)

        marker_container = QtWidgets.QWidget()
        marker_layout = QtWidgets.QVBoxLayout(marker_container)
        marker_layout.setContentsMargins(0, 0, 0, 0)
        marker_layout.setSpacing(4)
        for index in range(4):
            line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen(color=pg.intColor(index), width=2))
            self.plot.addItem(line)
            label = QtWidgets.QLabel(f"Marker {index + 1}: -- Hz / -- dB")
            marker_layout.addWidget(label)
            line.sigPositionChanged.connect(self._update_marker_labels)
            self._markers.append(Marker(line=line, label=label))
        main_layout.addWidget(marker_container)

    def start(self) -> None:
        if self._timer.isActive():
            return
        self._reset_state()
        config = StreamConfig(
            sample_rate=self.sample_rate_spin.value(),
            center_frequency=self.center_spin.value(),
            bandwidth=self.span_spin.value(),
            buffer_size=4096,
        )
        self.manager.start_rx_stream(config, self._handle_samples)
        self._timer.start(100)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop(self) -> None:
        self._timer.stop()
        self.manager.stop_rx_stream()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _reset_state(self) -> None:
        self._max_hold = None
        self._min_hold = None
        self._avg_accum = None
        self._current_freqs = None
        self._current_psd = None
        self.plot.clear()
        for marker in self._markers:
            self.plot.addItem(marker.line)
            marker.label.setText("Marker: -- Hz / -- dB")

    def _handle_samples(self, data: np.ndarray) -> None:
        try:
            self._data_queue.put_nowait(data)
        except queue.Full:
            pass

    def _process_queue(self) -> None:
        if self._data_queue.empty():
            return
        try:
            data = self._data_queue.get_nowait()
        except queue.Empty:
            return

        settings = AnalyzerSettings(
            sample_rate=self.sample_rate_spin.value(),
            nfft=self._nfft_from_rbw(),
        )
        freqs, psd = compute_psd(data, settings)
        span = self.span_spin.value()
        mask = np.abs(freqs) <= span / 2
        freqs = freqs[mask]
        psd = psd[mask]

        detector = self.detector_combo.currentText()
        if detector == "Positive":
            stack = np.vstack([psd, np.roll(psd, 1), np.roll(psd, -1)])
            psd = np.max(stack, axis=0)
        elif detector == "Negative":
            stack = np.vstack([psd, np.roll(psd, 1), np.roll(psd, -1)])
            psd = np.min(stack, axis=0)

        if self.average_check.isChecked():
            target = max(1, int(self.average_spin.value()))
            alpha = 1.0 / target
            if self._avg_accum is None:
                self._avg_accum = psd
            else:
                self._avg_accum = (1 - alpha) * self._avg_accum + alpha * psd
            psd = self._avg_accum
        else:
            self._avg_accum = None

        if self.max_hold_check.isChecked():
            self._max_hold = update_max_hold(self._max_hold, psd)
        else:
            self._max_hold = None
        if self.min_hold_check.isChecked():
            self._min_hold = update_min_hold(self._min_hold, psd)
        else:
            self._min_hold = None

        self.plot.clear()
        self.plot.plot(freqs, psd, pen=pg.mkPen("#00d1ff", width=2))
        if self._max_hold is not None:
            self.plot.plot(freqs, self._max_hold, pen=pg.mkPen("#ff9f1c", width=1.5, style=QtCore.Qt.DashLine))
        if self._min_hold is not None:
            self.plot.plot(freqs, self._min_hold, pen=pg.mkPen("#00ff9f", width=1.5, style=QtCore.Qt.DashLine))

        for marker in self._markers:
            self.plot.addItem(marker.line)

        self._current_freqs = freqs
        self._current_psd = psd
        self._update_marker_labels()

    def _update_marker_labels(self) -> None:
        if self._current_freqs is None or self._current_psd is None:
            return
        for marker in self._markers:
            freq = marker.line.value()
            idx = (np.abs(self._current_freqs - freq)).argmin()
            power = self._current_psd[idx]
            marker.label.setText(f"Marker: {freq/1e6:.3f} MHz / {power:.1f} dBFS")

    def _nfft_from_rbw(self) -> int:
        sample_rate = self.sample_rate_spin.value()
        rbw = max(self.rbw_spin.value(), sample_rate / 16384)
        nfft = int(2 ** np.ceil(np.log2(sample_rate / rbw)))
        return max(256, min(nfft, 262144))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self.stop()
        super().closeEvent(event)
