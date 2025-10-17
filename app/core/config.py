"""Configuration management for the Pluto+ Windows control application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .logger import get_logger

LOGGER = get_logger(__name__)

_WINDOWS_CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "PlutoPlus"


class WaveformDefaults(BaseModel):
    """Default authoring parameters for generated waveforms."""

    amplitude: float = Field(0.8, ge=0.0, le=1.0, description="Default DAC amplitude scaling")
    crest_factor_limit_db: float = Field(6.0, ge=0.0, description="Maximum allowable crest factor")
    window: str = Field("hann", description="Default windowing function for preview FFTs")
    oversample_factor: int = Field(4, ge=1, description="Oversampling factor for previews")


class TxDefaults(BaseModel):
    """Per-channel configuration template."""

    enabled: bool = Field(False, description="Whether the channel is armed when sessions start")
    center_frequency_hz: float = Field(2.45e9, ge=70e6, le=6e9, description="Initial LO frequency")
    sample_rate_sps: float = Field(30.72e6, ge=10e3, le=61.44e6, description="Baseband sample rate")
    rf_bandwidth_hz: float = Field(20e6, ge=200e3, le=56e6, description="Analog filter bandwidth")
    attenuation_db: float = Field(-10.0, ge=-90.0, le=0.0, description="Digital attenuation to apply")
    sync_group: Optional[str] = Field(None, description="Optional synchronization group tag")

    @model_validator(mode="after")
    def _validate_bandwidth(cls, values: "TxDefaults") -> "TxDefaults":  # type: ignore[type-var]
        if values.rf_bandwidth_hz > values.sample_rate_sps:
            raise ValueError("RF bandwidth must not exceed the configured sample rate")
        return values


class LoggingDefaults(BaseModel):
    """Logging behaviour for the GUI and CLI entry points."""

    level: str = Field("INFO", description="Root logger level")
    directory: Path = Field(_WINDOWS_CONFIG_DIR / "logs", description="Where rotating logs are stored")
    rotate_bytes: int = Field(5 * 1024 * 1024, ge=1024, description="Maximum log size in bytes")
    backup_count: int = Field(5, ge=1, description="Number of rotated archives to keep")


class DiscoveryDefaults(BaseModel):
    """Behaviour for the USB/Ethernet discovery subsystem."""

    usb_poll_ms: int = Field(1500, ge=250, description="Interval used for USB scanning")
    ethernet_poll_ms: int = Field(3000, ge=250, description="Interval used for mDNS/hostname probing")
    telemetry_interval_ms: int = Field(2000, ge=500, description="Refresh interval for temperature & power")
    allow_mock: bool = Field(True, description="Expose the offline mock device in discovery lists")


class ProfileDefaults(BaseModel):
    """Settings for the experiment profile catalogue."""

    root: Path = Field(_WINDOWS_CONFIG_DIR / "profiles", description="Directory containing YAML profiles")
    schema_version: str = Field("2.0", description="Active profile schema version tag")


class AppConfig(BaseModel):
    """Top-level configuration for the Windows-only Pluto+ control board."""

    debug: bool = Field(False, description="Enable verbose logging and developer diagnostics")
    tx1: TxDefaults = Field(default_factory=TxDefaults)
    tx2: TxDefaults = Field(default_factory=TxDefaults)
    waveform: WaveformDefaults = Field(default_factory=WaveformDefaults)
    logging: LoggingDefaults = Field(default_factory=LoggingDefaults)
    discovery: DiscoveryDefaults = Field(default_factory=DiscoveryDefaults)
    profiles: ProfileDefaults = Field(default_factory=ProfileDefaults)

    @model_validator(mode="after")
    def _synchronise_groups(cls, values: "AppConfig") -> "AppConfig":  # type: ignore[type-var]
        if values.tx1.sync_group and values.tx1.sync_group == values.tx2.sync_group:
            LOGGER.debug("TX channels share a sync group", extra={"group": values.tx1.sync_group})
        return values


def _merge_dicts(base: MutableMapping[str, Any], overrides: Mapping[str, Any]) -> MutableMapping[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), MutableMapping):
            _merge_dicts(base[key], value)  # type: ignore[index]
        else:
            base[key] = value  # type: ignore[index]
    return base


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}
    if not isinstance(content, dict):
        raise TypeError("Configuration file must contain a mapping at the root level")
    return content


def load_config(path: Optional[Path] = None, overrides: Optional[Mapping[str, Any]] = None) -> AppConfig:
    """Load, merge, and validate the configuration tree."""

    if path is None:
        path = Path("configs/default.yaml")

    LOGGER.debug("Loading configuration", extra={"path": str(path)})

    config_map: MutableMapping[str, Any] = {}
    if path.exists():
        config_map = _load_yaml(path)
    else:
        LOGGER.warning("Configuration file not found, using defaults", extra={"path": str(path)})

    env_profile_root = os.getenv("PLUTO_PROFILE_DIR")
    if env_profile_root:
        config_map.setdefault("profiles", {})["root"] = env_profile_root

    if overrides:
        _merge_dicts(config_map, dict(overrides))

    try:
        config = AppConfig.model_validate(config_map)
    except ValidationError as exc:  # pragma: no cover - model handles messaging
        LOGGER.error("Invalid configuration", exc_info=exc)
        raise

    _prepare_directories(config)
    return config


def _prepare_directories(config: AppConfig) -> None:
    config.logging.directory.mkdir(parents=True, exist_ok=True)
    config.profiles.root.mkdir(parents=True, exist_ok=True)


__all__ = [
    "AppConfig",
    "DiscoveryDefaults",
    "LoggingDefaults",
    "ProfileDefaults",
    "TxDefaults",
    "WaveformDefaults",
    "load_config",
]
