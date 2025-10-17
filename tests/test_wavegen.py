import numpy as np

from app.dsp.wavegen import chirp, sine


def test_sine_waveform_shape():
    result = sine(sample_rate=1e6, frequency=100e3, duration_s=0.001)
    assert result.samples.dtype == np.complex64
    assert len(result.samples) == int(1e6 * 0.001)
    assert result.crest_factor_db >= 0


def test_chirp_metadata():
    result = chirp(sample_rate=1e6, f0=10e3, f1=200e3, duration_s=0.002)
    assert "f0" in result.metadata
    assert "f1" in result.metadata
    assert result.sample_rate == 1e6
