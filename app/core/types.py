"""Common dataclasses and enumerations used throughout the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass(slots=True)
class DeviceConn:
    """Represents a connection descriptor for a Pluto+ device."""

    uri: str
    serial: Optional[str] = None
    firmware: Optional[str] = None
    temperature_c: Optional[float] = None
    external_ref: Optional[bool] = None


@dataclass(slots=True)
class WaveformSpec:
    """Description of a generated or imported waveform."""

    name: str
    kind: Literal[
        "sine",
        "square",
        "triangle",
        "prbs",
        "multitone",
        "chirp",
        "ofdm",
        "arbitrary",
    ]
    amplitude: float
    sample_rate: float
    num_samples: int
    crest_factor_db: float
    path: Optional[Path] = None
    metadata: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(slots=True)
class TxConfig:
    """Configuration for a TX pipeline."""

    channel: Literal["tx1", "tx2"]
    frequency_hz: float
    sample_rate: float
    bandwidth_hz: float
    gain_db: float
    waveform: Optional[WaveformSpec] = None
    loop_mode: Literal["continuous", "finite"] = "continuous"
    finite_iterations: int = 1
    synchronized_start: bool = False
    enabled: bool = False


__all__ = ["DeviceConn", "TxConfig", "WaveformSpec"]
