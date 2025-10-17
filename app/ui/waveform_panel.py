"""Panel for designing and importing waveforms."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtWidgets
import pyqtgraph as pg

from app.core.config import AppConfig
from app.core.types import WaveformSpec
from app.dsp.wavegen import SUPPORTED_WAVEFORMS, generate_waveform, compute_crest_factor_db
from app.dsp.iqio import load_iq


class WaveformPanel(QtWidgets.QGroupBox):
    waveform_generated = QtCore.pyqtSignal(str, np.ndarray, WaveformSpec)

    def __init__(self, config: AppConfig, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Waveforms", parent)
        self.config = config
        self.setEnabled(False)

        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.addItems(["tx1", "tx2"])
        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItems(sorted(SUPPORTED_WAVEFORMS))
        self.frequency_spin = QtWidgets.QDoubleSpinBox()
        self.frequency_spin.setRange(1e3, 6e9)
        self.frequency_spin.setValue(1e6)
        self.amplitude_spin = QtWidgets.QDoubleSpinBox()
        self.amplitude_spin.setRange(0.0, 1.2)
        self.amplitude_spin.setSingleStep(0.05)
        self.amplitude_spin.setValue(self.config.waveform.amplitude)
        self.duration_spin = QtWidgets.QDoubleSpinBox()
        self.duration_spin.setRange(1e-4, 1.0)
        self.duration_spin.setValue(0.01)
        self.generate_button = QtWidgets.QPushButton("Generate")
        self.import_button = QtWidgets.QPushButton("Import")
        self.warning_banner = QtWidgets.QLabel("")
        self.warning_banner.setStyleSheet("color: orange; font-weight: bold;")

        self.time_plot = pg.PlotWidget(title="Time Domain")
        self.freq_plot = pg.PlotWidget(title="Frequency Domain")

        form = QtWidgets.QFormLayout()
        form.addRow("Channel", self.channel_combo)
        form.addRow("Kind", self.kind_combo)
        form.addRow("Frequency (Hz)", self.frequency_spin)
        form.addRow("Amplitude", self.amplitude_spin)
        form.addRow("Duration (s)", self.duration_spin)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.generate_button)
        buttons.addWidget(self.import_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.warning_banner)
        layout.addWidget(self.time_plot, stretch=2)
        layout.addWidget(self.freq_plot, stretch=2)

        self.generate_button.clicked.connect(self._on_generate)
        self.import_button.clicked.connect(self._on_import)

    def _on_generate(self) -> None:
        channel = self.channel_combo.currentText()
        kind = self.kind_combo.currentText()
        freq = self.frequency_spin.value()
        amplitude = self.amplitude_spin.value()
        duration = self.duration_spin.value()
        iq, spec = generate_waveform(
            name=f"{channel}-{kind}",
            kind=kind,
            sample_rate=self.config.tx1.sample_rate_sps,
            duration_s=duration,
            amplitude=amplitude,
            frequency=freq,
        )
        self._update_plots(iq, spec.sample_rate)
        if spec.metadata.get("clipped"):
            self.show_warning("Amplitude clipped to safe limit (0.8 FS)")
        else:
            self.show_warning("")
        self.waveform_generated.emit(channel, iq, spec)

    def _on_import(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import IQ", "", "IQ Files (*.npy *.c8 *.wav *.csv)")
        if not path:
            return
        iq, sample_rate = load_iq(Path(path))
        channel = self.channel_combo.currentText()
        crest = compute_crest_factor_db(iq)
        spec = WaveformSpec(
            name=Path(path).stem,
            kind="arbitrary",
            amplitude=float(np.max(np.abs(iq))),
            sample_rate=float(sample_rate or self.config.tx1.sample_rate_sps),
            num_samples=len(iq),
            crest_factor_db=crest,
            path=Path(path),
        )
        self._update_plots(iq, spec.sample_rate)
        self.show_warning("")
        self.waveform_generated.emit(channel, iq, spec)

    def _update_plots(self, iq: np.ndarray, sample_rate: float) -> None:
        times = np.arange(len(iq)) / sample_rate
        self.time_plot.clear()
        self.time_plot.plot(times, iq.real, pen="c", name="I")
        self.time_plot.plot(times, iq.imag, pen="m", name="Q")
        spectrum = np.fft.fftshift(np.fft.fft(iq))
        freqs = np.fft.fftshift(np.fft.fftfreq(len(iq), d=1 / sample_rate))
        self.freq_plot.clear()
        self.freq_plot.plot(freqs, 20 * np.log10(np.abs(spectrum) + 1e-12))

    def show_warning(self, message: str) -> None:
        self.warning_banner.setText(message)


__all__ = ["WaveformPanel"]
