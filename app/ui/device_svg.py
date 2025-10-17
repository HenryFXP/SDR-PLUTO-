"""Widget rendering a simplified Pluto+ front panel SVG."""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets


class DeviceSvgWidget(QtWidgets.QFrame):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(160)
        self._active = False
        self.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel | QtWidgets.QFrame.Shadow.Raised)

    def set_status(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.setPen(QtCore.Qt.GlobalColor.darkGray)
        painter.setBrush(QtGui.QColor("#2d2d30"))
        painter.drawRoundedRect(rect, 10, 10)

        pen = QtGui.QPen(QtGui.QColor("#4caf50" if self._active else "#777"), 4)
        painter.setPen(pen)
        painter.drawLine(rect.left() + 60, rect.center().y(), rect.left() + 160, rect.center().y())
        painter.drawLine(rect.right() - 160, rect.center().y(), rect.right() - 60, rect.center().y())

        painter.setPen(QtCore.Qt.GlobalColor.white)
        painter.drawText(rect.left() + 20, rect.center().y() - 20, "TX1")
        painter.drawText(rect.right() - 100, rect.center().y() - 20, "TX2")


__all__ = ["DeviceSvgWidget"]
