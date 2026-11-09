# All-module multichannel and codec audit

8/8 cases passed; 0 failed across 1 modules.

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
| Multiband/MultiBandGate.c5 | mono_stereo_wav | pass | audible diagnostic; 33092 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | stereo_mono_flac | pass | audible diagnostic; 36017 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | quad_stereo_aiff_chunks | pass | audible diagnostic; 92627 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | surround_quad_caf | pass | audible diagnostic; 36017 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | eight_surround_wav_chunks | pass | audible diagnostic; 92627 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | stereo_eight_pcm32 | pass | audible diagnostic; 36017 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | surround_sixteen_wav | pass | audible diagnostic; 22067 frames; four gate thresholds -80 dB |
| Multiband/MultiBandGate.c5 | eight_sixtyfour_wav | pass | audible diagnostic; 12017 frames; four gate thresholds -80 dB |
