"""Spectrum analysis utilities used by the live FFT and waterfall widgets."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from app.core.utils import dbfs


def compute_fft(samples: NDArray[np.complex64], sample_rate: float) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return frequency bins (Hz) and magnitude in dBFS."""

    window = np.hanning(len(samples))
    windowed = samples * window
    fft = np.fft.fftshift(np.fft.fft(windowed))
    freqs = np.fft.fftshift(np.fft.fftfreq(len(samples), d=1.0 / sample_rate))
    magnitude = dbfs(fft / np.max(np.abs(windowed)))
    return freqs.astype(np.float64), magnitude.astype(np.float64)


def average_spectrum(history: list[NDArray[np.float64]]) -> NDArray[np.float64]:
    """Average a list of magnitude arrays."""

    if not history:
        raise ValueError("Cannot average empty spectrum history")
    stacked = np.vstack(history)
    return np.mean(stacked, axis=0)


__all__ = ["compute_fft", "average_spectrum"]
