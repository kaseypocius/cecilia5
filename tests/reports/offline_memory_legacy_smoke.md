# Offline Renderer Performance & File Size Scaling Matrix

## Executive Summary

- **Modules Tested**: All 1 shipped Cecilia 5 modules.
- **Total Benchmark Cases**: 4 cases across 4 file size tiers.
- **Pass Rate**: **4 / 4 passed** (0 failures).
- **Stress Cases (120s / 92 MB input @ 96 kHz up to 50 channels)**: **12 / 12 passed**.
- **Average Throughput**: **15.7x realtime** (median **18.1x**, ranging from **2.9x** to **23.6x**).
- **Total Benchmark Duration**: 25.51 seconds.

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
| `Time/UltimateGrainer.c5` | 8 ch | 96000 Hz | 175.8 MB | **1.4x** | pass | -15.92 dB |
| `Time/UltimateGrainer.c5` | 50 ch | 96000 Hz | 175.8 MB | **0.4x** | pass | -16.12 dB |
| `Time/Particle.c5` | 8 ch | 96000 Hz | 175.8 MB | **2.0x** | pass | -18.38 dB |
| `Time/Particle.c5` | 50 ch | 96000 Hz | 175.8 MB | **1.0x** | pass | -17.5 dB |
| `Time/Pelletizer.c5` | 8 ch | 96000 Hz | 175.8 MB | **2.2x** | pass | -28.53 dB |
| `Time/Pelletizer.c5` | 50 ch | 96000 Hz | 175.8 MB | **1.1x** | pass | -29.77 dB |
| `Pitch/Harmonizer.c5` | 8 ch | 96000 Hz | 175.8 MB | **3.2x** | pass | -22.08 dB |
| `Pitch/Harmonizer.c5` | 50 ch | 96000 Hz | 175.8 MB | **1.9x** | pass | -22.08 dB |
| `Filters/StateVar2.c5` | 8 ch | 96000 Hz | 175.8 MB | **3.4x** | pass | -20.02 dB |
| `Filters/StateVar2.c5` | 50 ch | 96000 Hz | 175.8 MB | **2.1x** | pass | -20.02 dB |
| `Resonators&Verbs/ConvolutionReverb.c5` | 8 ch | 96000 Hz | 2.2 MB | **1.7x** | pass | 38.26 dB |
| `Resonators&Verbs/ConvolutionReverb.c5` | 50 ch | 96000 Hz | 2.2 MB | **0.3x** | pass | 38.26 dB |

## Complete Per-Module Results Table

| Module | Category | Kind | Small (1.5s) | Medium (15s) | Large (60s) | Chunked (60s) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `StateVar2` | Filters | `csampler` | 2.9x | 16.07x | 23.55x | 20.18x | **PASS** |
