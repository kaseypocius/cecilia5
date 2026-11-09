# Offline Renderer Performance & File Size Scaling Matrix

> Historical benchmark: reported RSS measures the coordinator (`RUSAGE_SELF`), excluding native worker subprocesses. Short outputs from large inputs do not establish gigabyte-output memory use or absence of leaks. See the [worker memory audit](offline_memory_findings.md) and [current size matrix](offline_memory.md).

## Executive Summary

- **Modules Tested**: All 69 shipped Cecilia 5 modules.
- **Total Benchmark Cases**: 276 cases across 4 file size tiers.
- **Pass Rate**: **276 / 276 passed** (0 failures).
- **Stress Cases (120s / 92 MB input @ 96 kHz up to 50 channels)**: **12 / 12 passed**.
- **Average Throughput**: **14.2x realtime** (median **14.7x**, ranging from **0.7x** to **34.2x**).
- **Total Benchmark Duration**: 224.89 seconds.

## Tested File Size Tiers

| Tier | Input Sound Size | Input Duration | Render Duration | Output Format | Acceleration Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small** | 0.50 MB | 1.5s | 1.0s | 2ch @ 44.1 kHz | Single-pass |
| **Medium** | 5.05 MB | 15.0s | 5.0s | 2ch @ 44.1 kHz | Single-pass |
| **Large** | 21.97 MB | 60.0s | 10.0s | 2ch @ 48.0 kHz | Single-pass |
| **Chunked Large** | 21.97 MB | 60.0s | 15.0s | 4ch @ 48.0 kHz | Time Chunks (2 threads) |

## High-Channel & Large-File Stress Results

| Module | Channels | Rate | Input File Size | Speedup | Status | Peak dB |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Time/UltimateGrainer.c5` | 8 ch | 96000 Hz | 175.8 MB | **1.6x** | pass | -15.92 dB |
| `Time/UltimateGrainer.c5` | 50 ch | 96000 Hz | 175.8 MB | **0.4x** | pass | -16.12 dB |
| `Time/Particle.c5` | 8 ch | 96000 Hz | 175.8 MB | **2.7x** | pass | -18.38 dB |
| `Time/Particle.c5` | 50 ch | 96000 Hz | 175.8 MB | **1.1x** | pass | -17.5 dB |
| `Time/Pelletizer.c5` | 8 ch | 96000 Hz | 175.8 MB | **2.8x** | pass | -28.53 dB |
| `Time/Pelletizer.c5` | 50 ch | 96000 Hz | 175.8 MB | **1.3x** | pass | -29.77 dB |
| `Pitch/Harmonizer.c5` | 8 ch | 96000 Hz | 175.8 MB | **3.3x** | pass | -22.08 dB |
| `Pitch/Harmonizer.c5` | 50 ch | 96000 Hz | 175.8 MB | **2.1x** | pass | -22.08 dB |
| `Filters/StateVar2.c5` | 8 ch | 96000 Hz | 175.8 MB | **3.4x** | pass | -20.02 dB |
| `Filters/StateVar2.c5` | 50 ch | 96000 Hz | 175.8 MB | **2.3x** | pass | -20.02 dB |
| `Resonators&Verbs/ConvolutionReverb.c5` | 8 ch | 96000 Hz | 2.2 MB | **1.8x** | pass | 38.26 dB |
| `Resonators&Verbs/ConvolutionReverb.c5` | 50 ch | 96000 Hz | 2.2 MB | **0.4x** | pass | 38.26 dB |

## Complete Per-Module Results Table

| Module | Category | Kind | Small (1.5s) | Medium (15s) | Large (60s) | Chunked (60s) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Degrade` | Dynamics | `csampler` | 3.43x | 15.63x | 27.36x | 22.72x | **PASS** |
| `Distortion` | Dynamics | `csampler` | 4.61x | 16.26x | 25.72x | 21.51x | **PASS** |
| `DynamicsProcessor` | Dynamics | `csampler` | 3.55x | 16.8x | 29.3x | 25.59x | **PASS** |
| `FeedbackLooper` | Dynamics | `cfilein` | 4.68x | 18.24x | 26.67x | 23.71x | **PASS** |
| `UpDistoRes` | Dynamics | `csampler` | 3.48x | 11.03x | 13.77x | 8.13x | **PASS** |
| `WaveShaper` | Dynamics | `csampler` | 3.86x | 17.63x | 28.65x | 24.68x | **PASS** |
| `AMFMFilter` | Filters | `csampler` | 4.5x | 14.57x | 25.39x | 19.87x | **PASS** |
| `AutoModFilter` | Filters | `csampler` | 4.04x | 16.47x | 26.13x | 23.88x | **PASS** |
| `Binaural` | Filters | `csampler` | 1.07x | 1.44x | 1.38x | 0.7x | **PASS** |
| `BrickWall` | Filters | `csampler` | 3.81x | 12.12x | 17.26x | 10.26x | **PASS** |
| `Flanger` | Filters | `csampler` | 4.42x | 18.67x | 28.34x | 24.98x | **PASS** |
| `MaskFilter` | Filters | `csampler` | 4.18x | 12.32x | 21.31x | 16.39x | **PASS** |
| `ParamEQ` | Filters | `csampler` | 4.55x | 17.51x | 25.69x | 20.63x | **PASS** |
| `Phaser` | Filters | `csampler` | 3.97x | 14.93x | 21.15x | 15.1x | **PASS** |
| `StateVar` | Filters | `csampler` | 4.46x | 17.5x | 27.5x | 24.76x | **PASS** |
| `StateVar2` | Filters | `csampler` | 4.6x | 20.46x | 27.89x | 23.91x | **PASS** |
| `Vocoder` | Filters | `csampler,csampler` | 3.63x | 13.41x | 22.03x | 17.62x | **PASS** |
| `MultiBandBeatMaker` | Multiband | `cfilein` | 3.99x | 13.51x | 23.32x | 21.96x | **PASS** |
| `MultiBandDelay` | Multiband | `csampler` | 4.55x | 17.64x | 27.79x | 21.2x | **PASS** |
| `MultiBandDisto` | Multiband | `csampler` | 3.98x | 15.67x | 24.36x | 21.44x | **PASS** |
| `MultiBandFreqShift` | Multiband | `csampler` | 3.74x | 14.76x | 21.9x | 15.76x | **PASS** |
| `MultiBandGate` | Multiband | `csampler` | 4.64x | 16.63x | 24.39x | 19.29x | **PASS** |
| `MultiBandHarmonizer` | Multiband | `csampler` | 3.14x | 14.55x | 22.47x | 18.87x | **PASS** |
| `MultiBandReverb` | Multiband | `csampler` | 4.24x | 13.83x | 21.88x | 14.95x | **PASS** |
| `ChordMaker` | Pitch | `csampler` | 3.65x | 17.52x | 26.24x | 19.22x | **PASS** |
| `Chorus` | Pitch | `csampler` | 4.12x | 15.08x | 27.25x | 24.24x | **PASS** |
| `FreqShift` | Pitch | `csampler` | 4.77x | 15.21x | 25.19x | 20.51x | **PASS** |
| `Harmonizer` | Pitch | `csampler` | 3.8x | 15.23x | 28.78x | 23.02x | **PASS** |
| `LooperBank` | Pitch | `cfilein` | 2.9x | 5.7x | 6.5x | 3.56x | **PASS** |
| `LooperMod` | Pitch | `cfilein` | 4.18x | 17.8x | 29.63x | 27.53x | **PASS** |
| `PitchLooper` | Pitch | `cfilein` | 4.85x | 16.12x | 29.52x | 28.0x | **PASS** |
| `RandomAccumulator` | Pitch | `csampler` | 3.82x | 17.59x | 29.23x | 24.53x | **PASS** |
| `ConvolutionReverb` | Resonators&Verbs | `csampler,cfilein` | 4.17x | 6.54x | 1.89x | 1.0x | **PASS** |
| `Convolve` | Resonators&Verbs | `csampler,cfilein` | 3.59x | 9.52x | 10.59x | 6.18x | **PASS** |
| `DetunedResonators` | Resonators&Verbs | `csampler` | 3.5x | 13.53x | 19.56x | 14.65x | **PASS** |
| `MatrixReverb` | Resonators&Verbs | `csampler` | 4.18x | 13.73x | 24.03x | 24.22x | **PASS** |
| `Resonators` | Resonators&Verbs | `csampler` | 3.68x | 15.96x | 21.88x | 15.35x | **PASS** |
| `WGuideBank` | Resonators&Verbs | `csampler` | 3.78x | 12.48x | 17.29x | 7.69x | **PASS** |
| `AddResynth` | Spectral | `csampler` | 2.13x | 7.88x | 10.44x | 7.62x | **PASS** |
| `BinModulator` | Spectral | `csampler` | 2.06x | 10.32x | 16.61x | 14.61x | **PASS** |
| `BinWarper` | Spectral | `csampler` | 3.04x | 11.15x | 8.75x | 7.15x | **PASS** |
| `CrossSynth` | Spectral | `csampler,csampler` | 2.22x | 9.6x | 13.75x | 12.44x | **PASS** |
| `CrossSynth2` | Spectral | `csampler,csampler` | 2.25x | 8.3x | 15.23x | 12.22x | **PASS** |
| `Morphing` | Spectral | `csampler,csampler` | 2.02x | 9.41x | 15.39x | 13.31x | **PASS** |
| `Shifter` | Spectral | `csampler` | 2.25x | 9.42x | 15.7x | 12.61x | **PASS** |
| `SpectralDelay` | Spectral | `csampler` | 2.2x | 9.78x | 16.24x | 12.5x | **PASS** |
| `SpectralFilter` | Spectral | `csampler` | 2.05x | 10.49x | 16.71x | 14.67x | **PASS** |
| `SpectralGate` | Spectral | `csampler` | 2.15x | 10.08x | 17.1x | 14.81x | **PASS** |
| `SpectralWarper` | Spectral | `csampler` | 4.3x | 13.58x | 23.38x | 17.48x | **PASS** |
| `Transpose` | Spectral | `csampler` | 2.26x | 8.86x | 15.21x | 11.71x | **PASS** |
| `Vectral` | Spectral | `csampler` | 2.3x | 9.38x | 16.86x | 14.78x | **PASS** |
| `AdditiveSynth` | Synthesis | `synthesis` | 4.18x | 12.07x | 19.54x | 11.8x | **PASS** |
| `BucketBrigadeDevice` | Synthesis | `csampler` | 4.14x | 17.07x | 23.42x | 22.03x | **PASS** |
| `CrossFreqMod` | Synthesis | `synthesis` | 3.46x | 17.99x | 34.19x | 27.75x | **PASS** |
| `FrequencyModulation` | Synthesis | `synthesis` | 4.22x | 16.85x | 28.69x | 29.24x | **PASS** |
| `Pulsar` | Synthesis | `synthesis` | 4.22x | 18.19x | 31.8x | 28.57x | **PASS** |
| `SpitSideBandSynth` | Synthesis | `synthesis` | 4.15x | 16.78x | 25.55x | 21.59x | **PASS** |
| `StochGrains` | Synthesis | `synthesis` | 2.83x | 8.33x | 10.19x | 9.5x | **PASS** |
| `StochGrains2` | Synthesis | `cfilein` | 3.28x | 8.7x | 10.8x | 9.05x | **PASS** |
| `SuperSaw` | Synthesis | `synthesis` | 3.86x | 17.78x | 31.7x | 24.67x | **PASS** |
| `WaveScanSynth` | Synthesis | `cfilein` | 3.96x | 16.05x | 29.32x | 25.06x | **PASS** |
| `4Delays` | Time | `csampler` | 4.23x | 14.92x | 27.35x | 21.16x | **PASS** |
| `BeatMaker` | Time | `cfilein` | 3.96x | 13.94x | 20.4x | 20.83x | **PASS** |
| `DelayMod` | Time | `csampler` | 4.22x | 19.89x | 29.98x | 26.64x | **PASS** |
| `Granulator` | Time | `cfilein` | 3.53x | 12.01x | 18.88x | 17.92x | **PASS** |
| `Particle` | Time | `cfilein` | 4.27x | 11.84x | 19.81x | 15.09x | **PASS** |
| `Pelletizer` | Time | `cfilein` | 3.51x | 12.7x | 20.99x | 16.04x | **PASS** |
| `Stutterer` | Time | `cfilein` | 4.09x | 19.8x | 28.03x | 28.06x | **PASS** |
| `UltimateGrainer` | Time | `cfilein` | 3.66x | 9.24x | 13.11x | 7.19x | **PASS** |
