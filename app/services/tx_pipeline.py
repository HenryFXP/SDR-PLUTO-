"""Dual TX pipeline management with worker threads and backpressure."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Dict

import numpy as np

from app.core.events import GLOBAL_BUS
from app.core.logger import get_logger
from app.core.types import TxConfig, WaveformSpec
from app.core.utils import ensure_safe_amplitude, nyquist_check
from app.dsp.wavegen import generate_waveform
from app.drivers.pluto_base import PlutoBase

LOGGER = get_logger(__name__)


@dataclass
class TxStatus:
    running: bool = False
    underrun: bool = False
    timestamp: float = 0.0


class TxWorker(threading.Thread):
    def __init__(self, driver: PlutoBase, channel: str, queue: "queue.Queue[np.ndarray]") -> None:
        super().__init__(daemon=True)
        self.driver = driver
        self.channel = channel
        self.queue = queue
        self._stop_event = threading.Event()
        self.status = TxStatus()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                data = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.driver.start_tx(self.channel, data)
                self.status.running = True
                self.status.timestamp = time.time()
                GLOBAL_BUS.publish(f"tx:{self.channel}:running", self.status)
            except Exception:  # pragma: no cover
                LOGGER.exception("TX worker failed")
                self.status.underrun = True
            finally:
                self.queue.task_done()

    def stop(self) -> None:
        self._stop_event.set()
        self.status.running = False
        GLOBAL_BUS.publish(f"tx:{self.channel}:stopped", self.status)


class TxPipeline:
    """Owns waveform generation, configuration, and worker coordination."""

    def __init__(self, driver: PlutoBase) -> None:
        self.driver = driver
        self._queues: Dict[str, queue.Queue[np.ndarray]] = {
            "tx1": queue.Queue(maxsize=2),
            "tx2": queue.Queue(maxsize=2),
        }
        self._workers: Dict[str, TxWorker] = {
            channel: TxWorker(driver, channel, q) for channel, q in self._queues.items()
        }
        self._last_waveform: Dict[str, tuple[np.ndarray, WaveformSpec]] = {}
        for worker in self._workers.values():
            worker.start()

    def configure(self, config: TxConfig) -> WaveformSpec:
        nyquist_check(config.sample_rate, config.bandwidth_hz)
        self.driver.set_tx_config(config.channel, config)
        iq_spec = self._last_waveform.get(config.channel)
        if config.waveform and iq_spec:
            iq, spec = iq_spec
        elif iq_spec:
            iq, spec = iq_spec
        else:
            iq, spec = generate_waveform(
                name=f"{config.channel}-default",
                kind="sine",
                sample_rate=config.sample_rate,
                duration_s=0.01,
                amplitude=0.8,
                frequency=1e6,
            )
            self._last_waveform[config.channel] = (iq, spec)
        try:
            self._queues[config.channel].put_nowait(iq)
        except queue.Full:
            LOGGER.warning("TX queue backpressure", extra={"channel": config.channel})
        return spec

    def push_waveform(self, channel: str, iq: np.ndarray, spec: WaveformSpec) -> None:
        max_amp = np.max(np.abs(iq))
        safe_amp, clipped = ensure_safe_amplitude(float(max_amp))
        if clipped and max_amp > 0:
            iq = iq * (safe_amp / max_amp)
            GLOBAL_BUS.publish("waveform:warning", f"Amplitude clipped for {channel}")
        try:
            spec.amplitude = float(safe_amp)
            spec.num_samples = len(iq)
            self._last_waveform[channel] = (iq.astype(np.complex64), spec)
            self._queues[channel].put_nowait(self._last_waveform[channel][0])
        except queue.Full:
            LOGGER.error("TX queue full", extra={"channel": channel})

    def stop(self, channel: str) -> None:
        self.driver.stop_tx(channel)
        self._workers[channel].stop()

    def shutdown(self) -> None:
        for channel, worker in self._workers.items():
            worker.stop()
            worker.join(timeout=1.0)
            self.driver.stop_tx(channel)


__all__ = ["TxPipeline", "TxStatus"]
