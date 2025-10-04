"""Waveform Generator tab implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from dsp import generator
from widgets.controls import FlexFormLayout, LabeledComboBox, LabeledSpinBox


@dataclass
class WaveformConfig:
    center_frequency: float
    sample_rate: float
    bandwidth: float
    amplitude: float
    num_samples: int
    modulation: str


class WaveformGeneratorTab(QtWidgets.QWidget):
    """Provide controls to synthesize baseband waveforms."""

    waveform_generated = QtCore.pyqtSignal(object, object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._waveform: Optional[np.ndarray] = None
        self._config: Optional[WaveformConfig] = None

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.layout().setSpacing(12)

        self.form = FlexFormLayout()
        self._create_controls()
        self.layout().addLayout(self.form)

        self.generate_button = QtWidgets.QPushButton("Generate Waveform")
        self.generate_button.setCheckable(False)
        self.generate_button.clicked.connect(self._on_generate)
        self.layout().addWidget(self.generate_button)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setBackground("#202020")
        self.plot_widget.setLabel("bottom", "Sample Index")
        self.plot_widget.setLabel("left", "Amplitude")
        self.layout().addWidget(self.plot_widget, 1)

    def _create_controls(self) -> None:
        self.center_spin = LabeledSpinBox(50e6, 6e9, 1e6, "Hz", decimals=0)
        self.center_spin.set_value(915e6)
        self.form.addRow("Center Frequency", self.center_spin)

        self.sample_rate_spin = LabeledSpinBox(1e5, 61.44e6, 1e5, "S/s", decimals=0)
        self.sample_rate_spin.set_value(2.5e6)
        self.form.addRow("Sample Rate", self.sample_rate_spin)

        self.bandwidth_spin = LabeledSpinBox(1e5, 20e6, 1e5, "Hz", decimals=0)
        self.bandwidth_spin.set_value(1e6)
        self.form.addRow("Bandwidth", self.bandwidth_spin)

        self.samples_spin = LabeledSpinBox(1024, 1_048_576, 1024, "", decimals=0)
        self.samples_spin.set_value(16384)
        self.form.addRow("Samples", self.samples_spin)

        self.amplitude_spin = LabeledSpinBox(0.01, 1.0, 0.01, "", decimals=2)
        self.amplitude_spin.set_value(0.5)
        self.form.addRow("Amplitude", self.amplitude_spin)

        self.mod_combo = LabeledComboBox("Modulation")
        self.mod_combo.add_items(["AWGN", "Multi-CW", "FHSS"])
        self.form.addRow(self.mod_combo)

    def _on_generate(self) -> None:
        config = WaveformConfig(
            center_frequency=self.center_spin.value(),
            sample_rate=self.sample_rate_spin.value(),
            bandwidth=self.bandwidth_spin.value(),
            amplitude=self.amplitude_spin.value(),
            num_samples=int(self.samples_spin.value()),
            modulation=self.mod_combo.current_text(),
        )
        waveform = self._generate_waveform(config)
        self._waveform = waveform
        self._config = config
        self._plot_waveform(waveform)
        self.waveform_generated.emit(waveform, config)

    def _generate_waveform(self, config: WaveformConfig) -> np.ndarray:
        if config.modulation == "AWGN":
            return generator.gen_awgn(
                num_samples=config.num_samples,
                sample_rate=config.sample_rate,
                bandwidth=config.bandwidth,
                amplitude=config.amplitude,
            )
        if config.modulation == "Multi-CW":
            tones = np.linspace(-config.bandwidth / 2, config.bandwidth / 2, 5)
            return generator.gen_multi_cw(
                frequencies=tones,
                num_samples=config.num_samples,
                sample_rate=config.sample_rate,
                amplitude=config.amplitude,
            )
        if config.modulation == "FHSS":
            hop_freqs = np.linspace(-config.bandwidth / 2, config.bandwidth / 2, 8)
            return generator.gen_fhss(
                hop_frequencies=hop_freqs,
                sample_rate=config.sample_rate,
                hop_duration=0.002,
                amplitude=config.amplitude,
                total_duration=config.num_samples / config.sample_rate,
            )
        raise ValueError(f"Unsupported modulation: {config.modulation}")

    def _plot_waveform(self, waveform: np.ndarray) -> None:
        self.plot_widget.clear()
        if waveform.size == 0:
            return
        real_curve = self.plot_widget.plot(waveform.real, pen=pg.mkPen("#00ff9f", width=2))
        imag_curve = self.plot_widget.plot(waveform.imag, pen=pg.mkPen("#ff6f00", width=2))
        real_curve.setDownsampling(auto=True)
        imag_curve.setDownsampling(auto=True)

    def current_waveform(self) -> Optional[np.ndarray]:
        return self._waveform

    def current_config(self) -> Optional[WaveformConfig]:
        return self._config
