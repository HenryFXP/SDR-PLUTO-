"""Application entry point for the PlutoSDR GUI."""
from __future__ import annotations

import argparse
import logging
import sys

from PyQt5 import QtCore, QtWidgets

from gui_app import MainWindow
from pluto_manager import PlutoManager


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PlutoSDR control GUI")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without hardware, using simulated data",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_argument_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    manager = PlutoManager(dry_run=args.dry_run)
    window = MainWindow(manager, dry_run=args.dry_run)
    window.showMaximized()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
