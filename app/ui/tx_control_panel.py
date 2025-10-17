"""TX control interface panel."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.events import EventBus
from app.core.types import TxChannelState
from app.services.session import SessionManager


class TxControlPanel(QGroupBox):  # pragma: no cover - requires Qt runtime
    def __init__(self, session: SessionManager, events: EventBus, parent: Optional[QWidget] = None) -> None:
        super().__init__("Transmitters", parent)
        self._session = session
        self._events = events

        self._tx1_freq = QLineEdit(str(session.snapshot().tx1.center_frequency_hz))
        self._tx1_rate = QLineEdit(str(session.snapshot().tx1.sample_rate_sps))
        self._tx1_bw = QLineEdit(str(session.snapshot().tx1.rf_bandwidth_hz))
        self._tx1_gain = QLineEdit(str(session.snapshot().tx1.attenuation_db))
        self._start_tx1 = QPushButton("Start TX1")
        self._stop_tx1 = QPushButton("Stop TX1")
        self._status = QLabel("TX idle")

        form = QFormLayout()
        form.addRow("TX1 Frequency", self._tx1_freq)
        form.addRow("TX1 Sample Rate", self._tx1_rate)
        form.addRow("TX1 Bandwidth", self._tx1_bw)
        form.addRow("TX1 Attenuation", self._tx1_gain)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._start_tx1)
        layout.addWidget(self._stop_tx1)
        layout.addWidget(self._status)
        layout.addStretch()

        self._start_tx1.clicked.connect(self._start_channel1)
        self._stop_tx1.clicked.connect(self._stop_channel1)

        self._events.subscribe("channel_started", self._on_started)
        self._events.subscribe("channel_stopped", self._on_stopped)

    def _build_state(self) -> TxChannelState:
        return TxChannelState(
            enabled=True,
            center_frequency_hz=float(self._tx1_freq.text()),
            sample_rate_sps=float(self._tx1_rate.text()),
            rf_bandwidth_hz=float(self._tx1_bw.text()),
            attenuation_db=float(self._tx1_gain.text()),
            waveform=self._session.snapshot().tx1.waveform,
        )

    def _start_channel1(self) -> None:
        state = self._build_state()
        result = self._session.apply_channel_config(1, state)
        if not result.is_valid:
            self._status.setText(result.message)
            return
        try:
            self._session.start(1)
        except Exception as exc:  # pragma: no cover - GUI error path
            self._status.setText(str(exc))

    def _stop_channel1(self) -> None:
        self._session.stop(1)

    def _on_started(self, payload: dict[str, object]) -> None:
        channel = payload.get("channel")
        if channel == 1:
            self._status.setText("TX1 running")

    def _on_stopped(self, payload: dict[str, object]) -> None:
        channel = payload.get("channel")
        if channel == 1:
            self._status.setText("TX1 stopped")


__all__ = ["TxControlPanel"]
