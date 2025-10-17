"""Optional receive monitor used for loopback verification."""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np

from app.core.events import EventBus
from app.core.logger import get_logger
from app.drivers.pluto_base import PlutoBase, PlutoDriverError

LOGGER = get_logger(__name__)


class RxMonitor(threading.Thread):
    def __init__(self, device: PlutoBase, channel: int, events: EventBus, chunk: int = 4096) -> None:
        super().__init__(daemon=True)
        self._device = device
        self._channel = channel
        self._events = events
        self._chunk = chunk
        self._stop_event = threading.Event()

    def run(self) -> None:  # pragma: no cover - thread tested indirectly
        LOGGER.info("RX monitor starting", extra={"channel": self._channel})
        while not self._stop_event.wait(1.0):
            try:
                data = self._device.capture(self._channel, self._chunk)
            except PlutoDriverError as exc:
                LOGGER.error("RX capture failed: %s", exc)
                self._events.emit("rx_error", channel=self._channel, message=str(exc))
                break
            spectrum = np.abs(np.fft.fftshift(np.fft.fft(data)))
            self._events.emit("rx_samples", channel=self._channel, samples=data, spectrum=spectrum)
        LOGGER.info("RX monitor stopped", extra={"channel": self._channel})

    def stop(self) -> None:
        self._stop_event.set()


class RxPipeline:
    def __init__(self, events: Optional[EventBus] = None) -> None:
        self._events = events or EventBus()
        self._worker: Optional[RxMonitor] = None

    def start(self, device: PlutoBase, channel: int = 1) -> None:
        if self._worker and self._worker.is_alive():
            LOGGER.debug("RX monitor already running")
            return
        self._worker = RxMonitor(device, channel, self._events)
        self._worker.start()

    def stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.join(timeout=2.0)
            self._worker = None


__all__ = ["RxPipeline"]
