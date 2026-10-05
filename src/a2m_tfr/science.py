"""Science-signal coherence and clock-stability evaluation."""

from __future__ import annotations

import numpy as np


def coherence_power_ratio(delay_s: float | np.ndarray, frequency_hz: float | np.ndarray) -> np.ndarray:
    """Two-element coherent power ratio for a relative timing error."""
    return np.cos(np.pi * np.asarray(frequency_hz) * np.asarray(delay_s)) ** 2


def science_tones(
    sample_rate_hz: float,
    duration_s: float,
    frequency_hz: float,
    relative_delay_s: float,
    clock_error_ppm: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate reference and remote complex science tones.

    Clock error is represented as an accumulating relative phase caused by a
    proportional frequency error in the remote sampling reference.
    """
    count = max(2, round(duration_s * sample_rate_hz))
    time_s = np.arange(count, dtype=float) / sample_rate_hz
    reference = np.exp(2j * np.pi * frequency_hz * time_s)
    frequency_offset_hz = frequency_hz * clock_error_ppm * 1.0e-6
    remote = np.exp(2j * np.pi * ((frequency_hz + frequency_offset_hz) * time_s - frequency_hz * relative_delay_s))
    return time_s, reference, remote


def coherent_power(reference: np.ndarray, remote: np.ndarray) -> float:
    """Return combined power normalized to an ideal in-phase pair."""
    return float(np.mean(np.abs(reference + remote) ** 2) / 4.0)

