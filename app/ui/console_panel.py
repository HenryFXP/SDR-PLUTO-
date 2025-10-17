"""Panel that displays log messages from the application."""

from __future__ import annotations

import logging
from queue import Queue
from typing import Optional

from PyQt6 import QtWidgets

class ConsolePanel(QtWidgets.QGroupBox):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Console", parent)
        self.text = QtWidgets.QPlainTextEdit(readOnly=True)
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.save_button = QtWidgets.QPushButton("Save Logs")

        layout = QtWidgets.QVBoxLayout(self)
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Level:"))
        controls.addWidget(self.filter_combo)
        controls.addStretch(1)
        controls.addWidget(self.save_button)
        layout.addLayout(controls)
        layout.addWidget(self.text)

        self.queue: Queue | None = None
        self.save_button.clicked.connect(self._save_logs)

    def attach_queue(self, queue: Queue) -> None:
        self.queue = queue

    def drain_queue(self) -> None:
        if not self.queue:
            return
        level_filter = self.filter_combo.currentText()
        threshold = getattr(logging, level_filter)
        while not self.queue.empty():
            record = self.queue.get_nowait()
            if record.levelno < threshold:
                continue
            self.text.appendPlainText(record.getMessage())

    def _save_logs(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Logs", "logs/session.log")
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.text.toPlainText())


__all__ = ["ConsolePanel"]
