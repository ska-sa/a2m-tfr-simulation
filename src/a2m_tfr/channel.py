"""Propagation delay, path gain, and additive-noise block."""

from __future__ import annotations

import numpy as np


def fractional_delay(signal: np.ndarray, delay_s: float, sample_rate_hz: float) -> np.ndarray:
    """Delay a finite signal using a padded Fourier-domain phase ramp."""
    pad = len(signal)
    padded = np.pad(signal, (pad, pad))
    frequencies = np.fft.fftfreq(len(padded), d=1.0 / sample_rate_hz)
    shifted = np.fft.ifft(np.fft.fft(padded) * np.exp(-2j * np.pi * frequencies * delay_s)).real
    return shifted[pad : 2 * pad]


def propagate(
    signal: np.ndarray,
    sample_rate_hz: float,
    delay_s: float,
    amplitude: float,
    snr_db: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Apply geometric delay, scalar path gain, and white Gaussian noise."""
    received = amplitude * fractional_delay(signal, delay_s, sample_rate_hz)
    signal_power = np.mean(received**2)
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = rng.normal(scale=np.sqrt(max(noise_power, np.finfo(float).eps)), size=received.shape)
    return received + noise

