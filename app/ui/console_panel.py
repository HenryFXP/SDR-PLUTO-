"""Log console widget for Windows GUI."""

from __future__ import annotations

import logging
from queue import Queue
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout


class ConsolePanel(QWidget):  # pragma: no cover - requires Qt runtime
    def __init__(self, log_queue: Queue, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._log_queue = log_queue
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._text)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_logs)
        self._timer.start(250)

    def _poll_logs(self) -> None:
        while not self._log_queue.empty():
            record = self._log_queue.get()
            message = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s").format(record)
            self._text.appendPlainText(message)


__all__ = ["ConsolePanel"]
