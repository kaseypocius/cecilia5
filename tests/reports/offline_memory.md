# Offline module memory audit

Recorded 552/552 planned cases. Latest results: 4 memory_limit, 28 not_applicable, 507 pass, 13 timeout.
All planned cases are recorded; no cases need retesting after source changes.

All 69 shipped modules; 48 kHz, eight channels, float WAV, init settings. A separate process runs each native job, with an externally sampled 3 GiB RSS stop and a 120-second deadline. `memory_limit` and `timeout` mean the case did not complete; they are not passes or proof of a native crash. Input tests load the complete primary source but render only one second. Auxiliary files remain small. Output tests loop a 1 MiB primary source and normalize the entire output. A source-independent generator has no applicable input-size case. Silent outputs establish file/finite-sample behavior only.

Payloads are 1 MiB, 64 MiB, 1 GiB, and 1.125 GiB (1.208 GB), plus headers. Fixtures are physically written; logical and allocated bytes are recorded. No sparse files are used. All output samples are scanned for NaN/Inf and exact frame/channel/rate metadata is checked.

| Payload MiB | Direction | Pass | Silent passes | N/A | Timeout | Memory stop | Error | Max RSS MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | input | 62 | 4 | 7 | 0 | 0 | 0 | 174.1 |
| 1 | output | 69 | 5 | 0 | 0 | 0 | 0 | 171.7 |
| 64 | input | 62 | 6 | 7 | 0 | 0 | 0 | 465.2 |
| 64 | output | 68 | 4 | 0 | 1 | 0 | 0 | 205.8 |
| 1024 | input | 60 | 4 | 7 | 0 | 2 | 0 | 3138.7 |
| 1024 | output | 63 | 4 | 0 | 6 | 0 | 0 | 197.9 |
| 1152 | input | 60 | 4 | 7 | 0 | 2 | 0 | 3239.5 |
| 1152 | output | 63 | 4 | 0 | 6 | 0 | 0 | 195.7 |

| Module | Payload MiB | Direction | Status | Silent | Seconds | Peak RSS MiB |
| --- | --- | --- | --- | --- | --- | --- |
| Dynamics/Degrade.c5 | 1 | input | pass |  | 0.37 | 93.1 |
| Dynamics/Degrade.c5 | 1 | output | pass |  | 0.33 | 87.7 |
| Dynamics/Distortion.c5 | 1 | input | pass |  | 0.37 | 92.2 |
| Dynamics/Distortion.c5 | 1 | output | pass |  | 0.57 | 89.3 |
| Dynamics/DynamicsProcessor.c5 | 1 | input | pass | yes | 0.37 | 89.2 |
| Dynamics/DynamicsProcessor.c5 | 1 | output | pass | yes | 0.41 | 84.9 |
| Dynamics/FeedbackLooper.c5 | 1 | input | pass |  | 0.67 | 94.2 |
| Dynamics/FeedbackLooper.c5 | 1 | output | pass |  | 0.42 | 91.5 |
| Dynamics/UpDistoRes.c5 | 1 | input | pass |  | 0.72 | 88.3 |
| Dynamics/UpDistoRes.c5 | 1 | output | pass |  | 0.65 | 88.2 |
| Dynamics/WaveShaper.c5 | 1 | input | pass |  | 0.39 | 92.5 |
| Dynamics/WaveShaper.c5 | 1 | output | pass |  | 0.43 | 88.7 |
| Filters/AMFMFilter.c5 | 1 | input | pass |  | 0.56 | 87.3 |
| Filters/AMFMFilter.c5 | 1 | output | pass |  | 0.51 | 87.7 |
| Filters/AutoModFilter.c5 | 1 | input | pass |  | 0.42 | 87.3 |
| Filters/AutoModFilter.c5 | 1 | output | pass |  | 0.61 | 93.5 |
| Filters/Binaural.c5 | 1 | input | pass |  | 4.24 | 97.9 |
| Filters/Binaural.c5 | 1 | output | pass |  | 3.34 | 86.7 |
| Filters/BrickWall.c5 | 1 | input | pass |  | 0.72 | 88.9 |
| Filters/BrickWall.c5 | 1 | output | pass |  | 0.56 | 91.3 |
| Filters/Flanger.c5 | 1 | input | pass |  | 0.57 | 84.9 |
| Filters/Flanger.c5 | 1 | output | pass |  | 0.36 | 88.7 |
| Filters/MaskFilter.c5 | 1 | input | pass |  | 0.67 | 95.6 |
| Filters/MaskFilter.c5 | 1 | output | pass |  | 0.38 | 83.2 |
| Filters/ParamEQ.c5 | 1 | input | pass |  | 0.53 | 91.1 |
| Filters/ParamEQ.c5 | 1 | output | pass |  | 0.52 | 91.4 |
| Filters/Phaser.c5 | 1 | input | pass |  | 0.54 | 94.4 |
| Filters/Phaser.c5 | 1 | output | pass |  | 0.52 | 89.5 |
| Filters/StateVar.c5 | 1 | input | pass |  | 0.40 | 89.7 |
| Filters/StateVar.c5 | 1 | output | pass |  | 0.48 | 85.3 |
| Filters/StateVar2.c5 | 1 | input | pass |  | 0.51 | 88.4 |
| Filters/StateVar2.c5 | 1 | output | pass |  | 0.41 | 86.5 |
| Filters/Vocoder.c5 | 1 | input | pass |  | 0.39 | 89.6 |
| Filters/Vocoder.c5 | 1 | output | pass |  | 0.41 | 85.7 |
| Multiband/MultiBandBeatMaker.c5 | 1 | input | pass |  | 0.37 | 92.3 |
| Multiband/MultiBandBeatMaker.c5 | 1 | output | pass |  | 0.27 | 85.3 |
| Multiband/MultiBandDelay.c5 | 1 | input | pass |  | 0.44 | 174.1 |
| Multiband/MultiBandDelay.c5 | 1 | output | pass |  | 0.32 | 171.7 |
| Multiband/MultiBandDisto.c5 | 1 | input | pass |  | 0.74 | 93.2 |
| Multiband/MultiBandDisto.c5 | 1 | output | pass |  | 0.36 | 89.3 |
| Multiband/MultiBandFreqShift.c5 | 1 | input | pass |  | 0.51 | 94.0 |
| Multiband/MultiBandFreqShift.c5 | 1 | output | pass |  | 0.41 | 88.3 |
| Multiband/MultiBandGate.c5 | 1 | input | pass | yes | 0.43 | 92.7 |
| Multiband/MultiBandGate.c5 | 1 | output | pass | yes | 0.45 | 83.7 |
| Multiband/MultiBandHarmonizer.c5 | 1 | input | pass |  | 0.42 | 93.3 |
| Multiband/MultiBandHarmonizer.c5 | 1 | output | pass |  | 0.46 | 89.7 |
| Multiband/MultiBandReverb.c5 | 1 | input | pass |  | 0.51 | 93.9 |
| Multiband/MultiBandReverb.c5 | 1 | output | pass |  | 0.49 | 90.2 |
| Pitch/ChordMaker.c5 | 1 | input | pass |  | 0.48 | 101.9 |
| Pitch/ChordMaker.c5 | 1 | output | pass |  | 0.53 | 96.8 |
| Pitch/Chorus.c5 | 1 | input | pass |  | 0.40 | 89.6 |
| Pitch/Chorus.c5 | 1 | output | pass |  | 0.42 | 82.5 |
| Pitch/FreqShift.c5 | 1 | input | pass |  | 0.50 | 97.1 |
| Pitch/FreqShift.c5 | 1 | output | pass |  | 0.46 | 91.0 |
| Pitch/Harmonizer.c5 | 1 | input | pass |  | 0.66 | 93.3 |
| Pitch/Harmonizer.c5 | 1 | output | pass |  | 0.54 | 87.0 |
| Pitch/LooperBank.c5 | 1 | input | pass |  | 1.33 | 83.9 |
| Pitch/LooperBank.c5 | 1 | output | pass |  | 1.38 | 89.1 |
| Pitch/LooperMod.c5 | 1 | input | pass |  | 0.35 | 88.9 |
| Pitch/LooperMod.c5 | 1 | output | pass |  | 0.37 | 83.6 |
| Pitch/PitchLooper.c5 | 1 | input | pass |  | 0.51 | 90.5 |
| Pitch/PitchLooper.c5 | 1 | output | pass |  | 0.55 | 87.9 |
| Pitch/RandomAccumulator.c5 | 1 | input | pass |  | 0.36 | 97.2 |
| Pitch/RandomAccumulator.c5 | 1 | output | pass |  | 0.40 | 93.1 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1 | input | pass |  | 0.54 | 98.0 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1 | output | pass |  | 0.40 | 94.2 |
| Resonators&Verbs/Convolve.c5 | 1 | input | pass |  | 0.82 | 90.8 |
| Resonators&Verbs/Convolve.c5 | 1 | output | pass |  | 0.58 | 89.9 |
| Resonators&Verbs/DetunedResonators.c5 | 1 | input | pass |  | 0.55 | 108.1 |
| Resonators&Verbs/DetunedResonators.c5 | 1 | output | pass |  | 0.71 | 100.3 |
| Resonators&Verbs/MatrixReverb.c5 | 1 | input | pass |  | 0.36 | 95.4 |
| Resonators&Verbs/MatrixReverb.c5 | 1 | output | pass |  | 0.40 | 93.2 |
| Resonators&Verbs/Resonators.c5 | 1 | input | pass |  | 0.51 | 93.1 |
| Resonators&Verbs/Resonators.c5 | 1 | output | pass |  | 0.45 | 89.1 |
| Resonators&Verbs/WGuideBank.c5 | 1 | input | pass |  | 1.15 | 106.2 |
| Resonators&Verbs/WGuideBank.c5 | 1 | output | pass |  | 0.88 | 100.4 |
| Spectral/AddResynth.c5 | 1 | input | pass |  | 0.91 | 93.4 |
| Spectral/AddResynth.c5 | 1 | output | pass |  | 0.76 | 90.7 |
| Spectral/BinModulator.c5 | 1 | input | pass |  | 0.59 | 90.0 |
| Spectral/BinModulator.c5 | 1 | output | pass |  | 0.54 | 90.8 |
| Spectral/BinWarper.c5 | 1 | input | pass |  | 0.39 | 91.2 |
| Spectral/BinWarper.c5 | 1 | output | pass | yes | 0.40 | 87.9 |
| Spectral/CrossSynth.c5 | 1 | input | pass |  | 0.56 | 90.1 |
| Spectral/CrossSynth.c5 | 1 | output | pass |  | 0.56 | 91.7 |
| Spectral/CrossSynth2.c5 | 1 | input | pass |  | 0.57 | 93.7 |
| Spectral/CrossSynth2.c5 | 1 | output | pass |  | 0.54 | 92.6 |
| Spectral/Morphing.c5 | 1 | input | pass |  | 0.62 | 95.8 |
| Spectral/Morphing.c5 | 1 | output | pass |  | 0.57 | 86.9 |
| Spectral/Shifter.c5 | 1 | input | pass |  | 0.69 | 88.1 |
| Spectral/Shifter.c5 | 1 | output | pass |  | 0.62 | 87.0 |
| Spectral/SpectralDelay.c5 | 1 | input | pass |  | 0.60 | 122.1 |
| Spectral/SpectralDelay.c5 | 1 | output | pass |  | 0.59 | 111.6 |
| Spectral/SpectralFilter.c5 | 1 | input | pass |  | 0.59 | 91.0 |
| Spectral/SpectralFilter.c5 | 1 | output | pass |  | 0.50 | 84.1 |
| Spectral/SpectralGate.c5 | 1 | input | pass | yes | 0.56 | 85.9 |
| Spectral/SpectralGate.c5 | 1 | output | pass | yes | 0.54 | 88.5 |
| Spectral/SpectralWarper.c5 | 1 | input | pass |  | 0.44 | 94.8 |
| Spectral/SpectralWarper.c5 | 1 | output | pass |  | 0.30 | 89.9 |
| Spectral/Transpose.c5 | 1 | input | pass |  | 0.62 | 91.2 |
| Spectral/Transpose.c5 | 1 | output | pass |  | 0.52 | 90.2 |
| Spectral/Vectral.c5 | 1 | input | pass | yes | 0.51 | 86.0 |
| Spectral/Vectral.c5 | 1 | output | pass | yes | 0.55 | 86.4 |
| Synthesis/AdditiveSynth.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/AdditiveSynth.c5 | 1 | output | pass |  | 0.41 | 84.8 |
| Synthesis/BucketBrigadeDevice.c5 | 1 | input | pass |  | 0.35 | 102.2 |
| Synthesis/BucketBrigadeDevice.c5 | 1 | output | pass |  | 0.36 | 94.3 |
| Synthesis/CrossFreqMod.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/CrossFreqMod.c5 | 1 | output | pass |  | 0.30 | 86.5 |
| Synthesis/FrequencyModulation.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/FrequencyModulation.c5 | 1 | output | pass |  | 0.33 | 89.8 |
| Synthesis/Pulsar.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/Pulsar.c5 | 1 | output | pass |  | 0.35 | 89.3 |
| Synthesis/SpitSideBandSynth.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SpitSideBandSynth.c5 | 1 | output | pass |  | 0.44 | 89.5 |
| Synthesis/StochGrains.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/StochGrains.c5 | 1 | output | pass |  | 0.46 | 96.1 |
| Synthesis/StochGrains2.c5 | 1 | input | pass |  | 0.50 | 90.2 |
| Synthesis/StochGrains2.c5 | 1 | output | pass |  | 0.40 | 92.7 |
| Synthesis/SuperSaw.c5 | 1 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SuperSaw.c5 | 1 | output | pass |  | 0.30 | 81.2 |
| Synthesis/WaveScanSynth.c5 | 1 | input | pass |  | 0.34 | 94.4 |
| Synthesis/WaveScanSynth.c5 | 1 | output | pass |  | 0.33 | 88.1 |
| Time/4Delays.c5 | 1 | input | pass |  | 0.34 | 114.9 |
| Time/4Delays.c5 | 1 | output | pass |  | 0.38 | 118.5 |
| Time/BeatMaker.c5 | 1 | input | pass |  | 0.42 | 99.3 |
| Time/BeatMaker.c5 | 1 | output | pass |  | 0.33 | 94.3 |
| Time/DelayMod.c5 | 1 | input | pass |  | 0.37 | 121.2 |
| Time/DelayMod.c5 | 1 | output | pass |  | 0.30 | 116.3 |
| Time/Granulator.c5 | 1 | input | pass |  | 0.46 | 91.7 |
| Time/Granulator.c5 | 1 | output | pass |  | 0.40 | 91.2 |
| Time/Particle.c5 | 1 | input | pass |  | 0.41 | 92.5 |
| Time/Particle.c5 | 1 | output | pass |  | 0.38 | 92.5 |
| Time/Pelletizer.c5 | 1 | input | pass |  | 0.39 | 95.3 |
| Time/Pelletizer.c5 | 1 | output | pass |  | 0.33 | 87.5 |
| Time/Stutterer.c5 | 1 | input | pass |  | 0.30 | 90.3 |
| Time/Stutterer.c5 | 1 | output | pass |  | 0.27 | 86.6 |
| Time/UltimateGrainer.c5 | 1 | input | pass |  | 0.51 | 87.7 |
| Time/UltimateGrainer.c5 | 1 | output | pass |  | 0.41 | 88.4 |
| Dynamics/Degrade.c5 | 64 | input | pass |  | 0.50 | 211.8 |
| Dynamics/Degrade.c5 | 64 | output | pass |  | 2.10 | 97.6 |
| Dynamics/Distortion.c5 | 64 | input | pass |  | 0.61 | 215.5 |
| Dynamics/Distortion.c5 | 64 | output | pass |  | 1.79 | 84.4 |
| Dynamics/DynamicsProcessor.c5 | 64 | input | pass | yes | 0.44 | 210.7 |
| Dynamics/DynamicsProcessor.c5 | 64 | output | pass | yes | 1.07 | 97.8 |
| Dynamics/FeedbackLooper.c5 | 64 | input | pass |  | 0.47 | 218.1 |
| Dynamics/FeedbackLooper.c5 | 64 | output | pass |  | 1.42 | 108.2 |
| Dynamics/UpDistoRes.c5 | 64 | input | pass |  | 0.63 | 216.6 |
| Dynamics/UpDistoRes.c5 | 64 | output | pass |  | 8.31 | 105.1 |
| Dynamics/WaveShaper.c5 | 64 | input | pass |  | 0.47 | 217.0 |
| Dynamics/WaveShaper.c5 | 64 | output | pass |  | 1.50 | 97.9 |
| Filters/AMFMFilter.c5 | 64 | input | pass |  | 0.47 | 216.2 |
| Filters/AMFMFilter.c5 | 64 | output | pass |  | 1.52 | 102.1 |
| Filters/AutoModFilter.c5 | 64 | input | pass |  | 0.47 | 219.2 |
| Filters/AutoModFilter.c5 | 64 | output | pass |  | 1.60 | 107.0 |
| Filters/Binaural.c5 | 64 | input | pass |  | 3.31 | 218.8 |
| Filters/Binaural.c5 | 64 | output | timeout |  | 120.00 | 78.6 |
| Filters/BrickWall.c5 | 64 | input | pass |  | 0.57 | 216.6 |
| Filters/BrickWall.c5 | 64 | output | pass |  | 6.37 | 104.8 |
| Filters/Flanger.c5 | 64 | input | pass |  | 0.53 | 213.5 |
| Filters/Flanger.c5 | 64 | output | pass |  | 1.25 | 97.8 |
| Filters/MaskFilter.c5 | 64 | input | pass |  | 0.51 | 210.9 |
| Filters/MaskFilter.c5 | 64 | output | pass |  | 3.16 | 97.1 |
| Filters/ParamEQ.c5 | 64 | input | pass |  | 0.48 | 214.8 |
| Filters/ParamEQ.c5 | 64 | output | pass |  | 2.20 | 101.8 |
| Filters/Phaser.c5 | 64 | input | pass |  | 0.54 | 216.1 |
| Filters/Phaser.c5 | 64 | output | pass |  | 3.78 | 96.8 |
| Filters/StateVar.c5 | 64 | input | pass |  | 0.45 | 219.5 |
| Filters/StateVar.c5 | 64 | output | pass |  | 1.31 | 96.8 |
| Filters/StateVar2.c5 | 64 | input | pass |  | 0.46 | 209.9 |
| Filters/StateVar2.c5 | 64 | output | pass |  | 1.44 | 98.6 |
| Filters/Vocoder.c5 | 64 | input | pass |  | 0.50 | 214.7 |
| Filters/Vocoder.c5 | 64 | output | pass |  | 2.67 | 97.0 |
| Multiband/MultiBandBeatMaker.c5 | 64 | input | pass |  | 0.48 | 221.0 |
| Multiband/MultiBandBeatMaker.c5 | 64 | output | pass |  | 1.71 | 101.3 |
| Multiband/MultiBandDelay.c5 | 64 | input | pass |  | 0.47 | 300.1 |
| Multiband/MultiBandDelay.c5 | 64 | output | pass |  | 2.33 | 205.8 |
| Multiband/MultiBandDisto.c5 | 64 | input | pass |  | 0.81 | 219.1 |
| Multiband/MultiBandDisto.c5 | 64 | output | pass |  | 4.94 | 117.7 |
| Multiband/MultiBandFreqShift.c5 | 64 | input | pass |  | 0.84 | 219.0 |
| Multiband/MultiBandFreqShift.c5 | 64 | output | pass |  | 3.90 | 102.1 |
| Multiband/MultiBandGate.c5 | 64 | input | pass | yes | 0.75 | 217.3 |
| Multiband/MultiBandGate.c5 | 64 | output | pass | yes | 3.33 | 111.7 |
| Multiband/MultiBandHarmonizer.c5 | 64 | input | pass |  | 0.84 | 222.6 |
| Multiband/MultiBandHarmonizer.c5 | 64 | output | pass |  | 4.16 | 115.2 |
| Multiband/MultiBandReverb.c5 | 64 | input | pass |  | 0.87 | 219.6 |
| Multiband/MultiBandReverb.c5 | 64 | output | pass |  | 6.98 | 120.0 |
| Pitch/ChordMaker.c5 | 64 | input | pass |  | 0.71 | 220.3 |
| Pitch/ChordMaker.c5 | 64 | output | pass |  | 3.55 | 118.3 |
| Pitch/Chorus.c5 | 64 | input | pass |  | 0.73 | 218.5 |
| Pitch/Chorus.c5 | 64 | output | pass |  | 1.80 | 103.9 |
| Pitch/FreqShift.c5 | 64 | input | pass |  | 0.76 | 225.8 |
| Pitch/FreqShift.c5 | 64 | output | pass |  | 4.00 | 113.7 |
| Pitch/Harmonizer.c5 | 64 | input | pass |  | 0.49 | 219.7 |
| Pitch/Harmonizer.c5 | 64 | output | pass |  | 1.74 | 111.6 |
| Pitch/LooperBank.c5 | 64 | input | pass |  | 0.93 | 210.9 |
| Pitch/LooperBank.c5 | 64 | output | pass |  | 25.00 | 100.5 |
| Pitch/LooperMod.c5 | 64 | input | pass |  | 0.65 | 216.0 |
| Pitch/LooperMod.c5 | 64 | output | pass |  | 1.00 | 104.4 |
| Pitch/PitchLooper.c5 | 64 | input | pass |  | 0.59 | 216.0 |
| Pitch/PitchLooper.c5 | 64 | output | pass |  | 1.09 | 103.4 |
| Pitch/RandomAccumulator.c5 | 64 | input | pass |  | 0.53 | 221.9 |
| Pitch/RandomAccumulator.c5 | 64 | output | pass |  | 1.85 | 114.4 |
| Resonators&Verbs/ConvolutionReverb.c5 | 64 | input | pass |  | 0.59 | 224.5 |
| Resonators&Verbs/ConvolutionReverb.c5 | 64 | output | pass |  | 2.52 | 107.1 |
| Resonators&Verbs/Convolve.c5 | 64 | input | pass |  | 0.90 | 217.2 |
| Resonators&Verbs/Convolve.c5 | 64 | output | pass |  | 13.37 | 111.3 |
| Resonators&Verbs/DetunedResonators.c5 | 64 | input | pass |  | 0.59 | 229.9 |
| Resonators&Verbs/DetunedResonators.c5 | 64 | output | pass |  | 5.02 | 116.7 |
| Resonators&Verbs/MatrixReverb.c5 | 64 | input | pass |  | 0.46 | 218.8 |
| Resonators&Verbs/MatrixReverb.c5 | 64 | output | pass |  | 1.47 | 104.5 |
| Resonators&Verbs/Resonators.c5 | 64 | input | pass |  | 0.56 | 219.1 |
| Resonators&Verbs/Resonators.c5 | 64 | output | pass |  | 3.40 | 112.0 |
| Resonators&Verbs/WGuideBank.c5 | 64 | input | pass |  | 0.84 | 225.0 |
| Resonators&Verbs/WGuideBank.c5 | 64 | output | pass |  | 17.14 | 116.1 |
| Spectral/AddResynth.c5 | 64 | input | pass |  | 0.90 | 215.3 |
| Spectral/AddResynth.c5 | 64 | output | pass |  | 9.46 | 99.9 |
| Spectral/BinModulator.c5 | 64 | input | pass |  | 0.78 | 211.1 |
| Spectral/BinModulator.c5 | 64 | output | pass |  | 3.15 | 92.8 |
| Spectral/BinWarper.c5 | 64 | input | pass | yes | 2.20 | 463.8 |
| Spectral/BinWarper.c5 | 64 | output | pass |  | 2.94 | 104.9 |
| Spectral/CrossSynth.c5 | 64 | input | pass |  | 0.77 | 219.4 |
| Spectral/CrossSynth.c5 | 64 | output | pass |  | 3.92 | 103.9 |
| Spectral/CrossSynth2.c5 | 64 | input | pass |  | 0.79 | 213.3 |
| Spectral/CrossSynth2.c5 | 64 | output | pass |  | 4.00 | 95.6 |
| Spectral/Morphing.c5 | 64 | input | pass |  | 0.76 | 217.2 |
| Spectral/Morphing.c5 | 64 | output | pass |  | 3.49 | 103.3 |
| Spectral/Shifter.c5 | 64 | input | pass |  | 0.72 | 216.1 |
| Spectral/Shifter.c5 | 64 | output | pass |  | 3.55 | 102.2 |
| Spectral/SpectralDelay.c5 | 64 | input | pass |  | 0.72 | 239.4 |
| Spectral/SpectralDelay.c5 | 64 | output | pass |  | 3.17 | 128.8 |
| Spectral/SpectralFilter.c5 | 64 | input | pass |  | 0.68 | 216.1 |
| Spectral/SpectralFilter.c5 | 64 | output | pass |  | 2.73 | 104.0 |
| Spectral/SpectralGate.c5 | 64 | input | pass | yes | 0.73 | 212.5 |
| Spectral/SpectralGate.c5 | 64 | output | pass | yes | 2.49 | 98.1 |
| Spectral/SpectralWarper.c5 | 64 | input | pass | yes | 0.55 | 465.2 |
| Spectral/SpectralWarper.c5 | 64 | output | pass |  | 2.75 | 104.2 |
| Spectral/Transpose.c5 | 64 | input | pass |  | 0.74 | 218.1 |
| Spectral/Transpose.c5 | 64 | output | pass |  | 4.19 | 101.7 |
| Spectral/Vectral.c5 | 64 | input | pass | yes | 0.72 | 211.8 |
| Spectral/Vectral.c5 | 64 | output | pass | yes | 2.89 | 100.1 |
| Synthesis/AdditiveSynth.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/AdditiveSynth.c5 | 64 | output | pass |  | 5.76 | 116.2 |
| Synthesis/BucketBrigadeDevice.c5 | 64 | input | pass |  | 0.51 | 218.6 |
| Synthesis/BucketBrigadeDevice.c5 | 64 | output | pass |  | 1.57 | 102.9 |
| Synthesis/CrossFreqMod.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/CrossFreqMod.c5 | 64 | output | pass |  | 1.01 | 93.6 |
| Synthesis/FrequencyModulation.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/FrequencyModulation.c5 | 64 | output | pass |  | 1.09 | 101.2 |
| Synthesis/Pulsar.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/Pulsar.c5 | 64 | output | pass |  | 0.99 | 101.7 |
| Synthesis/SpitSideBandSynth.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SpitSideBandSynth.c5 | 64 | output | pass |  | 1.69 | 101.5 |
| Synthesis/StochGrains.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/StochGrains.c5 | 64 | output | pass |  | 4.06 | 118.1 |
| Synthesis/StochGrains2.c5 | 64 | input | pass |  | 0.67 | 224.4 |
| Synthesis/StochGrains2.c5 | 64 | output | pass |  | 6.82 | 108.6 |
| Synthesis/SuperSaw.c5 | 64 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SuperSaw.c5 | 64 | output | pass |  | 1.12 | 108.0 |
| Synthesis/WaveScanSynth.c5 | 64 | input | pass |  | 0.48 | 212.0 |
| Synthesis/WaveScanSynth.c5 | 64 | output | pass |  | 1.33 | 103.0 |
| Time/4Delays.c5 | 64 | input | pass |  | 0.48 | 238.4 |
| Time/4Delays.c5 | 64 | output | pass |  | 1.87 | 138.1 |
| Time/BeatMaker.c5 | 64 | input | pass |  | 0.46 | 212.9 |
| Time/BeatMaker.c5 | 64 | output | pass |  | 1.42 | 109.3 |
| Time/DelayMod.c5 | 64 | input | pass |  | 0.54 | 242.9 |
| Time/DelayMod.c5 | 64 | output | pass |  | 1.08 | 134.8 |
| Time/Granulator.c5 | 64 | input | pass |  | 0.57 | 216.0 |
| Time/Granulator.c5 | 64 | output | pass |  | 3.53 | 107.6 |
| Time/Particle.c5 | 64 | input | pass |  | 0.66 | 219.9 |
| Time/Particle.c5 | 64 | output | pass |  | 3.21 | 106.5 |
| Time/Pelletizer.c5 | 64 | input | pass |  | 0.56 | 215.4 |
| Time/Pelletizer.c5 | 64 | output | pass |  | 2.74 | 110.6 |
| Time/Stutterer.c5 | 64 | input | pass |  | 0.50 | 216.3 |
| Time/Stutterer.c5 | 64 | output | pass |  | 1.08 | 99.1 |
| Time/UltimateGrainer.c5 | 64 | input | pass |  | 0.72 | 219.8 |
| Time/UltimateGrainer.c5 | 64 | output | pass |  | 8.06 | 108.5 |
| Dynamics/Degrade.c5 | 1024 | input | pass |  | 2.79 | 1150.5 |
| Dynamics/Degrade.c5 | 1024 | output | pass |  | 20.08 | 95.6 |
| Dynamics/Distortion.c5 | 1024 | input | pass |  | 3.01 | 1154.0 |
| Dynamics/Distortion.c5 | 1024 | output | pass |  | 38.15 | 110.7 |
| Dynamics/DynamicsProcessor.c5 | 1024 | input | pass | yes | 2.56 | 1154.4 |
| Dynamics/DynamicsProcessor.c5 | 1024 | output | pass | yes | 12.85 | 110.2 |
| Dynamics/FeedbackLooper.c5 | 1024 | input | pass |  | 2.47 | 1152.7 |
| Dynamics/FeedbackLooper.c5 | 1024 | output | pass |  | 20.40 | 114.8 |
| Dynamics/UpDistoRes.c5 | 1024 | input | pass |  | 2.75 | 1155.6 |
| Dynamics/UpDistoRes.c5 | 1024 | output | timeout |  | 120.01 | 80.9 |
| Dynamics/WaveShaper.c5 | 1024 | input | pass |  | 2.56 | 1158.0 |
| Dynamics/WaveShaper.c5 | 1024 | output | pass |  | 20.82 | 113.0 |
| Filters/AMFMFilter.c5 | 1024 | input | pass |  | 2.52 | 1149.2 |
| Filters/AMFMFilter.c5 | 1024 | output | pass |  | 23.76 | 117.2 |
| Filters/AutoModFilter.c5 | 1024 | input | pass |  | 2.50 | 1154.7 |
| Filters/AutoModFilter.c5 | 1024 | output | pass |  | 25.60 | 111.7 |
| Filters/Binaural.c5 | 1024 | input | pass |  | 5.32 | 1155.9 |
| Filters/Binaural.c5 | 1024 | output | timeout |  | 120.01 | 79.0 |
| Filters/BrickWall.c5 | 1024 | input | pass |  | 2.64 | 1150.3 |
| Filters/BrickWall.c5 | 1024 | output | pass |  | 102.77 | 118.2 |
| Filters/Flanger.c5 | 1024 | input | pass |  | 2.62 | 1159.4 |
| Filters/Flanger.c5 | 1024 | output | pass |  | 20.66 | 110.8 |
| Filters/MaskFilter.c5 | 1024 | input | pass |  | 2.60 | 1150.7 |
| Filters/MaskFilter.c5 | 1024 | output | pass |  | 52.22 | 110.8 |
| Filters/ParamEQ.c5 | 1024 | input | pass |  | 3.27 | 1156.0 |
| Filters/ParamEQ.c5 | 1024 | output | pass |  | 36.05 | 108.2 |
| Filters/Phaser.c5 | 1024 | input | pass |  | 2.56 | 1153.7 |
| Filters/Phaser.c5 | 1024 | output | pass |  | 64.94 | 118.8 |
| Filters/StateVar.c5 | 1024 | input | pass |  | 4.04 | 1160.2 |
| Filters/StateVar.c5 | 1024 | output | pass |  | 25.33 | 110.8 |
| Filters/StateVar2.c5 | 1024 | input | pass |  | 3.23 | 1150.9 |
| Filters/StateVar2.c5 | 1024 | output | pass |  | 22.28 | 101.8 |
| Filters/Vocoder.c5 | 1024 | input | pass |  | 3.17 | 1159.9 |
| Filters/Vocoder.c5 | 1024 | output | pass |  | 64.21 | 116.2 |
| Multiband/MultiBandBeatMaker.c5 | 1024 | input | pass |  | 4.03 | 1162.8 |
| Multiband/MultiBandBeatMaker.c5 | 1024 | output | pass |  | 37.53 | 112.0 |
| Multiband/MultiBandDelay.c5 | 1024 | input | pass |  | 2.79 | 1242.4 |
| Multiband/MultiBandDelay.c5 | 1024 | output | pass |  | 39.97 | 197.9 |
| Multiband/MultiBandDisto.c5 | 1024 | input | pass |  | 2.85 | 1150.6 |
| Multiband/MultiBandDisto.c5 | 1024 | output | pass |  | 37.98 | 99.0 |
| Multiband/MultiBandFreqShift.c5 | 1024 | input | pass |  | 2.49 | 1153.4 |
| Multiband/MultiBandFreqShift.c5 | 1024 | output | pass |  | 49.72 | 103.6 |
| Multiband/MultiBandGate.c5 | 1024 | input | pass | yes | 2.44 | 1151.9 |
| Multiband/MultiBandGate.c5 | 1024 | output | pass | yes | 28.97 | 87.8 |
| Multiband/MultiBandHarmonizer.c5 | 1024 | input | pass |  | 2.44 | 1154.5 |
| Multiband/MultiBandHarmonizer.c5 | 1024 | output | pass |  | 40.24 | 104.7 |
| Multiband/MultiBandReverb.c5 | 1024 | input | pass |  | 2.50 | 1156.9 |
| Multiband/MultiBandReverb.c5 | 1024 | output | pass |  | 61.44 | 114.4 |
| Pitch/ChordMaker.c5 | 1024 | input | pass |  | 2.50 | 1157.0 |
| Pitch/ChordMaker.c5 | 1024 | output | pass |  | 37.11 | 120.5 |
| Pitch/Chorus.c5 | 1024 | input | pass |  | 2.53 | 1151.7 |
| Pitch/Chorus.c5 | 1024 | output | pass |  | 24.26 | 104.5 |
| Pitch/FreqShift.c5 | 1024 | input | pass |  | 2.60 | 1157.5 |
| Pitch/FreqShift.c5 | 1024 | output | pass |  | 36.37 | 113.3 |
| Pitch/Harmonizer.c5 | 1024 | input | pass |  | 2.50 | 1158.2 |
| Pitch/Harmonizer.c5 | 1024 | output | pass |  | 24.89 | 108.3 |
| Pitch/LooperBank.c5 | 1024 | input | pass |  | 2.92 | 1154.3 |
| Pitch/LooperBank.c5 | 1024 | output | timeout |  | 120.03 | 77.2 |
| Pitch/LooperMod.c5 | 1024 | input | pass |  | 2.42 | 1148.4 |
| Pitch/LooperMod.c5 | 1024 | output | pass |  | 14.53 | 105.3 |
| Pitch/PitchLooper.c5 | 1024 | input | pass |  | 2.41 | 1156.4 |
| Pitch/PitchLooper.c5 | 1024 | output | pass |  | 15.53 | 100.3 |
| Pitch/RandomAccumulator.c5 | 1024 | input | pass |  | 2.40 | 1160.8 |
| Pitch/RandomAccumulator.c5 | 1024 | output | pass |  | 23.11 | 105.2 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1024 | input | pass |  | 2.49 | 1155.5 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1024 | output | pass |  | 32.97 | 95.0 |
| Resonators&Verbs/Convolve.c5 | 1024 | input | pass |  | 2.77 | 1153.7 |
| Resonators&Verbs/Convolve.c5 | 1024 | output | timeout |  | 120.03 | 78.1 |
| Resonators&Verbs/DetunedResonators.c5 | 1024 | input | pass |  | 2.52 | 1161.7 |
| Resonators&Verbs/DetunedResonators.c5 | 1024 | output | pass |  | 63.96 | 112.7 |
| Resonators&Verbs/MatrixReverb.c5 | 1024 | input | pass |  | 2.48 | 1153.3 |
| Resonators&Verbs/MatrixReverb.c5 | 1024 | output | pass |  | 14.11 | 102.9 |
| Resonators&Verbs/Resonators.c5 | 1024 | input | pass |  | 2.45 | 1150.7 |
| Resonators&Verbs/Resonators.c5 | 1024 | output | pass |  | 47.70 | 99.0 |
| Resonators&Verbs/WGuideBank.c5 | 1024 | input | pass |  | 2.77 | 1164.1 |
| Resonators&Verbs/WGuideBank.c5 | 1024 | output | timeout |  | 120.01 | 90.8 |
| Spectral/AddResynth.c5 | 1024 | input | pass |  | 2.86 | 1151.6 |
| Spectral/AddResynth.c5 | 1024 | output | timeout |  | 120.05 | 79.1 |
| Spectral/BinModulator.c5 | 1024 | input | pass |  | 2.74 | 1153.0 |
| Spectral/BinModulator.c5 | 1024 | output | pass |  | 43.27 | 95.8 |
| Spectral/BinWarper.c5 | 1024 | input | memory_limit |  | 2.58 | 3138.7 |
| Spectral/BinWarper.c5 | 1024 | output | pass |  | 43.43 | 114.8 |
| Spectral/CrossSynth.c5 | 1024 | input | pass |  | 2.74 | 1155.8 |
| Spectral/CrossSynth.c5 | 1024 | output | pass |  | 59.51 | 99.1 |
| Spectral/CrossSynth2.c5 | 1024 | input | pass |  | 2.80 | 1153.7 |
| Spectral/CrossSynth2.c5 | 1024 | output | pass |  | 58.34 | 98.5 |
| Spectral/Morphing.c5 | 1024 | input | pass |  | 2.80 | 1153.9 |
| Spectral/Morphing.c5 | 1024 | output | pass |  | 53.32 | 99.8 |
| Spectral/Shifter.c5 | 1024 | input | pass |  | 2.78 | 1155.4 |
| Spectral/Shifter.c5 | 1024 | output | pass |  | 58.92 | 99.9 |
| Spectral/SpectralDelay.c5 | 1024 | input | pass |  | 3.08 | 1178.6 |
| Spectral/SpectralDelay.c5 | 1024 | output | pass |  | 45.00 | 108.6 |
| Spectral/SpectralFilter.c5 | 1024 | input | pass |  | 2.72 | 1149.7 |
| Spectral/SpectralFilter.c5 | 1024 | output | pass |  | 40.07 | 94.7 |
| Spectral/SpectralGate.c5 | 1024 | input | pass | yes | 2.72 | 1149.2 |
| Spectral/SpectralGate.c5 | 1024 | output | pass | yes | 34.54 | 92.6 |
| Spectral/SpectralWarper.c5 | 1024 | input | memory_limit |  | 2.54 | 3135.2 |
| Spectral/SpectralWarper.c5 | 1024 | output | pass |  | 40.99 | 98.9 |
| Spectral/Transpose.c5 | 1024 | input | pass |  | 2.78 | 1150.7 |
| Spectral/Transpose.c5 | 1024 | output | pass |  | 64.22 | 100.3 |
| Spectral/Vectral.c5 | 1024 | input | pass | yes | 2.81 | 1151.5 |
| Spectral/Vectral.c5 | 1024 | output | pass | yes | 38.17 | 97.4 |
| Synthesis/AdditiveSynth.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/AdditiveSynth.c5 | 1024 | output | pass |  | 75.67 | 96.3 |
| Synthesis/BucketBrigadeDevice.c5 | 1024 | input | pass |  | 2.56 | 1156.0 |
| Synthesis/BucketBrigadeDevice.c5 | 1024 | output | pass |  | 20.18 | 114.6 |
| Synthesis/CrossFreqMod.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/CrossFreqMod.c5 | 1024 | output | pass |  | 10.05 | 105.8 |
| Synthesis/FrequencyModulation.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/FrequencyModulation.c5 | 1024 | output | pass |  | 9.65 | 105.2 |
| Synthesis/Pulsar.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/Pulsar.c5 | 1024 | output | pass |  | 8.37 | 95.9 |
| Synthesis/SpitSideBandSynth.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SpitSideBandSynth.c5 | 1024 | output | pass |  | 23.16 | 99.7 |
| Synthesis/StochGrains.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/StochGrains.c5 | 1024 | output | pass |  | 54.56 | 112.5 |
| Synthesis/StochGrains2.c5 | 1024 | input | pass |  | 2.54 | 1153.5 |
| Synthesis/StochGrains2.c5 | 1024 | output | pass |  | 100.29 | 101.8 |
| Synthesis/SuperSaw.c5 | 1024 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SuperSaw.c5 | 1024 | output | pass |  | 11.36 | 102.1 |
| Synthesis/WaveScanSynth.c5 | 1024 | input | pass |  | 2.39 | 1148.8 |
| Synthesis/WaveScanSynth.c5 | 1024 | output | pass |  | 15.27 | 110.8 |
| Time/4Delays.c5 | 1024 | input | pass |  | 2.46 | 1179.6 |
| Time/4Delays.c5 | 1024 | output | pass |  | 25.35 | 134.3 |
| Time/BeatMaker.c5 | 1024 | input | pass |  | 2.49 | 1152.8 |
| Time/BeatMaker.c5 | 1024 | output | pass |  | 16.15 | 104.4 |
| Time/DelayMod.c5 | 1024 | input | pass |  | 2.42 | 1177.2 |
| Time/DelayMod.c5 | 1024 | output | pass |  | 11.15 | 139.5 |
| Time/Granulator.c5 | 1024 | input | pass |  | 2.51 | 1148.8 |
| Time/Granulator.c5 | 1024 | output | pass |  | 49.75 | 99.3 |
| Time/Particle.c5 | 1024 | input | pass |  | 2.50 | 1149.9 |
| Time/Particle.c5 | 1024 | output | pass |  | 49.00 | 111.8 |
| Time/Pelletizer.c5 | 1024 | input | pass |  | 2.56 | 1152.4 |
| Time/Pelletizer.c5 | 1024 | output | pass |  | 44.47 | 110.5 |
| Time/Stutterer.c5 | 1024 | input | pass |  | 2.45 | 1149.9 |
| Time/Stutterer.c5 | 1024 | output | pass |  | 13.11 | 107.2 |
| Time/UltimateGrainer.c5 | 1024 | input | pass |  | 2.62 | 1156.1 |
| Time/UltimateGrainer.c5 | 1024 | output | pass |  | 117.20 | 119.3 |
| Dynamics/Degrade.c5 | 1152 | input | pass |  | 3.95 | 1284.5 |
| Dynamics/Degrade.c5 | 1152 | output | pass |  | 46.49 | 113.2 |
| Dynamics/Distortion.c5 | 1152 | input | pass |  | 3.05 | 1279.7 |
| Dynamics/Distortion.c5 | 1152 | output | pass |  | 33.27 | 105.6 |
| Dynamics/DynamicsProcessor.c5 | 1152 | input | pass | yes | 2.83 | 1280.5 |
| Dynamics/DynamicsProcessor.c5 | 1152 | output | pass | yes | 13.50 | 97.1 |
| Dynamics/FeedbackLooper.c5 | 1152 | input | pass |  | 2.73 | 1276.9 |
| Dynamics/FeedbackLooper.c5 | 1152 | output | pass |  | 21.29 | 101.4 |
| Dynamics/UpDistoRes.c5 | 1152 | input | pass |  | 2.87 | 1283.0 |
| Dynamics/UpDistoRes.c5 | 1152 | output | timeout |  | 120.02 | 77.5 |
| Dynamics/WaveShaper.c5 | 1152 | input | pass |  | 3.37 | 1289.0 |
| Dynamics/WaveShaper.c5 | 1152 | output | pass |  | 29.67 | 112.8 |
| Filters/AMFMFilter.c5 | 1152 | input | pass |  | 3.13 | 1289.4 |
| Filters/AMFMFilter.c5 | 1152 | output | pass |  | 27.11 | 107.0 |
| Filters/AutoModFilter.c5 | 1152 | input | pass |  | 2.86 | 1283.5 |
| Filters/AutoModFilter.c5 | 1152 | output | pass |  | 28.25 | 114.5 |
| Filters/Binaural.c5 | 1152 | input | pass |  | 5.70 | 1281.5 |
| Filters/Binaural.c5 | 1152 | output | timeout |  | 120.02 | 80.4 |
| Filters/BrickWall.c5 | 1152 | input | pass |  | 2.99 | 1278.2 |
| Filters/BrickWall.c5 | 1152 | output | pass |  | 107.50 | 109.1 |
| Filters/Flanger.c5 | 1152 | input | pass |  | 2.75 | 1279.0 |
| Filters/Flanger.c5 | 1152 | output | pass |  | 14.66 | 109.8 |
| Filters/MaskFilter.c5 | 1152 | input | pass |  | 2.76 | 1279.1 |
| Filters/MaskFilter.c5 | 1152 | output | pass |  | 48.78 | 98.7 |
| Filters/ParamEQ.c5 | 1152 | input | pass |  | 2.91 | 1276.2 |
| Filters/ParamEQ.c5 | 1152 | output | pass |  | 31.96 | 108.2 |
| Filters/Phaser.c5 | 1152 | input | pass |  | 2.87 | 1277.1 |
| Filters/Phaser.c5 | 1152 | output | pass |  | 61.49 | 96.1 |
| Filters/StateVar.c5 | 1152 | input | pass |  | 2.99 | 1276.6 |
| Filters/StateVar.c5 | 1152 | output | pass |  | 16.01 | 109.2 |
| Filters/StateVar2.c5 | 1152 | input | pass |  | 3.05 | 1277.0 |
| Filters/StateVar2.c5 | 1152 | output | pass |  | 19.05 | 111.2 |
| Filters/Vocoder.c5 | 1152 | input | pass |  | 2.95 | 1279.0 |
| Filters/Vocoder.c5 | 1152 | output | pass |  | 43.75 | 111.0 |
| Multiband/MultiBandBeatMaker.c5 | 1152 | input | pass |  | 2.99 | 1279.5 |
| Multiband/MultiBandBeatMaker.c5 | 1152 | output | pass |  | 24.66 | 108.2 |
| Multiband/MultiBandDelay.c5 | 1152 | input | pass |  | 3.05 | 1364.4 |
| Multiband/MultiBandDelay.c5 | 1152 | output | pass |  | 29.75 | 195.7 |
| Multiband/MultiBandDisto.c5 | 1152 | input | pass |  | 3.01 | 1280.6 |
| Multiband/MultiBandDisto.c5 | 1152 | output | pass |  | 33.35 | 106.2 |
| Multiband/MultiBandFreqShift.c5 | 1152 | input | pass |  | 2.82 | 1278.7 |
| Multiband/MultiBandFreqShift.c5 | 1152 | output | pass |  | 49.80 | 97.1 |
| Multiband/MultiBandGate.c5 | 1152 | input | pass | yes | 2.78 | 1277.8 |
| Multiband/MultiBandGate.c5 | 1152 | output | pass | yes | 33.42 | 103.8 |
| Multiband/MultiBandHarmonizer.c5 | 1152 | input | pass |  | 2.76 | 1280.9 |
| Multiband/MultiBandHarmonizer.c5 | 1152 | output | pass |  | 40.47 | 101.9 |
| Multiband/MultiBandReverb.c5 | 1152 | input | pass |  | 2.80 | 1280.4 |
| Multiband/MultiBandReverb.c5 | 1152 | output | pass |  | 59.72 | 108.9 |
| Pitch/ChordMaker.c5 | 1152 | input | pass |  | 2.74 | 1285.9 |
| Pitch/ChordMaker.c5 | 1152 | output | pass |  | 32.60 | 124.2 |
| Pitch/Chorus.c5 | 1152 | input | pass |  | 2.72 | 1278.2 |
| Pitch/Chorus.c5 | 1152 | output | pass |  | 19.56 | 112.0 |
| Pitch/FreqShift.c5 | 1152 | input | pass |  | 2.78 | 1288.0 |
| Pitch/FreqShift.c5 | 1152 | output | pass |  | 32.80 | 114.7 |
| Pitch/Harmonizer.c5 | 1152 | input | pass |  | 2.79 | 1290.5 |
| Pitch/Harmonizer.c5 | 1152 | output | pass |  | 21.03 | 114.5 |
| Pitch/LooperBank.c5 | 1152 | input | pass |  | 3.27 | 1275.8 |
| Pitch/LooperBank.c5 | 1152 | output | timeout |  | 120.04 | 77.6 |
| Pitch/LooperMod.c5 | 1152 | input | pass |  | 2.77 | 1277.6 |
| Pitch/LooperMod.c5 | 1152 | output | pass |  | 9.94 | 112.4 |
| Pitch/PitchLooper.c5 | 1152 | input | pass |  | 2.74 | 1278.2 |
| Pitch/PitchLooper.c5 | 1152 | output | pass |  | 10.45 | 110.1 |
| Pitch/RandomAccumulator.c5 | 1152 | input | pass |  | 2.74 | 1283.4 |
| Pitch/RandomAccumulator.c5 | 1152 | output | pass |  | 19.13 | 119.3 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1152 | input | pass |  | 2.82 | 1281.8 |
| Resonators&Verbs/ConvolutionReverb.c5 | 1152 | output | pass |  | 31.26 | 114.2 |
| Resonators&Verbs/Convolve.c5 | 1152 | input | pass |  | 2.98 | 1283.2 |
| Resonators&Verbs/Convolve.c5 | 1152 | output | timeout |  | 120.03 | 78.7 |
| Resonators&Verbs/DetunedResonators.c5 | 1152 | input | pass |  | 2.81 | 1289.2 |
| Resonators&Verbs/DetunedResonators.c5 | 1152 | output | pass |  | 72.76 | 124.0 |
| Resonators&Verbs/MatrixReverb.c5 | 1152 | input | pass |  | 2.81 | 1283.6 |
| Resonators&Verbs/MatrixReverb.c5 | 1152 | output | pass |  | 15.80 | 116.0 |
| Resonators&Verbs/Resonators.c5 | 1152 | input | pass |  | 2.88 | 1279.7 |
| Resonators&Verbs/Resonators.c5 | 1152 | output | pass |  | 54.11 | 112.9 |
| Resonators&Verbs/WGuideBank.c5 | 1152 | input | pass |  | 3.17 | 1291.0 |
| Resonators&Verbs/WGuideBank.c5 | 1152 | output | timeout |  | 120.03 | 90.4 |
| Spectral/AddResynth.c5 | 1152 | input | pass |  | 3.23 | 1276.8 |
| Spectral/AddResynth.c5 | 1152 | output | timeout |  | 120.01 | 81.1 |
| Spectral/BinModulator.c5 | 1152 | input | pass |  | 3.03 | 1279.7 |
| Spectral/BinModulator.c5 | 1152 | output | pass |  | 47.84 | 111.9 |
| Spectral/BinWarper.c5 | 1152 | input | memory_limit |  | 2.93 | 3239.5 |
| Spectral/BinWarper.c5 | 1152 | output | pass |  | 47.14 | 113.0 |
| Spectral/CrossSynth.c5 | 1152 | input | pass |  | 3.10 | 1282.8 |
| Spectral/CrossSynth.c5 | 1152 | output | pass |  | 67.21 | 107.1 |
| Spectral/CrossSynth2.c5 | 1152 | input | pass |  | 3.08 | 1283.0 |
| Spectral/CrossSynth2.c5 | 1152 | output | pass |  | 65.65 | 115.3 |
| Spectral/Morphing.c5 | 1152 | input | pass |  | 3.02 | 1283.3 |
| Spectral/Morphing.c5 | 1152 | output | pass |  | 61.50 | 112.1 |
| Spectral/Shifter.c5 | 1152 | input | pass |  | 3.05 | 1285.0 |
| Spectral/Shifter.c5 | 1152 | output | pass |  | 64.19 | 105.9 |
| Spectral/SpectralDelay.c5 | 1152 | input | pass |  | 3.02 | 1307.7 |
| Spectral/SpectralDelay.c5 | 1152 | output | pass |  | 51.13 | 129.1 |
| Spectral/SpectralFilter.c5 | 1152 | input | pass |  | 3.02 | 1284.6 |
| Spectral/SpectralFilter.c5 | 1152 | output | pass |  | 44.00 | 112.0 |
| Spectral/SpectralGate.c5 | 1152 | input | pass | yes | 2.99 | 1278.6 |
| Spectral/SpectralGate.c5 | 1152 | output | pass | yes | 41.39 | 94.0 |
| Spectral/SpectralWarper.c5 | 1152 | input | memory_limit |  | 2.93 | 3217.4 |
| Spectral/SpectralWarper.c5 | 1152 | output | pass |  | 47.02 | 115.1 |
| Spectral/Transpose.c5 | 1152 | input | pass |  | 3.14 | 1284.0 |
| Spectral/Transpose.c5 | 1152 | output | pass |  | 68.63 | 109.4 |
| Spectral/Vectral.c5 | 1152 | input | pass | yes | 3.04 | 1280.5 |
| Spectral/Vectral.c5 | 1152 | output | pass | yes | 43.28 | 95.5 |
| Synthesis/AdditiveSynth.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/AdditiveSynth.c5 | 1152 | output | pass |  | 82.54 | 91.8 |
| Synthesis/BucketBrigadeDevice.c5 | 1152 | input | pass |  | 2.70 | 1285.8 |
| Synthesis/BucketBrigadeDevice.c5 | 1152 | output | pass |  | 21.47 | 118.0 |
| Synthesis/CrossFreqMod.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/CrossFreqMod.c5 | 1152 | output | pass |  | 10.83 | 103.5 |
| Synthesis/FrequencyModulation.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/FrequencyModulation.c5 | 1152 | output | pass |  | 8.78 | 100.7 |
| Synthesis/Pulsar.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/Pulsar.c5 | 1152 | output | pass |  | 8.95 | 104.0 |
| Synthesis/SpitSideBandSynth.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SpitSideBandSynth.c5 | 1152 | output | pass |  | 25.65 | 106.1 |
| Synthesis/StochGrains.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/StochGrains.c5 | 1152 | output | pass |  | 64.11 | 116.6 |
| Synthesis/StochGrains2.c5 | 1152 | input | pass |  | 2.83 | 1283.5 |
| Synthesis/StochGrains2.c5 | 1152 | output | pass |  | 113.09 | 107.5 |
| Synthesis/SuperSaw.c5 | 1152 | input | not_applicable |  | 0.00 | 0.0 |
| Synthesis/SuperSaw.c5 | 1152 | output | pass |  | 12.61 | 97.1 |
| Synthesis/WaveScanSynth.c5 | 1152 | input | pass |  | 2.71 | 1277.7 |
| Synthesis/WaveScanSynth.c5 | 1152 | output | pass |  | 17.77 | 105.8 |
| Time/4Delays.c5 | 1152 | input | pass |  | 2.72 | 1306.4 |
| Time/4Delays.c5 | 1152 | output | pass |  | 26.60 | 129.0 |
| Time/BeatMaker.c5 | 1152 | input | pass |  | 2.68 | 1283.8 |
| Time/BeatMaker.c5 | 1152 | output | pass |  | 17.36 | 104.4 |
| Time/DelayMod.c5 | 1152 | input | pass |  | 2.70 | 1305.7 |
| Time/DelayMod.c5 | 1152 | output | pass |  | 10.95 | 132.5 |
| Time/Granulator.c5 | 1152 | input | pass |  | 2.72 | 1278.6 |
| Time/Granulator.c5 | 1152 | output | pass |  | 53.01 | 105.2 |
| Time/Particle.c5 | 1152 | input | pass |  | 2.78 | 1279.3 |
| Time/Particle.c5 | 1152 | output | pass |  | 45.51 | 113.6 |
| Time/Pelletizer.c5 | 1152 | input | pass |  | 2.77 | 1280.8 |
| Time/Pelletizer.c5 | 1152 | output | pass |  | 41.76 | 106.7 |
| Time/Stutterer.c5 | 1152 | input | pass |  | 2.73 | 1276.5 |
| Time/Stutterer.c5 | 1152 | output | pass |  | 9.99 | 105.8 |
| Time/UltimateGrainer.c5 | 1152 | input | pass |  | 2.92 | 1281.8 |
| Time/UltimateGrainer.c5 | 1152 | output | pass |  | 119.58 | 108.2 |

Pass describes the memory/file-integrity checks, not proof of audible intended DSP. Extended spectral input probes were silent; their RAM figures still include full input/analysis allocation. See `offline_memory_findings.md` for this unresolved warmup/duration limitation and separate larger-budget retries.

Reproduce: `cecillia/bin/python tests/check_offline_memory.py`, then `cecillia/bin/python tests/summarize_offline_memory.py`. Use `--resume` to rerun only cases invalidated by source edits; `--retry-status timeout` also retries completed timeout records. Raw attempt history remains in `offline_memory.jsonl`.
