# Spectral audio verification — November 10, 2026

**130/130 render/file cases passed across all 13 spectral modules**, plus **20/20 processing-response checks**. Every default-settings case produced audible output in every channel. No defaults or gate thresholds were changed to obtain the default-case passes.

## Reproduced and fixed

An eight-second recorded-audio input with a four-second performance produced completely silent master and tap files in both BinWarper and SpectralWarper. The other 11 modules produced audible default output with the same primary/secondary recordings.

SpectralWarper needed a complete phase-vocoder buffer before playback. BinWarper already requested pre-analysis, but it advanced envelopes, position automation and fades during that analysis. Live transport timing could also stop the performance while analysis was still running.

The shared live/offline graph now plans analysis separately, holds initial controls while buffers fill, starts or restarts performance readers and source samplers at the performance boundary, delays fades and GUI updates appropriately, and excludes analysis from playback/progress timing. Chained buffers record after upstream buffers become ready. Export taps contain performance audio rather than a large analysis prefix. Raw branch intermediates retain the history needed for exact master replay.

Fade nodes are created before their consumers for buffered graphs, avoiding a one-buffer envelope lag between capture paths. Existing non-buffer graphs retain their original timing.

| Previously silent module | Baseline peak | Fixed offline RMS dBFS | Fixed live RMS dBFS |
| --- | ---: | ---: | ---: |
| BinWarper.c5 | 0 | -31.00 | -31.00 |
| SpectralWarper.c5 | 0 | -29.42 | -29.42 |

[Before measurements](spectral_audio_baseline.json).

## Real inputs and measured outputs

The primary/secondary inputs are distinct bundled pyo recordings (`accord.aif` and `transparent.aif`), decoded, resampled to 48 kHz, repeated to eight seconds and peak-scaled to 0.7. They are actual sound-file inputs to the native DSP graph. Separate synthetic tones are used only for the frequency-response diagnostics.

Test settings use 32-bit native precision, a -6 dB master gain, 5 ms global fades and 256-frame DSP buffers. Module init controls are unchanged.

The four-second stereo, 48 kHz exports include 24-bit PCM, independently decoded with Python’s wave reader as well as libsndfile, and float32 live-path captures. All generated inputs, outputs, taps and reference files live in temporary directories and are deleted when the audit exits, including failures and Ctrl+C. Only JSON measurements and hashes remain. The earlier 28 saved WAV examples have also been removed.

| Module | Offline RMS dBFS, quieter channel | Live RMS dBFS, quieter channel |
| --- | ---: | ---: |
| AddResynth | -33.83 | -33.83 |
| BinModulator | -36.59 | -36.58 |
| BinWarper | -31.00 | -31.00 |
| CrossSynth | -37.71 | -37.71 |
| CrossSynth2 | -25.49 | -25.49 |
| Morphing | -32.30 | -32.30 |
| Shifter | -31.83 | -31.83 |
| SpectralDelay | -25.30 | -25.30 |
| SpectralFilter | -26.90 | -26.90 |
| SpectralGate | -34.62 | -34.62 |
| SpectralWarper | -29.42 | -29.42 |
| Transpose | -32.51 | -32.51 |
| Vectral | -34.47 | -34.47 |

## Coverage and sample checks

Each module receives ten cases: stereo 44.1 kHz offline/live, stereo 48 kHz offline float, exact two-worker chunks, stereo live-path capture, eight-channel 96 kHz offline and live-path captures, stereo WAV24 export, and 50-input/50-output-channel exports at 96 and 192 kHz. The configured 44.1 kHz application rate is covered, including non-buffer-aligned capture lengths. High-channel input files contain the same recordings with channel-specific sample offsets. All generated audio is removed after inspection.

Every master and requested module tap is decoded and checked for exact frame count/rate/channel count, finite samples and non-trivial peak/RMS in every channel. Four-second stereo exports contain exactly 192,000 frames. Every WAV24 export also passes an independent RIFF/PCM header and complete payload read. Audio SHA-256 values and all numeric metrics are retained in [the render matrix](spectral_audio_full.json).

Chunk/master comparisons retain absolute tolerance 0.000002. Independent live recordings compare the interior, excluding 0.15-second capture startup/shutdown margins, at absolute plus relative tolerance 0.000002 to allow native float32 gain-path rounding. These are distinct checks; the chunk tolerance is unchanged. Buffered-module taps also have exact single/chunk regression coverage.

## Processing-response checks

- Transpose with both voices at +1200 cents and fully wet output moves 440/660 Hz probes to approximately 880/1320 Hz in both live and offline paths.
- SpectralWarper traverses a two-note input; BinWarper at double playback speed also reaches the later note. Early/late spectral peaks verify buffer contents and the position/playback timeline, rather than merely detecting nonzero noise.
- CrossSynth, CrossSynth2 and Morphing outputs change measurably when the second recording changes, verifying that their auxiliary sampler is actually used.
- SpectralGate and Vectral intentionally suppress a quiet input at the default -30 dB threshold. Lowering the threshold to -90 dB restores audible output in both paths. This quiet-input silence is normal gating, not an invalid file. The loud recorded-input default cases pass with thresholds unchanged.

[All 20 numeric response checks](spectral_audio_functions.json).

## Regressions and limits

General discovery passes **174 tests, 68 skipped, zero failures** (242 total), with native DSP fixtures enabled. All six engine integration scenarios pass. [Test output](spectral_audio_tests.txt), [validation/source hashes](spectral_audio_validation.json).

New regressions cover analysis-aware live stopping, zero added delay for non-buffer graphs, long-source audible warpers in both paths, exact chunk/tap replay, a mixed normal/buffered graph, serial/parallel branch mixing with curved master-filter automation, and two buffer modules in series. A pre-existing mixed-memory-queue test now coordinates its fixture startup explicitly rather than relying on executor thread-start order.

Cleanup regressions exercise successful runs and partial-render failures in the offline probe, live probe, full audit and functional audit. They verify that generated inputs and outputs disappear while numeric probe reports remain. [Cleanup validation](spectral_audio_cleanup_validation.json) records the native reruns and removed artifact inventory.

Live verification executes the actual AudioServer.loadChain/start DSP path on pyo’s manual backend and records its real output. It does not open audio hardware, a microphone, or the GUI. Physical output-device permissions/routing and subjective listening remain untested. The results cover these files, init settings, listed layouts and explicit diagnostics, not every preset, automation curve or live microphone mode.

Whole-file spectral analysis still has startup CPU/RAM cost, and branch intermediates need temporary disk space. Preparation time is now excluded from the audible performance rather than being mistaken for silent audio. Earlier size-sweep reports remain historical measurements; their recorded silent outcomes have not been relabeled.

## Reproduce

```sh
cecillia/bin/python tests/check_spectral_audio.py --full --prefix spectral_audio_full
cecillia/bin/python tests/check_spectral_audio.py --functional
CECILIA_DSP_TESTS=1 cecillia/bin/python -m unittest discover -s tests -v
cecillia/bin/python tests/write_spectral_audio_findings.py
```
