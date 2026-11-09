# Shipped module offline audit

0/69 passed all checks; 65 failed; 4 inconclusive (silent). 192.4 seconds.

44100 Hz, 4 channels, 176417 frames, init settings, absolute tolerance 2e-06.

Checks: exact lengths/channels and finite audio for masters/taps/stems; single/chunk sample equality; disjoint-branch sum equality.
Channel identity is checked by single/chunk equality; this does not establish intended spatial behavior for every effect.
This covers init settings, not every preset or routing topology. Reproducibility failures are reported rather than ignored.

| Module | Result | Details |
| --- | --- | --- |
| Dynamics/Degrade.c5 | fail | parallel_routing: max 0.031866, seam 1.04308e-07 |
| Dynamics/Distortion.c5 | fail | parallel_routing: max 0.0849822, seam 4.47035e-08 |
| Dynamics/DynamicsProcessor.c5 | fail | parallel_routing: max 0.0419989, seam 1.49012e-07 |
| Dynamics/FeedbackLooper.c5 | fail | parallel_routing: max 0.0214108, seam 4.47035e-08 |
| Dynamics/UpDistoRes.c5 | fail | parallel_routing: max 0.174722, seam 1.04308e-07 |
| Dynamics/WaveShaper.c5 | fail | parallel_routing: max 0.214097, seam 1.19209e-07 |
| Filters/AMFMFilter.c5 | fail | parallel_routing: max 0.00847749, seam 1.11759e-08 |
| Filters/AutoModFilter.c5 | fail | parallel_routing: max 0.0542124, seam 2.98023e-08 |
| Filters/Binaural.c5 | fail | parallel_routing: max 0.0403389, seam 1.49012e-07 |
| Filters/BrickWall.c5 | fail | parallel_routing: max 0.0412139, seam 2.6077e-08 |
| Filters/Flanger.c5 | fail | parallel_routing: max 0.0430915, seam 7.45058e-08 |
| Filters/MaskFilter.c5 | fail | parallel_routing: max 0.0104081, seam 9.31323e-09 |
| Filters/ParamEQ.c5 | fail | parallel_routing: max 0.0262874, seam 8.9407e-08 |
| Filters/Phaser.c5 | fail | parallel_routing: max 0.0248058, seam 7.45058e-08 |
| Filters/StateVar.c5 | fail | parallel_routing: max 0.00456977, seam 4.65661e-09 |
| Filters/StateVar2.c5 | fail | parallel_routing: max 0.0320968, seam 1.49012e-07 |
| Filters/Vocoder.c5 | fail | parallel_routing: max 0.0552977, seam 2.98023e-08 |
| Multiband/MultiBandBeatMaker.c5 | fail | parallel_routing: max 0.0263701, seam 0.0242186 |
| Multiband/MultiBandDelay.c5 | fail | parallel_routing: max 0.030899, seam 1.86265e-08 |
| Multiband/MultiBandDisto.c5 | fail | parallel_routing: max 0.0487833, seam 2.98023e-08 |
| Multiband/MultiBandFreqShift.c5 | fail | parallel_routing: max 0.00803966, seam 1.49012e-08 |
| Multiband/MultiBandGate.c5 | fail | parallel_routing: max 0.0351794, seam 1.86265e-08 |
| Multiband/MultiBandHarmonizer.c5 | fail | parallel_routing: max 0.030343, seam 2.98023e-08 |
| Multiband/MultiBandReverb.c5 | fail | parallel_routing: max 0.02032, seam 0.0116429 |
| Pitch/ChordMaker.c5 | fail | parallel_routing: max 0.018812, seam 3.72529e-08 |
| Pitch/Chorus.c5 | fail | parallel_routing: max 0.0460741, seam 0.000349706 |
| Pitch/FreqShift.c5 | fail | parallel_routing: max 0.0513255, seam 8.9407e-08 |
| Pitch/Harmonizer.c5 | fail | parallel_routing: max 0.018622, seam 1.86265e-08 |
| Pitch/LooperBank.c5 | fail | parallel_routing: max 0.00406944, seam 2.32831e-09 |
| Pitch/LooperMod.c5 | fail | parallel_routing: max 0.018682, seam 0.0149169 |
| Pitch/PitchLooper.c5 | fail | parallel_routing: max 0.0283232, seam 3.72529e-08 |
| Pitch/RandomAccumulator.c5 | fail | chunks_master: max 0.0413863, seam 0.00756599; chunks_a: max 0.0825765, seam 0.0150961; single_reproducibility: max 0.0413863, seam 0.00756599; parallel_routing: max 0.0241154, seam 0.00534915 |
| Resonators&Verbs/ConvolutionReverb.c5 | fail | parallel_routing: max 0.161634, seam 1.66893e-06 |
| Resonators&Verbs/Convolve.c5 | fail | parallel_routing: max 0.0885342, seam 4.47035e-08 |
| Resonators&Verbs/DetunedResonators.c5 | fail | parallel_routing: max 0.0297586, seam 1.86265e-08 |
| Resonators&Verbs/MatrixReverb.c5 | fail | parallel_routing: max 0.0517919, seam 1.19209e-07 |
| Resonators&Verbs/Resonators.c5 | fail | parallel_routing: max 0.0135724, seam 1.49012e-08 |
| Resonators&Verbs/WGuideBank.c5 | fail | chunks_master: max 0.0824853, seam 0.0556427; chunks_a: max 0.16458, seam 0.111022; single_reproducibility: max 0.101593, seam 0.0580929; parallel_routing: max 0.15608, seam 0.0395566 |
| Spectral/AddResynth.c5 | fail | parallel_routing: max 0.0147321, seam 9.31323e-09 |
| Spectral/BinModulator.c5 | fail | parallel_routing: max 0.00889781, seam 2.6077e-08 |
| Spectral/BinWarper.c5 | inconclusive | silent init output; equality is inconclusive |
| Spectral/CrossSynth.c5 | fail | parallel_routing: max 0.0127008, seam 9.31323e-09 |
| Spectral/CrossSynth2.c5 | fail | parallel_routing: max 0.0440922, seam 1.04308e-07 |
| Spectral/Morphing.c5 | fail | parallel_routing: max 0.0223195, seam 7.45058e-08 |
| Spectral/Shifter.c5 | fail | parallel_routing: max 0.0143764, seam 2.98023e-08 |
| Spectral/SpectralDelay.c5 | fail | parallel_routing: max 0.0511609, seam 2.98023e-08 |
| Spectral/SpectralFilter.c5 | fail | parallel_routing: max 0.0184028, seam 2.23517e-08 |
| Spectral/SpectralGate.c5 | inconclusive | silent init output; equality is inconclusive |
| Spectral/SpectralWarper.c5 | inconclusive | silent init output; equality is inconclusive |
| Spectral/Transpose.c5 | fail | parallel_routing: max 0.0187147, seam 4.47035e-08 |
| Spectral/Vectral.c5 | inconclusive | silent init output; equality is inconclusive |
| Synthesis/AdditiveSynth.c5 | fail | parallel_routing: max 0.228698, seam 0.138724 |
| Synthesis/BucketBrigadeDevice.c5 | fail | parallel_routing: max 0.00600443, seam 0.00119507 |
| Synthesis/CrossFreqMod.c5 | fail | parallel_routing: max 0.0732499, seam 0.0336905 |
| Synthesis/FrequencyModulation.c5 | fail | parallel_routing: max 0.139051, seam 0.0122178 |
| Synthesis/Pulsar.c5 | fail | parallel_routing: max 0.131624, seam 0.120902 |
| Synthesis/SpitSideBandSynth.c5 | fail | parallel_routing: max 0.0711126, seam 0.0322129 |
| Synthesis/StochGrains.c5 | fail | chunks_master: max 0.185812, seam 0.0900065; chunks_a: max 0.370745, seam 0.179587; single_reproducibility: max 0.185812, seam 0.0900065; parallel_routing: max 0.193796, seam 0.0920262 |
| Synthesis/StochGrains2.c5 | fail | parallel_routing: max 0.0361727, seam 0.01936 |
| Synthesis/SuperSaw.c5 | fail | parallel_routing: max 0.0651453, seam 0.0341135 |
| Synthesis/WaveScanSynth.c5 | fail | parallel_routing: max 0.0301212, seam 1.49012e-08 |
| Time/4Delays.c5 | fail | parallel_routing: max 0.0575265, seam 0.0283005 |
| Time/BeatMaker.c5 | fail | chunks_master: max 0.039671, seam 0.0377045; chunks_a: max 0.0791542, seam 0.0752305; single_reproducibility: max 0.039671, seam 0.0377045; parallel_routing: max 0.0654556, seam 0.0303074 |
| Time/DelayMod.c5 | fail | parallel_routing: max 0.0248864, seam 2.6077e-08 |
| Time/Granulator.c5 | fail | parallel_routing: max 0.0438705, seam 0.040909 |
| Time/Particle.c5 | fail | parallel_routing: max 0.0862949, seam 0.0692817 |
| Time/Pelletizer.c5 | fail | parallel_routing: max 0.0264177, seam 0.0129471 |
| Time/Stutterer.c5 | fail | chunks_master: max 0.0359961, seam 0.0143949; chunks_a: max 0.0718218, seam 0.0287216; single_reproducibility: max 0.0284066, seam 0.0278964; parallel_routing: max 0.0657291, seam 0.0657291 |
| Time/UltimateGrainer.c5 | fail | parallel_routing: max 0.0884663, seam 0.0593684 |
