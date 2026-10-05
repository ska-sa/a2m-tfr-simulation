"""End-to-end orchestration of the separated TFR functional blocks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .adc import sample_and_quantize
from .alignment import DelayEstimate, correct_delay, estimate_delay
from .channel import propagate
from .config import TFRConfig
from .decimation import keep_every_nth_sample
from .filters import lowpass, rf_equivalent_bandlimit
from .frontend import apply_gain, power_detect
from .pulse_source import generate_pulse_train
from .science import coherent_power, science_tones


@dataclass(frozen=True)
class SimulationResult:
    config: TFRConfig
    internal_time_s: np.ndarray
    source: np.ndarray
    rf_equivalent: np.ndarray
    reference_analog: np.ndarray
    remote_analog: np.ndarray
    adc_time_s: np.ndarray
    reference_adc: np.ndarray
    remote_adc: np.ndarray
    corrected_remote_adc: np.ndarray
    delay_estimate: DelayEstimate
    true_relative_delay_s: float
    science_time_s: np.ndarray
    science_reference: np.ndarray
    science_remote_free_running: np.ndarray
    science_remote_shared_clock: np.ndarray
    science_remote_corrected: np.ndarray
    coherence_free_running: float
    coherence_shared_clock_uncorrected: float
    coherence_corrected: float


def _receiver_frontend(signal: np.ndarray, config: TFRConfig) -> np.ndarray:
    signal = apply_gain(signal, config.frontend.rx_gain_db, config.frontend.attenuation_db)
    signal = power_detect(signal, config.frontend.detector_mode)
    return lowpass(
        signal,
        config.frontend.detector_lowpass_hz,
        config.simulation.internal_sample_rate_hz,
        config.frontend.filter_order,
    )


def run_simulation(config: TFRConfig) -> SimulationResult:
    """Run pulse calibration, delay recovery, and science coherence evaluation."""
    config.validate()
    fs = config.simulation.internal_sample_rate_hz
    rng = np.random.default_rng(config.simulation.random_seed)
    internal_time_s, source = generate_pulse_train(config.pulse_source, fs)
    rf_equivalent = rf_equivalent_bandlimit(
        source, config.frontend.rf_equivalent_bandwidth_hz, fs, config.frontend.filter_order
    )
    reference_rx = propagate(
        rf_equivalent,
        fs,
        config.channel.reference_delay_s,
        config.channel.reference_amplitude,
        config.channel.snr_db,
        rng,
    )
    remote_rx = propagate(
        rf_equivalent,
        fs,
        config.channel.remote_delay_s,
        config.channel.remote_amplitude,
        config.channel.snr_db,
        rng,
    )
    reference_analog = _receiver_frontend(reference_rx, config)
    remote_analog = _receiver_frontend(remote_rx, config)
    adc_time_s, reference_adc = sample_and_quantize(reference_analog, fs, config.adc)
    _, remote_adc = sample_and_quantize(remote_analog, fs, config.adc)
    estimate = estimate_delay(
        reference_adc,
        remote_adc,
        config.adc.sample_rate_hz,
        config.alignment.expected_relative_delay_s,
        config.alignment.search_half_width_s,
        config.alignment.estimation_bandwidth_hz,
    )
    corrected_remote_adc = correct_delay(remote_adc, estimate.total_delay_s, config.adc.sample_rate_hz)
    true_relative_delay_s = config.channel.remote_delay_s - config.channel.reference_delay_s

    science_time_s_125m, science_reference_125m, science_remote_free_125m = science_tones(
        config.adc.sample_rate_hz,
        config.science.duration_s,
        config.science.tone_frequency_hz,
        true_relative_delay_s,
        config.science.free_running_clock_error_ppm,
    )
    _, _, science_remote_shared_125m = science_tones(
        config.adc.sample_rate_hz,
        config.science.duration_s,
        config.science.tone_frequency_hz,
        true_relative_delay_s,
        config.science.shared_clock_error_ppm,
    )
    residual_delay_s = true_relative_delay_s - estimate.total_delay_s
    _, _, science_remote_corrected_125m = science_tones(
        config.adc.sample_rate_hz,
        config.science.duration_s,
        config.science.tone_frequency_hz,
        residual_delay_s,
        config.science.shared_clock_error_ppm,
    )
    factor = config.science.decimation_factor
    science_time_s, science_reference = keep_every_nth_sample(
        science_time_s_125m, science_reference_125m, factor
    )
    _, science_remote_free = keep_every_nth_sample(
        science_time_s_125m, science_remote_free_125m, factor
    )
    _, science_remote_shared = keep_every_nth_sample(
        science_time_s_125m, science_remote_shared_125m, factor
    )
    _, science_remote_corrected = keep_every_nth_sample(
        science_time_s_125m, science_remote_corrected_125m, factor
    )
    return SimulationResult(
        config=config,
        internal_time_s=internal_time_s,
        source=source,
        rf_equivalent=rf_equivalent,
        reference_analog=reference_analog,
        remote_analog=remote_analog,
        adc_time_s=adc_time_s,
        reference_adc=reference_adc,
        remote_adc=remote_adc,
        corrected_remote_adc=corrected_remote_adc,
        delay_estimate=estimate,
        true_relative_delay_s=true_relative_delay_s,
        science_time_s=science_time_s,
        science_reference=science_reference,
        science_remote_free_running=science_remote_free,
        science_remote_shared_clock=science_remote_shared,
        science_remote_corrected=science_remote_corrected,
        coherence_free_running=coherent_power(science_reference, science_remote_free),
        coherence_shared_clock_uncorrected=coherent_power(science_reference, science_remote_shared),
        coherence_corrected=coherent_power(science_reference, science_remote_corrected),
    )
