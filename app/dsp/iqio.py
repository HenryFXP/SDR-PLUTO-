"""IQ file loading and saving helpers with Windows path handling."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from scipy.io import wavfile

SUPPORTED_EXTENSIONS = {".npy", ".c8", ".csv", ".wav"}


def load_iq(path: Path) -> Tuple[np.ndarray, float]:
    """Load IQ samples from disk and return samples + inferred sample rate."""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported IQ format: {suffix}")

    if suffix == ".npy":
        data = np.load(path)
        return np.asarray(data, dtype=np.complex64), 0.0
    if suffix == ".c8":
        raw = np.fromfile(path, dtype=np.int8)
        return raw.astype(np.float32).view(np.complex64) / 127.0, 0.0
    if suffix == ".csv":
        iq = np.loadtxt(path, delimiter=",", dtype=np.float32)
        return (iq[:, 0] + 1j * iq[:, 1]).astype(np.complex64), 0.0

    rate, data = wavfile.read(path)
    if data.ndim == 1:
        data = data.astype(np.float32)
        return data.view(np.complex64), float(rate)
    i = data[:, 0].astype(np.float32)
    q = data[:, 1].astype(np.float32)
    return (i + 1j * q).astype(np.complex64), float(rate)


def save_iq(path: Path, samples: np.ndarray, sample_rate: float) -> None:
    """Persist complex samples to the requested container type."""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported IQ format: {suffix}")

    if suffix == ".npy":
        np.save(path, samples.astype(np.complex64))
        return
    if suffix == ".c8":
        iq = np.clip(samples, -1.0, 1.0)
        interleaved = np.empty(2 * len(iq), dtype=np.int8)
        interleaved[0::2] = np.round(np.real(iq) * 127).astype(np.int8)
        interleaved[1::2] = np.round(np.imag(iq) * 127).astype(np.int8)
        interleaved.tofile(path)
        return
    if suffix == ".csv":
        stacked = np.column_stack((samples.real, samples.imag))
        np.savetxt(path, stacked, delimiter=",", fmt="%.6f")
        return

    normalized = np.clip(samples, -1.0, 1.0)
    stereo = np.column_stack((normalized.real, normalized.imag)).astype(np.float32)
    wavfile.write(path, int(sample_rate), stereo)


def normalise_to_dac_range(samples: np.ndarray, scale: float = 0.8) -> np.ndarray:
    """Scale IQ samples to the DAC safe operating range."""

    return np.clip(samples * scale, -1.0, 1.0).astype(np.complex64)


__all__ = ["load_iq", "save_iq", "normalise_to_dac_range", "SUPPORTED_EXTENSIONS"]
