"""Common utility helpers for rate checks, unit conversions, and shutdown."""

from __future__ import annotations

import math
import signal
import sys
from contextlib import contextmanager
from typing import Callable, Iterable, Iterator

from .logger import get_logger

LOGGER = get_logger(__name__)


def nyquist_check(sample_rate: float, bandwidth: float) -> bool:
    """Return ``True`` when the provided bandwidth satisfies Nyquist.

    Args:
        sample_rate: Sample rate in samples per second.
        bandwidth: Occupied bandwidth in Hertz.
    """

    valid = bandwidth <= sample_rate / 2
    if not valid:
        LOGGER.warning(
            "Nyquist check failed", extra={"sample_rate": sample_rate, "bandwidth": bandwidth}
        )
    return valid


def db_to_linear(value_db: float) -> float:
    return 10 ** (value_db / 20.0)


def linear_to_db(value_linear: float) -> float:
    return 20.0 * math.log10(max(value_linear, 1e-12))


@contextmanager
def graceful_shutdown(signals: Iterable[int] = (signal.SIGINT, signal.SIGTERM)) -> Iterator[None]:
    """Context manager that installs handlers to exit cleanly."""

    def _handler(signum: int, _frame: object) -> None:
        LOGGER.info("Received termination signal", extra={"signum": signum})
        raise SystemExit(0)

    previous = {sig: signal.getsignal(sig) for sig in signals}
    try:
        for sig in signals:
            signal.signal(sig, _handler)
        yield
    finally:  # pragma: no cover - OS specific
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def ensure_safe_amplitude(amplitude: float, safe_limit: float = 0.8) -> tuple[float, bool]:
    """Clamp amplitude to a safe value and report whether clipping occurred."""

    if amplitude <= safe_limit:
        return amplitude, False
    LOGGER.warning("Amplitude exceeds safe limit", extra={"amplitude": amplitude, "limit": safe_limit})
    return safe_limit, True


def install_excepthook() -> None:
    """Install a verbose exception hook for debug sessions."""

    def _hook(exc_type, exc_value, exc_traceback):  # pragma: no cover - interactive behavior
        LOGGER.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook


def run_with_timeout(callback: Callable[[], None], timeout_s: float) -> bool:
    """Run a callback and return ``True`` if it completes before ``timeout_s``."""

    import threading

    completed = threading.Event()

    def _wrapper() -> None:
        try:
            callback()
        finally:
            completed.set()

    thread = threading.Thread(target=_wrapper, daemon=True)
    thread.start()
    finished = completed.wait(timeout_s)
    if not finished:
        LOGGER.error("Operation timed out", extra={"timeout_s": timeout_s})
    return finished


__all__ = [
    "nyquist_check",
    "db_to_linear",
    "linear_to_db",
    "graceful_shutdown",
    "clamp",
    "ensure_safe_amplitude",
    "install_excepthook",
    "run_with_timeout",
]
