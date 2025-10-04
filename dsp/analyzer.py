"""Signal analysis utilities for the PlutoSDR GUI."""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

__all__ = [
    "AnalyzerSettings",
    "compute_fft",
    "compute_psd",
    "update_max_hold",
    "update_min_hold",
]


@dataclass
class AnalyzerSettings:
    """Settings for FFT/PSD analysis."""

    sample_rate: float
    nfft: int
    window: str = "hann"


def _window_function(name: str, n: int) -> np.ndarray:
    name = name.lower()
    if name == "hann":
        return np.hanning(n)
    if name == "hamming":
        return np.hamming(n)
    if name == "blackman":
        return np.blackman(n)
    return np.ones(n)


def compute_fft(iq: np.ndarray, settings: AnalyzerSettings) -> Tuple[np.ndarray, np.ndarray]:
    """Return frequency bins and FFT magnitude for the provided IQ data."""

    if settings.nfft <= 0:
        raise ValueError("nfft must be positive")
    data = np.asarray(iq, dtype=np.complex64)
    if data.size < settings.nfft:
        pad = settings.nfft - data.size
        data = np.pad(data, (0, pad), mode="constant")
    window = _window_function(settings.window, settings.nfft)
    spectrum = np.fft.fftshift(np.fft.fft(data[: settings.nfft] * window))
    freqs = np.fft.fftshift(np.fft.fftfreq(settings.nfft, d=1.0 / settings.sample_rate))
    magnitude = 20 * np.log10(np.maximum(np.abs(spectrum), 1e-12))
    return freqs, magnitude


def compute_psd(iq: np.ndarray, settings: AnalyzerSettings) -> Tuple[np.ndarray, np.ndarray]:
    """Compute the power spectral density in dBFS."""

    freqs, spectrum = compute_fft(iq, settings)
    psd = spectrum - 10 * np.log10(settings.nfft / 2)
    return freqs, psd


def update_max_hold(existing: Optional[np.ndarray], new_values: np.ndarray) -> np.ndarray:
    """Return an array containing the element-wise maximum hold."""

    if existing is None:
        return np.array(new_values, copy=True)
    return np.maximum(existing, new_values)


def update_min_hold(existing: Optional[np.ndarray], new_values: np.ndarray) -> np.ndarray:
    """Return an array containing the element-wise minimum hold."""

    if existing is None:
        return np.array(new_values, copy=True)
    return np.minimum(existing, new_values)
