# Offline-render debugging and final retest

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

## Fixes validated

- Branch workers preserve full graph construction order and record raw output
  before the server gain ramp. The mixed master uses the same pyo gain, fade and
  plugin path as the serial graph, applied once.
- Offline replay seeds Python and numpy randomness. Module requests for pyo seed
  zero use the job seed (currently 1); explicit nonzero seeds and live playback
  behavior are retained.
- Each job creates fresh DSP server state inside the persistent worker process,
  preventing retained startup gain-ramp state from shifting the first samples.
- Raw branch intermediates retain the buffer-rounded warmup prefix for master
  replay. Exported module/branch stems discard that prefix. Intermediates are
  float WAV regardless of the public stem format, avoiding premature quantization.
- Scratch recordings live in manager-owned temporary directories so cancellation
  removes raw intermediates and dummy recordings as well as public partial files.

## Before and after

The fresh failing baseline reproduced **65 failures and four inconclusive silent
cases**. Its [per-module table](offline_modules_before_debug.md) and
[numerical results](offline_modules_before_debug.json) are preserved. The
[final table](offline_modules.md) and [final numerical results](offline_modules.json)
contain the corrected results and diagnostic fixture details. The final matrix
completed in 233.15 seconds.

The earlier Distortion probe isolated a fade mismatch: maximum serial/parallel
error was about 0.0718977 with a 5 ms fade and 4.47e-8 with fades disabled. The
new regressions compare enabled fades, gain, muted branches and a master filter
without excluding edge samples. The first correction passed 68/69 module cases;
the BinWarper diagnostic then exposed the additional warmup-prefix alignment bug,
which is included in the final fix and regression suite.

The five formerly non-reproducible modules are `Pitch/RandomAccumulator`,
`Resonators&Verbs/WGuideBank`, `Synthesis/StochGrains`, `Synthesis/StochGrains2`,
and `Time/Stutterer`. They now pass both chunk equality and explicit repeat runs.

## Audible diagnostics for the original silent cases

`Spectral/BinWarper` and `Spectral/SpectralWarper` receive a half-second source
so their buffers can fill during the render. `Spectral/SpectralGate` and
`Spectral/Vectral` also receive a -90 dB gate threshold. The diagnostic source
uses three times the original fixture amplitude. Both original init checks and
these supplemental checks are retained in the JSON report; successful cases
are labeled `pass_with_diagnostic`. No module default was changed to force a pass.

## Scope and cost

Exact chunks replay the original timeline, and branch workers now reconstruct
the full graph before selecting one output. These preserve DSP history and random
stream construction order at additional CPU and temporary-storage cost; a single
job is not guaranteed to accelerate. Batch jobs still run across worker processes.

Selected 6-channel and 64-channel stem checks pass in the correctness suite;
the 69-module matrix itself uses four channels. Tests cover cancellation of chunks
and raw branches, including process exit and partial-file/scratch cleanup. They do
not cover cancellation separately for every module or every startup race. Silent
init output alone still cannot establish audio correctness. Hardware and GUI
validation remain outside this run.

See [test commands](../README.md) and the [rerunnable audit](../check_all_modules.py).

## Subsequent multichannel/codec validation

The follow-up matrix passes **552/552 cases across all 69 modules**, plus ten
audible diagnostics for silent init cases. It fixed integer overload wraparound,
float/FLAC intermediate path conflicts, and the reproduced native harmonizer
unison boundary instability. The latter also passed 300 repeated renders and a
routing retest of all three affected modules. Full details, preserved baselines
and scope limits are in [the format findings](multichannel_findings.md).
General discovery now passes **109 tests with 66 skipped** (175 total); all six
engine scenarios still pass. The earlier four-channel audit above remains a
separate validation record.
