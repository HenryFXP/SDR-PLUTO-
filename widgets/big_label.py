"""Reusable large label widgets for high-visibility UI."""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ["BigLabel", "apply_big_font"]


class BigLabel(QtWidgets.QLabel):
    """A QLabel with a scalable, high-contrast font."""

    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        apply_big_font(self)


def apply_big_font(widget: QtWidgets.QWidget, point_size: int | None = None) -> None:
    """Apply a large, legible font to *widget*."""

    font = widget.font()
    if point_size is None:
        point_size = max(font.pointSize(), 12)
    font.setPointSize(point_size)
    font.setBold(True)
    widget.setFont(font)
