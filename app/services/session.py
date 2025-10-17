"""Session orchestration bridging the UI to hardware services."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from app.core.config import AppConfig
from app.core.events import EventBus
from app.core.logger import get_logger
from app.core.types import DeviceConnection, TxChannelState
from app.core.utils import RateCheckResult, assert_windows, nyquist_check
from app.drivers.pluto_base import PlutoBase, PlutoDriverError
from app.drivers.pluto_mock import PlutoMock
from app.drivers.pluto_plus import PlutoPlus
from app.services.tx_pipeline import TxPipeline

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class SessionTelemetry:
    """Telemetry snapshot accessible to the UI."""

    connection: Optional[DeviceConnection]
    tx1: TxChannelState
    tx2: TxChannelState


class SessionManager:
    """High-level orchestrator for device lifecycle and pipelines."""

    def __init__(self, config: AppConfig, events: Optional[EventBus] = None) -> None:
        assert_windows()
        self._config = config
        self._events = events or EventBus()
        self._device: Optional[PlutoBase] = None
        self._connection: Optional[DeviceConnection] = None
        self._telemetry_lock = threading.Lock()
        self._tx_pipeline = TxPipeline(events=self._events)
        self._telemetry = SessionTelemetry(
            connection=None,
            tx1=TxChannelState(
                enabled=False,
                center_frequency_hz=config.tx1.center_frequency_hz,
                sample_rate_sps=config.tx1.sample_rate_sps,
                rf_bandwidth_hz=config.tx1.rf_bandwidth_hz,
                attenuation_db=config.tx1.attenuation_db,
            ),
            tx2=TxChannelState(
                enabled=False,
                center_frequency_hz=config.tx2.center_frequency_hz,
                sample_rate_sps=config.tx2.sample_rate_sps,
                rf_bandwidth_hz=config.tx2.rf_bandwidth_hz,
                attenuation_db=config.tx2.attenuation_db,
            ),
        )

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def telemetry(self) -> SessionTelemetry:
        with self._telemetry_lock:
            return self._telemetry

    def connect(self, uri: str) -> None:
        LOGGER.info("Connecting to device", extra={"uri": uri})
        driver: PlutoBase
        if uri.startswith("mock://"):
            driver = PlutoMock()
        else:
            driver = PlutoPlus()
        driver.connect(uri)
        self._device = driver
        self._connection = DeviceConnection(uri=uri, is_mock=isinstance(driver, PlutoMock))
        self._events.emit("device_connected", uri=uri)

    def disconnect(self) -> None:
        if self._device is None:
            return
        LOGGER.info("Disconnecting device")
        self._tx_pipeline.stop()
        self._device.disconnect()
        self._device = None
        self._connection = None
        self._events.emit("device_disconnected")

    def apply_channel_config(self, channel: int, state: TxChannelState) -> RateCheckResult:
        if self._device is None:
            raise PlutoDriverError("No connected device")
        result = nyquist_check(state.sample_rate_sps, state.rf_bandwidth_hz)
        if not result.is_valid:
            return result
        self._device.configure_channel(
            channel,
            center_frequency_hz=state.center_frequency_hz,
            sample_rate_sps=state.sample_rate_sps,
            rf_bandwidth_hz=state.rf_bandwidth_hz,
            attenuation_db=state.attenuation_db,
        )
        with self._telemetry_lock:
            if channel == 1:
                self._telemetry.tx1 = state
            else:
                self._telemetry.tx2 = state
        self._events.emit("channel_config_applied", channel=channel)
        return result

    def load_waveform(self, channel: int, state: TxChannelState) -> None:
        if self._device is None:
            raise PlutoDriverError("No connected device")
        if state.waveform is None or state.waveform.samples is None:
            raise PlutoDriverError("No waveform provided")
        LOGGER.debug("Loading waveform", extra={"channel": channel, "waveform": state.waveform.name})
        self._device.load_waveform(channel, state.waveform.samples, state.sample_rate_sps)
        self._events.emit("waveform_loaded", channel=channel)

    def start(self, channel: int) -> None:
        if self._device is None:
            raise PlutoDriverError("No connected device")
        self._tx_pipeline.start(channel, self._device)
        self._events.emit("channel_started", channel=channel)

    def stop(self, channel: int) -> None:
        if self._device is None:
            raise PlutoDriverError("No connected device")
        self._tx_pipeline.stop_channel(channel)
        self._events.emit("channel_stopped", channel=channel)

    def snapshot(self) -> SessionTelemetry:
        with self._telemetry_lock:
            return self._telemetry


__all__ = ["SessionManager", "SessionTelemetry"]
