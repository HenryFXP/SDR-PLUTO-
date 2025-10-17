"""Mock Pluto driver used for tests and offline demos."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from app.core.logger import get_logger
from app.core.types import DeviceConn, TxConfig
from .pluto_base import PlutoBase

LOGGER = get_logger(__name__)


class PlutoMockDriver(PlutoBase):
    """A mock implementation that records/replays IQ streams."""

    name = "PlutoMock"

    def __init__(self, iq_directory: Path | None = None) -> None:
        self._iq_directory = iq_directory or Path("tests/data")
        self._connected = False
        self._tx_buffers: Dict[str, np.ndarray] = {}
        self._recordings: Dict[str, Path] = {}

    def connect(self, uri: str, timeout_s: float = 5.0) -> DeviceConn:
        LOGGER.info("Mock connect", extra={"uri": uri})
        self._connected = True
        return DeviceConn(uri=uri, serial="MOCK1234", firmware="mock", temperature_c=32.0)

    def disconnect(self) -> None:
        LOGGER.info("Mock disconnect")
        self._connected = False

    def query_capabilities(self) -> dict[str, float | str | bool]:
        return {
            "min_lo_hz": 70e6,
            "max_lo_hz": 6e9,
            "max_sample_rate": 61.44e6,
            "dual_tx": True,
        }

    def set_tx_config(self, channel: str, config: TxConfig) -> None:
        self._ensure_connected()
        LOGGER.debug("Mock set TX config", extra={"channel": channel, "config": config})

    def start_tx(self, channel: str, iq: np.ndarray) -> None:
        self._ensure_connected()
        LOGGER.info("Mock start TX", extra={"channel": channel, "samples": len(iq)})
        self._tx_buffers[channel] = np.array(iq, dtype=np.complex64)
        if self._recordings.get(channel):
            path = self._recordings[channel]
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, self._tx_buffers[channel])

    def stop_tx(self, channel: str) -> None:
        self._ensure_connected()
        LOGGER.info("Mock stop TX", extra={"channel": channel})

    def capture_rx(self, duration_s: float, sample_rate: float) -> np.ndarray:
        self._ensure_connected()
        num_samples = int(duration_s * sample_rate)
        LOGGER.info(
            "Mock capture RX", extra={"duration_s": duration_s, "sample_rate": sample_rate, "samples": num_samples}
        )
        t = np.arange(num_samples) / sample_rate
        iq = 0.8 * np.exp(1j * 2 * np.pi * 1e6 * t)
        return iq.astype(np.complex64)

    def read_temperature(self) -> float:
        return 30.0 + 5.0 * np.sin(time.time() / 60.0)

    def set_external_reference(self, enabled: bool) -> bool:
        LOGGER.info("Mock set ext ref", extra={"enabled": enabled})
        return True

    def configure_recording(self, channel: str, path: Path) -> None:
        self._recordings[channel] = path

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Mock driver not connected")


__all__ = ["PlutoMockDriver"]
