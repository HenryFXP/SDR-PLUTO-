"""Session orchestration coordinating device lifecycle and discovery."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict

from app.core.config import AppConfig
from app.core.events import GLOBAL_BUS
from app.core.logger import get_logger
from app.core.types import DeviceConn
from app.drivers.pluto_base import PlutoBase
from app.drivers.pluto_mock import PlutoMockDriver
from app.drivers.pluto_plus import PlutoPlusDriver

LOGGER = get_logger(__name__)


DriverFactory = Callable[[], PlutoBase]


class SessionManager:
    """Manages connection state, discovery, and capability cache."""

    def __init__(self, config: AppConfig, driver_factory: DriverFactory | None = None) -> None:
        self.config = config
        self.driver_factory = driver_factory or PlutoPlusDriver
        self._driver: PlutoBase | None = None
        self.connection: DeviceConn | None = None
        self.capabilities: Dict[str, float | str | bool] = {}
        self._discovery_thread: threading.Thread | None = None
        self._stop_discovery = threading.Event()

    def start_discovery(self) -> None:
        if self._discovery_thread and self._discovery_thread.is_alive():
            return
        self._stop_discovery.clear()
        self._discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self._discovery_thread.start()

    def stop_discovery(self) -> None:
        if self._discovery_thread:
            self._stop_discovery.set()
            self._discovery_thread.join(timeout=1.0)

    def _discovery_loop(self) -> None:
        while not self._stop_discovery.is_set():
            devices = self._probe_devices()
            GLOBAL_BUS.publish("discovery:update", devices)
            time.sleep(self.config.discovery.discovery_interval_s)

    def _probe_devices(self) -> list[DeviceConn]:
        devices: list[DeviceConn] = []
        # Placeholder discovery logic - emit loopback mock device for bring-up
        devices.append(DeviceConn(uri="mock://loopback", serial="MOCK1234", firmware="mock"))
        return devices

    def connect(self, uri: str, use_mock: bool = False) -> DeviceConn:
        if self._driver:
            self.disconnect()
        driver_cls = PlutoMockDriver if use_mock else self.driver_factory
        self._driver = driver_cls()
        connection = self._driver.connect(uri)
        self.connection = connection
        self.capabilities = self._driver.query_capabilities()
        GLOBAL_BUS.publish("device:connected", connection)
        LOGGER.info("Connected", extra={"uri": uri, "capabilities": self.capabilities})
        return connection

    def disconnect(self) -> None:
        if self._driver:
            self._driver.disconnect()
            GLOBAL_BUS.publish("device:disconnected")
            self._driver = None
        self.connection = None

    @property
    def driver(self) -> PlutoBase:
        if not self._driver:
            raise RuntimeError("No active driver")
        return self._driver


__all__ = ["SessionManager"]
