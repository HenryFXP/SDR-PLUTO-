"""Executable entry point for the Pluto+ SDR GUI."""
from __future__ import annotations

from .gui import run_app


def main() -> None:
    """Run the Pluto+ SDR control center."""

    run_app()


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
