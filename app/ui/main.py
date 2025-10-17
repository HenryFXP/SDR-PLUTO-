"""Entry point for the Pluto+ SDR control board GUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from queue import Queue

from PyQt6 import QtWidgets

from app.core.config import load_config
from app.core.logger import configure_logging, set_gui_queue
from app.core.utils import install_excepthook
from app.services.session import SessionManager
from .main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pluto+ SDR control board")
    parser.add_argument("--config", type=Path, help="Path to configuration file", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--use-mock", action="store_true", help="Force the mock SDR driver")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.debug:
        config.debug = True
        config.logging.level = "DEBUG"

    gui_queue: Queue = Queue()
    set_gui_queue(gui_queue)
    configure_logging(
        level=config.logging.level,
        log_dir=config.logging.log_dir,
        rotate_megabytes=config.logging.rotate_megabytes,
        rotate_backups=config.logging.rotate_backups,
    )

    if config.debug:
        install_excepthook()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Pluto+ Control Board")

    session = SessionManager(config)
    window = MainWindow(config=config, session=session, gui_queue=gui_queue, use_mock=args.use_mock)
    window.show()

    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual invocation
    sys.exit(main())
