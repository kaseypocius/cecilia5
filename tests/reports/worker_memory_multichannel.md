# Worker memory: large multichannel/high-rate audit

Input: 64 MiB float32, 50 channels, 48 kHz. Output: 50 channels at 96/192 kHz, 2.2 seconds.
Two identical queue entries per case; four requested workers; 8192 MiB shared budget.

Every completed case checks both outputs for exact metadata, all-sample finiteness, repeat equality (absolute tolerance 0.000002), and coordinator cleanup. Silent init output is recorded and does not establish audible DSP correctness.

| Module | kHz | Result | Active workers | Peak pool MiB | Seconds | Silent |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| Dynamics/Degrade.c5 | 96 | pass | 2 | 472.3 | 2.596 | False |
| Dynamics/Degrade.c5 | 192 | pass | 2 | 491.9 | 3.32 | False |
| Dynamics/Distortion.c5 | 96 | pass | 2 | 476.9 | 2.763 | False |
| Dynamics/Distortion.c5 | 192 | pass | 2 | 485.3 | 3.61 | False |
| Dynamics/DynamicsProcessor.c5 | 96 | pass | 2 | 437.7 | 2.265 | True |
| Dynamics/DynamicsProcessor.c5 | 192 | pass | 2 | 440.1 | 2.779 | True |
| Dynamics/FeedbackLooper.c5 | 96 | pass | 2 | 465.3 | 2.329 | False |
| Dynamics/FeedbackLooper.c5 | 192 | pass | 2 | 469.0 | 2.789 | False |
| Dynamics/UpDistoRes.c5 | 96 | pass | 2 | 459.3 | 6.505 | False |
| Dynamics/UpDistoRes.c5 | 192 | pass | 2 | 501.3 | 15.491 | False |
| Dynamics/WaveShaper.c5 | 96 | pass | 2 | 485.8 | 3.031 | False |
| Dynamics/WaveShaper.c5 | 192 | pass | 2 | 477.5 | 4.124 | False |
| Filters/AMFMFilter.c5 | 96 | pass | 2 | 485.3 | 3.599 | False |
| Filters/AMFMFilter.c5 | 192 | pass | 2 | 491.8 | 3.542 | False |
| Filters/AutoModFilter.c5 | 96 | pass | 2 | 481.8 | 3.318 | False |
| Filters/AutoModFilter.c5 | 192 | pass | 2 | 502.7 | 3.618 | False |
| Filters/Binaural.c5 | 96 | timeout | 2 | 435.4 | 60.044 |  |
| Filters/Binaural.c5 | 192 | timeout | 2 | 436.6 | 60.041 |  |
| Filters/BrickWall.c5 | 96 | pass | 2 | 468.9 | 5.437 | False |
| Filters/BrickWall.c5 | 192 | pass | 2 | 476.5 | 9.033 | False |
| Filters/Flanger.c5 | 96 | pass | 2 | 438.6 | 2.194 | False |
| Filters/Flanger.c5 | 192 | pass | 2 | 441.6 | 2.703 | False |
| Filters/MaskFilter.c5 | 96 | pass | 2 | 475.4 | 3.487 | False |
| Filters/MaskFilter.c5 | 192 | pass | 2 | 466.4 | 5.297 | False |
| Filters/ParamEQ.c5 | 96 | pass | 2 | 467.6 | 2.763 | False |
| Filters/ParamEQ.c5 | 192 | pass | 2 | 488.5 | 4.086 | False |
| Filters/Phaser.c5 | 96 | pass | 2 | 472.5 | 3.94 | False |
| Filters/Phaser.c5 | 192 | pass | 2 | 475.7 | 7.263 | False |
| Filters/StateVar.c5 | 96 | pass | 2 | 467.9 | 2.408 | False |
| Filters/StateVar.c5 | 192 | pass | 2 | 477.1 | 2.923 | False |
| Filters/StateVar2.c5 | 96 | pass | 2 | 485.1 | 2.913 | False |
| Filters/StateVar2.c5 | 192 | pass | 2 | 479.6 | 3.221 | False |
| Filters/Vocoder.c5 | 96 | pass | 2 | 564.1 | 4.895 | False |
| Filters/Vocoder.c5 | 192 | pass | 2 | 608.1 | 6.703 | False |
| Multiband/MultiBandBeatMaker.c5 | 96 | pass | 2 | 429.8 | 2.478 | False |
| Multiband/MultiBandBeatMaker.c5 | 192 | pass | 2 | 434.7 | 3.202 | False |
| Multiband/MultiBandDelay.c5 | 96 | pass | 2 | 552.5 | 2.779 | False |
| Multiband/MultiBandDelay.c5 | 192 | pass | 2 | 652.9 | 3.642 | False |
| Multiband/MultiBandDisto.c5 | 96 | pass | 2 | 468.6 | 2.805 | False |
| Multiband/MultiBandDisto.c5 | 192 | pass | 2 | 457.4 | 3.871 | False |
| Multiband/MultiBandFreqShift.c5 | 96 | pass | 2 | 463.7 | 3.431 | False |
| Multiband/MultiBandFreqShift.c5 | 192 | pass | 2 | 468.3 | 5.238 | False |
| Multiband/MultiBandGate.c5 | 96 | pass | 2 | 470.0 | 2.854 | True |
| Multiband/MultiBandGate.c5 | 192 | pass | 2 | 474.2 | 3.943 | True |
| Multiband/MultiBandHarmonizer.c5 | 96 | pass | 2 | 612.0 | 3.107 | False |
| Multiband/MultiBandHarmonizer.c5 | 192 | pass | 2 | 773.0 | 5.458 | False |
| Multiband/MultiBandReverb.c5 | 96 | pass | 2 | 561.6 | 4.167 | False |
| Multiband/MultiBandReverb.c5 | 192 | pass | 2 | 665.9 | 6.347 | False |
| Pitch/ChordMaker.c5 | 96 | pass | 2 | 706.6 | 3.091 | False |
| Pitch/ChordMaker.c5 | 192 | pass | 2 | 914.0 | 4.167 | False |
| Pitch/Chorus.c5 | 96 | pass | 2 | 482.6 | 2.493 | False |
| Pitch/Chorus.c5 | 192 | pass | 2 | 484.8 | 3.295 | False |
| Pitch/FreqShift.c5 | 96 | pass | 2 | 540.5 | 2.987 | False |
| Pitch/FreqShift.c5 | 192 | pass | 2 | 628.4 | 4.096 | False |
| Pitch/Harmonizer.c5 | 96 | pass | 2 | 572.8 | 2.476 | False |
| Pitch/Harmonizer.c5 | 192 | pass | 2 | 695.1 | 3.269 | False |
| Pitch/LooperBank.c5 | 96 | pass | 2 | 466.6 | 15.917 | False |
| Pitch/LooperBank.c5 | 192 | pass | 2 | 479.9 | 30.237 | False |
| Pitch/LooperMod.c5 | 96 | pass | 2 | 469.1 | 2.429 | False |
| Pitch/LooperMod.c5 | 192 | pass | 2 | 459.8 | 2.44 | False |
| Pitch/PitchLooper.c5 | 96 | pass | 2 | 439.6 | 2.267 | False |
| Pitch/PitchLooper.c5 | 192 | pass | 2 | 433.6 | 2.498 | False |
| Pitch/RandomAccumulator.c5 | 96 | pass | 2 | 585.0 | 2.625 | False |
| Pitch/RandomAccumulator.c5 | 192 | pass | 2 | 733.5 | 3.261 | False |
| Resonators&Verbs/ConvolutionReverb.c5 | 96 | pass | 2 | 1079.5 | 11.034 | False |
| Resonators&Verbs/ConvolutionReverb.c5 | 192 | pass | 2 | 1091.4 | 18.024 | False |
| Resonators&Verbs/Convolve.c5 | 96 | pass | 2 | 569.0 | 10.715 | False |
| Resonators&Verbs/Convolve.c5 | 192 | pass | 2 | 566.0 | 18.022 | False |
| Resonators&Verbs/DetunedResonators.c5 | 96 | pass | 2 | 784.8 | 4.367 | False |
| Resonators&Verbs/DetunedResonators.c5 | 192 | pass | 2 | 1083.7 | 6.741 | False |
| Resonators&Verbs/MatrixReverb.c5 | 96 | pass | 2 | 472.7 | 2.066 | False |
| Resonators&Verbs/MatrixReverb.c5 | 192 | pass | 2 | 495.6 | 2.414 | False |
| Resonators&Verbs/Resonators.c5 | 96 | pass | 2 | 503.9 | 3.598 | False |
| Resonators&Verbs/Resonators.c5 | 192 | pass | 2 | 510.9 | 5.387 | False |
| Resonators&Verbs/WGuideBank.c5 | 96 | timeout | 2 | 2444.7 | 60.074 |  |
| Resonators&Verbs/WGuideBank.c5 | 192 | timeout | 2 | 3681.2 | 60.075 |  |
| Spectral/AddResynth.c5 | 96 | pass | 2 | 502.1 | 10.267 | False |
| Spectral/AddResynth.c5 | 192 | pass | 2 | 498.9 | 20.698 | False |
| Spectral/BinModulator.c5 | 96 | pass | 2 | 493.1 | 4.446 | False |
| Spectral/BinModulator.c5 | 192 | pass | 2 | 520.7 | 5.499 | False |
| Spectral/BinWarper.c5 | 96 | pass | 2 | 1455.2 | 7.33 | True |
| Spectral/BinWarper.c5 | 192 | pass | 2 | 2273.0 | 13.5 | True |
| Spectral/CrossSynth.c5 | 96 | pass | 2 | 573.3 | 5.687 | False |
| Spectral/CrossSynth.c5 | 192 | pass | 2 | 583.9 | 8.058 | False |
| Spectral/CrossSynth2.c5 | 96 | pass | 2 | 589.7 | 5.827 | False |
| Spectral/CrossSynth2.c5 | 192 | pass | 2 | 633.4 | 7.622 | False |
| Spectral/Morphing.c5 | 96 | pass | 2 | 600.7 | 5.331 | False |
| Spectral/Morphing.c5 | 192 | pass | 2 | 637.7 | 7.199 | False |
| Spectral/Shifter.c5 | 96 | pass | 2 | 467.5 | 3.915 | False |
| Spectral/Shifter.c5 | 192 | pass | 2 | 507.8 | 5.932 | False |
| Spectral/SpectralDelay.c5 | 96 | pass | 2 | 1230.0 | 4.044 | False |
| Spectral/SpectralDelay.c5 | 192 | pass | 2 | 2002.5 | 6.405 | False |
| Spectral/SpectralFilter.c5 | 96 | pass | 2 | 505.2 | 3.412 | False |
| Spectral/SpectralFilter.c5 | 192 | pass | 2 | 530.2 | 4.759 | False |
| Spectral/SpectralGate.c5 | 96 | pass | 2 | 451.8 | 3.252 | True |
| Spectral/SpectralGate.c5 | 192 | pass | 2 | 474.2 | 4.731 | True |
| Spectral/SpectralWarper.c5 | 96 | pass | 2 | 1483.0 | 3.19 | True |
| Spectral/SpectralWarper.c5 | 192 | pass | 2 | 2518.3 | 4.727 | True |
| Spectral/Transpose.c5 | 96 | pass | 2 | 478.2 | 5.727 | False |
| Spectral/Transpose.c5 | 192 | pass | 2 | 508.9 | 6.824 | False |
| Spectral/Vectral.c5 | 96 | pass | 2 | 490.9 | 3.615 | True |
| Spectral/Vectral.c5 | 192 | pass | 2 | 557.0 | 4.989 | True |
| Synthesis/AdditiveSynth.c5 | 96 | pass | 2 | 200.1 | 3.434 | False |
| Synthesis/AdditiveSynth.c5 | 192 | pass | 2 | 201.4 | 6.327 | False |
| Synthesis/BucketBrigadeDevice.c5 | 96 | pass | 2 | 574.8 | 2.511 | False |
| Synthesis/BucketBrigadeDevice.c5 | 192 | pass | 2 | 723.5 | 3.216 | False |
| Synthesis/CrossFreqMod.c5 | 96 | pass | 2 | 203.9 | 0.787 | False |
| Synthesis/CrossFreqMod.c5 | 192 | pass | 2 | 196.2 | 1.109 | False |
| Synthesis/FrequencyModulation.c5 | 96 | pass | 2 | 196.7 | 0.804 | False |
| Synthesis/FrequencyModulation.c5 | 192 | pass | 2 | 191.6 | 0.958 | False |
| Synthesis/Pulsar.c5 | 96 | pass | 2 | 199.5 | 0.703 | False |
| Synthesis/Pulsar.c5 | 192 | pass | 2 | 200.1 | 0.996 | False |
| Synthesis/SpitSideBandSynth.c5 | 96 | pass | 2 | 194.0 | 1.188 | False |
| Synthesis/SpitSideBandSynth.c5 | 192 | pass | 2 | 207.3 | 1.966 | False |
| Synthesis/StochGrains.c5 | 96 | pass | 2 | 241.4 | 1.186 | False |
| Synthesis/StochGrains.c5 | 192 | pass | 2 | 226.9 | 2.937 | False |
| Synthesis/StochGrains2.c5 | 96 | pass | 2 | 594.6 | 13.008 | False |
| Synthesis/StochGrains2.c5 | 192 | pass | 2 | 599.8 | 22.856 | False |
| Synthesis/SuperSaw.c5 | 96 | pass | 2 | 193.6 | 0.884 | False |
| Synthesis/SuperSaw.c5 | 192 | pass | 2 | 216.7 | 1.315 | False |
| Synthesis/WaveScanSynth.c5 | 96 | pass | 2 | 455.7 | 3.243 | False |
| Synthesis/WaveScanSynth.c5 | 192 | pass | 2 | 457.3 | 3.087 | False |
| Time/4Delays.c5 | 96 | pass | 2 | 1155.8 | 2.801 | False |
| Time/4Delays.c5 | 192 | pass | 2 | 1906.7 | 3.697 | False |
| Time/BeatMaker.c5 | 96 | pass | 2 | 429.9 | 2.106 | False |
| Time/BeatMaker.c5 | 192 | pass | 2 | 428.2 | 2.535 | False |
| Time/DelayMod.c5 | 96 | pass | 2 | 1190.0 | 2.173 | False |
| Time/DelayMod.c5 | 192 | pass | 2 | 1932.3 | 2.544 | False |
| Time/Granulator.c5 | 96 | pass | 2 | 464.9 | 3.607 | False |
| Time/Granulator.c5 | 192 | pass | 2 | 459.9 | 5.259 | False |
| Time/Particle.c5 | 96 | pass | 2 | 479.6 | 3.739 | False |
| Time/Particle.c5 | 192 | pass | 2 | 498.3 | 5.905 | False |
| Time/Pelletizer.c5 | 96 | pass | 2 | 462.9 | 3.627 | False |
| Time/Pelletizer.c5 | 192 | pass | 2 | 463.4 | 4.48 | False |
| Time/Stutterer.c5 | 96 | pass | 2 | 424.5 | 2.08 | False |
| Time/Stutterer.c5 | 192 | pass | 2 | 417.9 | 2.527 | False |
| Time/UltimateGrainer.c5 | 96 | pass | 2 | 492.5 | 7.005 | False |
| Time/UltimateGrainer.c5 | 192 | pass | 2 | 520.9 | 12.622 | False |

Result: 134/138 cases passed. Silent completed cases: 12.

Peak RSS samples sum all live native workers at 25 ms intervals; short peaks can be missed. This audit covers init settings and these layouts, rather than arbitrary presets or sustained leaks.
