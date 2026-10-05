"""Time-domain and frequency-domain views of simulation stages."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .pipeline import SimulationResult
from .science import coherence_power_ratio


def _spectrum(signal: np.ndarray, sample_rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(signal)
    window = np.hanning(len(values))
    spectrum = np.fft.rfft(np.real(values) * window)
    frequency_hz = np.fft.rfftfreq(len(values), d=1 / sample_rate_hz)
    magnitude = 20 * np.log10(np.maximum(np.abs(spectrum), np.finfo(float).eps))
    magnitude -= np.max(magnitude)
    return frequency_hz, magnitude


def plot_signal_domains(result: SimulationResult, output_path: str | Path) -> None:
    """Plot time and frequency domains for each major calibration stage."""
    stages = [
        ("Pulse source", result.internal_time_s, result.source, result.config.simulation.internal_sample_rate_hz),
        ("RF-equivalent band limit", result.internal_time_s, result.rf_equivalent, result.config.simulation.internal_sample_rate_hz),
        ("Reference detector + LPF", result.internal_time_s, result.reference_analog, result.config.simulation.internal_sample_rate_hz),
        ("Remote detector + LPF", result.internal_time_s, result.remote_analog, result.config.simulation.internal_sample_rate_hz),
        ("Reference ADC", result.adc_time_s, result.reference_adc, result.config.adc.sample_rate_hz),
        ("Remote ADC", result.adc_time_s, result.remote_adc, result.config.adc.sample_rate_hz),
    ]
    fig, axes = plt.subplots(len(stages), 2, figsize=(14, 15), constrained_layout=True)
    for row, (title, time_s, signal, fs) in enumerate(stages):
        axes[row, 0].plot(time_s * 1e6, signal, lw=0.9)
        axes[row, 0].set(title=title, xlabel="Time (µs)", ylabel="Amplitude")
        axes[row, 0].grid(alpha=0.25)
        frequency_hz, magnitude_db = _spectrum(signal, fs)
        axes[row, 1].plot(frequency_hz * 1e-6, magnitude_db, lw=0.9)
        axes[row, 1].set(xlabel="Frequency (MHz)", ylabel="Relative magnitude (dB)", ylim=(-100, 3))
        axes[row, 1].grid(alpha=0.25)
    fig.suptitle("A2M TFR calibration signal: functional-block domains", fontsize=15)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_alignment_summary(result: SimulationResult, output_path: str | Path) -> None:
    """Plot delay recovery, aligned ADC signals, clock drift, and coherence."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    estimate = result.delay_estimate
    search_center = result.config.alignment.expected_relative_delay_s
    search_half = result.config.alignment.search_half_width_s
    mask = np.abs(estimate.correlation_lags_s - search_center) <= search_half
    axes[0, 0].plot(estimate.correlation_lags_s[mask] * 1e9, estimate.correlation[mask])
    axes[0, 0].axvline(result.true_relative_delay_s * 1e9, color="black", ls="--", label="true")
    axes[0, 0].axvline(estimate.total_delay_s * 1e9, color="tab:red", ls=":", label="estimated")
    axes[0, 0].set(xlabel="Relative delay (ns)", ylabel="Correlation", title="Geometry-constrained delay search")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.25)

    time_us = result.adc_time_s * 1e6
    axes[0, 1].plot(time_us, result.reference_adc, label="reference", lw=1)
    axes[0, 1].plot(time_us, result.corrected_remote_adc, label="corrected remote", lw=1, alpha=0.8)
    axes[0, 1].set(xlabel="Time (µs)", ylabel="ADC voltage", title="Fine-aligned pulse captures")
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.25)

    samples = min(len(result.science_time_s), 2500)
    combined_free = np.abs(result.science_reference[:samples] + result.science_remote_free_running[:samples]) ** 2 / 4
    combined_locked = np.abs(result.science_reference[:samples] + result.science_remote_corrected[:samples]) ** 2 / 4
    axes[1, 0].plot(result.science_time_s[:samples] * 1e6, combined_free, label="free-running clock")
    axes[1, 0].plot(result.science_time_s[:samples] * 1e6, combined_locked, label="shared clock + correction")
    axes[1, 0].set(xlabel="Time (µs)", ylabel="Normalized combined power", title="Clock stability during science tone")
    axes[1, 0].legend()
    axes[1, 0].grid(alpha=0.25)

    frequencies = np.linspace(0, 20e6, 500)
    before = coherence_power_ratio(result.true_relative_delay_s, frequencies)
    residual = result.true_relative_delay_s - estimate.total_delay_s
    after = coherence_power_ratio(residual, frequencies)
    axes[1, 1].plot(frequencies * 1e-6, 100 * before, label="before correction")
    axes[1, 1].plot(frequencies * 1e-6, 100 * after, label="after correction")
    axes[1, 1].axhline(90, color="black", ls="--", lw=1, label="90% requirement")
    axes[1, 1].set(xlabel="Science frequency (MHz)", ylabel="Coherent power (%)", title="Timing-error coherence response", ylim=(0, 105))
    axes[1, 1].legend()
    axes[1, 1].grid(alpha=0.25)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_delay_estimation(result: SimulationResult, output_path: str | Path) -> None:
    """Show the coarse correlation and fine phase-slope estimate explicitly."""
    estimate = result.delay_estimate
    true_ns = result.true_relative_delay_s * 1e9
    coarse_ns = estimate.coarse_delay_s * 1e9
    fine_ns = estimate.fine_delay_s * 1e9
    total_ns = estimate.total_delay_s * 1e9
    error_ns = total_ns - true_ns

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), constrained_layout=True)

    search_center = result.config.alignment.expected_relative_delay_s
    search_half = result.config.alignment.search_half_width_s
    mask = np.abs(estimate.correlation_lags_s - search_center) <= search_half
    lag_ns = estimate.correlation_lags_s[mask] * 1e9
    correlation = estimate.correlation[mask]
    axes[0].plot(lag_ns, correlation, "o-", lw=1.5, ms=5, label="ADC-lag correlation")
    axes[0].axvline(coarse_ns, color="tab:blue", ls="--", label=f"coarse = {coarse_ns:.3f} ns")
    axes[0].axvline(true_ns, color="black", ls=":", label=f"true = {true_ns:.3f} ns")
    axes[0].set(
        title="1. Coarse integer-sample estimate",
        xlabel="Relative delay (ns)",
        ylabel="Cross-correlation",
    )
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=9)
    axes[0].text(
        0.03,
        0.04,
        f"ADC period = {1e9 / result.config.adc.sample_rate_hz:.1f} ns",
        transform=axes[0].transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    frequency_mhz = estimate.phase_frequencies_hz * 1e-6
    axes[1].scatter(
        frequency_mhz,
        estimate.cross_phase_rad,
        s=24,
        color="tab:blue",
        label="unwrapped cross-phase",
    )
    axes[1].plot(
        frequency_mhz,
        estimate.phase_fit_rad,
        color="tab:red",
        lw=2,
        label="weighted linear fit",
    )
    axes[1].set(
        title="2. Fine phase-slope estimate",
        xlabel="Frequency (MHz)",
        ylabel="Cross-spectrum phase (rad)",
    )
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=9)
    axes[1].text(
        0.03,
        0.04,
        f"fine = {fine_ns:+.3f} ns\nτ = −slope / 2π",
        transform=axes[1].transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    axes[2].barh(["Estimated delay"], [coarse_ns], color="tab:blue", label="coarse")
    axes[2].barh(
        ["Estimated delay"],
        [fine_ns],
        left=[coarse_ns],
        color="tab:orange",
        label="fine",
    )
    axes[2].axvline(true_ns, color="black", ls="--", lw=2, label="true delay")
    margin_ns = max(2.0, abs(fine_ns) * 2.5)
    axes[2].set_xlim(min(coarse_ns, true_ns) - margin_ns, max(total_ns, true_ns) + margin_ns)
    axes[2].set(
        title="3. Combined delay outcome",
        xlabel="Relative delay (ns)",
    )
    axes[2].grid(axis="x", alpha=0.25)
    axes[2].legend(fontsize=9)
    axes[2].text(
        0.03,
        0.15,
        (
            f"coarse  {coarse_ns:.3f} ns\n"
            f"fine       {fine_ns:+.3f} ns\n"
            f"total     {total_ns:.3f} ns\n"
            f"true       {true_ns:.3f} ns\n"
            f"error      {error_ns:+.3f} ns"
        ),
        transform=axes[2].transAxes,
        family="monospace",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )

    fig.suptitle("A2M fine-alignment delay estimate", fontsize=15)
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
