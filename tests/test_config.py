from pathlib import Path

import pytest

from a2m_tfr.config import load_config


def test_baseline_config_loads() -> None:
    config = load_config(Path("configs/baseline.toml"))
    assert config.pulse_source.pulse_count == 30
    assert config.pulse_source.active_duration_s == pytest.approx(1.745e-6)
