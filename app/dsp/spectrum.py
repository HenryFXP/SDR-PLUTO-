"""Spectrum estimation utilities for FFT, averaging, and peak hold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from app.core.logger import get_logger
from app.core.utils import linear_to_db

LOGGER = get_logger(__name__)


@dataclass
class SpectrumResult:
    freqs: np.ndarray
    magnitude_db: np.ndarray
    peak_freq: float
    peak_db: float


class SpectrumAnalyzer:
    """Incremental spectrum analyzer supporting averaging and peak hold."""

    def __init__(self, sample_rate: float, size: int, averaging: int = 1, peak_hold: bool = True) -> None:
        self.sample_rate = sample_rate
        self.size = size
        self.averaging = max(1, averaging)
        self.peak_hold = peak_hold
        self._avg_buffer: Optional[np.ndarray] = None
        self._peak_buffer: Optional[np.ndarray] = None
        self._count = 0

    def process(self, iq: np.ndarray) -> SpectrumResult:
        window = np.hanning(self.size)
        segment = iq[: self.size] * window
        fft = np.fft.fftshift(np.fft.fft(segment))
        mag = np.abs(fft)
        mag_db = linear_to_db(mag / np.max(mag))

        if self._avg_buffer is None:
            self._avg_buffer = mag_db
        else:
            self._avg_buffer = (self._avg_buffer * self._count + mag_db) / (self._count + 1)

        if self.peak_hold:
            if self._peak_buffer is None:
                self._peak_buffer = mag_db
            else:
                self._peak_buffer = np.maximum(self._peak_buffer, mag_db)
            plot_data = self._peak_buffer
        else:
            plot_data = self._avg_buffer

        self._count = min(self._count + 1, self.averaging)
        freqs = np.fft.fftshift(np.fft.fftfreq(self.size, 1 / self.sample_rate))
        peak_idx = int(np.argmax(plot_data))
        result = SpectrumResult(freqs=freqs, magnitude_db=plot_data, peak_freq=float(freqs[peak_idx]), peak_db=float(plot_data[peak_idx]))
        LOGGER.debug("Spectrum updated", extra={"peak_freq": result.peak_freq, "peak_db": result.peak_db})
        return result


__all__ = ["SpectrumAnalyzer", "SpectrumResult"]
