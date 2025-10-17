"""Rational resampling utilities."""

from __future__ import annotations

from fractions import Fraction

import numpy as np
from scipy import signal

from app.core.logger import get_logger

LOGGER = get_logger(__name__)


def rational_resample(iq: np.ndarray, input_rate: float, output_rate: float) -> np.ndarray:
    """Resample IQ data using a rational approximation of the rate change."""

    if input_rate == output_rate:
        return iq

    frac = Fraction(output_rate, input_rate).limit_denominator(1024)
    LOGGER.info(
        "Resampling IQ",
        extra={"input_rate": input_rate, "output_rate": output_rate, "up": frac.numerator, "down": frac.denominator},
    )
    resampled = signal.resample_poly(iq, frac.numerator, frac.denominator)
    return resampled.astype(np.complex64)


__all__ = ["rational_resample"]
