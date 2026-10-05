from pathlib import Path

from a2m_tfr import load_config, run_simulation


def test_baseline_pipeline_recovers_delay() -> None:
    result = run_simulation(load_config(Path("configs/baseline.toml")))
    error_ns = abs(result.delay_estimate.total_delay_s - result.true_relative_delay_s) * 1e9
    assert error_ns < 2.0
    assert result.coherence_corrected > result.coherence_shared_clock_uncorrected
    expected_samples = round(result.config.science.duration_s * result.config.adc.sample_rate_hz)
    assert len(result.science_time_s) == (expected_samples + 2) // 3
