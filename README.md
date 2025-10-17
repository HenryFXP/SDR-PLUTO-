# Pluto+ SDR Control Board

A modular, production-ready PyQt6 application for Pluto+ SDR bring-up and chamber testing. The
application delivers dual-TX waveform generation, routing, live spectrum monitoring, profile
management, and an integrated console suitable for fast lab deployments.

## Features

- Dual TX pipelines with independent configuration, synchronized triggering, and underrun alerts
- Waveform designer supporting sine, square, triangle, PRBS, multitone, chirp, OFDM, and arbitrary IQ
- Real-time FFT and waterfall displays powered by `pyqtgraph`
- Device discovery and telemetry (temperature, external reference) with session orchestration
- Configurable profile system with YAML presets for repeatable experiments
- Mock driver and CLI utilities for CI smoke tests and headless automation
- Extensive logging with rotating files, GUI console mirroring, and debug stack traces

## Installation

### Prerequisites

- Python 3.11+
- libiio installed on the host (see Analog Devices instructions)
- Pluto+ firmware 0.38 or newer
- System packages: `libglib2.0`, `libusb-1.0`, and the XCB Qt platform plugins on Linux

### Using Poetry

```bash
poetry install
```

### Using pip-tools

If you prefer `pip-tools`, export from Poetry:

```bash
poetry export -f requirements.txt --output requirements.lock
pip install -r requirements.lock
```

## Drivers and Discovery

The application supports USB and Ethernet discovery. Ensure `libiio` detects the device:

```bash
iio_info -s
```

USB permissions on Linux may require udev rules; see the Troubleshooting section.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `PLUTO_URI` | Override the default connection URI (`usb:0`) |
| `PLUTO_PROFILE_DIR` | Custom location for saved profiles |
| `QT_QPA_PLATFORM` | Set to `xcb` or `wayland` when running under non-default desktops |

## Quick Start

```bash
poetry run pluto-gui
```

1. Connect your Pluto+ via USB or Ethernet.
2. Use the Device panel to enter the URI (e.g., `usb:0`, `ip:pluto.local`).
3. Generate or import a waveform, review crest-factor warnings, and assign to TX1 or TX2.
4. Configure TX frequency, sample rate, RF bandwidth, and gain.
5. Start TX and monitor spectrum/waterfall updates at ~5–10 Hz.

## Usage Recipes

### Load and transmit a saved profile headlessly

```bash
poetry run pluto-cli profile chamber_bringup
```

### Export IQ for offline analysis

```bash
poetry run pluto-cli export-iq sine --frequency 2e6 --duration 0.05 --output iq.npy
```

### Run smoke tests with the mock SDR

```bash
poetry run pluto-cli smoke
```

## Architecture Map

```
app/
  core/       – configuration, events, logging, datatypes, utilities
  drivers/    – pluto_base ABC, pluto_plus hardware driver, pluto_mock for CI
  dsp/        – waveform generation, resampling, spectrum math, IQ I/O helpers
  services/   – session orchestration, TX/RX pipelines, profile store
  ui/         – PyQt6 widgets (device, waveform, spectrum, console, TX control)
cli/          – headless commands
configs/      – default YAML presets
resources/    – QSS themes, icons, SVGs
examples/     – ready-to-run profile samples
```

## Developer Guidelines

- Follow [Black](https://black.readthedocs.io/) style with 100-char lines; run `ruff` and `mypy` before
  submitting patches.
- Add docstrings to public classes and functions describing signal paths and constraints.
- Emit structured logging (`extra={...}`) for device operations, especially around TX enable/disable.
- New waveforms belong in `app/dsp/wavegen.py`; update `SUPPORTED_WAVEFORMS` and add tests.
- Additional drivers should subclass `PlutoBase` and live in `app/drivers/`; ensure proper timeouts and
  friendly error messaging.
- Tests live under `tests/` and should use the mock driver or golden IQ fixtures.

## FAQ

**Why do I see a crest-factor warning?**
: The waveform exceeds the default crest factor limit (6 dB). Reduce amplitude, apply windowing, or
  enable crest reduction.

**Can I synchronize TX1 and TX2?**
: Enable both channels and use the synchronized start option in future releases. The current version
  prepares the pipelines so they launch together when both queues receive data.

**How do I use an external reference?**
: Connect the ext-ref port and enable the External Reference checkbox. The driver reports lock status
  and temperature via the Device panel.

## Troubleshooting

- **USB permissions**: Add a udev rule (`/etc/udev/rules.d/53-adi-pluto.rules`) with appropriate
  vendor/product IDs, then reload rules.
- **libiio not found**: Install `libiio` and ensure `LD_LIBRARY_PATH` or `PATH` includes the library.
- **Bad URI `usb:X.Y.Z`**: Use `iio_info -s` to list devices, confirm the URI matches, and avoid USB hubs
  that block access.
- **External reference lock failures**: Verify the reference source amplitude and connector seating; the
  Device panel indicator flashes red when lock is lost.
- **Buffer underruns**: Increase waveform duration, reduce sample rate, or check for CPU contention; the
  TX panel displays underrun flags when worker threads starve.

## Exporting Telemetry

Use the Spectrum panel's **Export** button to capture the current magnitude data to CSV. Device telemetry
(temperature, gain, LO) is mirrored in logs (`logs/pluto_plus.log`) for inclusion in lab notebooks.

## Testing

```bash
poetry run pytest
```

## License

MIT License. See `LICENSE` for details.
