"""Thread-safe event bus used to decouple services from the UI."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List

from .logger import get_logger

LOGGER = get_logger(__name__)
Callback = Callable[..., None]


class EventBus:
    """Simple event emitter with subscription support."""

    def __init__(self) -> None:
        self._callbacks: DefaultDict[str, List[Callback]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, callback: Callback) -> None:
        with self._lock:
            self._callbacks[event].append(callback)
            LOGGER.debug("Subscribed callback", extra={"event": event, "count": len(self._callbacks[event])})

    def unsubscribe(self, event: str, callback: Callback) -> None:
        with self._lock:
            try:
                self._callbacks[event].remove(callback)
            except ValueError:
                LOGGER.debug("Callback not registered", extra={"event": event})

    def publish(self, event: str, *args, **kwargs) -> None:
        with self._lock:
            callbacks = list(self._callbacks[event])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception:  # pragma: no cover
                LOGGER.exception("Event callback raised", extra={"event": event, "callback": repr(callback)})


GLOBAL_BUS = EventBus()


__all__ = ["EventBus", "GLOBAL_BUS"]
