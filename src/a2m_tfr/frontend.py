"""BALL TFR receive amplification, attenuation, and detector blocks."""

from __future__ import annotations

import numpy as np


def apply_gain(signal: np.ndarray, gain_db: float, attenuation_db: float) -> np.ndarray:
    """Apply voltage gain and attenuation in dB."""
    scale = 10.0 ** ((gain_db - attenuation_db) / 20.0)
    return signal * scale


def power_detect(signal: np.ndarray, mode: str = "square_law") -> np.ndarray:
    """Apply an idealized wideband power/envelope detector."""
    if mode == "square_law":
        return signal**2
    if mode == "envelope":
        return np.abs(signal)
    raise ValueError(f"unsupported detector mode: {mode}")

