"""Sub-sample timing estimation and correction blocks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import correlate, correlation_lags

from .channel import fractional_delay


@dataclass(frozen=True)
class DelayEstimate:
    coarse_delay_s: float
    fine_delay_s: float
    total_delay_s: float
    correlation_lags_s: np.ndarray
    correlation: np.ndarray
    phase_frequencies_hz: np.ndarray
    cross_phase_rad: np.ndarray
    phase_fit_rad: np.ndarray


def _overlap(reference: np.ndarray, remote: np.ndarray, lag_samples: int) -> tuple[np.ndarray, np.ndarray]:
    if lag_samples >= 0:
        return reference[: len(reference) - lag_samples or None], remote[lag_samples:]
    return reference[-lag_samples:], remote[: len(remote) + lag_samples]


def estimate_delay(
    reference: np.ndarray,
    remote: np.ndarray,
    sample_rate_hz: float,
    expected_delay_s: float,
    search_half_width_s: float,
    bandwidth_hz: float,
) -> DelayEstimate:
    """Estimate relative delay using constrained correlation plus phase slope.

    The expected geometry resolves pulse-to-pulse ambiguity. Integer-sample
    correlation supplies the coarse delay; cross-spectrum phase slope supplies
    the residual sub-sample delay.
    """
    ref = reference - np.mean(reference)
    rem = remote - np.mean(remote)
    corr = correlate(rem, ref, mode="full", method="fft")
    lags = correlation_lags(len(rem), len(ref), mode="full")
    center = expected_delay_s * sample_rate_hz
    half_width = max(1.0, search_half_width_s * sample_rate_hz)
    valid = np.abs(lags - center) <= half_width
    if not np.any(valid):
        raise ValueError("delay search window does not contain a correlation lag")
    valid_indices = np.flatnonzero(valid)
    peak_index = valid_indices[np.argmax(np.abs(corr[valid]))]
    coarse_samples = int(lags[peak_index])

    ref_overlap, rem_overlap = _overlap(ref, rem, coarse_samples)
    size = min(len(ref_overlap), len(rem_overlap))
    window = np.hanning(size)
    ref_spectrum = np.fft.rfft(ref_overlap[:size] * window)
    rem_spectrum = np.fft.rfft(rem_overlap[:size] * window)
    frequencies = np.fft.rfftfreq(size, d=1.0 / sample_rate_hz)
    cross = rem_spectrum * np.conj(ref_spectrum)
    weights = np.abs(cross)
    band = (frequencies > 0) & (frequencies <= min(bandwidth_hz, sample_rate_hz / 2))
    phase_frequencies_hz = np.array([], dtype=float)
    cross_phase_rad = np.array([], dtype=float)
    phase_fit_rad = np.array([], dtype=float)
    if np.count_nonzero(band) < 3 or np.max(weights[band]) == 0:
        fine_delay_s = 0.0
    else:
        useful = band & (weights >= 0.05 * np.max(weights[band]))
        phase_frequencies_hz = frequencies[useful]
        cross_phase_rad = np.unwrap(np.angle(cross[useful]))
        slope, intercept = np.polyfit(
            phase_frequencies_hz,
            cross_phase_rad,
            1,
            w=np.sqrt(weights[useful]),
        )
        fine_delay_s = -slope / (2 * np.pi)
        sample_period = 1.0 / sample_rate_hz
        fine_delay_s = float(np.clip(fine_delay_s, -0.5 * sample_period, 0.5 * sample_period))
        phase_fit_rad = slope * phase_frequencies_hz + intercept
    coarse_delay_s = coarse_samples / sample_rate_hz
    return DelayEstimate(
        coarse_delay_s=coarse_delay_s,
        fine_delay_s=fine_delay_s,
        total_delay_s=coarse_delay_s + fine_delay_s,
        correlation_lags_s=lags / sample_rate_hz,
        correlation=corr,
        phase_frequencies_hz=phase_frequencies_hz,
        cross_phase_rad=cross_phase_rad,
        phase_fit_rad=phase_fit_rad,
    )


def correct_delay(signal: np.ndarray, estimated_delay_s: float, sample_rate_hz: float) -> np.ndarray:
    """Advance a signal by its estimated relative delay."""
    return fractional_delay(signal, -estimated_delay_s, sample_rate_hz)
