"""Headless utilities for Windows hosts."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from app.core.config import load_config
from app.core.logger import LoggerConfig, configure_logging
from app.core.types import TxChannelState, WaveformSpec
from app.core.utils import crest_factor_db
from app.dsp.iqio import load_iq, normalise_to_dac_range
from app.services.session import SessionManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pluto+ headless utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    tx_parser = sub.add_parser("transmit", help="Load a waveform and transmit it once")
    tx_parser.add_argument("uri", type=str, help="Device URI (usb: or ip:")
    tx_parser.add_argument("iq_file", type=Path, help="Path to IQ samples")
    tx_parser.add_argument("--center", type=float, required=True, help="Center frequency in Hz")
    tx_parser.add_argument("--rate", type=float, required=True, help="Sample rate in SPS")
    tx_parser.add_argument("--bandwidth", type=float, required=True, help="RF bandwidth in Hz")
    tx_parser.add_argument("--attenuation", type=float, default=-10.0, help="Digital attenuation in dB")

    return parser


def handle_transmit(args: argparse.Namespace) -> None:
    config = load_config()
    configure_logging(
        LoggerConfig(
            level=config.logging.level,
            directory=config.logging.directory,
            rotate_bytes=config.logging.rotate_bytes,
            backup_count=config.logging.backup_count,
        ),
        enable_console=True,
    )
    session = SessionManager(config)
    session.connect(args.uri)
    samples, inferred_rate = load_iq(args.iq_file)
    if inferred_rate and not args.rate:
        args.rate = inferred_rate
    scaled = normalise_to_dac_range(samples, config.waveform.amplitude)
    waveform = WaveformSpec(
        name=args.iq_file.stem,
        samples=scaled,
        sample_rate=args.rate,
        rms_level=float(np.sqrt(np.mean(np.abs(scaled) ** 2))),
        crest_factor_db=crest_factor_db(scaled),
        metadata={"source": str(args.iq_file)},
        source_path=args.iq_file,
    )
    tx_state = TxChannelState(
        enabled=True,
        center_frequency_hz=args.center,
        sample_rate_sps=args.rate,
        rf_bandwidth_hz=args.bandwidth,
        attenuation_db=args.attenuation,
        waveform=waveform,
    )
    session.apply_channel_config(1, tx_state)
    session.load_waveform(1, tx_state)
    session.start(1)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "transmit":
        handle_transmit(args)
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
