import numpy as np
import pytest

from a2m_tfr.alignment import estimate_delay
from a2m_tfr.channel import fractional_delay


def test_phase_slope_delay_estimation_is_sub_sample() -> None:
    fs = 125e6
    rng = np.random.default_rng(8)
    reference = rng.normal(size=1024)
    true_delay = 19.4e-9
    remote = fractional_delay(reference, true_delay, fs)
    estimate = estimate_delay(reference, remote, fs, 20e-9, 12e-9, 50e6)
    assert estimate.total_delay_s == pytest.approx(true_delay, abs=0.8e-9)
    assert len(estimate.phase_frequencies_hz) == len(estimate.cross_phase_rad)
    assert len(estimate.cross_phase_rad) == len(estimate.phase_fit_rad)
