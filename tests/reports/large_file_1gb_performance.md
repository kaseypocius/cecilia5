# Very Large File Performance & 1 GB Stress Benchmark Report

> Historical benchmark: reported RSS measures the coordinator (`RUSAGE_SELF`), excluding native worker subprocesses. Short outputs from large inputs do not establish gigabyte-output memory use or absence of leaks. See the [worker memory audit](offline_memory_findings.md) and [current size matrix](offline_memory.md).

## Executive Summary

- **Max File Size Tested**: **1.00 GB** (`1,000,000,000 bytes` / 125,000,000 samples @ 48 kHz / 43.4 minutes audio).
- **Total Benchmark Cases**: **42**.
- **Pass Rate**: **42 / 42 passed (100% pass rate, 0 failures)**.
- **Average Throughput**: **7.5x realtime** (median **5.6x**, max **31.1x**).
- **Total Benchmark Runtime**: **41.85 seconds**.

## Part 1: File Size Progression (250 MB -> 1.00 GB)

| Size Tier | Input File Size | Input Duration | Module | Render Dur | Speedup | Peak RSS | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 250MB | 238.4 MB | 651.0s | `Filters/StateVar2.c5` | 5.0s | **11.6x** | 73.3 MB | **PASS** |
| 250MB | 238.4 MB | 651.0s | `Time/UltimateGrainer.c5` | 5.0s | **7.2x** | 83.0 MB | **PASS** |
| 500MB | 476.8 MB | 1302.1s | `Filters/StateVar2.c5` | 5.0s | **6.5x** | 92.8 MB | **PASS** |
| 500MB | 476.8 MB | 1302.1s | `Time/UltimateGrainer.c5` | 5.0s | **5.0x** | 102.2 MB | **PASS** |
| 750MB | 715.3 MB | 1953.1s | `Filters/StateVar2.c5` | 5.0s | **7.3x** | 108.7 MB | **PASS** |
| 750MB | 715.3 MB | 1953.1s | `Time/UltimateGrainer.c5` | 5.0s | **5.6x** | 118.1 MB | **PASS** |
| 1.00GB | 953.7 MB | 2604.2s | `Filters/StateVar2.c5` | 5.0s | **5.8x** | 127.5 MB | **PASS** |
| 1.00GB | 953.7 MB | 2604.2s | `Time/UltimateGrainer.c5` | 5.0s | **4.5x** | 127.7 MB | **PASS** |

## Part 2: Representative Modules with 1.00 GB Audio (48 kHz, 2ch, 43.4 min source)

| Module | Category / Engine | Speedup | Peak dBFS | Peak RSS | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Time/UltimateGrainer.c5` | Granular / Particle2 | **4.1x** | -14.83 dB | 128.0 MB | **PASS** |
| `Time/Particle.c5` | Granular / Table | **5.0x** | -16.44 dB | 128.0 MB | **PASS** |
| `Time/Pelletizer.c5` | Granular / Looper | **5.1x** | -24.85 dB | 131.7 MB | **PASS** |
| `Filters/StateVar2.c5` | Filters / StateVar | **5.6x** | -31.07 dB | 131.7 MB | **PASS** |
| `Filters/BrickWall.c5` | Filters / BrickWall | **4.9x** | -28.37 dB | 131.7 MB | **PASS** |
| `Filters/AMFMFilter.c5` | Filters / Modulated | **6.0x** | -36.75 dB | 135.4 MB | **PASS** |
| `Dynamics/Distortion.c5` | Dynamics / Distort | **6.0x** | -25.49 dB | 135.4 MB | **PASS** |
| `Dynamics/DynamicsProcessor.c5` | Dynamics / Compressor | **5.9x** | -28.39 dB | 135.4 MB | **PASS** |
| `Dynamics/FeedbackLooper.c5` | Dynamics / TableLooper | **5.7x** | -17.11 dB | 135.4 MB | **PASS** |
| `Multiband/MultiBandDelay.c5` | Multiband / Delay | **5.8x** | -30.02 dB | 135.4 MB | **PASS** |
| `Multiband/MultiBandReverb.c5` | Multiband / Reverb | **5.4x** | -39.17 dB | 135.4 MB | **PASS** |
| `Pitch/Harmonizer.c5` | Pitch / Harmonizer | **5.9x** | -32.00 dB | 135.5 MB | **PASS** |
| `Pitch/ChordMaker.c5` | Pitch / MultiVoice | **5.9x** | -25.26 dB | 135.5 MB | **PASS** |
| `Pitch/PitchLooper.c5` | Pitch / TableLooper | **6.1x** | -15.23 dB | 135.6 MB | **PASS** |
| `Spectral/SpectralWarper.c5` | Spectral / PhaseVocoder | **3.5x** | -120.00 dB | 135.6 MB | **PASS** |
| `Spectral/SpectralDelay.c5` | Spectral / PVSpectralDelay | **4.6x** | -29.11 dB | 135.6 MB | **PASS** |
| `Resonators&Verbs/MatrixReverb.c5` | Resonators / MatrixReverb | **6.1x** | -30.41 dB | 137.1 MB | **PASS** |
| `Synthesis/StochGrains2.c5` | Synthesis / FileGrain | **4.5x** | -22.65 dB | 137.1 MB | **PASS** |

## Part 3: Multichannel Outputs from 1.00 GB Audio

| Module | Channels | Layout | Speedup | Peak dBFS | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Filters/StateVar2.c5` | 2 ch | Stereo | **4.8x** | -33.01 dB | **PASS** |
| `Time/UltimateGrainer.c5` | 2 ch | Stereo | **4.0x** | -14.08 dB | **PASS** |
| `Pitch/Harmonizer.c5` | 2 ch | Stereo | **4.9x** | -34.07 dB | **PASS** |
| `Filters/StateVar2.c5` | 6 ch | 5.1 Surround | **4.5x** | -33.01 dB | **PASS** |
| `Time/UltimateGrainer.c5` | 6 ch | 5.1 Surround | **2.8x** | -11.67 dB | **PASS** |
| `Pitch/Harmonizer.c5` | 6 ch | 5.1 Surround | **4.5x** | -34.07 dB | **PASS** |
| `Filters/StateVar2.c5` | 8 ch | 8ch Octaphonic | **4.5x** | -33.01 dB | **PASS** |
| `Time/UltimateGrainer.c5` | 8 ch | 8ch Octaphonic | **2.6x** | -9.65 dB | **PASS** |
| `Pitch/Harmonizer.c5` | 8 ch | 8ch Octaphonic | **4.8x** | -34.07 dB | **PASS** |

## Part 4: Multi-Worker Time-Chunked Rendering from 1.00 GB Audio

| Module | Strategy | Render Duration | Speedup | Peak dBFS | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Filters/StateVar2.c5` | Time Chunks (2 workers) | 10.0s | **9.8x** | -25.05 dB | **PASS** |
| `Dynamics/Distortion.c5` | Time Chunks (2 workers) | 10.0s | **10.2x** | -23.00 dB | **PASS** |
| `Pitch/Harmonizer.c5` | Time Chunks (2 workers) | 10.0s | **10.2x** | -26.10 dB | **PASS** |
| `Time/Particle.c5` | Time Chunks (2 workers) | 10.0s | **8.8x** | -16.40 dB | **PASS** |

## Part 5: Extended Duration Bounces (30.0s) from 1.00 GB Audio

| Module | Render Duration | Elapsed Time | Speedup | Peak dBFS | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Filters/StateVar2.c5` | 30.0s | 0.99s | **30.2x** | -16.69 dB | **PASS** |
| `Dynamics/DynamicsProcessor.c5` | 30.0s | 0.96s | **31.1x** | -13.96 dB | **PASS** |
| `Multiband/MultiBandDelay.c5` | 30.0s | 1.06s | **28.3x** | -13.79 dB | **PASS** |
