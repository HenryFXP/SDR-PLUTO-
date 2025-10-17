"""Abstract base driver for Pluto family devices."""

from __future__ import annotations

import abc
from typing import Iterable, Optional

import numpy as np

from app.core.types import DeviceConn, TxConfig


class PlutoBase(abc.ABC):
    """Defines the interface used by the rest of the application."""

    name: str = "Generic Pluto"

    @abc.abstractmethod
    def connect(self, uri: str, timeout_s: float = 5.0) -> DeviceConn:
        """Connect to the device at ``uri`` and return a connection descriptor."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Tear down any active connections."""

    @abc.abstractmethod
    def query_capabilities(self) -> dict[str, float | str | bool]:
        """Return a dictionary of device capabilities."""

    @abc.abstractmethod
    def set_tx_config(self, channel: str, config: TxConfig) -> None:
        """Apply the TX configuration without starting the stream."""

    @abc.abstractmethod
    def start_tx(self, channel: str, iq: np.ndarray) -> None:
        """Start transmitting IQ samples on ``channel``."""

    @abc.abstractmethod
    def stop_tx(self, channel: str) -> None:
        """Stop transmission on ``channel``."""

    def capture_rx(self, duration_s: float, sample_rate: float) -> np.ndarray:
        """Optional RX capture for monitoring; default raises ``NotImplementedError``."""

        raise NotImplementedError

    def read_temperature(self) -> Optional[float]:
        return None

    def set_external_reference(self, enabled: bool) -> bool:
        """Attempt to enable or disable an external reference."""

        return False

    def set_lo(self, channel: str, frequency_hz: float) -> None:
        """Set the LO frequency for the given channel."""

    def set_gain(self, channel: str, gain_db: float) -> None:
        """Adjust the output gain/attenuation."""


__all__ = ["PlutoBase"]
