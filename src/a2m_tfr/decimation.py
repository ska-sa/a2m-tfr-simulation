"""HF science-data sample-selection block."""

from __future__ import annotations

import numpy as np


def keep_every_nth_sample(
    time_s: np.ndarray, signal: np.ndarray, factor: int
) -> tuple[np.ndarray, np.ndarray]:
    """Keep one of every N samples, matching the proposed FPGA scheme.

    The proposal relies on the HF analogue path already being limited to
    20 MHz, so no additional digital anti-alias filter is inserted here.
    """
    if factor < 1:
        raise ValueError("decimation factor must be positive")
    return time_s[::factor], signal[::factor]

