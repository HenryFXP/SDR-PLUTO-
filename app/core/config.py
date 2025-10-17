"""Application configuration loading and validation utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, validator

from .logger import get_logger

LOGGER = get_logger(__name__)


class WaveformConfig(BaseModel):
    """Configuration block for waveform defaults."""

    amplitude: float = Field(0.8, ge=0.0, le=1.2, description="Fraction of full-scale output.")
    crest_factor_limit: float = Field(6.0, ge=0.0, description="Maximum crest factor in dB.")
    window: str = Field("hann", description="Default window to apply to generated waveforms.")


class TxChannelConfig(BaseModel):
    """Configuration block describing TX channel defaults and constraints."""

    enabled: bool = False
    center_frequency_hz: float = Field(2.4e9, description="Initial RF center frequency in Hz.")
    sample_rate_sps: float = Field(30.72e6, ge=1e3, description="Default DAC sample rate.")
    rf_bandwidth_hz: float = Field(20e6, ge=1e3, description="Analog filter bandwidth in Hz.")
    gain_db: float = Field(-10.0, ge=-90.0, le=0.0, description="Initial TX attenuation in dB.")
    allow_headroom_overdrive: bool = False

    @validator("rf_bandwidth_hz")
    def _validate_bandwidth(cls, value: float, values: Dict[str, Any]) -> float:
        sample_rate = values.get("sample_rate_sps", value)
        if value > sample_rate:
            raise ValueError("RF bandwidth must not exceed the sample rate to satisfy Nyquist")
        return value


class LoggingConfig(BaseModel):
    """Runtime logging configuration."""

    level: str = Field("INFO", description="Default logging level for the application.")
    log_dir: Path = Field(Path("logs"), description="Directory where log files will be stored.")
    rotate_megabytes: int = Field(10, ge=1, description="Maximum log file size before rotation.")
    rotate_backups: int = Field(5, ge=1, description="Number of rotated log files to retain.")


class DeviceDiscoveryConfig(BaseModel):
    """Configuration values used during device discovery and monitoring."""

    usb_enabled: bool = True
    ethernet_enabled: bool = True
    discovery_interval_s: float = Field(2.0, ge=0.1, description="How frequently to probe for devices.")
    temperature_poll_interval_s: float = Field(5.0, ge=1.0, description="Temperature polling rate.")


class ProfileConfig(BaseModel):
    """Configuration block for profile persistence."""

    directory: Path = Field(Path("profiles"), description="Directory containing saved profiles.")
    schema_version: str = Field("1.0", description="Profiles schema version string.")


class AppConfig(BaseModel):
    """Root configuration model for the Pluto+ control application."""

    tx1: TxChannelConfig = Field(default_factory=TxChannelConfig)
    tx2: TxChannelConfig = Field(default_factory=TxChannelConfig)
    waveform: WaveformConfig = Field(default_factory=WaveformConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    discovery: DeviceDiscoveryConfig = Field(default_factory=DeviceDiscoveryConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    debug: bool = False


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"Configuration file {path} must contain a mapping at the root level.")
    return data


def load_config(path: Optional[Path] = None, overrides: Optional[Dict[str, Any]] = None) -> AppConfig:
    """Load the application configuration from disk and apply overrides.

    Args:
        path: Optional path to a YAML configuration file. When ``None`` the
            ``configs/default.yaml`` file will be used.
        overrides: Optional mapping of configuration overrides. Nested values are
            merged on top of the parsed YAML.

    Returns:
        A fully validated :class:`AppConfig` instance.
    """

    if path is None:
        path = Path("configs/default.yaml")

    LOGGER.debug("Loading configuration", extra={"path": str(path)})

    config_dict: Dict[str, Any] = {}
    if path.exists():
        config_dict = _load_yaml(path)
    else:
        LOGGER.warning("Configuration file not found, falling back to defaults", extra={"path": str(path)})

    if overrides:
        config_dict = _deep_merge(config_dict, overrides)

    env_profile_dir = os.getenv("PLUTO_PROFILE_DIR")
    if env_profile_dir:
        config_dict.setdefault("profile", {})["directory"] = env_profile_dir

    try:
        config = AppConfig.model_validate(config_dict)
    except ValidationError as exc:
        LOGGER.error("Configuration validation failed: %s", exc)
        raise

    _ensure_directories(config)
    return config


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _ensure_directories(config: AppConfig) -> None:
    config.logging.log_dir.mkdir(parents=True, exist_ok=True)
    config.profile.directory.mkdir(parents=True, exist_ok=True)


__all__ = ["AppConfig", "load_config"]
