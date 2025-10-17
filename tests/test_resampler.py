import numpy as np

from app.dsp.resampler import rational_resample


def test_rational_resample_identity():
    iq = np.ones(1024, dtype=np.complex64)
    out, rate = rational_resample(iq, 1e6, 1e6)
    assert np.array_equal(out, iq)
    assert rate == 1e6


def test_rational_resample_downsample():
    t = np.arange(1024)
    iq = np.exp(1j * 2 * np.pi * 0.1 * t)
    out, rate = rational_resample(iq, 2e6, 1e6)
    assert len(out) > 0
    assert rate == 1e6
