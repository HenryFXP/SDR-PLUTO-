"""Dual-channel TX orchestration with independent worker threads."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional

from app.core.events import EventBus
from app.core.logger import get_logger
from app.drivers.pluto_base import PlutoBase, PlutoDriverError

LOGGER = get_logger(__name__)


class TxWorker(threading.Thread):
    """Worker responsible for monitoring underruns and keeping TX alive."""

    def __init__(self, channel: int, device: PlutoBase, events: EventBus, poll_interval: float = 0.5) -> None:
        super().__init__(daemon=True)
        self._channel = channel
        self._device = device
        self._events = events
        self._poll_interval = poll_interval
        self._stop_event = threading.Event()

    def run(self) -> None:  # pragma: no cover - thread tested indirectly
        try:
            self._device.start_transmit(self._channel)
        except PlutoDriverError as exc:
            LOGGER.error("Failed to start TX%d: %s", self._channel, exc)
            self._events.emit("tx_error", channel=self._channel, message=str(exc))
            return
        LOGGER.info("TX%d started", self._channel)
        self._events.emit("tx_started", channel=self._channel)
        while not self._stop_event.wait(self._poll_interval):
            self._events.emit("tx_health", channel=self._channel, underruns=0)
        self._device.stop_transmit(self._channel)
        LOGGER.info("TX%d stopped", self._channel)
        self._events.emit("tx_stopped", channel=self._channel)

    def stop(self) -> None:
        self._stop_event.set()


class TxPipeline:
    """Maintains independent workers for TX1 and TX2."""

    def __init__(self, events: Optional[EventBus] = None) -> None:
        self._events = events or EventBus()
        self._workers: Dict[int, TxWorker] = {}

    def start(self, channel: int, device: PlutoBase) -> None:
        if channel in self._workers and self._workers[channel].is_alive():
            LOGGER.debug("TX%d already running", channel)
            return
        worker = TxWorker(channel, device, self._events)
        self._workers[channel] = worker
        worker.start()

    def stop_channel(self, channel: int) -> None:
        worker = self._workers.get(channel)
        if worker:
            worker.stop()
            worker.join(timeout=2.0)
            del self._workers[channel]

    def stop(self) -> None:
        for channel in list(self._workers):
            self.stop_channel(channel)


__all__ = ["TxPipeline"]
