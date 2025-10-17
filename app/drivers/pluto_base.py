"""Hardware abstraction for Pluto+ SDR hardware running on Windows hosts."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np


@dataclass(slots=True)
class DeviceTelemetry:
    """Telemetry data reported by the radio."""

    temperature_c: Optional[float]
    lo_locked: bool
    tx_power_dbm: Optional[float]


class PlutoDriverError(RuntimeError):
    """Raised when the device returns an unexpected error."""


class PlutoBase(abc.ABC):
    """Abstract base class shared by the real and mock Pluto+ drivers."""

    name: str = "pluto-base"

    @abc.abstractmethod
    def connect(self, uri: str, timeout: float = 5.0) -> None:
        """Establish a connection to the radio."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close the connection and release resources."""

    @abc.abstractmethod
    def enumerate_capabilities(self) -> Dict[str, object]:
        """Return a dictionary describing the device limits."""

    @abc.abstractmethod
    def load_waveform(self, channel: int, samples: np.ndarray, sample_rate: float) -> None:
        """Load a waveform into the TX buffer for a given channel."""

    @abc.abstractmethod
    def start_transmit(self, channel: int) -> None:
        """Begin transmitting samples on the specified channel."""

    @abc.abstractmethod
    def stop_transmit(self, channel: int) -> None:
        """Stop active transmission for the specified channel."""

    @abc.abstractmethod
    def configure_channel(
        self,
        channel: int,
        *,
        center_frequency_hz: float,
        sample_rate_sps: float,
        rf_bandwidth_hz: float,
        attenuation_db: float,
    ) -> None:
        """Apply RF configuration parameters to the channel."""

    @abc.abstractmethod
    def read_temperature(self) -> DeviceTelemetry:
        """Return the latest telemetry snapshot from the radio."""

    def capture(self, channel: int, samples: int) -> np.ndarray:
        """Optional receive capture, default implementation raises."""

        raise NotImplementedError("RX capture not supported by this driver")

    def close(self) -> None:
        self.disconnect()


__all__ = ["DeviceTelemetry", "PlutoBase", "PlutoDriverError"]
