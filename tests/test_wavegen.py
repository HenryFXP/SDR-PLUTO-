import numpy as np

from app.dsp.wavegen import generate_waveform


def test_generate_sine_waveform():
    iq, spec = generate_waveform(
        name="test",
        kind="sine",
        sample_rate=1e6,
        duration_s=0.001,
        amplitude=0.5,
        frequency=100e3,
    )
    assert iq.dtype == np.complex64
    assert len(iq) == int(1e6 * 0.001)
    assert spec.name == "test"
    assert spec.crest_factor_db >= 0
