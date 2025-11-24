from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import adi
import iio


class PlutoController:
    """
    Lazy wrapper around pyadi-iio PlutoSDR for connection and parameter updates.
    """

    def __init__(self) -> None:
        self.sdr: Optional[adi.Pluto] = None
        self.uri: Optional[str] = None

    def scan_contexts(self) -> Dict[str, str]:
        try:
            contexts = iio.scan_contexts()
        except Exception:
            return {}
        return contexts or {}

    def connect(self, uri: Optional[str] = None) -> None:
        selected_uri = None if not uri or uri == "auto" else uri
        try:
            self.sdr = adi.Pluto(uri=selected_uri)
            self.uri = uri or "auto"
        except Exception as exc:
            self.sdr = None
            raise ConnectionError(f"Failed to connect to Pluto: {exc}") from exc

    def disconnect(self) -> None:
        if self.sdr is not None:
            try:
                self.sdr.rx_destroy_buffer()
            except Exception:
                pass
            try:
                self.sdr.tx_destroy_buffer()
            except Exception:
                pass
            self.sdr = None
            self.uri = None

    @property
    def connected(self) -> bool:
        return self.sdr is not None

    def apply_rx(self, *, center_frequency: float, sample_rate: float, rf_bandwidth: float,
                 gain_mode: str, gain: float, buffer_size: int) -> None:
        if not self.sdr:
            raise RuntimeError("Pluto not connected")
        self.sdr.rx_lo = int(center_frequency)
        self.sdr.sample_rate = int(sample_rate)
        self.sdr.rx_rf_bandwidth = int(rf_bandwidth)
        self.sdr.rx_buffer_size = int(buffer_size)
        self.sdr.rx_gain_control_mode_chan0 = gain_mode
        if gain_mode.lower() == "manual":
            self.sdr.rx_hardwaregain_chan0 = float(gain)

    def apply_tx(self, *, center_frequency: float, sample_rate: float, rf_bandwidth: float,
                 attenuation: float, cyclic: bool) -> None:
        if not self.sdr:
            raise RuntimeError("Pluto not connected")
        self.sdr.tx_lo = int(center_frequency)
        self.sdr.sample_rate = int(sample_rate)
        self.sdr.tx_rf_bandwidth = int(rf_bandwidth)
        self.sdr.tx_hardwaregain_chan0 = float(attenuation)
        self.sdr.tx_cyclic_buffer = bool(cyclic)

    def rx(self) -> np.ndarray:
        if not self.sdr:
            raise RuntimeError("Pluto not connected")
        return self.sdr.rx()

    def tx(self, samples: np.ndarray) -> None:
        if not self.sdr:
            raise RuntimeError("Pluto not connected")
        self.sdr.tx(samples)
