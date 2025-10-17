"""Optional RX monitoring pipeline using the active driver."""

from __future__ import annotations

import threading
import time
from typing import Optional

import numpy as np

from app.core.events import GLOBAL_BUS
from app.core.logger import get_logger
from app.dsp.spectrum import SpectrumAnalyzer
from app.drivers.pluto_base import PlutoBase

LOGGER = get_logger(__name__)


class RxPipeline:
    """Capture IQ from the device and compute spectra for monitoring."""

    def __init__(self, driver: PlutoBase, sample_rate: float, fft_size: int = 4096) -> None:
        self.driver = driver
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._analyzer = SpectrumAnalyzer(sample_rate, fft_size)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                iq = self.driver.capture_rx(duration_s=0.02, sample_rate=self.sample_rate)
            except NotImplementedError:
                LOGGER.debug("RX capture not implemented for driver")
                return
            except Exception:  # pragma: no cover
                LOGGER.exception("RX capture failed")
                time.sleep(1.0)
                continue
            spectrum = self._analyzer.process(iq)
            GLOBAL_BUS.publish("rx:spectrum", spectrum)
            time.sleep(0.1)


__all__ = ["RxPipeline"]
