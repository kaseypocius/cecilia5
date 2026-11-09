# All-module multichannel and codec audit

549/552 cases passed; 3 failed across 69 modules.

Every case compares float-WAV reference master/tap audio against the requested output codec/layout, including exact frame count, rate, channels, container and bit depth.
Input codecs are roundtripped with distinct per-channel signals. Comparisons preserve channel/sample positions and use PCM-aware tolerances. This is not an oracle for the spatial design of each processor.
Gate diagnostics use -90 dB; spectral buffers use a 0.125-second source. Other settings are init. Silent cases verify metadata/codecs only; they cannot establish DSP correctness.

| Scenario | Input | Output | Rate | Mode |
| --- | --- | --- | --- | --- |
| mono_stereo_wav | 1ch wav 16 bit int | 2ch wav 24 bit int | 44100 | single |
| stereo_mono_flac | 2ch aif 24 bit int | 1ch flac 24 bit int | 48000 | single |
| quad_stereo_aiff_chunks | 4ch flac 24 bit int | 2ch aif 24 bit int | 44100 | chunks |
| surround_quad_caf | 6ch wav 32 bit float | 4ch caf 32 bit float | 48000 | single |
| eight_surround_wav_chunks | 8ch aif 24 bit int | 6ch wav 32 bit float | 44100 | chunks |
| stereo_eight_pcm32 | 2ch wav 32 bit float | 8ch wav 32 bit int | 48000 | single |
| surround_sixteen_wav | 6ch caf 32 bit float | 16ch wav 32 bit float | 44100 | single |
| eight_sixtyfour_wav | 8ch wav 32 bit float | 64ch wav 32 bit float | 48000 | single |

| Module | Scenario | Result | Notes |
| --- | --- | --- | --- |
| Dynamics/Degrade.c5 | mono_stereo_wav | pass |  |
| Dynamics/Distortion.c5 | mono_stereo_wav | pass |  |
| Dynamics/DynamicsProcessor.c5 | mono_stereo_wav | pass |  |
| Dynamics/FeedbackLooper.c5 | mono_stereo_wav | pass |  |
| Dynamics/UpDistoRes.c5 | mono_stereo_wav | pass |  |
| Dynamics/WaveShaper.c5 | mono_stereo_wav | pass |  |
| Filters/AMFMFilter.c5 | mono_stereo_wav | pass |  |
| Filters/AutoModFilter.c5 | mono_stereo_wav | pass |  |
| Filters/Binaural.c5 | mono_stereo_wav | pass |  |
| Filters/BrickWall.c5 | mono_stereo_wav | pass |  |
| Filters/Flanger.c5 | mono_stereo_wav | pass |  |
| Filters/MaskFilter.c5 | mono_stereo_wav | pass |  |
| Filters/ParamEQ.c5 | mono_stereo_wav | pass |  |
| Filters/Phaser.c5 | mono_stereo_wav | pass |  |
| Filters/StateVar.c5 | mono_stereo_wav | pass |  |
| Filters/StateVar2.c5 | mono_stereo_wav | pass |  |
| Filters/Vocoder.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandBeatMaker.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandDelay.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandDisto.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandFreqShift.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandGate.c5 | mono_stereo_wav | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | mono_stereo_wav | pass |  |
| Multiband/MultiBandReverb.c5 | mono_stereo_wav | pass |  |
| Pitch/ChordMaker.c5 | mono_stereo_wav | pass |  |
| Pitch/Chorus.c5 | mono_stereo_wav | pass |  |
| Pitch/FreqShift.c5 | mono_stereo_wav | pass |  |
| Pitch/Harmonizer.c5 | mono_stereo_wav | pass |  |
| Pitch/LooperBank.c5 | mono_stereo_wav | pass |  |
| Pitch/LooperMod.c5 | mono_stereo_wav | pass |  |
| Pitch/PitchLooper.c5 | mono_stereo_wav | pass |  |
| Pitch/RandomAccumulator.c5 | mono_stereo_wav | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | mono_stereo_wav | fail | tap: max error 1.99996 |
| Resonators&Verbs/Convolve.c5 | mono_stereo_wav | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | mono_stereo_wav | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | mono_stereo_wav | pass |  |
| Resonators&Verbs/Resonators.c5 | mono_stereo_wav | pass |  |
| Resonators&Verbs/WGuideBank.c5 | mono_stereo_wav | pass |  |
| Spectral/AddResynth.c5 | mono_stereo_wav | pass |  |
| Spectral/BinModulator.c5 | mono_stereo_wav | pass |  |
| Spectral/BinWarper.c5 | mono_stereo_wav | pass |  |
| Spectral/CrossSynth.c5 | mono_stereo_wav | pass |  |
| Spectral/CrossSynth2.c5 | mono_stereo_wav | pass |  |
| Spectral/Morphing.c5 | mono_stereo_wav | pass |  |
| Spectral/Shifter.c5 | mono_stereo_wav | pass |  |
| Spectral/SpectralDelay.c5 | mono_stereo_wav | pass |  |
| Spectral/SpectralFilter.c5 | mono_stereo_wav | pass |  |
| Spectral/SpectralGate.c5 | mono_stereo_wav | pass |  |
| Spectral/SpectralWarper.c5 | mono_stereo_wav | pass |  |
| Spectral/Transpose.c5 | mono_stereo_wav | pass |  |
| Spectral/Vectral.c5 | mono_stereo_wav | pass |  |
| Synthesis/AdditiveSynth.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | mono_stereo_wav | pass |  |
| Synthesis/CrossFreqMod.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | mono_stereo_wav | pass |  |
| Synthesis/SuperSaw.c5 | mono_stereo_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | mono_stereo_wav | pass |  |
| Time/4Delays.c5 | mono_stereo_wav | pass |  |
| Time/BeatMaker.c5 | mono_stereo_wav | pass |  |
| Time/DelayMod.c5 | mono_stereo_wav | pass |  |
| Time/Granulator.c5 | mono_stereo_wav | pass |  |
| Time/Particle.c5 | mono_stereo_wav | pass |  |
| Time/Pelletizer.c5 | mono_stereo_wav | pass |  |
| Time/Stutterer.c5 | mono_stereo_wav | pass |  |
| Time/UltimateGrainer.c5 | mono_stereo_wav | pass |  |
| Dynamics/Degrade.c5 | stereo_mono_flac | pass |  |
| Dynamics/Distortion.c5 | stereo_mono_flac | pass |  |
| Dynamics/DynamicsProcessor.c5 | stereo_mono_flac | pass |  |
| Dynamics/FeedbackLooper.c5 | stereo_mono_flac | pass |  |
| Dynamics/UpDistoRes.c5 | stereo_mono_flac | pass |  |
| Dynamics/WaveShaper.c5 | stereo_mono_flac | pass |  |
| Filters/AMFMFilter.c5 | stereo_mono_flac | pass |  |
| Filters/AutoModFilter.c5 | stereo_mono_flac | pass |  |
| Filters/Binaural.c5 | stereo_mono_flac | pass |  |
| Filters/BrickWall.c5 | stereo_mono_flac | pass |  |
| Filters/Flanger.c5 | stereo_mono_flac | pass |  |
| Filters/MaskFilter.c5 | stereo_mono_flac | pass |  |
| Filters/ParamEQ.c5 | stereo_mono_flac | pass |  |
| Filters/Phaser.c5 | stereo_mono_flac | pass |  |
| Filters/StateVar.c5 | stereo_mono_flac | pass |  |
| Filters/StateVar2.c5 | stereo_mono_flac | pass |  |
| Filters/Vocoder.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandBeatMaker.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandDelay.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandDisto.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandFreqShift.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandGate.c5 | stereo_mono_flac | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | stereo_mono_flac | pass |  |
| Multiband/MultiBandReverb.c5 | stereo_mono_flac | pass |  |
| Pitch/ChordMaker.c5 | stereo_mono_flac | pass |  |
| Pitch/Chorus.c5 | stereo_mono_flac | pass |  |
| Pitch/FreqShift.c5 | stereo_mono_flac | pass |  |
| Pitch/Harmonizer.c5 | stereo_mono_flac | pass |  |
| Pitch/LooperBank.c5 | stereo_mono_flac | pass |  |
| Pitch/LooperMod.c5 | stereo_mono_flac | pass |  |
| Pitch/PitchLooper.c5 | stereo_mono_flac | pass |  |
| Pitch/RandomAccumulator.c5 | stereo_mono_flac | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | stereo_mono_flac | fail | 32_encoded: Offline worker exited unexpectedly. |
| Resonators&Verbs/Convolve.c5 | stereo_mono_flac | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | stereo_mono_flac | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | stereo_mono_flac | pass |  |
| Resonators&Verbs/Resonators.c5 | stereo_mono_flac | pass |  |
| Resonators&Verbs/WGuideBank.c5 | stereo_mono_flac | pass |  |
| Spectral/AddResynth.c5 | stereo_mono_flac | pass |  |
| Spectral/BinModulator.c5 | stereo_mono_flac | pass |  |
| Spectral/BinWarper.c5 | stereo_mono_flac | pass |  |
| Spectral/CrossSynth.c5 | stereo_mono_flac | pass |  |
| Spectral/CrossSynth2.c5 | stereo_mono_flac | pass |  |
| Spectral/Morphing.c5 | stereo_mono_flac | pass |  |
| Spectral/Shifter.c5 | stereo_mono_flac | pass |  |
| Spectral/SpectralDelay.c5 | stereo_mono_flac | pass |  |
| Spectral/SpectralFilter.c5 | stereo_mono_flac | pass |  |
| Spectral/SpectralGate.c5 | stereo_mono_flac | pass |  |
| Spectral/SpectralWarper.c5 | stereo_mono_flac | pass |  |
| Spectral/Transpose.c5 | stereo_mono_flac | pass |  |
| Spectral/Vectral.c5 | stereo_mono_flac | pass |  |
| Synthesis/AdditiveSynth.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | stereo_mono_flac | pass |  |
| Synthesis/CrossFreqMod.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | stereo_mono_flac | pass |  |
| Synthesis/SuperSaw.c5 | stereo_mono_flac | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | stereo_mono_flac | pass |  |
| Time/4Delays.c5 | stereo_mono_flac | pass |  |
| Time/BeatMaker.c5 | stereo_mono_flac | pass |  |
| Time/DelayMod.c5 | stereo_mono_flac | pass |  |
| Time/Granulator.c5 | stereo_mono_flac | pass |  |
| Time/Particle.c5 | stereo_mono_flac | pass |  |
| Time/Pelletizer.c5 | stereo_mono_flac | pass |  |
| Time/Stutterer.c5 | stereo_mono_flac | pass |  |
| Time/UltimateGrainer.c5 | stereo_mono_flac | pass |  |
| Dynamics/Degrade.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/Distortion.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/DynamicsProcessor.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/FeedbackLooper.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/UpDistoRes.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/WaveShaper.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/AMFMFilter.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/AutoModFilter.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/Binaural.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/BrickWall.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/Flanger.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/MaskFilter.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/ParamEQ.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/Phaser.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/StateVar.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/StateVar2.c5 | quad_stereo_aiff_chunks | pass |  |
| Filters/Vocoder.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandBeatMaker.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandDelay.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandDisto.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandFreqShift.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandGate.c5 | quad_stereo_aiff_chunks | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | quad_stereo_aiff_chunks | pass |  |
| Multiband/MultiBandReverb.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/ChordMaker.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/Chorus.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/FreqShift.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/Harmonizer.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/LooperBank.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/LooperMod.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/PitchLooper.c5 | quad_stereo_aiff_chunks | pass |  |
| Pitch/RandomAccumulator.c5 | quad_stereo_aiff_chunks | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | quad_stereo_aiff_chunks | fail | tap: max error 2 |
| Resonators&Verbs/Convolve.c5 | quad_stereo_aiff_chunks | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | quad_stereo_aiff_chunks | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | quad_stereo_aiff_chunks | pass |  |
| Resonators&Verbs/Resonators.c5 | quad_stereo_aiff_chunks | pass |  |
| Resonators&Verbs/WGuideBank.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/AddResynth.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/BinModulator.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/BinWarper.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/CrossSynth.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/CrossSynth2.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/Morphing.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/Shifter.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/SpectralDelay.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/SpectralFilter.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/SpectralGate.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/SpectralWarper.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/Transpose.c5 | quad_stereo_aiff_chunks | pass |  |
| Spectral/Vectral.c5 | quad_stereo_aiff_chunks | pass |  |
| Synthesis/AdditiveSynth.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | quad_stereo_aiff_chunks | pass |  |
| Synthesis/CrossFreqMod.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | quad_stereo_aiff_chunks | pass |  |
| Synthesis/SuperSaw.c5 | quad_stereo_aiff_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/4Delays.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/BeatMaker.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/DelayMod.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/Granulator.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/Particle.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/Pelletizer.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/Stutterer.c5 | quad_stereo_aiff_chunks | pass |  |
| Time/UltimateGrainer.c5 | quad_stereo_aiff_chunks | pass |  |
| Dynamics/Degrade.c5 | surround_quad_caf | pass |  |
| Dynamics/Distortion.c5 | surround_quad_caf | pass |  |
| Dynamics/DynamicsProcessor.c5 | surround_quad_caf | pass |  |
| Dynamics/FeedbackLooper.c5 | surround_quad_caf | pass |  |
| Dynamics/UpDistoRes.c5 | surround_quad_caf | pass |  |
| Dynamics/WaveShaper.c5 | surround_quad_caf | pass |  |
| Filters/AMFMFilter.c5 | surround_quad_caf | pass |  |
| Filters/AutoModFilter.c5 | surround_quad_caf | pass |  |
| Filters/Binaural.c5 | surround_quad_caf | pass |  |
| Filters/BrickWall.c5 | surround_quad_caf | pass |  |
| Filters/Flanger.c5 | surround_quad_caf | pass |  |
| Filters/MaskFilter.c5 | surround_quad_caf | pass |  |
| Filters/ParamEQ.c5 | surround_quad_caf | pass |  |
| Filters/Phaser.c5 | surround_quad_caf | pass |  |
| Filters/StateVar.c5 | surround_quad_caf | pass |  |
| Filters/StateVar2.c5 | surround_quad_caf | pass |  |
| Filters/Vocoder.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandBeatMaker.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandDelay.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandDisto.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandFreqShift.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandGate.c5 | surround_quad_caf | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | surround_quad_caf | pass |  |
| Multiband/MultiBandReverb.c5 | surround_quad_caf | pass |  |
| Pitch/ChordMaker.c5 | surround_quad_caf | pass |  |
| Pitch/Chorus.c5 | surround_quad_caf | pass |  |
| Pitch/FreqShift.c5 | surround_quad_caf | pass |  |
| Pitch/Harmonizer.c5 | surround_quad_caf | pass |  |
| Pitch/LooperBank.c5 | surround_quad_caf | pass |  |
| Pitch/LooperMod.c5 | surround_quad_caf | pass |  |
| Pitch/PitchLooper.c5 | surround_quad_caf | pass |  |
| Pitch/RandomAccumulator.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/Convolve.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/Resonators.c5 | surround_quad_caf | pass |  |
| Resonators&Verbs/WGuideBank.c5 | surround_quad_caf | pass |  |
| Spectral/AddResynth.c5 | surround_quad_caf | pass |  |
| Spectral/BinModulator.c5 | surround_quad_caf | pass |  |
| Spectral/BinWarper.c5 | surround_quad_caf | pass |  |
| Spectral/CrossSynth.c5 | surround_quad_caf | pass |  |
| Spectral/CrossSynth2.c5 | surround_quad_caf | pass |  |
| Spectral/Morphing.c5 | surround_quad_caf | pass |  |
| Spectral/Shifter.c5 | surround_quad_caf | pass |  |
| Spectral/SpectralDelay.c5 | surround_quad_caf | pass |  |
| Spectral/SpectralFilter.c5 | surround_quad_caf | pass |  |
| Spectral/SpectralGate.c5 | surround_quad_caf | pass |  |
| Spectral/SpectralWarper.c5 | surround_quad_caf | pass |  |
| Spectral/Transpose.c5 | surround_quad_caf | pass |  |
| Spectral/Vectral.c5 | surround_quad_caf | pass |  |
| Synthesis/AdditiveSynth.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | surround_quad_caf | pass |  |
| Synthesis/CrossFreqMod.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | surround_quad_caf | pass |  |
| Synthesis/SuperSaw.c5 | surround_quad_caf | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | surround_quad_caf | pass |  |
| Time/4Delays.c5 | surround_quad_caf | pass |  |
| Time/BeatMaker.c5 | surround_quad_caf | pass |  |
| Time/DelayMod.c5 | surround_quad_caf | pass |  |
| Time/Granulator.c5 | surround_quad_caf | pass |  |
| Time/Particle.c5 | surround_quad_caf | pass |  |
| Time/Pelletizer.c5 | surround_quad_caf | pass |  |
| Time/Stutterer.c5 | surround_quad_caf | pass |  |
| Time/UltimateGrainer.c5 | surround_quad_caf | pass |  |
| Dynamics/Degrade.c5 | eight_surround_wav_chunks | pass |  |
| Dynamics/Distortion.c5 | eight_surround_wav_chunks | pass |  |
| Dynamics/DynamicsProcessor.c5 | eight_surround_wav_chunks | pass |  |
| Dynamics/FeedbackLooper.c5 | eight_surround_wav_chunks | pass |  |
| Dynamics/UpDistoRes.c5 | eight_surround_wav_chunks | pass |  |
| Dynamics/WaveShaper.c5 | eight_surround_wav_chunks | pass |  |
| Filters/AMFMFilter.c5 | eight_surround_wav_chunks | pass |  |
| Filters/AutoModFilter.c5 | eight_surround_wav_chunks | pass |  |
| Filters/Binaural.c5 | eight_surround_wav_chunks | pass |  |
| Filters/BrickWall.c5 | eight_surround_wav_chunks | pass |  |
| Filters/Flanger.c5 | eight_surround_wav_chunks | pass |  |
| Filters/MaskFilter.c5 | eight_surround_wav_chunks | pass |  |
| Filters/ParamEQ.c5 | eight_surround_wav_chunks | pass |  |
| Filters/Phaser.c5 | eight_surround_wav_chunks | pass |  |
| Filters/StateVar.c5 | eight_surround_wav_chunks | pass |  |
| Filters/StateVar2.c5 | eight_surround_wav_chunks | pass |  |
| Filters/Vocoder.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandBeatMaker.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandDelay.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandDisto.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandFreqShift.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandGate.c5 | eight_surround_wav_chunks | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | eight_surround_wav_chunks | pass |  |
| Multiband/MultiBandReverb.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/ChordMaker.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/Chorus.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/FreqShift.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/Harmonizer.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/LooperBank.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/LooperMod.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/PitchLooper.c5 | eight_surround_wav_chunks | pass |  |
| Pitch/RandomAccumulator.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/Convolve.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/Resonators.c5 | eight_surround_wav_chunks | pass |  |
| Resonators&Verbs/WGuideBank.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/AddResynth.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/BinModulator.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/BinWarper.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/CrossSynth.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/CrossSynth2.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/Morphing.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/Shifter.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/SpectralDelay.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/SpectralFilter.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/SpectralGate.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/SpectralWarper.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/Transpose.c5 | eight_surround_wav_chunks | pass |  |
| Spectral/Vectral.c5 | eight_surround_wav_chunks | pass |  |
| Synthesis/AdditiveSynth.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | eight_surround_wav_chunks | pass |  |
| Synthesis/CrossFreqMod.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | eight_surround_wav_chunks | pass |  |
| Synthesis/SuperSaw.c5 | eight_surround_wav_chunks | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | eight_surround_wav_chunks | pass |  |
| Time/4Delays.c5 | eight_surround_wav_chunks | pass |  |
| Time/BeatMaker.c5 | eight_surround_wav_chunks | pass |  |
| Time/DelayMod.c5 | eight_surround_wav_chunks | pass |  |
| Time/Granulator.c5 | eight_surround_wav_chunks | pass |  |
| Time/Particle.c5 | eight_surround_wav_chunks | pass |  |
| Time/Pelletizer.c5 | eight_surround_wav_chunks | pass |  |
| Time/Stutterer.c5 | eight_surround_wav_chunks | pass |  |
| Time/UltimateGrainer.c5 | eight_surround_wav_chunks | pass |  |
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
| Dynamics/Degrade.c5 | surround_sixteen_wav | pass |  |
| Dynamics/Distortion.c5 | surround_sixteen_wav | pass |  |
| Dynamics/DynamicsProcessor.c5 | surround_sixteen_wav | pass |  |
| Dynamics/FeedbackLooper.c5 | surround_sixteen_wav | pass |  |
| Dynamics/UpDistoRes.c5 | surround_sixteen_wav | pass |  |
| Dynamics/WaveShaper.c5 | surround_sixteen_wav | pass |  |
| Filters/AMFMFilter.c5 | surround_sixteen_wav | pass |  |
| Filters/AutoModFilter.c5 | surround_sixteen_wav | pass |  |
| Filters/Binaural.c5 | surround_sixteen_wav | pass |  |
| Filters/BrickWall.c5 | surround_sixteen_wav | pass |  |
| Filters/Flanger.c5 | surround_sixteen_wav | pass |  |
| Filters/MaskFilter.c5 | surround_sixteen_wav | pass |  |
| Filters/ParamEQ.c5 | surround_sixteen_wav | pass |  |
| Filters/Phaser.c5 | surround_sixteen_wav | pass |  |
| Filters/StateVar.c5 | surround_sixteen_wav | pass |  |
| Filters/StateVar2.c5 | surround_sixteen_wav | pass |  |
| Filters/Vocoder.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandBeatMaker.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandDelay.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandDisto.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandFreqShift.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandGate.c5 | surround_sixteen_wav | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | surround_sixteen_wav | pass |  |
| Multiband/MultiBandReverb.c5 | surround_sixteen_wav | pass |  |
| Pitch/ChordMaker.c5 | surround_sixteen_wav | pass |  |
| Pitch/Chorus.c5 | surround_sixteen_wav | pass |  |
| Pitch/FreqShift.c5 | surround_sixteen_wav | pass |  |
| Pitch/Harmonizer.c5 | surround_sixteen_wav | pass |  |
| Pitch/LooperBank.c5 | surround_sixteen_wav | pass |  |
| Pitch/LooperMod.c5 | surround_sixteen_wav | pass |  |
| Pitch/PitchLooper.c5 | surround_sixteen_wav | pass |  |
| Pitch/RandomAccumulator.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/Convolve.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/Resonators.c5 | surround_sixteen_wav | pass |  |
| Resonators&Verbs/WGuideBank.c5 | surround_sixteen_wav | pass |  |
| Spectral/AddResynth.c5 | surround_sixteen_wav | pass |  |
| Spectral/BinModulator.c5 | surround_sixteen_wav | pass |  |
| Spectral/BinWarper.c5 | surround_sixteen_wav | pass |  |
| Spectral/CrossSynth.c5 | surround_sixteen_wav | pass |  |
| Spectral/CrossSynth2.c5 | surround_sixteen_wav | pass |  |
| Spectral/Morphing.c5 | surround_sixteen_wav | pass |  |
| Spectral/Shifter.c5 | surround_sixteen_wav | pass |  |
| Spectral/SpectralDelay.c5 | surround_sixteen_wav | pass |  |
| Spectral/SpectralFilter.c5 | surround_sixteen_wav | pass |  |
| Spectral/SpectralGate.c5 | surround_sixteen_wav | pass |  |
| Spectral/SpectralWarper.c5 | surround_sixteen_wav | pass |  |
| Spectral/Transpose.c5 | surround_sixteen_wav | pass |  |
| Spectral/Vectral.c5 | surround_sixteen_wav | pass |  |
| Synthesis/AdditiveSynth.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | surround_sixteen_wav | pass |  |
| Synthesis/CrossFreqMod.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | surround_sixteen_wav | pass |  |
| Synthesis/SuperSaw.c5 | surround_sixteen_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | surround_sixteen_wav | pass |  |
| Time/4Delays.c5 | surround_sixteen_wav | pass |  |
| Time/BeatMaker.c5 | surround_sixteen_wav | pass |  |
| Time/DelayMod.c5 | surround_sixteen_wav | pass |  |
| Time/Granulator.c5 | surround_sixteen_wav | pass |  |
| Time/Particle.c5 | surround_sixteen_wav | pass |  |
| Time/Pelletizer.c5 | surround_sixteen_wav | pass |  |
| Time/Stutterer.c5 | surround_sixteen_wav | pass |  |
| Time/UltimateGrainer.c5 | surround_sixteen_wav | pass |  |
| Dynamics/Degrade.c5 | eight_sixtyfour_wav | pass |  |
| Dynamics/Distortion.c5 | eight_sixtyfour_wav | pass |  |
| Dynamics/DynamicsProcessor.c5 | eight_sixtyfour_wav | pass |  |
| Dynamics/FeedbackLooper.c5 | eight_sixtyfour_wav | pass |  |
| Dynamics/UpDistoRes.c5 | eight_sixtyfour_wav | pass |  |
| Dynamics/WaveShaper.c5 | eight_sixtyfour_wav | pass |  |
| Filters/AMFMFilter.c5 | eight_sixtyfour_wav | pass |  |
| Filters/AutoModFilter.c5 | eight_sixtyfour_wav | pass |  |
| Filters/Binaural.c5 | eight_sixtyfour_wav | pass |  |
| Filters/BrickWall.c5 | eight_sixtyfour_wav | pass |  |
| Filters/Flanger.c5 | eight_sixtyfour_wav | pass |  |
| Filters/MaskFilter.c5 | eight_sixtyfour_wav | pass |  |
| Filters/ParamEQ.c5 | eight_sixtyfour_wav | pass |  |
| Filters/Phaser.c5 | eight_sixtyfour_wav | pass |  |
| Filters/StateVar.c5 | eight_sixtyfour_wav | pass |  |
| Filters/StateVar2.c5 | eight_sixtyfour_wav | pass |  |
| Filters/Vocoder.c5 | eight_sixtyfour_wav | pass |  |
| Multiband/MultiBandBeatMaker.c5 | eight_sixtyfour_wav | pass |  |
| Multiband/MultiBandDelay.c5 | eight_sixtyfour_wav | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandDisto.c5 | eight_sixtyfour_wav | pass |  |
| Multiband/MultiBandFreqShift.c5 | eight_sixtyfour_wav | pass |  |
| Multiband/MultiBandGate.c5 | eight_sixtyfour_wav | pass | silent: DSP equality inconclusive |
| Multiband/MultiBandHarmonizer.c5 | eight_sixtyfour_wav | pass |  |
| Multiband/MultiBandReverb.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/ChordMaker.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/Chorus.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/FreqShift.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/Harmonizer.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/LooperBank.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/LooperMod.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/PitchLooper.c5 | eight_sixtyfour_wav | pass |  |
| Pitch/RandomAccumulator.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/ConvolutionReverb.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/Convolve.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/DetunedResonators.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/MatrixReverb.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/Resonators.c5 | eight_sixtyfour_wav | pass |  |
| Resonators&Verbs/WGuideBank.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/AddResynth.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/BinModulator.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/BinWarper.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/CrossSynth.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/CrossSynth2.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/Morphing.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/Shifter.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/SpectralDelay.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/SpectralFilter.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/SpectralGate.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/SpectralWarper.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/Transpose.c5 | eight_sixtyfour_wav | pass |  |
| Spectral/Vectral.c5 | eight_sixtyfour_wav | pass |  |
| Synthesis/AdditiveSynth.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/BucketBrigadeDevice.c5 | eight_sixtyfour_wav | pass | silent: DSP equality inconclusive |
| Synthesis/CrossFreqMod.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/FrequencyModulation.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/Pulsar.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/SpitSideBandSynth.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/StochGrains2.c5 | eight_sixtyfour_wav | pass |  |
| Synthesis/SuperSaw.c5 | eight_sixtyfour_wav | pass | synthesis without file input; input codec not used by module |
| Synthesis/WaveScanSynth.c5 | eight_sixtyfour_wav | pass |  |
| Time/4Delays.c5 | eight_sixtyfour_wav | pass |  |
| Time/BeatMaker.c5 | eight_sixtyfour_wav | pass |  |
| Time/DelayMod.c5 | eight_sixtyfour_wav | pass |  |
| Time/Granulator.c5 | eight_sixtyfour_wav | pass |  |
| Time/Particle.c5 | eight_sixtyfour_wav | pass |  |
| Time/Pelletizer.c5 | eight_sixtyfour_wav | pass |  |
| Time/Stutterer.c5 | eight_sixtyfour_wav | pass |  |
| Time/UltimateGrainer.c5 | eight_sixtyfour_wav | pass |  |
