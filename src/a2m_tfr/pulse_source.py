"""Wideband synchronization pulse-train source block."""

from __future__ import annotations

import numpy as np

from .config import PulseSourceConfig


def generate_pulse_train(config: PulseSourceConfig, sample_rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Create a Gaussian impulse train and its time axis.

    A Gaussian shape avoids the numerical edge artefacts of a one-sample ideal
    impulse while retaining a controllable effective pulse width.
    """
    duration = config.capture_duration_s
    count = int(np.ceil(duration * sample_rate_hz))
    time_s = np.arange(count, dtype=float) / sample_rate_hz
    signal = np.zeros(count, dtype=float)
    sigma_s = config.pulse_width_s / 2.355
    first_center_s = config.leading_guard_s + config.pulse_width_s / 2
    for index in range(config.pulse_count):
        center_s = first_center_s + index * config.pulse_interval_s
        signal += config.amplitude * np.exp(-0.5 * ((time_s - center_s) / sigma_s) ** 2)
    return time_s, signal

