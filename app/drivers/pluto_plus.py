"""Windows-oriented Pluto+ SDR driver built on top of pyadi-iio."""

from __future__ import annotations

import contextlib
from typing import Dict, Optional

import numpy as np

try:  # pragma: no cover - heavy dependency
    import adi
except ImportError as exc:  # pragma: no cover - provide a helpful message
    adi = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:  # pragma: no cover
    _IMPORT_ERROR = None

from .pluto_base import DeviceTelemetry, PlutoBase, PlutoDriverError


class PlutoPlus(PlutoBase):
    """Concrete driver for the Pluto+ board."""

    name = "pluto-plus"

    def __init__(self) -> None:
        self._device: Optional["adi.Pluto"] = None
        self._uri: Optional[str] = None

    def connect(self, uri: str, timeout: float = 5.0) -> None:  # noqa: ARG002
        if adi is None:
            raise PlutoDriverError(
                "pyadi-iio is not available. Install the Analog Devices libiio and pyadi-iio packages."
            ) from _IMPORT_ERROR
        self._device = adi.Pluto(uri=uri)
        self._uri = uri

    def disconnect(self) -> None:
        if self._device is not None:
            with contextlib.suppress(Exception):
                self._device.destroy()
            self._device = None
        self._uri = None

    def enumerate_capabilities(self) -> Dict[str, object]:
        if self._device is None:
            raise PlutoDriverError("Device not connected")
        return {
            "max_sample_rate": getattr(self._device, "tx_sample_rate", 61.44e6),
            "min_sample_rate": getattr(self._device, "tx_sample_rate", 1e6) / 32,
            "dual_tx": True,
            "supports_profile_export": True,
        }

    def load_waveform(self, channel: int, samples: np.ndarray, sample_rate: float) -> None:
        device = self._require_device()
        if channel == 1:
            device.tx1()[:] = samples  # type: ignore[index]
        elif channel == 2:
            device.tx2()[:] = samples  # type: ignore[index]
        else:
            raise PlutoDriverError("Channel must be 1 or 2")
        setattr(device, f"tx{channel}_sample_rate", int(sample_rate))

    def start_transmit(self, channel: int) -> None:
        device = self._require_device()
        if channel == 1:
            device.tx_cyclic_buffer = True
            device.tx_enabled_channels = [0]
        elif channel == 2:
            device.tx_cyclic_buffer = True
            device.tx_enabled_channels = [1]
        else:
            raise PlutoDriverError("Channel must be 1 or 2")
        device._ctx.attrs["adi,tx-enable"].value = "enabled"  # type: ignore[attr-defined]

    def stop_transmit(self, channel: int) -> None:  # noqa: ARG002
        device = self._require_device()
        device._ctx.attrs["adi,tx-enable"].value = "disabled"  # type: ignore[attr-defined]

    def configure_channel(
        self,
        channel: int,
        *,
        center_frequency_hz: float,
        sample_rate_sps: float,
        rf_bandwidth_hz: float,
        attenuation_db: float,
    ) -> None:
        device = self._require_device()
        lo_attr = getattr(device, f"tx_lo{channel}", None)
        if lo_attr is None:
            raise PlutoDriverError(f"TX{channel} LO not exposed by device")
        lo_attr.frequency = int(center_frequency_hz)
        setattr(device, f"tx{channel}_sample_rate", int(sample_rate_sps))
        setattr(device, f"tx{channel}_rf_bandwidth", int(rf_bandwidth_hz))
        gain_attr = getattr(device, f"tx{channel}_hardwaregain", None)
        if gain_attr is None:
            raise PlutoDriverError(f"TX{channel} gain control not available")
        gain_attr = min(max(-89.75, attenuation_db), 0.0)
        setattr(device, f"tx{channel}_hardwaregain", gain_attr)

    def read_temperature(self) -> DeviceTelemetry:
        device = self._require_device()
        try:
            temp = float(device.temp0.input)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - depends on libiio
            raise PlutoDriverError("Unable to read device temperature") from exc
        lo_locked = bool(getattr(device, "tx_lo", None))
        return DeviceTelemetry(temperature_c=temp, lo_locked=lo_locked, tx_power_dbm=None)

    def capture(self, channel: int, samples: int) -> np.ndarray:
        device = self._require_device()
        if channel not in (1, 2):
            raise PlutoDriverError("Channel must be 1 or 2")
        rx = device.rx()
        rx.rx_enabled_channels = [channel - 1]
        rx.rx_buffer_size = samples
        data = rx.rx()
        return np.asarray(data, dtype=np.complex64)

    def _require_device(self) -> "adi.Pluto":
        if self._device is None:
            raise PlutoDriverError("Device not connected")
        return self._device


__all__ = ["PlutoPlus"]
