"""Profile persistence for experiment presets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from app.core.config import AppConfig
from app.core.logger import get_logger

LOGGER = get_logger(__name__)


class ProfileStore:
    """Persist and recall experiment YAMLs with schema versioning."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.directory = config.profile.directory
        self.schema_version = config.profile.schema_version
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, payload: Dict[str, Any]) -> Path:
        payload = dict(payload)
        payload["schema_version"] = self.schema_version
        path = self.directory / f"{name}.yaml"
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle)
        LOGGER.info("Saved profile", extra={"path": str(path)})
        return path

    def load(self, name: str) -> Dict[str, Any]:
        path = self.directory / f"{name}.yaml"
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        version = payload.get("schema_version")
        if version != self.schema_version:
            LOGGER.warning(
                "Profile schema mismatch", extra={"expected": self.schema_version, "found": version}
            )
        return payload

    def list_profiles(self) -> list[str]:
        return sorted(p.stem for p in self.directory.glob("*.yaml"))


__all__ = ["ProfileStore"]
