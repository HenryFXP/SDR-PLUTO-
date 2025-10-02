"""Signal processing helpers for the Pluto+ SDR GUI."""
from __future__ import annotations

import numpy as np
from typing import Tuple


WINDOWS = {
    "hann": np.hanning,
    "hamming": np.hamming,
    "blackman": np.blackman,
    "rect": lambda n: np.ones(n, dtype=float),
}


def window_samples(samples: np.ndarray, window: str) -> np.ndarray:
    """Apply a named window function to the provided samples.

    Parameters
    ----------
    samples:
        Complex baseband samples.
    window:
        Name of the window function in :data:`WINDOWS`.
    """

    func = WINDOWS.get(window, WINDOWS["hann"])
    taps = func(len(samples))
    return samples * taps


def compute_psd(
    samples: np.ndarray,
    sample_rate: float,
    *,
    window: str = "hann",
    fft_size: int = 4096,
    average: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute the power spectral density of the provided samples.

    Returns frequency bins (Hz) and magnitudes (dBFS).
    """

    if samples.size < fft_size:
        samples = np.pad(samples, (0, fft_size - samples.size), mode="constant")

    segments = max(1, min(average, samples.size // fft_size))
    spectra = []
    for idx in range(segments):
        start = idx * fft_size
        end = start + fft_size
        windowed = window_samples(samples[start:end], window)
        fft = np.fft.fftshift(np.fft.fft(windowed))
        spectra.append(np.abs(fft))

    if not spectra:
        windowed = window_samples(samples[:fft_size], window)
        spectra.append(np.abs(np.fft.fftshift(np.fft.fft(windowed))))

    avg_fft = np.mean(spectra, axis=0)
    magnitude = 20 * np.log10(np.maximum(avg_fft, 1e-12))
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1.0 / sample_rate))
    return freqs, magnitude


def estimate_power_dbfs(samples: np.ndarray) -> float:
    """Estimate the TX power in dBFS from baseband samples."""

    rms = np.sqrt(np.mean(np.abs(samples) ** 2))
    return 20 * np.log10(max(rms, 1e-12))


__all__ = ["WINDOWS", "window_samples", "compute_psd", "estimate_power_dbfs"]
