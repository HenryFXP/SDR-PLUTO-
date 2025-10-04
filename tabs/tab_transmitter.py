"""Transmitter tab implementation."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets

from pluto_manager import PlutoManager, StreamConfig
from widgets.controls import FlexFormLayout, LabeledSpinBox


class TransmitterTab(QtWidgets.QWidget):
    """Configure and control PlutoSDR transmissions safely."""

    def __init__(self, manager: PlutoManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._waveform: Optional[np.ndarray] = None

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        warning = QtWidgets.QLabel(
            "⚠️ TX DISABLED BY DEFAULT. Enable only when connected to a dummy load or attenuated setup."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #ff5555; font-weight: bold; font-size: 16px;")
        main_layout.addWidget(warning)

        form = FlexFormLayout()

        self.center_spin = LabeledSpinBox(50e6, 6e9, 1e6, "Hz", decimals=0)
        self.center_spin.set_value(915e6)
        form.addRow("Center Frequency", self.center_spin)

        self.sample_rate_spin = LabeledSpinBox(1e5, 61.44e6, 1e5, "S/s", decimals=0)
        self.sample_rate_spin.set_value(2.5e6)
        form.addRow("Sample Rate", self.sample_rate_spin)

        self.bandwidth_spin = LabeledSpinBox(1e5, 20e6, 1e5, "Hz", decimals=0)
        self.bandwidth_spin.set_value(1e6)
        form.addRow("Bandwidth", self.bandwidth_spin)

        self.gain_spin = LabeledSpinBox(-40, 0, 1, "dB", decimals=0)
        self.gain_spin.set_value(-10)
        form.addRow("TX Gain", self.gain_spin)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.addItems(["A", "B"])
        form.addRow("Port", self.port_combo)

        self.tx_enable_check = QtWidgets.QCheckBox("Enable RF Output (Interlock)")
        self.tx_enable_check.setChecked(False)
        form.addRow("", self.tx_enable_check)

        self.dry_run_check = QtWidgets.QCheckBox("Dry-Run (No RF)")
        self.dry_run_check.setChecked(True)
        form.addRow("", self.dry_run_check)

        main_layout.addLayout(form)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)
        self.start_button = QtWidgets.QPushButton("Start TX")
        self.stop_button = QtWidgets.QPushButton("Stop TX")
        self.stop_button.setEnabled(False)
        self.kill_button = QtWidgets.QPushButton("EMERGENCY STOP")
        self.kill_button.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        self.start_button.clicked.connect(self._start_tx)
        self.stop_button.clicked.connect(self._stop_tx)
        self.kill_button.clicked.connect(self.emergency_kill)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.kill_button)
        main_layout.addLayout(button_layout)

        self.status_label = QtWidgets.QLabel("TX Idle")
        self.status_label.setStyleSheet("font-size: 14px;")
        main_layout.addWidget(self.status_label)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#202020")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", "Sample Index")
        self.plot_widget.setLabel("left", "Amplitude")
        main_layout.addWidget(self.plot_widget, 1)

    def set_waveform(self, waveform: np.ndarray) -> None:
        self._waveform = np.asarray(waveform, dtype=np.complex64)
        self._plot_waveform()

    def _plot_waveform(self) -> None:
        self.plot_widget.clear()
        if self._waveform is None or self._waveform.size == 0:
            return
        self.plot_widget.plot(self._waveform.real, pen=pg.mkPen("#00ff9f", width=2))
        self.plot_widget.plot(self._waveform.imag, pen=pg.mkPen("#ff6f00", width=2))

    def _start_tx(self) -> None:
        if not self.tx_enable_check.isChecked():
            self.status_label.setText("Interlock disabled. Check the box to enable RF.")
            return
        if self._waveform is None:
            self.status_label.setText("No waveform loaded. Generate a waveform first.")
            return
        config = StreamConfig(
            sample_rate=self.sample_rate_spin.value(),
            center_frequency=self.center_spin.value(),
            bandwidth=self.bandwidth_spin.value(),
            gain=self.gain_spin.value(),
            buffer_size=len(self._waveform),
            port=self.port_combo.currentText(),
        )
        try:
            self.manager.configure_tx(config)
            if not self.dry_run_check.isChecked():
                self.manager.transmit(self._waveform)
            self.status_label.setText("Transmitting" if not self.dry_run_check.isChecked() else "Dry-run active")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        except Exception as exc:
            self.status_label.setText(f"TX error: {exc}")

    def _stop_tx(self) -> None:
        self.manager.disable_tx()
        self.status_label.setText("TX Stopped")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def emergency_kill(self) -> None:
        self.manager.disable_tx()
        self.tx_enable_check.setChecked(False)
        self.status_label.setText("EMERGENCY STOP")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
