"""Spectrum and waterfall display using pyqtgraph."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from app.core.events import EventBus


class SpectrumPanel(QGroupBox):  # pragma: no cover - requires Qt runtime
    def __init__(self, events: EventBus, parent: Optional[QWidget] = None) -> None:
        super().__init__("Spectrum", parent)
        self._events = events

        self._plot = pg.PlotWidget(title="Live Spectrum")
        self._plot.setLabel("bottom", "Frequency", units="Hz")
        self._plot.setLabel("left", "Magnitude", units="dBFS")
        self._curve = self._plot.plot(pen="y")

        layout = QVBoxLayout(self)
        layout.addWidget(self._plot)

        self._events.subscribe("rx_samples", self._on_rx_samples)

    def _on_rx_samples(self, payload: dict[str, object]) -> None:
        spectrum = payload.get("spectrum")
        if spectrum is None:
            return
        magnitudes = 20 * np.log10(np.maximum(np.asarray(spectrum, dtype=float), 1e-12))
        self._curve.setData(magnitudes)


__all__ = ["SpectrumPanel"]
