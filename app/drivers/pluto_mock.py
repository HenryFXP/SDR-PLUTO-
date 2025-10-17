"""Offline mock driver used for CI and demo workflows."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from app.core.utils import crest_factor_db

from .pluto_base import DeviceTelemetry, PlutoBase, PlutoDriverError


class PlutoMock(PlutoBase):
    """Software-only Pluto+ emulation with deterministic timing."""

    name = "pluto-mock"

    def __init__(self, playback_path: Optional[Path] = None) -> None:
        self._uri: Optional[str] = None
        self._playback_path = playback_path
        self._channels: Dict[int, np.ndarray] = {}
        self._sample_rates: Dict[int, float] = {}
        self._running: Dict[int, bool] = {}
        self._temperatures = 32.0
        self._start_time = time.perf_counter()

    def connect(self, uri: str, timeout: float = 5.0) -> None:  # noqa: ARG002 - signature parity
        if not uri.startswith("mock://"):
            raise PlutoDriverError("Mock driver only accepts URIs beginning with mock://")
        self._uri = uri
        self._start_time = time.perf_counter()

    def disconnect(self) -> None:
        self._uri = None
        self._channels.clear()
        self._running.clear()

    def enumerate_capabilities(self) -> Dict[str, object]:
        return {
            "max_sample_rate": 61.44e6,
            "min_sample_rate": 1e3,
            "dual_tx": True,
            "supports_profile_export": True,
        }

    def load_waveform(self, channel: int, samples: np.ndarray, sample_rate: float) -> None:
        crest = crest_factor_db(samples)
        if crest > 9.0:
            raise PlutoDriverError("Crest factor too high for safe playback")
        self._channels[channel] = samples.astype(np.complex64)
        self._sample_rates[channel] = float(sample_rate)

    def start_transmit(self, channel: int) -> None:
        if channel not in self._channels:
            raise PlutoDriverError("Load a waveform before starting transmit")
        self._running[channel] = True

    def stop_transmit(self, channel: int) -> None:
        self._running[channel] = False

    def configure_channel(
        self,
        channel: int,
        *,
        center_frequency_hz: float,
        sample_rate_sps: float,
        rf_bandwidth_hz: float,
        attenuation_db: float,
    ) -> None:
        if not (70e6 <= center_frequency_hz <= 6e9):
            raise PlutoDriverError("Center frequency out of range")
        if rf_bandwidth_hz > sample_rate_sps:
            raise PlutoDriverError("RF bandwidth must not exceed sample rate")
        self._sample_rates[channel] = sample_rate_sps

    def read_temperature(self) -> DeviceTelemetry:
        elapsed = time.perf_counter() - self._start_time
        temperature = self._temperatures + 1.5 * math.sin(elapsed / 30.0)
        return DeviceTelemetry(temperature_c=temperature, lo_locked=True, tx_power_dbm=-10.0)

    def capture(self, channel: int, samples: int) -> np.ndarray:
        waveform = self._channels.get(channel)
        if waveform is None:
            raise PlutoDriverError("Nothing captured; channel is empty")
        tiles = int(np.ceil(samples / len(waveform)))
        repeated = np.tile(waveform, tiles)
        return repeated[:samples]


__all__ = ["PlutoMock"]
