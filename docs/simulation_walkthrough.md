# Detailed simulation walkthrough

## 1. Purpose of the simulation

The simulator evaluates whether the proposed Africa2Moon timing and frequency
reference can provide sufficiently accurate relative timing for coherent HF
processing. It models two representative BALL receivers: one reference BALL
and one remote BALL. The same method can later be extended to all three BALLS.

The simulation answers three main questions:

1. What pulse waveform reaches each BALL after propagation, receiver processing,
   filtering, sampling, and quantization?
2. Can ground processing recover the relative arrival delay to substantially
   better than the 8 ns ADC sample period?
3. What coherent science-signal power remains before and after correction, both
   with a shared clock and with a free-running clock?

The simulation has two architectural phases:

```text
BALL acquisition                         Ground processing
----------------                         -----------------
receive calibration pulses               associate BALL captures
apply analogue receiver response          estimate relative delay
power detection                           correct science-stream timing
60 MHz low-pass filtering                 combine science signals coherently
125 MS/s ADC capture                      evaluate retained coherent power
store and downlink samples
```

The current program executes these phases consecutively in memory, but the
delay estimate uses only the simulated BALL ADC captures. It does not use the
original transmitted waveform.

## 2. Load and validate the configuration

The run begins by loading `configs/baseline.toml`. Configuration is separated
into simulation, pulse-source, channel, receiver-front-end, ADC, alignment, and
science sections.

Important baseline values are:

```text
Internal simulation rate:       1.000 GS/s
Pulse count:                    30
Pulse interval:                 60 ns
Pulse width:                    5 ns
Reference propagation delay:    33.36 ns
Remote propagation delay:       90.39 ns
True differential delay:        57.03 ns
Channel SNR:                    20 dB
Detector low-pass cutoff:       60 MHz
ADC sample rate:                125 MS/s
ADC sample period:              8 ns
ADC resolution:                 12 bits
Science frequency:              20 MHz
HF science decimation:          3
Effective science sample rate:  41.667 MS/s
```

The configuration validator checks, among other things, that:

- the internal rate can represent the detector bandwidth;
- the internal-to-ADC sample-rate ratio is an integer;
- the pulse width is shorter than the pulse interval;
- the detector mode is supported;
- the science decimation factor is positive; and
- the science tone is below the decimated Nyquist frequency.

## 3. Generate the calibration pulse train

`generate_pulse_train()` creates the waveform transmitted by the LBU timing
calibration source. Each pulse is represented by a Gaussian:

```text
p(t) = A exp[-0.5 ((t - t₀)/σ)²]
```

The configured pulse width is converted to Gaussian standard deviation using:

```text
σ = pulse_width / 2.355
```

With a 5 ns pulse width and 1 GS/s internal rate, each pulse is represented by
several internal samples rather than an ideal one-sample impulse. This avoids
unphysical numerical behaviour while retaining a wide spectrum.

The 30 pulse centres are separated by 60 ns. Their repetition frequency is:

```text
1 / 60 ns = 16.667 MHz
```

Consequently, the frequency-domain plot contains a comb with spectral lines
separated by approximately 16.667 MHz. The envelope of that comb is determined
by the individual Gaussian pulse shape.

The active sequence lasts:

```text
(30 - 1) × 60 ns + 5 ns = 1.745 µs
```

The baseline adds 200 ns guards before and after the train, producing a capture
window of approximately 2.145 µs.

## 4. Apply the RF-equivalent bandwidth

The proposal places the calibration transmission in approximately the
5.15–5.70 GHz band. Explicitly generating a 5.425 GHz carrier would require a
sample rate above approximately 11 GS/s and would add substantial computation
without improving the timing-envelope calculation.

The simulator therefore uses an equivalent baseband representation. The RF
band has a total width of:

```text
5.70 GHz - 5.15 GHz = 550 MHz
```

A real baseband signal with a 275 MHz positive-frequency cutoff represents a
two-sided bandwidth from -275 MHz to +275 MHz, giving the same 550 MHz total
bandwidth. `rf_equivalent_bandlimit()` applies this bandwidth with a zero-phase
Butterworth low-pass filter.

This stage models bandwidth-dependent pulse broadening, but not the absolute RF
carrier phase, antenna response, component S-parameters, or RF group-delay
ripple.

## 5. Propagate the signal to each BALL

`propagate()` independently models the LBU-to-BALL channel for the reference
and remote receivers.

### 5.1 Fractional geometric delay

The waveform is delayed with a Fourier-domain phase ramp:

```text
X_delayed(f) = X(f) exp(-j 2π f τ)
```

This permits delays that are not integer multiples of the 1 ns internal sample
period. Padding is added before the FFT so that the delay does not wrap energy
from the end of the capture back to the beginning.

The baseline delays are approximately equivalent to:

```text
Reference BALL: 33.36 ns ≈ 10.0 m
Remote BALL:    90.39 ns ≈ 27.1 m
Difference:     57.03 ns ≈ 17.1 m
```

### 5.2 Channel amplitude

Each delayed waveform is multiplied by a normalized voltage amplitude:

```text
Reference amplitude: 1.00
Remote amplitude:    0.75
```

The remote-to-reference power ratio is therefore:

```text
0.75² = 0.5625, or approximately -2.5 dB
```

These are illustrative normalized values. They are not yet computed from a
transmitter, antenna, free-space path-loss, or receiver-noise link budget.

### 5.3 Add receiver-channel noise

Independent white Gaussian noise is added to each BALL waveform. Noise power is
calculated as:

```text
P_noise = P_signal / 10^(SNR_dB/10)
```

At 20 dB, the average noise power is one hundredth of the average signal power.
The current signal power is averaged across the complete capture, including the
intervals between pulses. The parameter therefore represents capture-average
SNR rather than peak-pulse SNR or a physical noise spectral density.

## 6. Model the BALL receiver front end

Each BALL processes its own received waveform independently.

### 6.1 Gain and attenuation

`apply_gain()` applies the configured net voltage gain:

```text
voltage scale = 10^((gain_dB - attenuation_dB)/20)
```

The baseline has 20 dB receiver gain and 20 dB attenuation, producing unity net
voltage gain. Keeping them as separate parameters allows ADC drive level and
detector operating point to be explored later.

### 6.2 Power detection

The baseline ideal detector uses square-law detection:

```text
v_detector(t) = v_RF-equivalent(t)²
```

An ideal envelope option is also available:

```text
v_detector(t) = |v_RF-equivalent(t)|
```

Square-law detection produces a positive mean and changes both the waveform and
noise statistics. The simulator removes this mean later before delay estimation
so that DC does not dominate the correlation or cross-spectrum.

This is an ideal detector. It does not currently model sensitivity threshold,
dynamic range, saturation, video impedance, temperature dependence, or a
measured detector transfer curve.

### 6.3 Detector low-pass filtering

The detected waveform passes through a sixth-order, 60 MHz Butterworth low-pass
filter. This represents the proposed receiver filter immediately ahead of the
ADC and limits the timing information delivered to the digitizer.

The filter is applied forwards and backwards to produce zero phase in the
behavioral model. This prevents the simulated filter itself from adding a common
delay, but it is not a causal hardware implementation. Real component group
delay and group-delay mismatch between BALLS should eventually be included.

## 7. Sample and quantize at each BALL

`sample_and_quantize()` represents the BALL ADC.

### 7.1 Resample to 125 MS/s

The internal 1 GS/s waveform is reduced to 125 MS/s by an eight-to-one
polyphase resampler:

```text
1 GS/s / 125 MS/s = 8
```

The resampler includes anti-alias filtering. At 125 MS/s, the sample period is:

```text
T_sample = 1 / 125 MHz = 8 ns
```

Since the required timing accuracy is approximately 5.12 ns at 20 MHz, an
integer-sample delay estimate alone cannot satisfy the requirement reliably.

### 7.2 ADC clipping and quantization

For the baseline 1.6 V full-scale ADC, samples are clipped to:

```text
-0.8 V to +0.8 V
```

The 12-bit converter has 4096 levels and an ideal step size of approximately:

```text
1.6 V / (4096 - 1) ≈ 391 µV
```

The clipped waveform is rounded to the nearest available level. The output of
this stage is the data that would be stored on each BALL and sent to the ground.

No delay estimation is performed onboard in the intended architecture.

## 8. Associate the BALL captures on the ground

The ground processor receives one pulse capture from each BALL. In the current
two-receiver simulation, these are called `reference_adc` and `remote_adc`.

The present model assumes that the two arrays have already been associated with
the same calibration event and placed in approximately corresponding windows.
The expected geometric delay then resolves the remaining pulse-index ambiguity.

A flight-representative implementation must additionally use BALL identifiers,
network timestamps, sample counters, clock-lock state, and capture metadata. It
must locate the pulse header inside each downloaded data product and handle
unequal windows or missing samples.

## 9. Remove DC before timing estimation

The detector outputs contain a positive mean, so `estimate_delay()` first
subtracts the mean of each ADC capture:

```text
x_ref = reference - mean(reference)
x_remote = remote - mean(remote)
```

This keeps the DC component from overwhelming the waveform correlation and
frequency-domain phase fit.

## 10. Estimate the coarse integer-sample delay

The ground processor computes the full cross-correlation:

```text
R_yx[k] = Σ y[n] x[n-k]
```

where `x` is the reference BALL capture and `y` is the remote BALL capture. A
positive lag means the remote signal arrived later.

The repeated 60 ns pulses create multiple similar correlation peaks separated
by approximately 60 ns. Because the nominal differential delay is about 57 ns,
an unconstrained maximum could associate a remote pulse with the neighbouring
reference pulse.

The simulator therefore searches only around the geometric prediction:

```text
Expected delay:     57.03 ns
Search half-width:  20.00 ns
Search interval:    37.03 ns to 77.03 ns
```

At 125 MS/s, correlation lags occur every 8 ns. The baseline peak occurs at
seven samples:

```text
7 × 8 ns = 56 ns
```

This is the coarse delay estimate.

## 11. Estimate the fractional-sample delay

The coarse integer delay is removed by selecting overlapping sections of the
reference and remote captures. A Hann window is applied to reduce FFT boundary
leakage, and the ground processor calculates their cross-spectrum:

```text
C_yx(f) = Y(f) X*(f)
```

If the remote waveform still has a small residual delay `τ`, then:

```text
Y(f) = X(f) exp(-j 2π f τ)
```

and therefore:

```text
phase[C_yx(f)] = -2π f τ
```

The delay is encoded in the slope of cross-spectrum phase against frequency:

```text
τ = -slope / (2π)
```

The estimator excludes DC, uses only frequencies up to the configured 50 MHz
estimation bandwidth, and rejects bins whose cross-spectrum magnitude is below
5% of the strongest in-band bin. It unwraps phase and performs a magnitude-
weighted straight-line fit.

Because coarse correlation should already have selected the nearest sample, the
fine result is constrained to half a sample:

```text
-4 ns ≤ fine delay ≤ +4 ns
```

The baseline result is approximately:

```text
Coarse delay:       56.000 ns
Fine delay:          1.052 ns
Total estimate:     57.052 ns
True delay:         57.030 ns
Estimation error:    0.022 ns
```

## 12. Correct the remote timing on the ground

The estimated delay is removed from the remote data using the inverse
Fourier-domain phase ramp:

```text
Y_corrected(f) = Y(f) exp(+j 2π f τ_estimated)
```

This advances the remote waveform by the estimated relative delay. Correction
is applied during ground processing; the BALL does not modify its captured data.

In a complete processing system, the same timing correction or its equivalent
phase correction would be applied to the corresponding science data stream.

## 13. Generate diagnostic science signals

`science_tones()` generates ideal complex test tones to translate timing and
clock errors into coherent-power performance. These tones are diagnostic
signals inside the simulation, not calibration tones transmitted by the LBU and
not a model of a particular astronomical waveform.

The reference tone is:

```text
x(t) = exp(j 2π f t)
```

The remote tone is:

```text
y(t) = exp{j 2π [(f + Δf)t - fτ]}
```

where `τ` is relative timing error and clock error produces:

```text
Δf = f × clock_error_ppm × 10^-6
```

At 20 MHz, a 1 ppm relative clock error produces a 20 Hz relative frequency
offset. That offset causes relative phase to drift over the observation.

The simulator creates three cases:

1. A free-running remote clock with the full timing delay and configured ppm
   error.
2. A shared clock with no relative frequency error but with the timing delay not
   yet corrected.
3. A shared clock after correction, containing only the residual delay-estimation
   error.

## 14. Apply the proposed HF sample selection

Science tones are initially generated at 125 MS/s. The proposed FPGA sampling
scheme keeps one of every three HF samples:

```text
125 MS/s / 3 = 41.667 MS/s
```

The resulting Nyquist frequency is approximately 20.833 MHz, just above the
20 MHz upper science frequency. The simulator does not insert another digital
anti-alias filter at this step because the concept assumes that the HF analogue
input has already been limited to 20 MHz.

The calibration pulse header remains at the full 125 MS/s; the one-in-three
selection applies only to the HF science stream.

## 15. Calculate coherent power

The reference and remote complex science signals are summed. Their combined
power is normalized to the power of two perfectly aligned unit signals:

```text
P_coherent = mean(|x + y|²) / 4
```

Interpretation is:

```text
1.0  = ideal coherent combination
0.9  = maximum permitted 10% power loss
0.0  = complete destructive cancellation
```

For two signals with only a constant relative timing error:

```text
P_coherent = cos²(π f τ)
```

At 20 MHz, the uncorrected 57.03 ns delay gives approximately 81.7% coherent
power and fails the 90% requirement. After correction, the approximate 0.022 ns
residual gives 99.9998% in the baseline run.

The free-running result should not be compared from a single short interval as
if it were a fixed loss. Clock-frequency error makes relative phase drift, so
coherent power varies with observation time and will cycle through constructive
and destructive values during sufficiently long observations.

## 16. Generate result products

The CLI writes three outputs.

### `summary.json`

This records the true delay, estimated delay, delay error, three coherence
results, capture sizes, and effective HF science rate. The true delay exists
only as simulation truth and would not be available to real ground processing.

### `signal_domains.png`

This plots time and frequency views of:

1. the source pulse train;
2. the RF-equivalent band-limited waveform;
3. the reference detector and low-pass output;
4. the remote detector and low-pass output;
5. the reference ADC capture; and
6. the remote ADC capture.

These plots show where pulse broadening, attenuation, noise, detection,
filtering, sampling, and quantization enter the chain.

### `alignment_summary.png`

This plots:

1. the constrained correlation peak and true/estimated delay;
2. the reference and corrected remote pulse captures;
3. science coherent power versus time for free-running and corrected clocks;
   and
4. coherent power versus science frequency before and after timing correction.

### `delay_estimation.png`

This makes the two-stage delay result explicit. The first panel shows the
integer-sample correlation peak and its 8 ns lag spacing. The second shows the
unwrapped cross-spectrum phase and weighted slope used for the fractional delay.
The third decomposes the final estimate into coarse and fine contributions and
compares their sum with the known simulated delay.

## 17. Interpretation and limitations

The baseline 0.022 ns error demonstrates that the implemented estimator can
recover sub-sample delay under the model's assumptions. It is not yet evidence
that flight hardware will achieve 22 ps accuracy.

The result presently assumes:

- white Gaussian noise;
- ideal scalar channel gain;
- no lunar multipath;
- identical zero-phase filters at the BALLS;
- an ideal power detector;
- ideal ADC sample timing and uniform quantization;
- a known geometric search region;
- no missing samples or timestamp mistakes;
- a simple relative ppm clock-error model; and
- a single diagnostic science tone.

The most important next step is a Monte Carlo and component-informed model using
realistic filter group delay, detector characteristics, ADC aperture jitter,
clock/PLL phase noise, channel multipath, position uncertainty, and candidate
component measurements. Results should then be reported as timing-error and
coherence distributions rather than a single deterministic baseline run.
