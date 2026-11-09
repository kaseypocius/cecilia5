# Pitch-window stability stress test

30 renders across 3 modules; 0 failed modules.

48 kHz, stereo file input, eight-channel masters/taps, float-WAV references and PCM32 exports. Checks include exact shapes, finite samples, codec equality and repeated float-master equality.

| Module | Renders | Status | Maximum comparison error |
| --- | --- | --- | --- |
| Pitch/ChordMaker.c5 | 10 | pass | 2.32830644e-10 |
| Pitch/Harmonizer.c5 | 10 | pass | 2.32830644e-10 |
| Multiband/MultiBandHarmonizer.c5 | 10 | pass | 2.32830644e-10 |
