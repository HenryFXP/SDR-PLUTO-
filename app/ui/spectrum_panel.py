"""Panel presenting spectrum and waterfall plots."""

from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt6 import QtWidgets
import pyqtgraph as pg

from app.core.config import AppConfig
from app.core.logger import get_logger
from app.dsp.spectrum import SpectrumResult

LOGGER = get_logger(__name__)


class SpectrumPanel(QtWidgets.QGroupBox):
    def __init__(self, config: AppConfig, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Spectrum", parent)
        self.plot = pg.PlotWidget(title="FFT")
        self.waterfall = pg.ImageView()
        self.marker_label = QtWidgets.QLabel("Peak: -- Hz / -- dB")
        self.export_button = QtWidgets.QPushButton("Export")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.plot, stretch=2)
        layout.addWidget(self.waterfall, stretch=2)
        layout.addWidget(self.marker_label)
        layout.addWidget(self.export_button)

        self._history: list[np.ndarray] = []
        self.export_button.clicked.connect(self._export)

    def update_spectrum(self, result: SpectrumResult) -> None:
        self.plot.clear()
        self.plot.plot(result.freqs, result.magnitude_db)
        self.marker_label.setText(f"Peak: {result.peak_freq/1e6:.3f} MHz / {result.peak_db:.1f} dB")
        self._history.append(result.magnitude_db)
        if len(self._history) > 100:
            self._history.pop(0)
        image = np.array(self._history)
        self.waterfall.setImage(image, autoLevels=True)

    def _export(self) -> None:
        if not self._history:
            QtWidgets.QMessageBox.information(self, "Export", "No spectrum data available")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Spectrum", "spectrum.csv")
        if path:
            data = np.column_stack((np.arange(len(self._history[-1])), self._history[-1]))
            np.savetxt(path, data, delimiter=",")


__all__ = ["SpectrumPanel"]
