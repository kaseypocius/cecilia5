# Multichannel input/output and codec debugging results

## Final validation

- **552/552 matrix cases pass** across all 69 shipped modules and eight scenarios.
- **10/10 supplemental audible cases pass** for the ten silent init-fixture cases.
- **300/300 repeated renders pass** across ChordMaker, Harmonizer and MultiBandHarmonizer.
- General discovery: **175 tests, 109 passed and 66 skipped**, with replay/PCM fixtures enabled.
- All six engine scenarios pass, including cancellation and normalization.
- The earlier 69-module routing audit passed again. The three harmonizer modules
  additionally passed their four-channel single/chunk/parallel routing retest after
  the shared native-window correction.

Environment: Python 3.13.3, pyo 1.1.0, numpy 2.5.4, macOS arm64. The isolated full
matrix took 122.35 seconds. Tests were headless; GUI/hardware tests were not enabled.

## Matrix

| Case | Input | Output | Rate | Mode |
| --- | --- | --- | --- | --- |
| mono_stereo_wav | 1ch wav PCM16 | 2ch wav PCM24 | 44100 Hz | single |
| stereo_mono_flac | 2ch aif PCM24 | 1ch flac PCM24 | 48000 Hz | single |
| quad_stereo_aiff_chunks | 4ch flac PCM24 | 2ch aif PCM24 | 44100 Hz | chunks |
| surround_quad_caf | 6ch wav float32 | 4ch caf float32 | 48000 Hz | single |
| eight_surround_wav_chunks | 8ch aif PCM24 | 6ch wav float32 | 44100 Hz | chunks |
| stereo_eight_pcm32 | 2ch wav float32 | 8ch wav PCM32 | 48000 Hz | single |
| surround_sixteen_wav | 6ch caf float32 | 16ch wav float32 | 44100 Hz | single |
| eight_sixtyfour_wav | 8ch wav float32 | 64ch wav float32 | 48000 Hz | single |

Each case checks master and module-tap frame count, sample rate, channel count,
container, bit depth and finite samples. Target-codec audio is compared by channel
and sample position against a float-WAV reference. Input codec roundtrips use
channel-distinct tones and impulses. PCM comparisons use saturation-aware
references and an explicit precision tolerance; float tolerance remains 0.000002.
The two chunk scenarios compare single-pass references against chunked exports.

[Final matrix](multichannel_formats_final.md) · [Numerical results](multichannel_formats_final.json)

## Bugs reproduced and corrected

### Integer overload wraparound and container selection

The valid baseline passed 549/552 cases. ConvolutionReverb's overloaded integer
stems wrapped in WAV/AIFF (maximum error nearly 2.0), and one FLAC worker exited.
[Baseline table](multichannel_formats_before_debug.md) and
[baseline values](multichannel_formats_before_debug.json) are preserved.

Masters, taps and mixed masters now remain float WAV until sample/warmup alignment
is complete. Genuine `.wav` scratch filenames avoid pyo's extension-based container
override; requesting float audio with a `.flac` extension is not a valid float
intermediate. Final PCM conversion saturates rather than wrapping. The explicit
WAV PCM16/24/32 writer rounds once, packs interleaved channels, handles signed
24-bit data and pads odd data chunks correctly. Other integer encoders receive
range-limited samples; float formats retain overload headroom. Non-finite arrays
are rejected rather than silently cast to integers. Non-WAV stem peak measurement
now reads all channels.

Five focused PCM/window tests pass, covering overloaded direct encoding,
master/tap/branch exports, odd-length mono PCM24 RIFF headers, and native-window
boundary arithmetic. Tolerances were not loosened to hide the overload failures.

### Intermittent unison Harmonizer non-finite samples

One intermediate format run reported ChordMaker failure despite isolated reruns
passing. Repeated workers reproduced three failed jobs in a 100-render batch.
Instrumented traces then located the first NaN in `harm1` at frame 2,400 (half of
a 100 ms window at 48 kHz), before Balance and before encoding. The first
reset-only experiment did not fix it and was removed.

The traces are consistent with float32 circular-index rounding at an interpolation
boundary in the [native pyo Harmonizer kernel](https://github.com/belangeo/pyo/blob/master/src/objects/harmonizermodule.c).
This is an inference from the traced stage/timing and the source's wrapped
current/next-index read, not a patched native dependency. Cecilia now expresses
the effective harmonizer window as a half-integer sample count, keeping the
unison half-window read away from that boundary. Pitch is unchanged; the nominal
window changes by at most one sample. Corresponding dry-delay calculations use
the effective window. The helper is used by ChordMaker, Harmonizer,
MultiBandHarmonizer and the master Harmonizer plugin.

The instrumented batch improved from 10 failures in 80 renders to 80/80 completed
with no non-finite stages. A subsequent stress run passed 300/300 renders, checking
exact shapes, finite samples, PCM32/reference equality and repeated float-master
equality. Maximum comparison error was 2.32830644e-10.

[Before trace](multichannel_chord_trace_before_debug.json) ·
[After trace](multichannel_chord_trace.json) ·
[Stress report](pitch_window_stability_final.md) ·
[Post-fix routing retest](harmonizer_routing_retest.md)

## Silent fixtures and audible diagnostics

Ten main-matrix init cases are silent: MultiBandGate in all eight scenarios, plus
MultiBandDelay and BucketBrigadeDevice in the short 64-channel scenario. Their
metadata/codec checks pass, but silent equality alone cannot prove DSP behavior.
All ten receive separate audible diagnostics without changing shipped defaults:

- MultiBandGate: four gate thresholds set to the supported -80 dB minimum;
  [8/8 cases pass with non-silent output](multichannel_gate_diagnostics_final.md).
- MultiBandDelay: 64-channel render extended to 1.25 seconds;
  [audible case passes](multichannel_delay_diagnostic_final.md).
- BucketBrigadeDevice: the same longer render lets the delay respond;
  [audible case passes](multichannel_bbd_diagnostic_final.md).

SpectralGate/Vectral use the previously documented -90 dB diagnostic threshold;
BinWarper/SpectralWarper use a shorter source so their spectral buffers fill.
The seven modules without file inputs contribute 56 format/output cases, not
file-input processing checks. Their rows identify this distinction.

## Scope and reruns

These are selected channel-count/codec combinations, not the complete Cartesian
product. They validate numbered channels and reference sample ordering, not a
speaker-position oracle for each effect. Input/output sample rates match within
each case; cross-rate resampling, every preset, all speaker masks/DAWs, very long
files, OGG/AU/SD2 and physical hardware are outside this matrix. Original snapshots
and explicit diagnostics remain distinguishable in the reports.

Use an isolated report prefix when concurrent audits share the workspace:

```sh
cecillia/bin/python tests/check_multichannel_formats.py --report-prefix multichannel_formats_final
cecillia/bin/python tests/check_multichannel_formats.py --module MultiBandGate --audible-diagnostics --report-prefix multichannel_gate_diagnostics_final
cecillia/bin/python tests/check_multichannel_formats.py --module MultiBandDelay --scenario eight_sixtyfour_wav --audible-diagnostics --report-prefix multichannel_delay_diagnostic_final
cecillia/bin/python tests/check_multichannel_formats.py --module BucketBrigadeDevice --scenario eight_sixtyfour_wav --audible-diagnostics --report-prefix multichannel_bbd_diagnostic_final
cecillia/bin/python tests/check_pitch_window_stability.py --report-prefix pitch_window_stability_final
CECILIA_DSP_TESTS=1 cecillia/bin/python -m unittest discover -s tests -v
```

DSP is recorded before final encoding, so non-WAV/integer exports incur an extra
float scratch/encoding step. Exact history/graph replay still adds CPU and disk
cost. Audio fixtures are temporary; JSON/Markdown findings and failing baselines
are retained. Concurrent report writers were observed, so the isolated `*_final`
artifacts above are authoritative for this run.
