"""Waveform generation helpers for the PlutoSDR GUI."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

__all__ = ["gen_awgn", "gen_multi_cw", "gen_fhss"]


def _ensure_complex64(data: np.ndarray) -> np.ndarray:
    if data.dtype != np.complex64:
        return data.astype(np.complex64)
    return data


def gen_awgn(num_samples: int, sample_rate: float, bandwidth: float, amplitude: float) -> np.ndarray:
    """Generate additive white Gaussian noise IQ samples."""

    if num_samples <= 0:
        raise ValueError("num_samples must be positive")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    bandwidth = max(min(bandwidth, sample_rate / 2), sample_rate / 100)
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) / math.sqrt(2)
    window = np.hanning(num_samples)
    spectrum = np.fft.fft(noise * window)
    freqs = np.fft.fftfreq(num_samples, d=1.0 / sample_rate)
    mask = np.abs(freqs) <= bandwidth
    spectrum *= mask.astype(float)
    noise = np.fft.ifft(spectrum)
    noise = amplitude * noise / max(np.max(np.abs(noise)), 1e-9)
    return _ensure_complex64(noise)


def gen_multi_cw(
    frequencies: Sequence[float],
    num_samples: int,
    sample_rate: float,
    amplitude: float,
) -> np.ndarray:
    """Generate multiple continuous-wave carriers."""

    if num_samples <= 0:
        raise ValueError("num_samples must be positive")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    t = np.arange(num_samples) / sample_rate
    signal = np.zeros(num_samples, dtype=np.complex128)
    for index, freq in enumerate(frequencies):
        phase = 2 * np.pi * freq * t
        signal += np.exp(1j * phase)
    if np.all(signal == 0):
        return np.zeros(num_samples, dtype=np.complex64)
    signal *= amplitude / np.max(np.abs(signal))
    return _ensure_complex64(signal)


def gen_fhss(
    hop_frequencies: Sequence[float],
    sample_rate: float,
    hop_duration: float,
    amplitude: float,
    total_duration: float,
) -> np.ndarray:
    """Generate a frequency hopping spread spectrum waveform."""

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if hop_duration <= 0:
        raise ValueError("hop_duration must be positive")
    if total_duration <= 0:
        raise ValueError("total_duration must be positive")
    if not hop_frequencies:
        raise ValueError("hop_frequencies must not be empty")

    samples_per_hop = max(int(hop_duration * sample_rate), 1)
    total_samples = max(int(total_duration * sample_rate), samples_per_hop)
    t = np.arange(total_samples) / sample_rate
    signal = np.zeros(total_samples, dtype=np.complex128)

    freq_cycle = list(hop_frequencies)
    hop_count = int(math.ceil(total_samples / samples_per_hop))
    phase = 0.0
    for hop_index in range(hop_count):
        freq = freq_cycle[hop_index % len(freq_cycle)]
        start = hop_index * samples_per_hop
        end = min(start + samples_per_hop, total_samples)
        hop_t = t[start:end]
        phase_increment = 2 * np.pi * freq / sample_rate
        phases = phase + np.arange(end - start) * phase_increment
        signal[start:end] = np.exp(1j * phases)
        phase = (phase + phase_increment * (end - start)) % (2 * np.pi)

    signal *= amplitude / max(np.max(np.abs(signal)), 1e-9)
    return _ensure_complex64(signal)
