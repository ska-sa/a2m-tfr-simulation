"""ADC resampling and quantization block."""

from __future__ import annotations

import numpy as np
from scipy.signal import resample_poly

from .config import ADCConfig


def sample_and_quantize(
    signal: np.ndarray, internal_sample_rate_hz: float, config: ADCConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Anti-alias decimate to the ADC rate and apply ideal uniform quantization."""
    ratio = internal_sample_rate_hz / config.sample_rate_hz
    down = round(ratio)
    if abs(ratio - down) > 1e-9:
        raise ValueError("sample-rate ratio must be an integer")
    sampled = resample_poly(signal, up=1, down=down)
    half_scale = config.full_scale_v / 2.0
    levels = 2**config.bits
    lsb = config.full_scale_v / (levels - 1)
    clipped = np.clip(sampled, -half_scale, half_scale)
    quantized = np.round((clipped + half_scale) / lsb) * lsb - half_scale
    time_s = np.arange(len(quantized), dtype=float) / config.sample_rate_hz
    return time_s, quantized

