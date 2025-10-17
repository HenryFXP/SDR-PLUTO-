"""Waveform authoring panel."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig
from app.core.events import EventBus
from app.core.types import WaveformSpec
from app.dsp import wavegen
from app.dsp.iqio import normalise_to_dac_range
from app.services.session import SessionManager


class WaveformPanel(QGroupBox):  # pragma: no cover - requires Qt runtime
    def __init__(
        self, session: SessionManager, events: EventBus, config: AppConfig, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__("Waveform", parent)
        self._session = session
        self._events = events
        self._config = config

        self._frequency = QLineEdit("1e6")
        self._duration = QLineEdit("0.01")
        self._generate_button = QPushButton("Generate Sine")
        self._import_button = QPushButton("Import IQ")
        self._status = QLabel("No waveform loaded")

        form = QFormLayout()
        form.addRow("Frequency (Hz)", self._frequency)
        form.addRow("Duration (s)", self._duration)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._generate_button)
        layout.addWidget(self._import_button)
        layout.addWidget(self._status)
        layout.addStretch()

        self._generate_button.clicked.connect(self._generate)
        self._import_button.clicked.connect(self._import)

    def _generate(self) -> None:
        freq = float(self._frequency.text())
        duration = float(self._duration.text())
        result = wavegen.sine(self._config.tx1.sample_rate_sps, freq, duration)
        scaled = normalise_to_dac_range(result.samples, self._config.waveform.amplitude)
        spec = WaveformSpec(
            name=result.name,
            samples=scaled,
            sample_rate=result.sample_rate,
            rms_level=float(np.sqrt(np.mean(np.abs(scaled) ** 2))),
            crest_factor_db=result.crest_factor_db,
            metadata=result.metadata,
        )
        tx_state = self._session.snapshot().tx1
        tx_state.waveform = spec
        self._session.load_waveform(1, tx_state)
        self._status.setText(f"Generated {result.name} with crest factor {result.crest_factor_db:.2f} dB")

    def _import(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import IQ", str(Path.home()), "IQ Files (*.npy *.c8 *.csv *.wav)")
        if not filename:
            return
        result = wavegen.arbitrary_from_file(Path(filename), self._config.tx1.sample_rate_sps)
        scaled = normalise_to_dac_range(result.samples, self._config.waveform.amplitude)
        spec = WaveformSpec(
            name=result.name,
            samples=scaled,
            sample_rate=result.sample_rate,
            rms_level=float(np.sqrt(np.mean(np.abs(scaled) ** 2))),
            crest_factor_db=result.crest_factor_db,
            metadata=result.metadata,
            source_path=Path(filename),
        )
        tx_state = self._session.snapshot().tx1
        tx_state.waveform = spec
        self._session.load_waveform(1, tx_state)
        self._status.setText(f"Loaded {Path(filename).name}")


__all__ = ["WaveformPanel"]
