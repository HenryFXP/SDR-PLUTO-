"""Concrete Pluto+ driver using pyadi-iio."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.core.logger import get_logger
from app.core.types import DeviceConn, TxConfig
from .pluto_base import PlutoBase

LOGGER = get_logger(__name__)

try:  # pragma: no cover - optional dependency
    import adi
except ImportError:  # pragma: no cover - handled at runtime
    adi = None


class PlutoPlusDriver(PlutoBase):
    """Driver that talks to Pluto+ hardware via libiio."""

    name = "Pluto+"

    def __init__(self) -> None:
        self._device: Any | None = None

    def connect(self, uri: str, timeout_s: float = 5.0) -> DeviceConn:
        if adi is None:
            raise RuntimeError("pyadi-iio is not installed; cannot connect to Pluto+")

        LOGGER.info("Connecting to Pluto+", extra={"uri": uri})
        start = time.time()
        while time.time() - start < timeout_s:
            try:
                self._device = adi.Pluto(uri=uri)
                break
            except Exception as exc:  # pragma: no cover - hardware dependent
                LOGGER.warning("Failed to connect, retrying", extra={"error": str(exc)})
                time.sleep(0.5)
        if self._device is None:
            raise TimeoutError(f"Failed to connect to {uri} within {timeout_s}s")

        return DeviceConn(
            uri=uri,
            serial=getattr(self._device, "serial", None),
            firmware=getattr(self._device, "fw_version", None),
            temperature_c=self.read_temperature(),
            external_ref=getattr(self._device, "rx_ext_ref_en", None),
        )

    def disconnect(self) -> None:
        if self._device:
            LOGGER.info("Disconnecting Pluto+")
            self._device = None

    def query_capabilities(self) -> dict[str, float | str | bool]:
        if not self._device:
            return {}
        return {
            "min_lo_hz": getattr(self._device, "_ctx", None) and 47e6,
            "max_lo_hz": getattr(self._device, "_ctx", None) and 6e9,
            "max_sample_rate": getattr(self._device, "tx_sample_rate", None),
            "dual_tx": True,
        }

    def set_tx_config(self, channel: str, config: TxConfig) -> None:
        if not self._device:
            raise RuntimeError("Device not connected")
        tx = self._device
        LOGGER.debug("Applying TX config", extra={"channel": channel, "config": config})
        tx.tx_rf_bandwidth = int(config.bandwidth_hz)
        tx.tx_lo = int(config.frequency_hz)
        tx.sample_rate = int(config.sample_rate)
        setattr(tx, f"tx_{channel[-1]}_attenuation", float(-config.gain_db))

    def start_tx(self, channel: str, iq: np.ndarray) -> None:
        if not self._device:
            raise RuntimeError("Device not connected")
        tx_attr = getattr(self._device, f"tx_{channel[-1]}")
        LOGGER.info("Starting TX", extra={"channel": channel, "samples": len(iq)})
        tx_attr.enabled = True
        tx_attr.dds_single_tone(scale=0, freq=0)
        tx_attr.tx_cyclic_buffer = True
        tx_attr.tx_destroy_buffer()
        tx_attr.tx(iq.astype(np.complex64).tolist())

    def stop_tx(self, channel: str) -> None:
        if not self._device:
            return
        tx_attr = getattr(self._device, f"tx_{channel[-1]}")
        LOGGER.info("Stopping TX", extra={"channel": channel})
        tx_attr.enabled = False

    def capture_rx(self, duration_s: float, sample_rate: float) -> np.ndarray:
        if not self._device:
            raise RuntimeError("Device not connected")
        rx = self._device.rx()
        num_samples = int(duration_s * sample_rate)
        rx.sample_rate = int(sample_rate)
        rx.rx_enabled_channels = [0]
        data = np.array(rx.rx_buffer_size(num_samples), dtype=np.complex64)
        return data

    def read_temperature(self) -> float | None:
        if not self._device:
            return None
        try:
            return float(getattr(self._device, "temp0_input", 0.0)) / 1000.0
        except Exception:  # pragma: no cover
            LOGGER.exception("Failed to read temperature")
            return None

    def set_external_reference(self, enabled: bool) -> bool:
        if not self._device:
            return False
        try:
            setattr(self._device, "rx_ext_ref_en", bool(enabled))
            return True
        except Exception:  # pragma: no cover
            LOGGER.exception("Failed to set external reference")
            return False

    def set_lo(self, channel: str, frequency_hz: float) -> None:
        if not self._device:
            raise RuntimeError("Device not connected")
        setattr(self._device, f"tx{channel[-1]}_lo", int(frequency_hz))

    def set_gain(self, channel: str, gain_db: float) -> None:
        if not self._device:
            raise RuntimeError("Device not connected")
        setattr(self._device, f"tx{channel[-1]}_hardwaregain", float(gain_db))


__all__ = ["PlutoPlusDriver"]
