# PlutoSDR Control Studio

A multi-tab PyQt5 application that generates, analyzes, and visualizes ADALM-Pluto SDR signals. The GUI auto-detects connected devices, supports a safe default receive-only workflow, and exposes waveform generation, live spectrum analysis, transmitter control, and time-domain visualization.

## Features

- **Device management**: Automatic PlutoSDR discovery via `pyadi-iio` with stubbed dry-run mode for development.
- **Waveform generator**: Configure center frequency, sample rate, bandwidth, amplitude, modulation (AWGN, multi-tone CW, FHSS) and preview IQ waveforms.
- **Spectrum analyzer**: Real-time FFT/PSD display with configurable span, RBW, detectors (sample/positive/negative), averaging, and Max/Min Hold traces plus four draggable markers.
- **Transmitter**: High-visibility controls for center frequency, sample rate, bandwidth, gain, port selection, dry-run toggle, RF interlock, and emergency stop. Baseband preview updates when new waveforms are generated.
- **Time visualization**: Live IQ vs. time traces with waterfall STFT to illustrate time-frequency evolution.
- **Scalable UI**: Fullscreen-friendly layout with large fonts and consistent styling for lab environments.

## Safety Notes

- The application launches with transmission disabled and the interlock unchecked. **Do not enable TX without proper attenuation or a dummy load.**
- Use the *Dry-Run* option to validate signal chains without emitting RF.
- Keep TX gain within the provided range (-40 dB to 0 dB). Higher levels may damage equipment.
- An emergency stop button immediately disables RF output.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ensure the ADALM-Pluto USB drivers and libiio backend are installed on your system. For Linux hosts, adding udev rules for the Pluto device may be required.

## Running

```bash
python main.py           # hardware mode (requires Pluto connected)
python main.py --dry-run # simulate device streams
```

The GUI maximizes to fill the screen and scales fonts appropriately on high-DPI displays.

## Project Structure

```
├── main.py
├── gui_app.py
├── pluto_manager.py
├── dsp/
│   ├── analyzer.py
│   └── generator.py
├── tabs/
│   ├── tab_waveform.py
│   ├── tab_spectrum.py
│   ├── tab_transmitter.py
│   └── tab_timevis.py
├── widgets/
│   ├── big_label.py
│   └── controls.py
└── requirements.txt
```

Each tab module encapsulates its UI logic and streams data via `PlutoManager`, which hides hardware differences and offers a stubbed simulation path.

## Development Notes

- The GUI relies on background threads and Qt timers for streaming; avoid blocking slots with heavy work.
- Extend waveform types by adding functions in `dsp/generator.py` and wiring them through the waveform tab.
- Spectrum analyzer detector and averaging logic live in `tabs/tab_spectrum.py`—modify there for custom DSP behaviours.

## License

MIT License. See `LICENSE` if provided.
