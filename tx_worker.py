from __future__ import annotations

from typing import Dict

import numpy as np
from PySide6.QtCore import QThread, Signal

from pluto_controller import PlutoController


class TxWorker(QThread):
    finished_once = Signal()
    error = Signal(str)

    def __init__(self, controller: PlutoController, settings: Dict[str, float], data: np.ndarray,
                 cyclic: bool):
        super().__init__()
        self.controller = controller
        self.settings = settings
        self.data = data
        self.cyclic = cyclic

    def run(self) -> None:
        if self.data.size == 0:
            self.error.emit("No TX data loaded")
            return
        try:
            self.controller.apply_tx(**self.settings, cyclic=self.cyclic)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        try:
            self.controller.tx(self.data)
            if not self.cyclic:
                self.finished_once.emit()
        except Exception as exc:
            self.error.emit(str(exc))
