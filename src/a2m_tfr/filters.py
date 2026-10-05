"""Band-limiting functional blocks."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt


def lowpass(signal: np.ndarray, cutoff_hz: float, sample_rate_hz: float, order: int = 6) -> np.ndarray:
    """Apply a zero-phase Butterworth low-pass filter."""
    if cutoff_hz >= sample_rate_hz / 2:
        return signal.copy()
    sos = butter(order, cutoff_hz, btype="lowpass", fs=sample_rate_hz, output="sos")
    return sosfiltfilt(sos, signal)


def rf_equivalent_bandlimit(
    signal: np.ndarray, bandwidth_hz: float, sample_rate_hz: float, order: int = 6
) -> np.ndarray:
    """Model the 5.15–5.7 GHz RF channel as its complex-envelope bandwidth.

    The 5+ GHz carrier itself is intentionally omitted. This preserves timing
    and envelope behaviour without requiring a multi-gigasample RF waveform.
    """
    return lowpass(signal, bandwidth_hz, sample_rate_hz, order)

