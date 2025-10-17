"""Centralised logging utilities with a GUI-friendly queue handler."""

from __future__ import annotations

import logging
import logging.handlers
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Iterable

_LOG_QUEUE: "Queue[logging.LogRecord]" | None = None


@dataclass(slots=True)
class LoggerConfig:
    """Runtime logging configuration extracted from the validated settings."""

    level: str
    directory: Path
    rotate_bytes: int
    backup_count: int


def configure_logging(config: LoggerConfig, enable_console: bool = True) -> Queue[logging.LogRecord]:
    """Set up a rotating file logger and optional console sink."""

    global _LOG_QUEUE

    log_dir = config.directory
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    root_logger.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "plutoplus.log",
        maxBytes=config.rotate_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(_default_formatter())
    root_logger.addHandler(file_handler)

    if enable_console:
        console = logging.StreamHandler()
        console.setFormatter(_color_formatter())
        root_logger.addHandler(console)

    _LOG_QUEUE = Queue()
    queue_handler = logging.handlers.QueueHandler(_LOG_QUEUE)
    root_logger.addHandler(queue_handler)

    logging.captureWarnings(True)
    return _LOG_QUEUE


def get_log_queue() -> Queue[logging.LogRecord]:
    if _LOG_QUEUE is None:
        raise RuntimeError("Logging has not been configured")
    return _LOG_QUEUE


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def iter_recent_logs(log_directory: Path, limit: int = 200) -> Iterable[str]:
    """Yield the most recent log lines from the rotating log file."""

    log_file = log_directory / "plutoplus.log"
    if not log_file.exists():
        return []
    with log_file.open("r", encoding="utf-8", errors="ignore") as handle:
        lines = handle.readlines()[-limit:]
    return [line.rstrip("\n") for line in lines]


def _default_formatter() -> logging.Formatter:
    return logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")


def _color_formatter() -> logging.Formatter:
    class _Color(logging.Formatter):
        COLORS = {
            "DEBUG": "\033[37m",
            "INFO": "\033[32m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[35m",
        }

        RESET = "\033[0m"

        def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - cosmetic
            color = self.COLORS.get(record.levelname, "")
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    return _Color("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")


__all__ = [
    "LoggerConfig",
    "configure_logging",
    "get_log_queue",
    "get_logger",
    "iter_recent_logs",
]
