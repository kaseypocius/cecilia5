# Offline renderer memory findings

The standard size sweep is complete. Recorded 552/552 cases; 0 need retesting after source changes.

Whole-file post-processing amplified memory, and parallel workers each loaded their own input tables. Earlier large-file reports measured coordinator-only `RUSAGE_SELF`, excluding native workers. Their sub-140-MB numbers did not bound renderer memory or test gigabyte outputs. Historical reports now state that limit.

## Changes

- Stream peak scans, normalization, trim/encoding, chunk stitching and branch accumulation in bounded blocks. Stream mixed branches through the native master graph instead of another full audio table.
- Estimate decoded inputs, mono `cfilein` replication, full spectral histories, and replicated convolution filters. Reduce worker count within at most 35% of physical RAM and half reported available RAM. Try estimates above the budget with one RSS-monitored worker. Reject such estimates only when resident-memory monitoring is unavailable. Auto mode uses one pass when the worker allowance is one.
- Sample real worker RSS on macOS/Linux and stop an over-budget worker with an explicit error. A lone single-pass job gets the whole budget. The UI explains the RAM worker allowance. Sampling is best-effort protection, not a hard allocation cap.
- Reap stopped workers and clean incomplete destinations plus destination-specific atomic encoder files. Admission rejection and failure before any write preserve an existing destination. Cleanup compares its original file signature, including when a later queued overwrite fails.
- Guard reproduced circular-read NaNs in MultiBandDelay and DetunedResonators, and fix DetunedResonators voice activation for mono/multichannel output.

## Measured post-processing memory

Original separate-process 64 MiB probes peaked at **492,601,344 bytes** during normalization and **1,080,934,400 bytes** during whole-array AIFF export. Streaming normalization measured **60,801,024 bytes** on the same fixture. The following repeatable utility checks use physically written audio and scan every output sample.

| Operation | Payload MiB | Peak RSS MiB | Seconds | Result |
| --- | --- | --- | --- | --- |
| normalize | 64 | 73.0 | 0.28 | pass |
| encode | 64 | 79.5 | 0.23 | pass |
| trim | 64 | 71.5 | 0.26 | pass |
| stitch | 64 | 131.2 | 0.37 | pass |
| mix | 64 | 198.4 | 1.11 | pass |
| normalize | 1024 | 82.2 | 8.58 | pass |
| encode | 1024 | 83.8 | 4.10 | pass |
| trim | 1024 | 78.8 | 3.79 | pass |
| stitch | 1024 | 158.1 | 7.02 | pass |
| mix | 1024 | 221.1 | 23.68 | pass |
| normalize | 1152 | 78.5 | 10.39 | pass |
| encode | 1152 | 82.8 | 9.25 | pass |
| trim | 1152 | 72.5 | 7.67 | pass |
| stitch | 1152 | 149.9 | 9.82 | pass |
| mix | 1152 | 201.3 | 30.45 | pass |

The branch mixer additionally compares every sample after the initial server gain ramp. AIFF24 uses three bytes per sample, so its output is smaller than the float32 source. [Raw utility results](offline_memory_utilities_final.jsonl).

## All-module size sweep

All 69 modules, 48 kHz, eight channels, float32 WAV, init settings. Input and output growth are tested separately at **1 MiB, 64 MiB, 1 GiB and 1.125 GiB (1.208 GB)**. Inputs contain physically written nonzero samples; logical and allocated bytes are retained. Large-input cases load the complete primary source and render one second; large-output cases loop a 1 MiB source. Auxiliary inputs remain small in this matrix and are tested separately.

Each child has a sampled **3 GiB RSS stop and 120-second deadline**. Output checks cover exact frame/channel/rate metadata, normalization, and every sample for NaN/Inf. Generators with no file input are not applicable to input growth. Pass means memory/file integrity only; silent outputs are visible and do not establish intended DSP. Timings include import/render/post-processing/validation and can vary with concurrent machine workload.

Latest standard counts: **4 memory_limit**, **28 not_applicable**, **507 pass**, **13 timeout**.
There are 35 silent completed cases. See the [complete per-case matrix](offline_memory.md) and [raw attempt history](offline_memory.jsonl).

## Large secondary inputs and higher allowances

Secondary slots: 22/24 completed under the standard limits. Slots include Vocoder excitation, convolution impulse/table inputs, and the second source of CrossSynth/CrossSynth2/Morphing. [Results](offline_memory_aux.jsonl).

| Module / slot | Payload MiB | RSS allowance GiB | Peak RSS GiB | Seconds | Result | Silent |
| --- | --- | --- | --- | --- | --- | --- |
| Spectral/BinWarper.c5 / primary | 1024 | 6 | 5.15 | 31.87 | pass | yes |
| Spectral/SpectralWarper.c5 / primary | 1024 | 6 | 5.15 | 3.20 | pass | yes |
| Resonators&Verbs/ConvolutionReverb.c5 / impulse | 1024 | 6 | 6.16 | 7.44 | memory_limit |  |
| Spectral/BinWarper.c5 / primary | 1152 | 6 | 5.78 | 47.95 | pass | yes |
| Spectral/SpectralWarper.c5 / primary | 1152 | 6 | 5.78 | 3.98 | pass | yes |
| Resonators&Verbs/ConvolutionReverb.c5 / impulse | 1152 | 6 | 6.06 | 8.79 | memory_limit |  |
| Resonators&Verbs/ConvolutionReverb.c5 / impulse | 1024 | 10 | 6.27 | 31.44 | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 / impulse | 1152 | 10 | 7.04 | 34.41 | pass |  |

The higher-budget retries distinguish a resource allowance from a native crash. Both spectral cases complete with 6 GiB; large convolution IRs complete with 10 GiB. The latter allowance was below the measured 11.2 GiB system render budget on this 32 GiB machine. These limits are not promises for different presets, FFT sizes, precision or polyphony. [6 GiB results](offline_memory_extended.jsonl), [10 GiB IR results](offline_memory_impulse_10g.jsonl).

## Real coordinator and longer output checks

| Managed module | Requested / scheduled workers | Peak worker RSS GiB | Seconds | Result |
| --- | --- | --- | --- | --- |
| Spectral/BinWarper.c5 | 6 / 1 | 5.80 | 72.47 | pass |
| Resonators&Verbs/ConvolutionReverb.c5 | 6 / 1 | 7.04 | 170.04 | pass |

Managed probes use 1.125 GiB inputs, chunk rendering, normalization, activity events, exact metadata, and worker/scratch cleanup. BinWarper is silent in this short probe; ConvolutionReverb is audible. [Coordinator results](offline_memory_manager.json).

Long-output retries: 15/15 recorded attempts completed (15 planned). At most two small-input children run together, each with a 512 MiB RSS stop and 600-second deadline. The main 120-second outcomes remain recorded separately.

| Module | Payload MiB | Peak RSS MiB | Seconds | Result |
| --- | --- | --- | --- | --- |
| Dynamics/UpDistoRes.c5 | 1024 | 116.0 | 127.17 | pass |
| Dynamics/UpDistoRes.c5 | 1152 | 110.1 | 143.03 | pass |
| Pitch/LooperBank.c5 | 1024 | 112.9 | 387.23 | pass |
| Pitch/LooperBank.c5 | 1152 | 101.6 | 430.09 | pass |
| Resonators&Verbs/Convolve.c5 | 1024 | 109.4 | 188.99 | pass |
| Resonators&Verbs/Convolve.c5 | 1152 | 111.1 | 212.13 | pass |
| Resonators&Verbs/WGuideBank.c5 | 1024 | 118.6 | 260.40 | pass |
| Resonators&Verbs/WGuideBank.c5 | 1152 | 113.1 | 292.67 | pass |
| Spectral/AddResynth.c5 | 1024 | 110.1 | 132.05 | pass |
| Time/UltimateGrainer.c5 | 1024 | 113.9 | 119.62 | pass |
| Spectral/AddResynth.c5 | 1152 | 113.2 | 148.69 | pass |
| Filters/BrickWall.c5 | 1024 | 110.2 | 96.76 | pass |
| Time/UltimateGrainer.c5 | 1152 | 115.0 | 127.76 | pass |
| Filters/BrickWall.c5 | 1152 | 111.2 | 109.27 | pass |
| Filters/Binaural.c5 | 64 | 97.0 | 125.18 | pass |

Representative paired jobs load and render 1.125 GiB at the same time (180-second deadline, 3 GiB RSS stop). The convolution IR stays small. These three do not replace the all-module factor sweep.

| Paired module | Peak RSS GiB | Seconds | Result |
| --- | --- | --- | --- |
| Filters/StateVar2.c5 | 1.26 | 20.02 | pass |
| Multiband/MultiBandDelay.c5 | 1.35 | 30.56 | pass |
| Resonators&Verbs/ConvolutionReverb.c5 | 1.28 | 31.91 | pass |

[Paired input/output results](offline_memory_paired.jsonl).

[Long-output results](offline_memory_output_extended.jsonl). Supplemental multi-gigabyte Binaural attempts were interrupted after slow file growth; no completed gigabyte Binaural output is claimed. Process-list verification found no surviving Binaural workers.

## Correctness and remaining limits

- Unit discovery: **135 passed, 66 skipped, 0 failed** (201 total). The six engine integration scenarios also pass, including cancellation and normalization. [Validation](offline_memory_validation.json), [unit log](offline_memory_unit.log), [engine log](offline_memory_engine.log).
- All 69 module single/chunk/parallel audits pass at absolute tolerance 0.000002, with short audible spectral diagnostics. The current layout/codec matrix is 552/552; it combines a full sweep with a fresh eight-scenario DetunedResonators retest after that file changed between reference and encoding phases. [Routing](offline_memory_correctness.json), [codecs](offline_memory_formats_current.md).
- MultiBandDelay reproduced 8 NaN failures in 150 persistent-worker jobs. DetunedResonators reproduced 13 in 150. Their guarded versions each pass 150 instrumented and 150 persistent-worker repetitions. Stage logs are retained as `offline_memory_*_stages_*.log`. [Native Delay/AllpassWG source inspected](https://github.com/belangeo/pyo/blob/master/src/objects/delaymodule.c).
- MultiBandDelay moves only near-edge delay positions by at most 0.125 sample at 48 kHz with its 15-second buffer. DetunedResonators similarly guards its main period by at most 0.0078125 sample at 44.1 kHz. These small timing/pitch changes avoid the reproduced native wrap-rounding read.
- **Unresolved DSP scope:** the short large-input spectral probes are silent. SpectralWarper needs buffer-fill time; BinWarper pre-analysis can advance envelopes/fades beyond a shorter performance. Warmup/performance timeline separation is not claimed fixed. RAM allocation measurements remain valid; these are not audible long-source correctness passes.
- Tests cover default settings and the documented diagnostics, not every preset, spatial intent, routing topology, large-input/output pairing or persistent-process leak soak. Display-dependent checks were skipped. Standalone packaging and other operating systems still need validation.
- File export and atomic replacement need disk headroom too. No fixed free-disk threshold guarantees enough RAM.

## Reproduction and source changes

Run the commands in [tests/README.md](../README.md). Primary drivers are `check_offline_memory.py`, `check_offline_aux_memory.py`, `check_offline_memory_utilities.py`, `check_offline_memory_extended.py`, `check_offline_memory_manager.py`, and `check_offline_output_extended.py`. The shared harness records child PIDs and reaps interrupted children.

The directory watcher found owned source edits during this run; affected cases were repeated. Full source hashes remain in each attempt. `offline_memory_source_versions.json` accepts equivalence only when the native-pipeline AST is identical; coordinator/pool/process-handle changes are covered separately by coordinator/unit/integration checks. Audio I/O, graph, module and native helper changes still invalidate cases. `--resume` and `retest_offline_memory_stale.py` repeat invalidated cases without substituting cached passes.

Measured on macOS-12.6-arm64-arm-64bit-Mach-O, Python 3.13.3, 32 GiB RAM. Earlier throughput reports retain notices correcting coordinator-only RSS attribution. This report is generated by `tests/write_offline_memory_findings.py`.
