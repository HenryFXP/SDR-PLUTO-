"""Panel exposing per-channel TX controls."""

from __future__ import annotations

from typing import Dict, Optional

from PyQt6 import QtCore, QtWidgets

from app.core.config import AppConfig
from app.core.types import TxConfig, WaveformSpec


class TxControlPanel(QtWidgets.QGroupBox):
    tx_config_requested = QtCore.pyqtSignal(TxConfig)
    tx_stop_requested = QtCore.pyqtSignal(str)

    def __init__(self, config: AppConfig, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Transmit Control", parent)
        self.setEnabled(False)
        self.config = config
        self._metadata_labels: Dict[str, QtWidgets.QLabel] = {}

        layout = QtWidgets.QGridLayout(self)
        self._add_channel_controls(layout, "tx1", 0, config.tx1)
        self._add_channel_controls(layout, "tx2", 6, config.tx2)

    def _add_channel_controls(self, layout: QtWidgets.QGridLayout, channel: str, row: int, tx_config) -> None:
        header = QtWidgets.QLabel(channel.upper())
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header, row, 0)

        freq = QtWidgets.QDoubleSpinBox()
        freq.setRange(47e6, 6e9)
        freq.setValue(tx_config.center_frequency_hz)
        sr = QtWidgets.QDoubleSpinBox()
        sr.setRange(1e3, 61.44e6)
        sr.setValue(tx_config.sample_rate_sps)
        bw = QtWidgets.QDoubleSpinBox()
        bw.setRange(1e3, 40e6)
        bw.setValue(tx_config.rf_bandwidth_hz)
        gain = QtWidgets.QDoubleSpinBox()
        gain.setRange(-90.0, 0.0)
        gain.setValue(tx_config.gain_db)
        enable = QtWidgets.QCheckBox("Enable")
        start = QtWidgets.QPushButton("Start")
        stop = QtWidgets.QPushButton("Stop")
        loop = QtWidgets.QComboBox()
        loop.addItems(["continuous", "finite"])
        metadata = QtWidgets.QLabel("No waveform")
        self._metadata_labels[channel] = metadata

        layout.addWidget(QtWidgets.QLabel("Frequency (Hz)"), row + 1, 0)
        layout.addWidget(freq, row + 1, 1)
        layout.addWidget(QtWidgets.QLabel("Sample Rate"), row + 2, 0)
        layout.addWidget(sr, row + 2, 1)
        layout.addWidget(QtWidgets.QLabel("Bandwidth"), row + 3, 0)
        layout.addWidget(bw, row + 3, 1)
        layout.addWidget(QtWidgets.QLabel("Gain (dB)"), row + 4, 0)
        layout.addWidget(gain, row + 4, 1)
        layout.addWidget(loop, row + 5, 0)
        layout.addWidget(enable, row + 5, 1)
        layout.addWidget(start, row + 6, 0)
        layout.addWidget(stop, row + 6, 1)
        layout.addWidget(metadata, row + 7, 0, 1, 2)

        def _start() -> None:
            config = TxConfig(
                channel=channel,
                frequency_hz=freq.value(),
                sample_rate=sr.value(),
                bandwidth_hz=bw.value(),
                gain_db=gain.value(),
                loop_mode=loop.currentText(),
                enabled=enable.isChecked(),
            )
            self.tx_config_requested.emit(config)

        def _stop() -> None:
            self.tx_stop_requested.emit(channel)

        start.clicked.connect(_start)
        stop.clicked.connect(_stop)

    def update_waveform_metadata(self, channel: str, spec: WaveformSpec) -> None:
        label = self._metadata_labels.get(channel)
        if label:
            label.setText(
                f"Waveform: {spec.name} | Samples: {spec.num_samples} | Crest: {spec.crest_factor_db:.2f} dB"
            )


__all__ = ["TxControlPanel"]
