"""Command line utilities for the Pluto+ control application."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import load_config
from app.core.logger import configure_logging
from app.core.types import TxConfig
from app.dsp.iqio import save_iq
from app.dsp.wavegen import generate_waveform
from app.services.session import SessionManager
from app.services.profiles import ProfileStore
from app.drivers.pluto_mock import PlutoMockDriver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pluto+ CLI")
    sub = parser.add_subparsers(dest="command")

    profile = sub.add_parser("profile", help="Load a profile and start transmitting")
    profile.add_argument("name", help="Profile name")
    profile.add_argument("--config", type=Path, default=None)

    export = sub.add_parser("export-iq", help="Generate a waveform and export IQ")
    export.add_argument("kind", choices=["sine", "square", "chirp", "prbs"])
    export.add_argument("--duration", type=float, default=0.01)
    export.add_argument("--frequency", type=float, default=1e6)
    export.add_argument("--amplitude", type=float, default=0.8)
    export.add_argument("--output", type=Path, required=True)

    sub.add_parser("smoke", help="Run a smoke test with the mock driver")

    return parser


def cmd_profile(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    configure_logging(
        level=config.logging.level,
        log_dir=config.logging.log_dir,
        rotate_megabytes=config.logging.rotate_megabytes,
        rotate_backups=config.logging.rotate_backups,
    )
    session = SessionManager(config)
    store = ProfileStore(config)
    session.connect("usb:0")
    payload = store.load(args.name)
    tx_config = TxConfig(
        channel="tx1",
        frequency_hz=payload["tx1"]["frequency"],
        sample_rate=payload["tx1"]["sample_rate"],
        bandwidth_hz=payload["tx1"]["bandwidth"],
        gain_db=payload["tx1"]["gain_db"],
    )
    print(f"Loaded profile {args.name}: {tx_config}")


def cmd_export(args: argparse.Namespace) -> None:
    config = load_config()
    configure_logging(
        level=config.logging.level,
        log_dir=config.logging.log_dir,
        rotate_megabytes=config.logging.rotate_megabytes,
        rotate_backups=config.logging.rotate_backups,
    )
    iq, _spec = generate_waveform(
        name=args.kind,
        kind=args.kind,
        sample_rate=config.tx1.sample_rate_sps,
        duration_s=args.duration,
        amplitude=args.amplitude,
        frequency=args.frequency,
    )
    save_iq(args.output, iq, config.tx1.sample_rate_sps)
    print(f"Saved IQ to {args.output}")


def cmd_smoke(_: argparse.Namespace) -> None:
    config = load_config()
    session = SessionManager(config, driver_factory=PlutoMockDriver)
    session.connect("mock://loopback", use_mock=True)
    print("Smoke test completed with mock driver")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "profile":
        cmd_profile(args)
    elif args.command == "export-iq":
        cmd_export(args)
    elif args.command == "smoke":
        cmd_smoke(args)
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
