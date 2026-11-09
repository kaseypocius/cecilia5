# All-module multichannel and codec audit

69/69 cases passed; 0 failed across 69 modules.

Every case compares float-WAV reference master/tap audio against the requested output codec/layout, including exact frame count, rate, channels, container and bit depth.
Input codecs are roundtripped with distinct per-channel signals. Comparisons preserve channel/sample positions and use PCM-aware tolerances. This is not an oracle for the spatial design of each processor.
Gate diagnostics use -90 dB; spectral buffers use a 0.125-second source. Other settings are init. Silent cases verify metadata/codecs only; they cannot establish DSP correctness.

| Scenario | Input | Output | Rate | Mode |
| --- | --- | --- | --- | --- |
| stereo_eight_pcm32 | 2ch wav 32 bit float | 8ch wav 32 bit int | 48000 | single |

| Module | Scenario | Result | Notes |
| --- | --- | --- | --- |
| Dynamics/Degrade.c5 | stereo_eight_pcm32 | pass |  |
| Dynamics/Distortion.c5 | stereo_eight_pcm32 | pass |  |
| Dynamics/DynamicsProcessor.c5 | stereo_eight_pcm32 | pass |  |
| Dynamics/FeedbackLooper.c5 | stereo_eight_pcm32 | pass |  |
| Dynamics/UpDistoRes.c5 | stereo_eight_pcm32 | pass |  |
| Dynamics/WaveShaper.c5 | stereo_eight_pcm32 | pass |  |
| Filters/AMFMFilter.c5 | stereo_eight_pcm32 | pass |  |
| Filters/AutoModFilter.c5 | stereo_eight_pcm32 | pass |  |
| Filters/Binaural.c5 | stereo_eight_pcm32 | pass |  |
| Filters/BrickWall.c5 | stereo_eight_pcm32 | pass |  |
| Filters/Flanger.c5 | stereo_eight_pcm32 | pass |  |
| Filters/MaskFilter.c5 | stereo_eight_pcm32 | pass |  |
| Filters/ParamEQ.c5 | stereo_eight_pcm32 | pass |  |
| Filters/Phaser.c5 | stereo_eight_pcm32 | pass |  |
| Filters/StateVar.c5 | stereo_eight_pcm32 | pass |  |
| Filters/StateVar2.c5 | stereo_eight_pcm32 | pass |  |
| Filters/Vocoder.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandBeatMaker.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandDelay.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandDisto.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandFreqShift.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandGate.c5 | stereo_eight_pcm32 | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | stereo_eight_pcm32 | pass |  |
| Multiband/MultiBandReverb.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/ChordMaker.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/Chorus.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/FreqShift.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/Harmonizer.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/LooperBank.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/LooperMod.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/PitchLooper.c5 | stereo_eight_pcm32 | pass |  |
| Pitch/RandomAccumulator.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/Convolve.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/Resonators.c5 | stereo_eight_pcm32 | pass |  |
| Resonators&Verbs/WGuideBank.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/AddResynth.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/BinModulator.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/BinWarper.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/CrossSynth.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/CrossSynth2.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/Morphing.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/Shifter.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/SpectralDelay.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/SpectralFilter.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/SpectralGate.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/SpectralWarper.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/Transpose.c5 | stereo_eight_pcm32 | pass |  |
| Spectral/Vectral.c5 | stereo_eight_pcm32 | pass |  |
| Synthesis/AdditiveSynth.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | stereo_eight_pcm32 | pass |  |
| Synthesis/CrossFreqMod.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | stereo_eight_pcm32 | pass |  |
| Synthesis/SuperSaw.c5 | stereo_eight_pcm32 | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | stereo_eight_pcm32 | pass |  |
| Time/4Delays.c5 | stereo_eight_pcm32 | pass |  |
| Time/BeatMaker.c5 | stereo_eight_pcm32 | pass |  |
| Time/DelayMod.c5 | stereo_eight_pcm32 | pass |  |
| Time/Granulator.c5 | stereo_eight_pcm32 | pass |  |
| Time/Particle.c5 | stereo_eight_pcm32 | pass |  |
| Time/Pelletizer.c5 | stereo_eight_pcm32 | pass |  |
| Time/Stutterer.c5 | stereo_eight_pcm32 | pass |  |
| Time/UltimateGrainer.c5 | stereo_eight_pcm32 | pass |  |
