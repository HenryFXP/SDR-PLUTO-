from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from scipy.signal import get_window


def compute_psd(
    samples: np.ndarray,
    sample_rate: float,
    window: str = "hann",
    avg_state: Dict[str, np.ndarray] | None = None,
    avg_alpha: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    if samples.size == 0:
        return np.array([]), np.array([])

    win = get_window(window, len(samples))
    windowed = samples * win
    spectrum = np.fft.fftshift(np.fft.fft(windowed))
    power = np.abs(spectrum) ** 2
    psd = 10 * np.log10(power + 1e-12)
    freqs = np.fft.fftshift(np.fft.fftfreq(len(samples), d=1.0 / sample_rate))

    if avg_state is not None:
        prev = avg_state.get("psd")
        if prev is None:
            avg_state["psd"] = psd
        else:
            avg_state["psd"] = avg_alpha * psd + (1 - avg_alpha) * prev
        psd = avg_state["psd"]
    return freqs, psd


def concatenate_buffers(buffers: list[np.ndarray]) -> np.ndarray:
    if not buffers:
        return np.array([], dtype=np.complex64)
    return np.concatenate(buffers).astype(np.complex64)
