# Pluto+ Windows Control Board

A modular Python 3.11+ application that targets **Windows 10/11** hosts and provides a
fast, stable GUI control surface for the Pluto+ SDR. The toolset includes dual-TX
waveform design, routing, monitoring, and headless automation utilities. The GUI is
implemented with PyQt6 + pyqtgraph and depends on Analog Devices' libiio + pyadi-iio
for hardware access.

> **Important**
> This release is tailored exclusively for Windows. Linux or macOS users should run the
> headless CLI from WSL/containers instead of launching the GUI.

## Features

- Validated YAML configuration with Windows-friendly default directories.
- Dual-transmitter control with synchronous start, underrun monitoring, and logging.
- Waveform authoring (sine, multitone, PRBS, chirp, arbitrary IQ import) with
  automatic crest-factor analysis and safe amplitude scaling.
- Live spectrum display and optional RX loopback monitor.
- Log console with rotating file capture and GUI tailing.
- Profile persistence for lab experiments, along with export helpers.
- CLI utilities for scripted transmission when the GUI is unavailable.

## Quick Start (Windows 10/11)

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) and ensure
   the "Add Python to PATH" option is checked.
2. Install libiio and pyadi-iio drivers:
   - Download and install the [Analog Devices IIO USB drivers](https://wiki.analog.com/resources/tools-software/linux-software/libiio).
   - Install the Python bindings:
     ```powershell
     py -3.11 -m pip install --upgrade pip
     py -3.11 -m pip install pyadi-iio libiio
     ```
3. Clone the repository and install dependencies via Poetry:
   ```powershell
   git clone https://example.com/SDR-PLUTO-WINDOWS.git
   cd SDR-PLUTO-WINDOWS
   py -3.11 -m pip install poetry
   poetry install
   ```
4. Launch the GUI:
   ```powershell
   poetry run pluto-gui --debug
   ```

## Configuration

Configuration files live under `configs/`. At startup the app loads `configs/default.yaml`
and merges any overrides provided via the `--config` flag or environment variables:

- `PLUTO_PROFILE_DIR` – override the profile directory.

All directories default to `%LOCALAPPDATA%\PlutoPlus`, ensuring the application has
write access without elevated privileges.

## Dual-TX Operation

- Each TX channel can be configured independently for frequency, sample rate, RF
  bandwidth, and attenuation.
- Waveforms are validated against Nyquist criteria and crest-factor limits before being
  loaded to the hardware.
- The `TxPipeline` runs worker threads per-channel so that TX1 and TX2 stream
  concurrently. Health notifications update the GUI roughly twice per second.

## Waveform Design

Use the **Waveform** panel to generate a sine tone or import IQ from `.npy`, `.c8`,
`.csv`, or `.wav`. Imported samples are normalised to 0.8 full scale by default. Crest
factor and RMS level are displayed to help maintain DAC headroom.

## Spectrum & RX Monitoring

Enable the RX monitor to stream samples into the spectrum panel for quick loopback
checks. FFT magnitudes update in real time using pyqtgraph for smooth rendering.

## CLI Utilities

Headless tasks are exposed via `poetry run pluto-cli`:

```powershell
poetry run pluto-cli transmit usb:0 .\examples\chamber_bringup.npy --center 2.45e9 --rate 30.72e6 --bandwidth 20e6
```

The CLI enforces the same validations as the GUI and shares configuration defaults.

## Profiles

Profiles are stored as YAML in `%LOCALAPPDATA%\PlutoPlus\profiles`. Use the GUI to
save or load experiment setups, or copy files between machines for repeatable chamber
runs.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Bad URI usb:0` | Ensure the Analog Devices USB driver is installed and the device is plugged in before launching the GUI. |
| `pyadi-iio is not available` | Install `libiio` and `pyadi-iio` for Windows using the steps above. |
| GUI closes immediately | Run from an elevated PowerShell to capture stack traces, or enable `--debug` for verbose logging. |
| Buffer underruns | Lower the waveform sample rate or reduce crest factor; verify USB 2.0 HS connectivity. |
| External reference not locking | Check cabling and ensure the external reference frequency matches the device configuration. |

## Developer Notes

- Code is formatted with `black` (line length 100) and linted with `ruff`.
- Pydantic models validate configuration early to surface issues before connecting to
  hardware.
- Logging uses a rotating file in `%LOCALAPPDATA%\PlutoPlus\logs` and is mirrored to the
  GUI console.
- To add a new waveform, implement a generator in `app/dsp/wavegen.py` and wire it into
  the `WaveformPanel`.
- To add a new driver, subclass `app/drivers/pluto_base.PlutoBase` and register it in
  `SessionManager.connect`.

## Testing

Unit tests run via `pytest`. Some tests mock DSP functions and therefore do not require
hardware access. Install optional dev dependencies with `poetry install --with dev`.

## License

See [LICENSE](LICENSE).
