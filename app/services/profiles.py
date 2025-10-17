"""Experiment profile persistence for Windows hosts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Dict, List

from app.core.types import TxChannelState, WaveformSpec

PROFILE_EXTENSION = ".yaml"

try:
    import yaml
except ImportError as exc:  # pragma: no cover - documented dependency
    raise RuntimeError("pyyaml must be installed to use the profile subsystem") from exc


@dataclass(slots=True)
class Profile:
    """Describes a saved experiment configuration."""

    name: str
    tx1: TxChannelState
    tx2: TxChannelState
    waveforms: List[WaveformSpec]
    metadata: Dict[str, str]


def list_profiles(directory: Path) -> List[Path]:
    return sorted(directory.glob(f"*{PROFILE_EXTENSION}"))


def load_profile(path: Path) -> Profile:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    tx1 = TxChannelState(**data["tx1"])
    tx2 = TxChannelState(**data["tx2"])
    waveforms = []
    for wf in data.get("waveforms", []):
        waveforms.append(WaveformSpec(**wf))
    return Profile(
        name=data.get("name", path.stem),
        tx1=tx1,
        tx2=tx2,
        waveforms=waveforms,
        metadata=data.get("metadata", {}),
    )


def save_profile(path: Path, profile: Profile) -> None:
    payload = {
        "name": profile.name,
        "tx1": asdict(replace(profile.tx1, waveform=None)),
        "tx2": asdict(replace(profile.tx2, waveform=None)),
        "waveforms": [
            {
                "name": wf.name,
                "sample_rate": wf.sample_rate,
                "rms_level": wf.rms_level,
                "crest_factor_db": wf.crest_factor_db,
                "metadata": wf.metadata,
                "source_path": str(wf.source_path) if wf.source_path else None,
            }
            for wf in profile.waveforms
        ],
        "metadata": profile.metadata,
    }
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def export_profile_json(path: Path, profile: Profile) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "name": profile.name,
                "tx1": asdict(replace(profile.tx1, waveform=None)),
                "tx2": asdict(replace(profile.tx2, waveform=None)),
                "waveforms": [
                    {
                        "name": wf.name,
                        "sample_rate": wf.sample_rate,
                        "rms_level": wf.rms_level,
                        "crest_factor_db": wf.crest_factor_db,
                        "metadata": wf.metadata,
                        "source_path": str(wf.source_path) if wf.source_path else None,
                    }
                    for wf in profile.waveforms
                ],
                "metadata": profile.metadata,
            },
            handle,
            indent=2,
        )


__all__ = ["Profile", "list_profiles", "load_profile", "save_profile", "export_profile_json"]
