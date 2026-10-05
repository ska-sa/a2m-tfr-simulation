"""Command-line interface for reproducible TFR simulations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .pipeline import run_simulation
from .plotting import plot_alignment_summary, plot_delay_estimation, plot_signal_domains


def _human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if amount < 1024 or unit == "GiB":
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def simulate(config_path: Path, output_dir: Path) -> dict[str, float | int | str]:
    config = load_config(config_path)
    result = run_simulation(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_signal_domains(result, output_dir / "signal_domains.png")
    plot_alignment_summary(result, output_dir / "alignment_summary.png")
    plot_delay_estimation(result, output_dir / "delay_estimation.png")
    estimate = result.delay_estimate
    summary: dict[str, float | int | str] = {
        "true_relative_delay_ns": result.true_relative_delay_s * 1e9,
        "coarse_delay_ns": estimate.coarse_delay_s * 1e9,
        "fine_delay_ns": estimate.fine_delay_s * 1e9,
        "estimated_relative_delay_ns": estimate.total_delay_s * 1e9,
        "delay_error_ns": (estimate.total_delay_s - result.true_relative_delay_s) * 1e9,
        "coherence_free_running_percent": 100 * result.coherence_free_running,
        "coherence_shared_clock_uncorrected_percent": 100 * result.coherence_shared_clock_uncorrected,
        "coherence_corrected_percent": 100 * result.coherence_corrected,
        "simulated_capture_samples": len(result.reference_adc),
        "simulated_capture_size": _human_bytes(config.adc.capture_size_bytes(config.pulse_source.capture_duration_s)),
        "effective_science_sample_rate_hz": config.adc.sample_rate_hz / config.science.decimation_factor,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Africa2Moon TFR signal-path simulator")
    parser.add_argument("--config", type=Path, default=Path("configs/baseline.toml"), help="TOML configuration")
    parser.add_argument("--output-dir", type=Path, default=Path("results"), help="result directory")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = simulate(args.config, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
