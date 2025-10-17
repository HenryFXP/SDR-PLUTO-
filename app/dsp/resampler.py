"""Rational resampling helpers for waveform preparation."""

from __future__ import annotations

from fractions import Fraction
from typing import Tuple

import numpy as np
from scipy.signal import resample_poly


def rational_resample(samples: np.ndarray, input_rate: float, output_rate: float) -> Tuple[np.ndarray, float]:
    """Resample complex IQ data to a new rate using polyphase filtering."""

    if input_rate == output_rate:
        return samples.astype(np.complex64), output_rate
    ratio = Fraction(output_rate, input_rate).limit_denominator(512)
    up, down = ratio.numerator, ratio.denominator
    resampled = resample_poly(samples, up, down, axis=0)
    return resampled.astype(np.complex64), output_rate


__all__ = ["rational_resample"]
