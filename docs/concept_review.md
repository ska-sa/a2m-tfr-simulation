# Concept review and simulation traceability

## What the model implements

| Concept function | Simulation implementation |
|---|---|
| Coarse time and known array geometry | An expected differential delay and bounded correlation search window select the correct pulse peak. |
| Wideband pulse calibration | Configurable Gaussian pulse train with pulse count, width, spacing, and guards. |
| 5.15–5.7 GHz transmission channel | Equivalent-envelope bandwidth model; the 5.425 GHz centre carrier is not explicitly sampled. |
| LBU-to-BALL propagation | Independent fractional geometric delays, path amplitudes, and AWGN for reference and remote BALLS. |
| BALL receive chain | Gain, attenuation, ideal square-law/envelope detector, 60 MHz low-pass response, and quantizing 125 MS/s ADC. |
| Fine time alignment | Geometry-constrained cross-correlation followed by cross-spectrum phase-slope interpolation and Fourier delay correction. |
| HF sample selection | One of every three 125 MS/s samples retained, giving 41.67 MS/s for the 0–20 MHz science band. |
| Frequency synchronization | Shared-clock and free-running-clock cases represented by configurable relative ppm error. |
| Coherence requirement | Two-element coherent power is evaluated versus time and across the 0–20 MHz band. |

## Review findings

1. The stated 10% maximum coherent-power loss corresponds to
   `cos²(Δφ/2) = 0.9`, or about 36.9° maximum phase difference. At 20 MHz this
   is about 5.12 ns, matching the document.
2. The nominal LBU-to-BALL differential path is about 17.1 m or 57 ns. A ±2 m
   relative position uncertainty is ±6.7 ns and can exceed the 5.12 ns budget
   unless BALL positions or astronomical geometric delays are estimated more
   accurately after deployment.
3. Thirty pulses at 60 ns spacing occupy about 1.745 µs. Capture-control and
   storage design should derive the acquisition window from this active duration
   plus explicit timing, switching, and filter-settling guards.
4. Sixty-nanosecond pulse spacing is almost the same as the nominal 57 ns
   differential geometric delay. An unconstrained correlator can associate a
   pulse from one BALL with the neighbouring pulse from another. The simulator
   uses a geometry prior and bounded search; flight processing needs an equally
   explicit ambiguity-resolution rule.
5. A 60 MHz analogue cutoff is only 2.5 MHz below the 62.5 MHz Nyquist limit of
   the 125 MS/s ADC. Real filter transition width, rejection at aliases, group
   delay, and component tolerance need to be included before declaring the
   pulse path alias-safe.
6. The prose calls the LBU filter a low-pass filter that removes transmissions
   below 5.7 GHz, while the block diagram shows a 5.15–5.7 GHz band-pass. The
   simulator follows the diagram and treats this as a 550 MHz RF bandwidth.
7. The filename says Revision 4 while the document title block says Revision 3.
   Resolve this before using the document as a controlled design baseline.
8. Combining 30 independent measurements improves amplitude-estimation SNR by
   approximately `sqrt(30)`; coherent voltage integration or power SNR should
   be stated separately because their scaling and assumptions differ.

## Recommended next model increments

1. Replace scalar RF blocks with candidate component S-parameters, measured
   group delay, detector transfer curves, compression, and ADC aperture jitter.
2. Run Monte Carlo sweeps over SNR, BALL position uncertainty, pulse spacing,
   filter tolerance, quantization, and clock phase noise; report 95th/99th
   percentile residual timing error rather than a single seed.
3. Add lunar multipath/reflection hypotheses and test correlation-peak bias.
4. Model the 6 GHz recovery PLL, divider, phase noise, loss of lock, reacquisition,
   and holdover to translate clock quality into coherence over observation time.
5. Simulate all three BALLS and sky-direction geometric compensation, then
   compute array rather than two-element coherent sensitivity.
