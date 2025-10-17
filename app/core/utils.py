"""Utility helpers shared across the Windows-only control application."""

from __future__ import annotations

import math
import platform
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, Iterator, Tuple

import numpy as np


@dataclass(slots=True)
class RateCheckResult:
    """Outcome of a rate compatibility check."""

    is_valid: bool
    message: str


WINDOWS_ONLY_MESSAGE = (
    "This application is intended for Windows 10/11. For other platforms please use the CLI tools."
)


def assert_windows() -> None:
    """Ensure the host platform is Windows, otherwise raise an informative error."""

    if platform.system().lower() != "windows":
        raise RuntimeError(WINDOWS_ONLY_MESSAGE)


def nyquist_check(sample_rate: float, bandwidth: float) -> RateCheckResult:
    """Verify that the provided bandwidth fits within Nyquist criteria."""

    if bandwidth > sample_rate / 2:
        return RateCheckResult(
            is_valid=False,
            message=f"Bandwidth {bandwidth/1e6:.2f} MHz exceeds Nyquist for {sample_rate/1e6:.2f} MHz sample rate",
        )
    return RateCheckResult(True, "Passes Nyquist checks")


def crest_factor_db(samples: np.ndarray) -> float:
    """Calculate crest factor in dB for a complex waveform."""

    peak = np.max(np.abs(samples))
    rms = np.sqrt(np.mean(np.abs(samples) ** 2))
    if rms == 0:
        return 0.0
    return 20 * math.log10(peak / rms)


@contextmanager
def stopwatch(name: str) -> Iterator[None]:  # pragma: no cover - instrumentation helper
    start = time.perf_counter()
    yield
    duration = (time.perf_counter() - start) * 1e3
    print(f"{name} took {duration:.2f} ms")


def moving_average(values: Iterable[float], window: int) -> Iterator[float]:
    """Compute a simple moving average across a stream of values."""

    values_iter = iter(values)
    buf = []
    total = 0.0
    for value in values_iter:
        buf.append(value)
        total += value
        if len(buf) > window:
            total -= buf.pop(0)
        if len(buf) == window:
            yield total / window


def dbfs(values: np.ndarray) -> np.ndarray:
    """Convert linear samples to dBFS."""

    epsilon = 1e-12
    return 20 * np.log10(np.abs(values) + epsilon)


def integrate_band(power_spectrum: np.ndarray, freqs: np.ndarray, band: Tuple[float, float]) -> float:
    """Return integrated power across a frequency band."""

    mask = (freqs >= band[0]) & (freqs <= band[1])
    return float(np.trapz(power_spectrum[mask], freqs[mask]))


__all__ = [
    "RateCheckResult",
    "assert_windows",
    "crest_factor_db",
    "dbfs",
    "integrate_band",
    "moving_average",
    "nyquist_check",
    "stopwatch",
]
