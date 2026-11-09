# Shipped module offline audit

69/69 passed all checks; 0 failed; 0 inconclusive (silent). 259.9 seconds. Four previously silent modules also receive audible diagnostic fixtures.

44100 Hz, 4 channels, 176417 frames, init settings, absolute tolerance 2e-06.

Checks: exact lengths/channels and finite audio for masters/taps/stems; single/chunk sample equality; disjoint-branch sum equality.
Channel identity is checked by single/chunk equality; this does not establish intended spatial behavior for every effect.
This covers init settings, not every preset or routing topology. Reproducibility failures are reported rather than ignored.

| Module | Result | Details |
| --- | --- | --- |
| Dynamics/Degrade.c5 | pass |  |
| Dynamics/Distortion.c5 | pass |  |
| Dynamics/DynamicsProcessor.c5 | pass |  |
| Dynamics/FeedbackLooper.c5 | pass |  |
| Dynamics/UpDistoRes.c5 | pass |  |
| Dynamics/WaveShaper.c5 | pass |  |
| Filters/AMFMFilter.c5 | pass |  |
| Filters/AutoModFilter.c5 | pass |  |
| Filters/Binaural.c5 | pass |  |
| Filters/BrickWall.c5 | pass |  |
| Filters/Flanger.c5 | pass |  |
| Filters/MaskFilter.c5 | pass |  |
| Filters/ParamEQ.c5 | pass |  |
| Filters/Phaser.c5 | pass |  |
| Filters/StateVar.c5 | pass |  |
| Filters/StateVar2.c5 | pass |  |
| Filters/Vocoder.c5 | pass |  |
| Multiband/MultiBandBeatMaker.c5 | pass |  |
| Multiband/MultiBandDelay.c5 | pass |  |
| Multiband/MultiBandDisto.c5 | pass |  |
| Multiband/MultiBandFreqShift.c5 | pass |  |
| Multiband/MultiBandGate.c5 | pass |  |
| Multiband/MultiBandHarmonizer.c5 | pass |  |
| Multiband/MultiBandReverb.c5 | pass |  |
| Pitch/ChordMaker.c5 | pass |  |
| Pitch/Chorus.c5 | pass |  |
| Pitch/FreqShift.c5 | pass |  |
| Pitch/Harmonizer.c5 | pass |  |
| Pitch/LooperBank.c5 | pass |  |
| Pitch/LooperMod.c5 | pass |  |
| Pitch/PitchLooper.c5 | pass |  |
| Pitch/RandomAccumulator.c5 | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | pass |  |
| Resonators&Verbs/Convolve.c5 | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | pass |  |
| Resonators&Verbs/Resonators.c5 | pass |  |
| Resonators&Verbs/WGuideBank.c5 | pass |  |
| Spectral/AddResynth.c5 | pass |  |
| Spectral/BinModulator.c5 | pass |  |
| Spectral/BinWarper.c5 | pass_with_diagnostic | audible diagnostic: pass; 0.5-second source, 3x amplitude; original init fixture silent; see audible diagnostic |
| Spectral/CrossSynth.c5 | pass |  |
| Spectral/CrossSynth2.c5 | pass |  |
| Spectral/Morphing.c5 | pass |  |
| Spectral/Shifter.c5 | pass |  |
| Spectral/SpectralDelay.c5 | pass |  |
| Spectral/SpectralFilter.c5 | pass |  |
| Spectral/SpectralGate.c5 | pass_with_diagnostic | audible diagnostic: pass; 0.5-second source, 3x amplitude, gate threshold -90 dB; original init fixture silent; see audible diagnostic |
| Spectral/SpectralWarper.c5 | pass_with_diagnostic | audible diagnostic: pass; 0.5-second source, 3x amplitude; original init fixture silent; see audible diagnostic |
| Spectral/Transpose.c5 | pass |  |
| Spectral/Vectral.c5 | pass_with_diagnostic | audible diagnostic: pass; 0.5-second source, 3x amplitude, gate threshold -90 dB; original init fixture silent; see audible diagnostic |
| Synthesis/AdditiveSynth.c5 | pass |  |
| Synthesis/BucketBrigadeDevice.c5 | pass |  |
| Synthesis/CrossFreqMod.c5 | pass |  |
| Synthesis/FrequencyModulation.c5 | pass |  |
| Synthesis/Pulsar.c5 | pass |  |
| Synthesis/SpitSideBandSynth.c5 | pass |  |
| Synthesis/StochGrains.c5 | pass |  |
| Synthesis/StochGrains2.c5 | pass |  |
| Synthesis/SuperSaw.c5 | pass |  |
| Synthesis/WaveScanSynth.c5 | pass |  |
| Time/4Delays.c5 | pass |  |
| Time/BeatMaker.c5 | pass |  |
| Time/DelayMod.c5 | pass |  |
| Time/Granulator.c5 | pass |  |
| Time/Particle.c5 | pass |  |
| Time/Pelletizer.c5 | pass |  |
| Time/Stutterer.c5 | pass |  |
| Time/UltimateGrainer.c5 | pass |  |
