"""Device controller for Pluto+ SDR.

This module provides a thread-safe wrapper around ``adi.Pluto`` that handles
context discovery, RX streaming, TX waveform control, and shared device
configuration. The controller exposes a callback-based API so that GUI or other
clients can react to asynchronous events without directly depending on Qt.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from importlib import import_module, util
from pathlib import Path
from typing import Callable, Dict, List, Optional

adi_spec = util.find_spec("adi")
adi = import_module("adi") if adi_spec is not None else None  # type: ignore

iio_spec = util.find_spec("iio")
iio = import_module("iio") if iio_spec is not None else None  # type: ignore

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Collection of metadata about the connected SDR."""

    name: str = "Unknown"
    uri: str = ""
    driver: str = ""
    firmware: str = ""


@dataclass
class RXSettings:
    """Runtime configuration for a single RX channel."""

    channel: int = 0
    center_frequency: float = 2.4e9
    sample_rate: float = 20e6
    rf_bandwidth: float = 20e6
    fft_size: int = 4096
    averaging: int = 1
    gain: float = 0.0
    agc_enabled: bool = True
    buffer_size: int = 4096


@dataclass
class TXSettings:
    """Runtime configuration for a single TX channel."""

    channel: int = 0
    center_frequency: float = 2.4e9
    sample_rate: float = 20e6
    rf_bandwidth: float = 20e6
    hardware_gain: float = -10.0
    baseband_amplitude: float = 0.5
    waveform: str = "single-tone"
    cyclic: bool = True
    buffer_size: int = 4096


class PlutoConnectionError(RuntimeError):
    """Raised when a connection to the Pluto+ device cannot be established."""


class DeviceController:
    """Thread-safe controller that manages a Pluto+ SDR instance.

    Parameters
    ----------
    rx_callback:
        Optional callable that receives RX baseband samples as a NumPy array
        along with a monotonic timestamp whenever new data is captured.
    simulate:
        When ``True`` a mock device is created to ease development or unit
        testing on machines without access to real hardware.
    """

    RXCallback = Callable[[np.ndarray, float, RXSettings], None]

    def __init__(
        self,
        rx_callback: Optional[RXCallback] = None,
        *,
        simulate: bool = False,
    ) -> None:
        self._rx_callback = rx_callback
        self._simulate = simulate or adi is None
        self._device: Optional["adi.Pluto"] = None  # type: ignore[name-defined]
        self._rx_thread: Optional[threading.Thread] = None
        self._rx_stop = threading.Event()
        self._lock = threading.RLock()
        self._rx_settings = RXSettings()
        self._tx_settings: Dict[int, TXSettings] = {
            0: TXSettings(channel=0),
            1: TXSettings(channel=1),
        }
        self._connected = False
        self._device_info = DeviceInfo()

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    def discover_contexts(self) -> List[str]:
        """Discover available IIO contexts.

        The function prefers USB URIs followed by IP-based URIs. When libiio is
        unavailable, a default list containing only ``"local"`` is returned.
        """

        usb_contexts: List[str] = []
        ip_contexts: List[str] = []
        if iio is None:
            logger.warning("libiio not available; falling back to local context")
            return ["local"]

        try:
            contexts = getattr(iio, "scan_contexts", None)
            if contexts is None:
                raise AttributeError("scan_contexts not available")
            for uri, desc in contexts().items():  # type: ignore[call-arg]
                uri = str(uri)
                if uri.startswith("usb"):
                    usb_contexts.append(uri)
                elif uri.startswith("ip"):
                    ip_contexts.append(uri)
                else:
                    ip_contexts.append(uri)
        except Exception as exc:  # pragma: no cover - discovery failure
            logger.error("Unable to scan IIO contexts: %s", exc)

        ordered = usb_contexts + ip_contexts
        if not ordered:
            ordered.append("local")
        return ordered

    def connect(self) -> None:
        """Attempt to connect to the first available context."""

        with self._lock:
            if self._connected:
                return

            if self._simulate:
                logger.info("Starting device controller in simulation mode")
                self._device_info = DeviceInfo(name="Simulated Pluto+", uri="sim")
                self._connected = True
                return

            if adi is None:  # pragma: no cover - already covered by simulate flag
                raise PlutoConnectionError("pyadi-iio is not available")

            for uri in self.discover_contexts():
                try:
                    logger.info("Attempting to connect to Pluto+ at %s", uri)
                    device = adi.Pluto(uri=uri)
                    self._device = device
                    self._connected = True
                    self._device_info = DeviceInfo(
                        name=getattr(device, "name", "Pluto"),
                        uri=uri,
                        driver=str(getattr(device, "context", "")),
                        firmware=str(getattr(device, "rx_buffer_size", "")),
                    )
                    logger.info("Connected to Pluto+ at %s", uri)
                    return
                except Exception as exc:  # pragma: no cover - hardware specific
                    logger.error("Failed to connect to %s: %s", uri, exc)

            raise PlutoConnectionError("Unable to connect to any Pluto+ device")

    def disconnect(self) -> None:
        """Disconnect from the device and release all resources."""

        with self._lock:
            self.stop_rx()
            if not self._connected:
                return
            self._device = None
            self._connected = False
            logger.info("Disconnected from Pluto+")

    # ------------------------------------------------------------------
    # RX control
    # ------------------------------------------------------------------
    def configure_rx(self, settings: RXSettings) -> None:
        """Update the configuration for the RX path."""

        with self._lock:
            self._rx_settings = settings
            if self._device is not None:
                self._apply_rx_settings()

    def _apply_rx_settings(self) -> None:
        if self._device is None:  # pragma: no cover - simulation path
            return
        device = self._device
        device.rx_lo = int(self._rx_settings.center_frequency)
        device.sample_rate = int(self._rx_settings.sample_rate)
        device.rx_rf_bandwidth = int(self._rx_settings.rf_bandwidth)
        device.gain_control_mode = "slow_attack" if self._rx_settings.agc_enabled else "manual"
        if not self._rx_settings.agc_enabled:
            device.rx_hardwaregain = float(self._rx_settings.gain)
        device.rx_buffer_size = int(self._rx_settings.buffer_size)

    def start_rx(self) -> None:
        """Start the RX worker thread if it is not already running."""

        with self._lock:
            if self._rx_thread and self._rx_thread.is_alive():
                return
            self._rx_stop.clear()
            self._rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
            self._rx_thread.start()

    def stop_rx(self) -> None:
        """Stop the RX worker thread."""

        with self._lock:
            self._rx_stop.set()
            if self._rx_thread and self._rx_thread.is_alive():
                self._rx_thread.join(timeout=1.0)
            self._rx_thread = None

    def _rx_worker(self) -> None:
        logger.debug("RX worker started")
        while not self._rx_stop.is_set():
            try:
                samples = self._read_rx_samples()
            except Exception as exc:  # pragma: no cover - runtime failure
                logger.exception("RX worker error: %s", exc)
                time.sleep(0.25)
                continue

            if samples is None or samples.size == 0:
                time.sleep(0.01)
                continue

            if self._rx_callback:
                timestamp = time.monotonic()
                try:
                    self._rx_callback(samples, timestamp, self._rx_settings)
                except Exception:  # pragma: no cover - consumer failure
                    logger.exception("RX callback raised an exception")

        logger.debug("RX worker stopped")

    def _read_rx_samples(self) -> Optional[np.ndarray]:
        """Fetch baseband samples from the device or simulator."""

        if self._simulate or self._device is None:
            size = self._rx_settings.buffer_size
            tone = np.exp(
                1j
                * 2
                * np.pi
                * np.linspace(0, 1, size, endpoint=False)
                * (self._rx_settings.center_frequency % 1e6)
                / 1e6
            )
            noise = 0.05 * (np.random.randn(size) + 1j * np.random.randn(size))
            return (tone + noise).astype(np.complex64)

        samples = self._device.rx()  # type: ignore[operator]
        return np.asarray(samples)

    # ------------------------------------------------------------------
    # TX control
    # ------------------------------------------------------------------
    def configure_tx(self, settings: TXSettings) -> None:
        """Update the configuration for a TX channel."""

        with self._lock:
            self._tx_settings[settings.channel] = settings
            if self._device is not None:
                self._apply_tx_settings(settings)

    def _apply_tx_settings(self, settings: TXSettings) -> None:
        if self._device is None:  # pragma: no cover - simulation path
            return
        device = self._device
        device.tx_lo = int(settings.center_frequency)
        device.tx_rf_bandwidth = int(settings.rf_bandwidth)
        device.tx_hardwaregain = float(settings.hardware_gain)
        device.tx_cyclic_buffer = bool(settings.cyclic)
        device.tx_buffer_size = int(settings.buffer_size)

    def stop_tx(self) -> None:
        """Stop TX on all channels."""

        if self._device is None or self._simulate:
            return
        self._device.tx_destroy_buffer()

    def transmit_waveform(self, channel: int, waveform: np.ndarray) -> None:
        """Load and transmit a baseband waveform on the given channel."""

        with self._lock:
            settings = self._tx_settings[channel]
            if self._simulate or self._device is None:
                logger.info(
                    "Simulated transmission on channel %s with %d samples",
                    channel,
                    waveform.size,
                )
                return

            self._apply_tx_settings(settings)
            self._device.tx(waveform)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Shared configuration
    # ------------------------------------------------------------------
    def set_shared_setting(self, name: str, value: object) -> None:
        """Set attributes that affect both RX and TX paths."""

        with self._lock:
            if self._device is None or self._simulate:
                return
            setattr(self._device, name, value)

    # ------------------------------------------------------------------
    # Device information & persistence
    # ------------------------------------------------------------------
    @property
    def device_info(self) -> DeviceInfo:
        """Return metadata about the current connection."""

        return self._device_info

    def export_settings(self) -> Dict[str, object]:
        """Export RX, TX, and shared settings to a dictionary."""

        with self._lock:
            return {
                "rx": self._rx_settings.__dict__,
                "tx": {k: v.__dict__ for k, v in self._tx_settings.items()},
                "device": self._device_info.__dict__,
            }

    def import_settings(self, data: Dict[str, object]) -> None:
        """Load settings from a dictionary previously created by
        :meth:`export_settings`.
        """

        rx = data.get("rx")
        if isinstance(rx, dict):
            self.configure_rx(RXSettings(**rx))

        tx_block = data.get("tx")
        if isinstance(tx_block, dict):
            for channel, tx_data in tx_block.items():
                if isinstance(tx_data, dict):
                    settings = TXSettings(**tx_data)
                    self.configure_tx(settings)

    def save_profile(self, path: Path) -> None:
        """Persist the current configuration to a JSON file."""

        payload = self.export_settings()
        path.write_text(json.dumps(payload, indent=2))

    def load_profile(self, path: Path) -> None:
        """Load a configuration profile from disk."""

        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("Invalid profile structure")
        self.import_settings(data)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Cleanly release all resources."""

        self.stop_rx()
        self.stop_tx()
        self.disconnect()


__all__ = [
    "DeviceController",
    "RXSettings",
    "TXSettings",
    "DeviceInfo",
    "PlutoConnectionError",
]
