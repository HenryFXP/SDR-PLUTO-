"""Centralized logging utilities with rotating file handlers and GUI sink."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from queue import Queue
from typing import Optional

_LOGGER_CACHE: dict[str, logging.Logger] = {}
_GUI_QUEUE: Optional[Queue[logging.LogRecord]] = None


class QueueHandler(logging.Handler):
    """Simple logging handler that writes log records to a queue."""

    def __init__(self, queue: Queue[logging.LogRecord]):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except Exception:  # pragma: no cover - best effort
            pass


def configure_logging(level: str, log_dir: Path, rotate_megabytes: int, rotate_backups: int) -> None:
    """Configure global logging handlers."""

    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / "pluto_plus.log"

    handlers: list[logging.Handler] = []
    file_handler = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=rotate_megabytes * 1024 * 1024, backupCount=rotate_backups, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    handlers.append(file_handler)

    if _GUI_QUEUE is not None:
        queue_handler = QueueHandler(_GUI_QUEUE)
        queue_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        handlers.append(queue_handler)

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), handlers=handlers)


def get_logger(name: str) -> logging.Logger:
    """Get a module-level logger with caching."""

    if name not in _LOGGER_CACHE:
        _LOGGER_CACHE[name] = logging.getLogger(name)
    return _LOGGER_CACHE[name]


def set_gui_queue(queue: Queue[logging.LogRecord]) -> None:
    """Install a queue that mirrors log records to the GUI console."""

    global _GUI_QUEUE
    _GUI_QUEUE = queue


__all__ = ["configure_logging", "get_logger", "set_gui_queue", "QueueHandler"]
