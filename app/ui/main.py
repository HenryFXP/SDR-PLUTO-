"""Entry point that initialises logging and launches the PyQt6 GUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.core.config import load_config
from app.core.logger import LoggerConfig, configure_logging
from app.ui.main_window import MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pluto+ Windows control board")
    parser.add_argument("--config", type=str, default=None, help="Path to configuration YAML file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(Path(args.config) if args.config else None)
    if args.debug:
        config.debug = True
        config.logging.level = "DEBUG"
    log_queue = configure_logging(
        LoggerConfig(
            level=config.logging.level,
            directory=config.logging.directory,
            rotate_bytes=config.logging.rotate_bytes,
            backup_count=config.logging.backup_count,
        )
    )
    app = QApplication(sys.argv)
    window = MainWindow(config=config, log_queue=log_queue)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
