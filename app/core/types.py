"""Typed containers shared throughout the Pluto+ Windows control board."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Protocol

import numpy as np


@dataclass(slots=True)
class DeviceConnection:
    """Captures how the application connects to a Pluto+ radio."""

    uri: str
    serial: Optional[str] = None
    firmware: Optional[str] = None
    is_mock: bool = False


@dataclass(slots=True)
class WaveformSpec:
    """Describes a waveform that can be scheduled on a TX path."""

    name: str
    samples: Optional[np.ndarray]
    sample_rate: float
    rms_level: float
    crest_factor_db: float
    metadata: Dict[str, str]
    source_path: Optional[Path] = None


@dataclass(slots=True)
class TxChannelState:
    """State exposed to the GUI for each transmitter."""

    enabled: bool
    center_frequency_hz: float
    sample_rate_sps: float
    rf_bandwidth_hz: float
    attenuation_db: float
    waveform: Optional[WaveformSpec] = None
    underruns: int = 0
    temperature_c: Optional[float] = None


class SupportsClose(Protocol):
    def close(self) -> None:  # pragma: no cover - structural type only
        ...


__all__ = [
    "DeviceConnection",
    "TxChannelState",
    "WaveformSpec",
    "SupportsClose",
]
