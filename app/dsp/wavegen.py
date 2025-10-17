"""Waveform synthesis helpers for the Pluto+ control board."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

import numpy as np
from scipy import signal

from app.core.utils import crest_factor_db


@dataclass(slots=True)
class WaveformResult:
    name: str
    samples: np.ndarray
    sample_rate: float
    metadata: Dict[str, str]
    crest_factor_db: float


def sine(sample_rate: float, frequency: float, duration_s: float) -> WaveformResult:
    t = np.arange(0, duration_s, 1.0 / sample_rate)
    samples = np.exp(1j * 2 * np.pi * frequency * t).astype(np.complex64)
    return WaveformResult(
        name="sine",
        samples=samples,
        sample_rate=sample_rate,
        metadata={"frequency": f"{frequency}"},
        crest_factor_db=crest_factor_db(samples),
    )


def square(sample_rate: float, frequency: float, duration_s: float) -> WaveformResult:
    t = np.arange(0, duration_s, 1.0 / sample_rate)
    samples = signal.square(2 * np.pi * frequency * t).astype(np.complex64)
    return WaveformResult(
        name="square",
        samples=samples,
        sample_rate=sample_rate,
        metadata={"frequency": f"{frequency}"},
        crest_factor_db=crest_factor_db(samples),
    )


def triangle(sample_rate: float, frequency: float, duration_s: float) -> WaveformResult:
    t = np.arange(0, duration_s, 1.0 / sample_rate)
    samples = signal.sawtooth(2 * np.pi * frequency * t, width=0.5).astype(np.complex64)
    return WaveformResult(
        name="triangle",
        samples=samples,
        sample_rate=sample_rate,
        metadata={"frequency": f"{frequency}"},
        crest_factor_db=crest_factor_db(samples),
    )


def chirp(sample_rate: float, f0: float, f1: float, duration_s: float) -> WaveformResult:
    t = np.arange(0, duration_s, 1.0 / sample_rate)
    samples = signal.chirp(t, f0=f0, f1=f1, t1=duration_s, method="linear")
    waveform = samples.astype(np.complex64)
    return WaveformResult(
        name="chirp",
        samples=waveform,
        sample_rate=sample_rate,
        metadata={"f0": f"{f0}", "f1": f"{f1}"},
        crest_factor_db=crest_factor_db(waveform),
    )


def multitone(sample_rate: float, tones: Iterable[Tuple[float, float]], duration_s: float) -> WaveformResult:
    t = np.arange(0, duration_s, 1.0 / sample_rate)
    waveform = np.zeros_like(t, dtype=np.complex64)
    meta: Dict[str, str] = {}
    for idx, (freq, amp) in enumerate(tones):
        waveform += amp * np.exp(1j * 2 * np.pi * freq * t)
        meta[f"tone_{idx}"] = f"{freq}:{amp}"
    return WaveformResult(
        name="multitone",
        samples=waveform.astype(np.complex64),
        sample_rate=sample_rate,
        metadata=meta,
        crest_factor_db=crest_factor_db(waveform),
    )


def prbs(sample_rate: float, order: int, duration_s: float) -> WaveformResult:
    seq_length = (1 << order) - 1
    seq = signal.max_len_seq(order)[0]
    repetitions = int(math.ceil((duration_s * sample_rate) / len(seq)))
    tiled = np.tile(seq, repetitions)[: int(duration_s * sample_rate)]
    samples = (2 * tiled - 1).astype(np.float32)
    waveform = samples.astype(np.complex64)
    return WaveformResult(
        name="prbs",
        samples=waveform,
        sample_rate=sample_rate,
        metadata={"order": str(order)},
        crest_factor_db=crest_factor_db(waveform),
    )


def arbitrary_from_file(path: Path, sample_rate: float) -> WaveformResult:
    from .iqio import load_iq

    samples, inferred_rate = load_iq(path)
    metadata = {"source": str(path)}
    if inferred_rate:
        metadata["source_rate"] = str(inferred_rate)
    return WaveformResult(
        name=path.stem,
        samples=samples.astype(np.complex64),
        sample_rate=sample_rate or inferred_rate,
        metadata=metadata,
        crest_factor_db=crest_factor_db(samples),
    )


WAVEFORMS: Dict[str, Callable[..., WaveformResult]] = {
    "sine": sine,
    "square": square,
    "triangle": triangle,
    "chirp": chirp,
    "multitone": multitone,
    "prbs": prbs,
}


__all__ = ["WaveformResult", "WAVEFORMS", "arbitrary_from_file"]
