"""Waveform generation utilities supporting multiple signal types."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
from scipy import signal

from app.core.logger import get_logger
from app.core.types import WaveformSpec
from app.core.utils import ensure_safe_amplitude, linear_to_db

LOGGER = get_logger(__name__)

SUPPORTED_WAVEFORMS = {"sine", "square", "triangle", "prbs", "multitone", "chirp", "ofdm", "arbitrary"}


def generate_waveform(
    name: str,
    kind: str,
    sample_rate: float,
    duration_s: float,
    amplitude: float,
    **kwargs,
) -> Tuple[np.ndarray, WaveformSpec]:
    """Generate a waveform and return IQ samples with metadata."""

    amplitude, clipped = ensure_safe_amplitude(amplitude)
    t = np.arange(int(sample_rate * duration_s)) / sample_rate
    if kind == "sine":
        freq = kwargs.get("frequency", 1e6)
        iq = amplitude * np.exp(1j * 2 * np.pi * freq * t)
    elif kind == "square":
        freq = kwargs.get("frequency", 1e6)
        iq = amplitude * signal.square(2 * np.pi * freq * t)
    elif kind == "triangle":
        freq = kwargs.get("frequency", 1e6)
        iq = amplitude * signal.sawtooth(2 * np.pi * freq * t, 0.5)
    elif kind == "prbs":
        order = int(kwargs.get("order", 9))
        taps = signal.max_len_seq(order, length=len(t))[0]
        iq = amplitude * (2 * taps - 1)
    elif kind == "multitone":
        tones = kwargs.get("tones", [1e6, 1.5e6])
        iq = sum(amplitude / len(tones) * np.exp(1j * 2 * np.pi * f * t) for f in tones)
    elif kind == "chirp":
        f0 = kwargs.get("f_start", 1e6)
        f1 = kwargs.get("f_stop", 10e6)
        iq = amplitude * signal.chirp(t, f0, duration_s, f1, method="linear")
    elif kind == "ofdm":
        num_subcarriers = int(kwargs.get("num_subcarriers", 64))
        symbol = np.exp(1j * 2 * np.pi * np.random.rand(num_subcarriers))
        iq = np.tile(np.fft.ifft(symbol), int(len(t) / num_subcarriers) + 1)[: len(t)]
        iq *= amplitude
    elif kind == "arbitrary":
        path: Path = Path(kwargs["path"])
        iq = load_iq(path)
        if kwargs.get("normalize", True):
            iq = amplitude * iq / np.max(np.abs(iq))
    else:
        raise ValueError(f"Unsupported waveform kind: {kind}")

    iq = iq.astype(np.complex64)
    crest_factor = compute_crest_factor_db(iq)
    spec = WaveformSpec(
        name=name,
        kind=kind,  # type: ignore[arg-type]
        amplitude=float(amplitude),
        sample_rate=float(sample_rate),
        num_samples=len(iq),
        crest_factor_db=crest_factor,
        metadata={"clipped": clipped, **{k: float(v) for k, v in kwargs.items() if isinstance(v, (int, float))}},
    )
    LOGGER.info("Generated waveform", extra={"name": name, "kind": kind, "crest_factor_db": crest_factor})
    return iq, spec


def compute_crest_factor_db(iq: np.ndarray) -> float:
    peak = np.max(np.abs(iq))
    rms = np.sqrt(np.mean(np.abs(iq) ** 2))
    crest_factor = linear_to_db(peak / max(rms, 1e-9))
    return float(crest_factor)


def load_iq(path: Path) -> np.ndarray:
    if path.suffix == ".npy":
        return np.load(path)
    raise ValueError(f"Unsupported arbitrary IQ format: {path.suffix}")


def window_iq(iq: np.ndarray, window: str = "hann") -> np.ndarray:
    win = signal.get_window(window, len(iq))
    return iq * win


__all__ = ["generate_waveform", "compute_crest_factor_db", "window_iq", "SUPPORTED_WAVEFORMS"]
