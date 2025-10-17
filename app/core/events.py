"""Lightweight event bus that integrates with PyQt6 on Windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, DefaultDict, Dict, Generator, List, Optional

try:  # pragma: no cover - Qt import is environment-specific
    from PyQt6.QtCore import QObject, pyqtSignal
except Exception:  # pragma: no cover - fallback for headless tools
    QObject = object  # type: ignore[assignment]
    pyqtSignal = None  # type: ignore[assignment]

Handler = Callable[[Dict[str, object]], None]


class _QtSignalProxy(QObject):  # pragma: no cover - relies on Qt runtime
    """Qt object exposing a single broadcast signal."""

    event = pyqtSignal(str, dict)  # type: ignore[misc]


@dataclass
class Subscription:
    """Represents a registered listener that can be cancelled."""

    event: str
    handler: Handler

    def cancel(self, bus: "EventBus") -> None:
        bus.unsubscribe(self.event, self.handler)


class EventBus:
    """Event dispatcher supporting both Qt signal emission and pure Python listeners."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[Handler]] = DefaultDict(list)
        self._qt_proxy: Optional[_QtSignalProxy] = None
        if pyqtSignal is not None:
            self._qt_proxy = _QtSignalProxy()

    def subscribe(self, event: str, handler: Handler) -> Subscription:
        """Attach a new listener to an event name."""

        self._handlers[event].append(handler)
        return Subscription(event=event, handler=handler)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        """Detach a registered listener."""

        if event not in self._handlers:
            return
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            return
        if not self._handlers[event]:
            del self._handlers[event]

    def emit(self, event: str, **payload: object) -> None:
        """Publish an event to Python and Qt listeners."""

        listeners = list(self._handlers.get(event, []))
        for handler in listeners:
            handler(dict(payload))
        if self._qt_proxy is not None:  # pragma: no cover - requires Qt
            self._qt_proxy.event.emit(event, dict(payload))

    def connect_qt(self, slot: Callable[[str, Dict[str, object]], None]) -> None:
        """Connect a Qt slot to the underlying signal when Qt is present."""

        if self._qt_proxy is None:
            raise RuntimeError("Qt runtime not available; cannot connect Qt slot")
        self._qt_proxy.event.connect(slot)  # type: ignore[union-attr]

    def iter_handlers(self, event: str) -> Generator[Handler, None, None]:
        """Yield registered handlers for diagnostics and testing."""

        yield from self._handlers.get(event, [])


__all__ = ["EventBus", "Subscription"]
