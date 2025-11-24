from __future__ import annotations

from typing import Dict, Optional

import numpy as np
from PySide6.QtCore import QThread, Signal

from dsp import compute_psd
from pluto_controller import PlutoController


class RxWorker(QThread):
    spectrum_ready = Signal(object, object)
    data_ready = Signal(object)
    error = Signal(str)

    def __init__(self, controller: PlutoController, settings: Dict[str, float]):
        super().__init__()
        self.controller = controller
        self.settings = settings
        self._running = False
        self._recording = False
        self.buffers: list[np.ndarray] = []
        self._avg_state: Dict[str, np.ndarray] = {}

    def run(self) -> None:
        try:
            self.controller.apply_rx(**self.settings)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        self._running = True
        while self._running:
            try:
                samples = self.controller.rx()
            except Exception as exc:
                self.error.emit(str(exc))
                break

            if samples is None or len(samples) == 0:
                continue

            freqs, psd = compute_psd(samples, self.settings["sample_rate"], avg_state=self._avg_state)
            self.spectrum_ready.emit(freqs, psd)
            self.data_ready.emit(samples)

            if self._recording:
                self.buffers.append(np.copy(samples))

    def stop(self) -> None:
        self._running = False
        self.wait(500)

    def set_recording(self, enabled: bool) -> None:
        self._recording = enabled

    def clear_buffers(self) -> None:
        self.buffers.clear()
