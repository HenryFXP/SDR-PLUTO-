# Pluto+ Control Center

A modular PyQt5 application for controlling an Analog Devices Pluto+ SDR with two RX and two TX channels. The application demonstrates a layered architecture with a device controller, signal-processing utilities, and a GUI built with PyQt5 and Matplotlib.

## Features

- Automatic IIO context discovery with preference for USB devices.
- Spectrum analyzer with FFT, averaging, and peak readouts.
- Dual-channel transmission control with waveform presets and power estimation.
- Global configuration tab for AGC, buffer sizes, and LO synchronization.
- JSON profile management for saving and loading presets.
- Integrated log console for diagnostics.

## Getting Started

```bash
pip install -r requirements.txt  # ensure PyQt5, matplotlib, numpy, pyadi-iio
python -m sdr_pluto_app.main
```

When no hardware is available the application transparently falls back to a simulation mode so the GUI can be explored without a connected device.
