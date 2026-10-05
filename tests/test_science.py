import numpy as np
import pytest

from a2m_tfr.science import coherence_power_ratio


def test_requirement_equivalent_delay_gives_90_percent_power() -> None:
    ratio = coherence_power_ratio(0.1024 / 20e6, 20e6)
    assert float(ratio) == pytest.approx(0.9, abs=0.002)


def test_zero_delay_is_fully_coherent() -> None:
    frequencies = np.linspace(0, 20e6, 10)
    assert np.allclose(coherence_power_ratio(0.0, frequencies), 1.0)

