from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from sigmf import SigMFFile


SIGMF_DATA_EXT = ".sigmf-data"
SIGMF_META_EXT = ".sigmf-meta"


def _base_paths(path: Path) -> Tuple[Path, Path]:
    base = path.with_suffix("") if path.suffix in (SIGMF_META_EXT, SIGMF_DATA_EXT) else path
    data_path = base.with_suffix(SIGMF_DATA_EXT)
    meta_path = base.with_suffix(SIGMF_META_EXT)
    return data_path, meta_path


def save_sigmf(
    path: Path,
    iq_data: np.ndarray,
    center_frequency: float,
    sample_rate: float,
    gain: float,
) -> Tuple[Path, Path]:
    data_path, meta_path = _base_paths(path)
    iq_data = np.asarray(iq_data, dtype=np.complex64)
    data_path.write_bytes(iq_data.tobytes())

    meta = SigMFFile(
        global_info={
            SigMFFile.GLOBAL_SAMPLE_RATE_KEY: sample_rate,
            "hw_gain_db": gain,
            "datetime": datetime.utcnow().isoformat() + "Z",
        }
    )
    meta.add_capture(0, metadata={SigMFFile.CAPTURE_FREQUENCY_KEY: center_frequency})
    meta.tofile(str(meta_path))
    return data_path, meta_path


def load_sigmf(meta_path: Path) -> Tuple[np.ndarray, Dict[str, float]]:
    meta = SigMFFile().fromfile(str(meta_path))
    data_path = Path(meta.data_file) if meta.data_file else meta_path.with_suffix(SIGMF_DATA_EXT)
    raw = np.fromfile(data_path, dtype=np.complex64)
    info = {
        "sample_rate": float(meta.get_global_field(SigMFFile.GLOBAL_SAMPLE_RATE_KEY) or 0.0),
        "center_frequency": float(
            meta.get_capture(0).get(SigMFFile.CAPTURE_FREQUENCY_KEY, 0.0) if meta.captures else 0.0
        ),
        "gain": float(meta.get_global_field("hw_gain_db") or 0.0),
    }
    return raw, info
