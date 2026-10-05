# Africa2Moon Timing and Frequency Reference Simulator

This project models the signal path proposed for Africa 2 Moon mission. 
It is intended to answer the question: how accurately can the proposed wideband pulse calibration estimate relative delay, and what coherence is retained across the 0–20 MHz science
band?

The implementation keeps each conceptual functional block separate:

```text
wideband pulse source
  → RF-equivalent band limit
  → geometric propagation delay + path gain + noise
  → receive gain / attenuation
  → power detector
  → 60 MHz low-pass filter
  → 125 MS/s quantizing ADC
  → keep one of every three HF science samples (41.67 MS/s effective)
  → constrained correlation + cross-spectrum phase-slope delay estimate
  → Fourier-domain fractional-delay correction
  → coherent science-signal evaluation
```

The 5.15–5.7 GHz link is represented by an equivalent-envelope model. The
carrier itself is not sampled, so the simulation remains fast while preserving
the bandwidth, timing, detector, ADC, and coherence effects relevant to the
concept.

## Run it with uv

```bash
uv sync
uv run a2m-tfr --config configs/baseline.toml --output-dir results
uv run pytest
```

The simulation writes:

- `results/signal_domains.png`: time- and frequency-domain plots at every main
  functional block;
- `results/alignment_summary.png`: delay estimate, aligned captures, clock
  drift, and coherence versus science frequency;
- `results/delay_estimation.png`: coarse correlation lag, fine cross-spectrum
  phase fit, and the combined delay estimate;
- `results/summary.json`: numerical delay, error, coherence, and capture-size
  results.

Copy `configs/baseline.toml` and change parameters to explore pulse width and
spacing, SNR, path delays, gain, attenuation, detector type, filter bandwidth,
ADC resolution, geometric prior, science frequency, or clock error.

The timing calibration header remains at 125 MS/s. The one-in-three selection
is applied only to the HF science stream, as described in the concept.

## Capture-window assumption

Thirty pulses spaced by 60 ns occupy about **1.745 µs**. The baseline models
exactly this pulse train with short configurable guards. Pulse count, spacing,
width, and guards are independent parameters in TOML, and the CLI reports the
resulting simulated capture size.

The 60 ns pulse spacing is also close to the nominal 57 ns BALL 3-to-BALL 1/2
propagation difference. This creates pulse-index ambiguity in an unconstrained
correlator. The estimator deliberately uses the geometric delay estimate and a
configurable search window to select the correct correlation peak, mirroring the
document's coarse-time and geometry information.

## Model boundaries

This is a behavioural signal-processing model, not a component-level RF or link
budget simulator. It currently assumes ideal scalar gain, white noise, an ideal
power detector, Butterworth-equivalent filtering, uniform ADC quantization, and
a single-tone science signal. Component S-parameters, nonlinear compression,
phase noise, multipath, group-delay ripple, detector video bandwidth, clock PLL
dynamics, and measured antenna/link budgets can be added behind the existing
block interfaces without changing the pipeline.

See [`docs/concept_review.md`](docs/concept_review.md) for requirement
traceability, document inconsistencies, and the next simulations recommended
before hardware selection.

See [`docs/simulation_walkthrough.md`](docs/simulation_walkthrough.md) for a
detailed step-by-step explanation of the simulated signal path, BALL capture,
ground delay estimation, correction, and coherence calculation.
