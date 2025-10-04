"""Device detection and interface layer for PlutoSDR GUI."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np

try:
    import adi  # type: ignore
except Exception:  # pragma: no cover - fallback when pyadi-iio missing
    adi = None

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration parameters for RX/TX streaming."""

    sample_rate: float
    center_frequency: float
    bandwidth: Optional[float] = None
    gain: Optional[float] = None
    buffer_size: int = 4096
    port: Optional[str] = None


class BasePlutoDevice:
    """Abstract Pluto device interface used by the GUI."""

    uri: str

    def start_rx(self, config: StreamConfig) -> None:
        raise NotImplementedError

    def stop_rx(self) -> None:
        raise NotImplementedError

    def read_once(self) -> np.ndarray:
        raise NotImplementedError

    def start_tx(self, config: StreamConfig) -> None:
        raise NotImplementedError

    def stop_tx(self) -> None:
        raise NotImplementedError

    def write_tx(self, data: np.ndarray) -> None:
        raise NotImplementedError


class StubPlutoDevice(BasePlutoDevice):
    """Stub device that simulates IQ streaming for development."""

    def __init__(self, uri: str = "stub://local") -> None:
        self.uri = uri
        self._rx_running = False
        self._tx_running = False
        self._rx_config: Optional[StreamConfig] = None
        self._tx_config: Optional[StreamConfig] = None
        self._phase = 0.0

    def start_rx(self, config: StreamConfig) -> None:
        self._rx_running = True
        self._rx_config = config
        logger.info("Starting stub RX with %s", config)

    def stop_rx(self) -> None:
        self._rx_running = False
        logger.info("Stopping stub RX")

    def read_once(self) -> np.ndarray:
        if not self._rx_running or self._rx_config is None:
            return np.zeros(1024, dtype=np.complex64)
        num_samples = self._rx_config.buffer_size
        t = np.arange(num_samples)
        tone_freq = 1e5
        phase_inc = 2 * np.pi * tone_freq / max(self._rx_config.sample_rate, 1.0)
        self._phase = (self._phase + phase_inc * num_samples) % (2 * np.pi)
        iq = 0.5 * np.exp(1j * (phase_inc * t + self._phase))
        noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.05
        return (iq + noise).astype(np.complex64)

    def start_tx(self, config: StreamConfig) -> None:
        self._tx_running = True
        self._tx_config = config
        logger.info("Starting stub TX with %s", config)

    def stop_tx(self) -> None:
        self._tx_running = False
        logger.info("Stopping stub TX")

    def write_tx(self, data: np.ndarray) -> None:
        if not self._tx_running:
            logger.warning("Attempted to write TX data while TX is stopped")
            return
        logger.debug("Stub TX writing %d samples", data.size)


class PlutoHardwareDevice(BasePlutoDevice):
    """Wrapper around :mod:`pyadi-iio` Pluto object."""

    def __init__(self, uri: str) -> None:
        if adi is None:
            raise RuntimeError("pyadi-iio not available")
        self.uri = uri
        self._device = adi.Pluto(uri=uri)
        self._rx_config: Optional[StreamConfig] = None
        self._tx_config: Optional[StreamConfig] = None

    def start_rx(self, config: StreamConfig) -> None:
        self._rx_config = config
        self._device.rx_rf_bandwidth = config.bandwidth or self._device.rx_rf_bandwidth
        self._device.rx_lo = config.center_frequency
        self._device.sample_rate = int(config.sample_rate)
        if config.gain is not None:
            self._device.rx_hardwaregain = config.gain
        self._device.rx_buffer_size = int(config.buffer_size)
        self._device.rx_enabled = True
        logger.info("Hardware RX started on %s", self.uri)

    def stop_rx(self) -> None:
        self._device.rx_enabled = False
        logger.info("Hardware RX stopped on %s", self.uri)

    def read_once(self) -> np.ndarray:
        data = self._device.rx()
        return np.asarray(data, dtype=np.complex64)

    def start_tx(self, config: StreamConfig) -> None:
        self._tx_config = config
        self._device.tx_rf_bandwidth = config.bandwidth or self._device.tx_rf_bandwidth
        self._device.tx_lo = config.center_frequency
        self._device.sample_rate = int(config.sample_rate)
        if config.gain is not None:
            self._device.tx_hardwaregain = config.gain
        if config.port and hasattr(self._device, "tx_enabled_channels"):
            try:
                self._device.tx_enabled_channels = [config.port]
            except Exception as exc:  # pragma: no cover - hardware specific
                logger.warning("Failed to set TX port: %s", exc)
        self._device.tx_cyclic_buffer = True
        logger.info("Hardware TX configured on %s", self.uri)

    def stop_tx(self) -> None:
        self._device.tx_destroy_buffer()
        logger.info("Hardware TX stopped on %s", self.uri)

    def write_tx(self, data: np.ndarray) -> None:
        if data.dtype != np.complex64:
            data = np.asarray(data, dtype=np.complex64)
        self._device.tx(data)


class PlutoManager:
    """High level management of Pluto SDR devices."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._device: Optional[BasePlutoDevice] = None
        self._rx_thread: Optional[threading.Thread] = None
        self._rx_running = False
        self._rx_callback: Optional[Callable[[np.ndarray], None]] = None
        self._rx_config: Optional[StreamConfig] = None
        self._tx_config: Optional[StreamConfig] = None

    def available_devices(self) -> List[str]:
        """Return list of URIs for detected Pluto devices."""

        if self.dry_run or adi is None:
            return ["stub://local"]
        uris: List[str] = []
        try:
            context_manager = adi.context_manager
        except AttributeError:
            context_manager = None
        if context_manager is not None:
            try:
                for uri in context_manager.list_connections():
                    if "pluto" in uri.lower():
                        uris.append(uri)
            except Exception as exc:  # pragma: no cover - hardware specific
                logger.warning("Context manager list failed: %s", exc)
        if not uris:
            try:
                device = adi.Pluto()  # type: ignore[call-arg]
                uris.append(device.uri)
                device._ctx.destroy()
            except Exception as exc:
                logger.warning("Could not instantiate Pluto: %s", exc)
        return uris

    def connect(self, uri: Optional[str] = None) -> BasePlutoDevice:
        """Connect to the requested device or create a stub."""

        if self.dry_run or adi is None:
            self._device = StubPlutoDevice(uri or "stub://local")
        else:
            devices = self.available_devices()
            selected_uri = uri or (devices[0] if devices else "ip:192.168.2.1")
            self._device = PlutoHardwareDevice(selected_uri)
        return self._device

    def device(self) -> BasePlutoDevice:
        if self._device is None:
            return self.connect()
        return self._device

    def start_rx_stream(self, config: StreamConfig, callback: Callable[[np.ndarray], None]) -> None:
        """Start background RX stream invoking *callback* with IQ blocks."""

        self.stop_rx_stream()
        device = self.device()
        device.start_rx(config)
        self._rx_config = config
        self._rx_callback = callback
        self._rx_running = True

        def _worker() -> None:
            logger.info("RX worker started")
            while self._rx_running:
                try:
                    data = device.read_once()
                except Exception as exc:
                    logger.exception("RX read failed: %s", exc)
                    break
                if self._rx_callback is not None:
                    self._rx_callback(data)
                time.sleep(0.01)
            logger.info("RX worker exiting")

        self._rx_thread = threading.Thread(target=_worker, daemon=True)
        self._rx_thread.start()

    def stop_rx_stream(self) -> None:
        self._rx_running = False
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=0.5)
        self._rx_thread = None
        if self._device is not None and self._rx_config is not None:
            try:
                self._device.stop_rx()
            except Exception as exc:
                logger.warning("Failed to stop RX: %s", exc)
        self._rx_config = None

    def configure_tx(self, config: StreamConfig) -> None:
        device = self.device()
        device.start_tx(config)
        self._tx_config = config

    def disable_tx(self) -> None:
        if self._device is not None:
            try:
                self._device.stop_tx()
            except Exception as exc:
                logger.warning("Failed to stop TX: %s", exc)
        self._tx_config = None

    def transmit(self, data: np.ndarray) -> None:
        if self._device is None:
            raise RuntimeError("Device not connected")
        self._device.write_tx(data)

    def is_tx_active(self) -> bool:
        return self._tx_config is not None

    def current_rx_config(self) -> Optional[StreamConfig]:
        return self._rx_config

    def current_tx_config(self) -> Optional[StreamConfig]:
        return self._tx_config


__all__ = [
    "PlutoManager",
    "StreamConfig",
    "BasePlutoDevice",
]
