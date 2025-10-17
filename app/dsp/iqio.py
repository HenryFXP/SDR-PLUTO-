"""IQ import/export helpers for multiple file formats."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from scipy.io import wavfile

from app.core.logger import get_logger

LOGGER = get_logger(__name__)


SUPPORTED_EXTS = {".npy", ".c8", ".wav", ".csv"}


def load_iq(path: Path) -> Tuple[np.ndarray, float | None]:
    """Load IQ samples from ``path`` and optionally return their sample rate."""

    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.load(path), None
    if suffix == ".c8":
        data = np.fromfile(path, dtype=np.complex64)
        return data, None
    if suffix == ".csv":
        data = np.loadtxt(path, delimiter=",", dtype=float)
        iq = data[:, 0] + 1j * data[:, 1]
        return iq.astype(np.complex64), None
    if suffix == ".wav":
        rate, samples = wavfile.read(path)
        samples = samples.astype(np.float32) / np.iinfo(samples.dtype).max
        iq = samples[:, 0] + 1j * samples[:, 1]
        return iq, float(rate)
    raise ValueError(f"Unsupported IQ format: {suffix}")


def save_iq(path: Path, iq: np.ndarray, sample_rate: float | None = None) -> None:
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".npy":
        np.save(path, iq)
    elif suffix == ".c8":
        iq.astype(np.complex64).tofile(path)
    elif suffix == ".csv":
        np.savetxt(path, np.column_stack((iq.real, iq.imag)), delimiter=",")
    elif suffix == ".wav":
        if sample_rate is None:
            raise ValueError("Sample rate required for WAV export")
        scaled = np.column_stack((iq.real, iq.imag))
        scaled = np.clip(scaled, -1.0, 1.0)
        wavfile.write(path, int(sample_rate), (scaled * 32767).astype(np.int16))
    else:
        raise ValueError(f"Unsupported export format: {suffix}")
    LOGGER.info("Saved IQ", extra={"path": str(path), "samples": len(iq)})


__all__ = ["load_iq", "save_iq", "SUPPORTED_EXTS"]
