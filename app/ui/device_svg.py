"""Placeholder widget rendering a static Pluto+ diagram."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QWidget


class DeviceSvg(QSvgWidget):  # pragma: no cover - requires Qt runtime
    def __init__(self, svg_path: Optional[Path] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        if svg_path and svg_path.exists():
            self.load(str(svg_path))


__all__ = ["DeviceSvg"]
