"""PyQt5 GUI for controlling the Pluto+ SDR."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .device_controller import DeviceController, RXSettings, TXSettings
from .signal_processing import compute_psd, estimate_power_dbfs


logger = logging.getLogger(__name__)


class LogConsole(QtWidgets.QTextEdit):
    """Simple console widget that mirrors the Python logging output."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(1000)

    def write(self, message: str) -> None:
        self.append(message.rstrip())

    def flush(self) -> None:  # pragma: no cover - Qt callback
        pass


class MatplotlibCanvas(FigureCanvas):
    """Matplotlib canvas with a single axes for spectrum plots."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        self._figure = Figure(figsize=(6, 4))
        self._axes = self._figure.add_subplot(111)
        super().__init__(self._figure)
        self.setParent(parent)
        self._axes.set_xlabel("Frequency (Hz)")
        self._axes.set_ylabel("Amplitude (dBFS)")
        self._axes.grid(True)
        self._line = self._axes.plot([], [])[0]

    def update_plot(self, freqs: np.ndarray, psd: np.ndarray) -> None:
        self._line.set_data(freqs, psd)
        self._axes.relim()
        self._axes.autoscale_view()
        self.draw_idle()


class SpectrumTab(QtWidgets.QWidget):
    """Spectrum analyzer tab handling RX visualization."""

    def __init__(self, controller: DeviceController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._current_settings = RXSettings()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.addItems(["RX1", "RX2"])
        form.addRow("Channel", self.channel_combo)

        self.center_freq = QtWidgets.QDoubleSpinBox()
        self.center_freq.setSuffix(" MHz")
        self.center_freq.setRange(50, 6000)
        self.center_freq.setValue(self._current_settings.center_frequency / 1e6)
        form.addRow("Center Frequency", self.center_freq)

        self.sample_rate = QtWidgets.QDoubleSpinBox()
        self.sample_rate.setSuffix(" MHz")
        self.sample_rate.setRange(5, 50)
        self.sample_rate.setValue(self._current_settings.sample_rate / 1e6)
        form.addRow("Sample Rate", self.sample_rate)

        self.bandwidth = QtWidgets.QDoubleSpinBox()
        self.bandwidth.setSuffix(" MHz")
        self.bandwidth.setRange(5, 50)
        self.bandwidth.setValue(self._current_settings.rf_bandwidth / 1e6)
        form.addRow("RF Bandwidth", self.bandwidth)

        self.fft_size = QtWidgets.QSpinBox()
        self.fft_size.setRange(256, 16384)
        self.fft_size.setValue(self._current_settings.fft_size)
        form.addRow("FFT Size", self.fft_size)

        self.averaging = QtWidgets.QSpinBox()
        self.averaging.setRange(1, 64)
        self.averaging.setValue(self._current_settings.averaging)
        form.addRow("Averaging", self.averaging)

        layout.addLayout(form)

        self.canvas = MatplotlibCanvas(self)
        layout.addWidget(self.canvas)

        controls = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.peak_label = QtWidgets.QLabel("Peak: -- dBFS")
        layout.addWidget(self.peak_label)

        self.start_button.clicked.connect(self.start_rx)
        self.stop_button.clicked.connect(self.stop_rx)

    def _collect_settings(self) -> RXSettings:
        settings = RXSettings(
            channel=self.channel_combo.currentIndex(),
            center_frequency=self.center_freq.value() * 1e6,
            sample_rate=self.sample_rate.value() * 1e6,
            rf_bandwidth=self.bandwidth.value() * 1e6,
            fft_size=self.fft_size.value(),
            averaging=self.averaging.value(),
        )
        return settings

    def start_rx(self) -> None:
        self._current_settings = self._collect_settings()
        self._controller.configure_rx(self._current_settings)
        self._controller.start_rx()

    def stop_rx(self) -> None:
        self._controller.stop_rx()

    def update_spectrum(self, samples: np.ndarray, timestamp: float, settings: RXSettings) -> None:
        freqs, psd = compute_psd(
            samples,
            settings.sample_rate,
            window="hann",
            fft_size=settings.fft_size,
            average=settings.averaging,
        )
        self.canvas.update_plot(freqs, psd)
        peak = float(np.max(psd))
        self.peak_label.setText(f"Peak: {peak:.1f} dBFS")


class TransmissionTab(QtWidgets.QWidget):
    """Transmission control tab."""

    waveform_requested = QtCore.pyqtSignal(int, np.ndarray)

    def __init__(self, controller: DeviceController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._settings = {
            0: TXSettings(channel=0),
            1: TXSettings(channel=1),
        }
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        for channel in (0, 1):
            tab = QtWidgets.QWidget()
            tab_layout = QtWidgets.QFormLayout(tab)

            freq = QtWidgets.QDoubleSpinBox()
            freq.setSuffix(" MHz")
            freq.setRange(50, 6000)
            freq.setValue(self._settings[channel].center_frequency / 1e6)
            tab_layout.addRow("Center Frequency", freq)

            sample = QtWidgets.QDoubleSpinBox()
            sample.setSuffix(" MHz")
            sample.setRange(5, 50)
            sample.setValue(self._settings[channel].sample_rate / 1e6)
            tab_layout.addRow("Sample Rate", sample)

            bw = QtWidgets.QDoubleSpinBox()
            bw.setSuffix(" MHz")
            bw.setRange(5, 50)
            bw.setValue(self._settings[channel].rf_bandwidth / 1e6)
            tab_layout.addRow("RF Bandwidth", bw)

            gain = QtWidgets.QDoubleSpinBox()
            gain.setSuffix(" dB")
            gain.setRange(-90, 0)
            gain.setValue(self._settings[channel].hardware_gain)
            tab_layout.addRow("Hardware Gain", gain)

            amplitude = QtWidgets.QDoubleSpinBox()
            amplitude.setRange(0.0, 1.0)
            amplitude.setSingleStep(0.01)
            amplitude.setValue(self._settings[channel].baseband_amplitude)
            tab_layout.addRow("Baseband Amplitude", amplitude)

            waveform = QtWidgets.QComboBox()
            waveform.addItems(["AWGN", "single-tone", "multi-tone", "from-file"])
            tab_layout.addRow("Waveform", waveform)

            cyclic = QtWidgets.QCheckBox("Cyclic Buffer")
            cyclic.setChecked(self._settings[channel].cyclic)
            tab_layout.addRow("", cyclic)

            buffer_size = QtWidgets.QSpinBox()
            buffer_size.setRange(1024, 1 << 16)
            buffer_size.setValue(self._settings[channel].buffer_size)
            tab_layout.addRow("Buffer Size", buffer_size)

            start_button = QtWidgets.QPushButton("Start TX")
            stop_button = QtWidgets.QPushButton("Stop TX")
            power_label = QtWidgets.QLabel("Power: -- dBFS")

            tab_layout.addRow(start_button, stop_button)
            tab_layout.addRow("TX Power", power_label)

            self.tabs.addTab(tab, f"TX{channel + 1}")

            start_button.clicked.connect(lambda _, ch=channel: self._start_tx(ch))
            stop_button.clicked.connect(lambda _, ch=channel: self._controller.stop_tx())

            # store references
            tab.freq = freq  # type: ignore[attr-defined]
            tab.sample = sample  # type: ignore[attr-defined]
            tab.bw = bw  # type: ignore[attr-defined]
            tab.gain = gain  # type: ignore[attr-defined]
            tab.amplitude = amplitude  # type: ignore[attr-defined]
            tab.waveform = waveform  # type: ignore[attr-defined]
            tab.cyclic = cyclic  # type: ignore[attr-defined]
            tab.buffer = buffer_size  # type: ignore[attr-defined]
            tab.power = power_label  # type: ignore[attr-defined]

        self.waveform_requested.connect(self._controller.transmit_waveform)

    def _collect_settings(self, channel: int) -> TXSettings:
        tab = self.tabs.widget(channel)
        assert tab is not None
        settings = TXSettings(
            channel=channel,
            center_frequency=tab.freq.value() * 1e6,
            sample_rate=tab.sample.value() * 1e6,
            rf_bandwidth=tab.bw.value() * 1e6,
            hardware_gain=tab.gain.value(),
            baseband_amplitude=tab.amplitude.value(),
            waveform=tab.waveform.currentText(),
            cyclic=tab.cyclic.isChecked(),
            buffer_size=tab.buffer.value(),
        )
        return settings

    def _generate_waveform(self, settings: TXSettings) -> np.ndarray:
        samples = settings.buffer_size
        t = np.arange(samples) / settings.sample_rate
        if settings.waveform == "AWGN":
            waveform = (
                np.random.randn(samples) + 1j * np.random.randn(samples)
            ) * settings.baseband_amplitude
        elif settings.waveform == "multi-tone":
            freqs = [0.05, 0.1, 0.15]
            waveform = sum(
                np.exp(2j * np.pi * f * t) for f in freqs
            ) * settings.baseband_amplitude / len(freqs)
        else:  # default single-tone
            waveform = settings.baseband_amplitude * np.exp(2j * np.pi * 0.1 * t)
        return waveform.astype(np.complex64)

    def _start_tx(self, channel: int) -> None:
        settings = self._collect_settings(channel)
        self._controller.configure_tx(settings)
        waveform = self._generate_waveform(settings)
        power = estimate_power_dbfs(waveform)
        tab = self.tabs.widget(channel)
        if tab is not None:
            tab.power.setText(f"Power: {power:.1f} dBFS")  # type: ignore[attr-defined]
        self.waveform_requested.emit(channel, waveform)


class ConfigTab(QtWidgets.QWidget):
    """Shared device configuration tab."""

    def __init__(self, controller: DeviceController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)

        self.agc = QtWidgets.QCheckBox("Enable AGC")
        layout.addRow(self.agc)

        self.dc_correction = QtWidgets.QCheckBox("DC Offset Correction")
        layout.addRow(self.dc_correction)

        self.lo_sync = QtWidgets.QCheckBox("LO Synchronization")
        layout.addRow(self.lo_sync)

        self.buffer_size = QtWidgets.QSpinBox()
        self.buffer_size.setRange(1024, 1 << 16)
        self.buffer_size.setValue(4096)
        layout.addRow("Shared Buffer Size", self.buffer_size)

        self.apply_button = QtWidgets.QPushButton("Apply")
        layout.addRow(self.apply_button)

        self.info_label = QtWidgets.QLabel("Device info not available")
        self.info_label.setWordWrap(True)
        layout.addRow("Device", self.info_label)

        self.apply_button.clicked.connect(self.apply_settings)

    def apply_settings(self) -> None:
        settings = {
            "rx_buffer_size": self.buffer_size.value(),
            "tx_buffer_size": self.buffer_size.value(),
            "dc_offset_tracking": int(self.dc_correction.isChecked()),
            "quad_tracking_en": int(self.lo_sync.isChecked()),
        }
        for key, value in settings.items():
            self._controller.set_shared_setting(key, value)
        info = self._controller.device_info
        self.info_label.setText(
            f"Name: {info.name}\nURI: {info.uri}\nDriver: {info.driver}\nFirmware: {info.firmware}"
        )


class ProfilesTab(QtWidgets.QWidget):
    """Manage user profiles for SDR settings."""

    def __init__(self, controller: DeviceController, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.path_edit = QtWidgets.QLineEdit(str(Path.home() / "pluto_profile.json"))
        layout.addWidget(self.path_edit)

        buttons = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Save Profile")
        self.load_button = QtWidgets.QPushButton("Load Profile")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.load_button)
        layout.addLayout(buttons)

        self.save_button.clicked.connect(self.save_profile)
        self.load_button.clicked.connect(self.load_profile)

    def save_profile(self) -> None:
        path = Path(self.path_edit.text())
        try:
            self._controller.save_profile(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def load_profile(self) -> None:
        path = Path(self.path_edit.text())
        try:
            self._controller.load_profile(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Load failed", str(exc))


class MainWindow(QtWidgets.QMainWindow):
    """Main application window that combines all tabs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pluto+ Control Center")
        self.resize(1200, 800)

        self.log_console = LogConsole()
        logging.getLogger().addHandler(self._create_handler())

        self.controller = DeviceController(rx_callback=self._on_rx_samples)
        try:
            self.controller.connect()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Connection error", str(exc))

        self.spectrum_tab = SpectrumTab(self.controller)
        self.tx_tab = TransmissionTab(self.controller)
        self.config_tab = ConfigTab(self.controller)
        self.profiles_tab = ProfilesTab(self.controller)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.spectrum_tab, "Spectrum Analyzer")
        tabs.addTab(self.tx_tab, "Transmission")
        tabs.addTab(self.config_tab, "Config")
        tabs.addTab(self.profiles_tab, "Profiles")

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(tabs)
        layout.addWidget(self.log_console)
        self.setCentralWidget(central)

    def _create_handler(self) -> logging.Handler:
        handler = logging.StreamHandler(self.log_console)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        return handler

    # ------------------------------------------------------------------
    # RX callback entry point
    # ------------------------------------------------------------------
    @QtCore.pyqtSlot(np.ndarray, float, RXSettings)
    def _on_rx_samples(self, samples: np.ndarray, timestamp: float, settings: RXSettings) -> None:
        QtCore.QMetaObject.invokeMethod(
            self,
            "_update_spectrum_ui",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(object, samples),
            QtCore.Q_ARG(float, timestamp),
            QtCore.Q_ARG(object, settings),
        )

    @QtCore.pyqtSlot(object, float, object)
    def _update_spectrum_ui(self, samples: np.ndarray, timestamp: float, settings: RXSettings) -> None:
        self.spectrum_tab.update_spectrum(samples, timestamp, settings)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # pragma: no cover - Qt
        try:
            self.controller.close()
        finally:
            super().closeEvent(event)


def run_app() -> None:
    """Entry point for launching the PyQt5 application."""

    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


__all__ = [
    "MainWindow",
    "run_app",
]
