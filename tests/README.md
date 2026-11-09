# Cecilia 5 Test Suites

## Unit and Session Model Tests
Run the session model and unit tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

## Offline Render Multithread Engine & Persistence Tests
Run the headless offline render engine test suite (exercises worker multiprocessing pools, single-pass rendering, time-chunked overlap crossfading, parallel branch decomposition, multi-stem tapping, batch rendering, and clean cancellation):

```sh
python3 tests/test_offline_engine.py
```

Run the cross-session preferences persistence test suite (exercises serialization and deserialization of all offline settings, type conversions, legacy preference fallback, DAC decoupling, and UI sync logic):

```sh
python3 tests/test_offline_persistence.py
```

## GUI & Studio Integration Tests
To include the full GUI integration tests (including the Offline Render Studio dialog, Routing Graph `[STEM]` badges and context menu toggles, ControlPanel buttons, batch preset tabs, render queue, and live VU meters), install Cecilia's normal wxPython and pyo dependencies and run with an available desktop display:

```sh
CECILIA_GUI_TESTS=1 python3 -m unittest discover -s tests -v
```

Or run the offline render UI and studio integration test directly:

```sh
python3 tests/test_offline_ui.py
```

The integration suite creates a temporary preferences profile, module fixtures,
audio files and session files. It exercises persistent editors, running pyo
processing with a manual server, offline rendering, recording, spectrum routing,
presets, shipped module declarations, and session recovery. Physical audio and
MIDI devices require a separate manual check.

## Sample-level offline correctness regressions

Run real headless worker renders, without a GUI display:

```sh
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_correctness.py -v
```

Requires numpy, pyo and wxPython in the selected interpreter. The shipped-module
correctness suite runs real DSP workers during discovery. The separate replay
fixture suite below requires `CECILIA_DSP_TESTS=1` and skips without that flag.
Audio fixtures use temporary directories. The shipped-module correctness script
redirects HOME to `/tmp`; the separate opt-in replay fixtures do not change HOME.

Together the correctness and replay suites compare single-pass and two-worker
chunked passthrough, delay,
feedback delay, Freeverb and finite convolution renders. Four distinct channel
signals and impulses near the seam exercise sample alignment and channel order.
Independent tests check module taps, exact frame counts, disjoint output mixing
with master gain and muted outputs, shared-ancestor rejection, and cancellation
after worker progress (including process exit, temporary directories and taps).
Tap/master comparisons exclude startup and shutdown ramps; exact-length checks
are separate. Every render now asserts an exact frame count, including unaligned
integer WAV, AIFF and compressed FLAC exports. Additional regressions compare
curved automation, oscillator phase, seeded noise, fades, both overlap curves,
and feedback with a delay longer than the legacy preroll.

Chunks replay from the original session origin with the same seed, automation
and envelope duration, then discard the prefix. This reconstructs DSP history
instead of approximating it with finite preroll. It costs more CPU and temporary
storage, and is not guaranteed to accelerate a single job. Legacy preroll values
remain readable but are unused. Both overlap curves have unity-sum weights for
correlated audio; global fades are applied once during rendering. Master and tap
files are trimmed to the requested sample count after pyo finishes its last buffer.

The original frame-padding and chunk mismatch regressions now pass in the
bundled Python 3.13 environment. Worker shutdown also waits for killed processes,
joins pipe readers and closes all pipes. The follow-up replay suite adds branch fade/filter and warmup alignment checks.
Broader routing topologies and cancellation during worker startup remain outside
this validation.

## Audit all shipped modules

```sh
cecillia/bin/python tests/check_all_modules.py
```

This explicitly runs every `Resources/modules/**/*.c5` module with its init
settings and a generated four-channel source (including seam-adjacent impulses).
It checks single-pass/chunked master and tap samples, exact lengths, finite
samples, channel counts, and a two-source disjoint-branch sum with stem exports.
It repeats the five previously non-reproducible modules even when chunk
comparisons pass, and repeats any other module whose chunk comparison differs. Every job has a 60-second completion deadline.

The runner writes a per-module summary to `tests/reports/offline_modules.md`
and numerical results/errors to `tests/reports/offline_modules.json`. It exits
nonzero if any check fails or remains inconclusive. Audio is temporary. Equality tests cannot establish
correctness for silent init output; such cases are noted in the report. The audit
covers init settings, not every preset, channel configuration or routing graph.
The separate correctness suite tests cancellation and explicit channel identity.

## Latest recorded results

The latest retest passes **all 69 shipped-module cases**: 65 with the original
init fixture and four with additional audible spectral diagnostics. Original
silent init results remain recorded; diagnostic passes do not imply those init
settings became audible. Every master, tap and branch stem has the expected
frame/channel count and finite samples. Single-pass/chunked and serial/parallel
comparisons use the unchanged absolute amplitude tolerance of **0.000002**.
The five previously non-reproducible modules also pass repeated single-pass runs.

Validation also passes **14 shipped-module correctness tests**, **14 focused
replay regressions**, **all six engine scenarios**, and general discovery with
**109 passed / 66 skipped** (175 total, replay/PCM tests enabled). GUI tests were not
enabled. The audit covers four channels at 44.1 kHz and 176,417 frames, init
settings plus the documented diagnostics, not every preset or routing topology.

See [debugging findings](reports/offline_findings.md),
[final per-module results](reports/offline_modules.md), and
[the failing baseline](reports/offline_modules_before_debug.md).

## Focused replay regressions

```sh
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_replay_regressions.py -v
```

This separate 14-test suite preserves coverage for exact lengths and channel
identity, stateful chunk seams, curved automation, oscillator phase, Python/pyo
randomness, fades, master filters, muted outputs, module-requested warmup, and
process/file cleanup during chunk and raw-branch cancellation. It skips without
the opt-in flag. General discovery with all replay fixtures enabled is:

```sh
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -v
```

The all-module runner retains the original silent init results and supplements
them with audible diagnostic fixtures: a half-second source at three times the
original amplitude, plus a -90 dB gate threshold for SpectralGate and Vectral.
Those four results are labeled `pass_with_diagnostic`; they do not imply that
the original init fixture was audible. The sample tolerance and exact-shape
checks are unchanged. Renderer fixes and the additional replay cost are detailed
in [the findings](reports/offline_findings.md).

## Multichannel and codec matrix

```sh
cecillia/bin/python tests/check_multichannel_formats.py --report-prefix multichannel_formats_final
```

The final audit passes **552/552 cases across 69 modules**, using 1/2/4/6/8 input
channels and 1/2/4/6/8/16/64 output channels. It covers WAV, AIFF, FLAC and CAF,
PCM16/24/32 and float32 variants at 44.1/48 kHz. Two scenarios compare chunked
exports against single-pass float references. Checks include exact metadata,
finite samples, input codec channel roundtrips and master/tap sample comparisons.

Ten silent init-fixture cases retain their original results and receive
**10/10 passing audible diagnostics**. `--audible-diagnostics` lowers the four
MultiBandGate thresholds to -80 dB, or extends the short 64-channel
MultiBandDelay/BucketBrigadeDevice cases to 1.25 seconds. It fails if output remains
silent. Per-case frame counts and diagnostic labels are recorded.

`--scenario NAME` and `--module TEXT` select targeted reruns. `--report-prefix NAME`
isolates artifacts from concurrent audits. The runner validates that every job
reaches a terminal state and logs complete failure records. Input-free synthesis
cases and silent cases are labeled rather than treated as file-input/DSP proof.

See [findings, fixes and coverage limits](reports/multichannel_findings.md),
[final matrix](reports/multichannel_formats_final.md), and
[failing baseline](reports/multichannel_formats_before_debug.md).

## PCM and pitch-window regressions

```sh
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_pcm_exports.py -v
cecillia/bin/python tests/check_pitch_window_stability.py --report-prefix pitch_window_stability_final
```

All **five focused PCM/window tests** pass: direct overload saturation,
master/tap/branch conversion, mono PCM24 RIFF padding, and native-window boundary
arithmetic. No tolerance was widened to hide the wraparound bug. Float scratch
filenames must end in `.wav` because pyo chooses its container from the extension.
Integer files are encoded after alignment, with saturation; float files preserve
headroom. Non-finite arrays fail instead of silently becoming integer samples.

The stress runner passes **300/300 renders** across ChordMaker, Harmonizer and
MultiBandHarmonizer, checking finite/exact-shaped masters and taps, PCM32 equality
and repeated float-master equality. The effective native window changes by at
most one sample to avoid the reproduced unison circular-read edge; pitch stays
unchanged. See the [stress report](reports/pitch_window_stability_final.md) and
[post-fix routing checks](reports/harmonizer_routing_retest.md).

Latest general discovery with replay/PCM fixtures enabled: **175 tests,
109 passed and 66 skipped**. The six engine scenarios pass. GUI and physical
hardware checks were not enabled. Exact commands for the supplemental audible
fixtures and explicit scope limits are in the [findings](reports/multichannel_findings.md).
