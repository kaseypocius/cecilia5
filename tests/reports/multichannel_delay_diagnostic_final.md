# All-module multichannel and codec audit

1/1 cases passed; 0 failed across 1 modules.

Every case compares float-WAV reference master/tap audio against the requested output codec/layout, including exact frame count, rate, channels, container and bit depth.
Input codecs are roundtripped with distinct per-channel signals. Comparisons preserve channel/sample positions and use PCM-aware tolerances. This is not an oracle for the spatial design of each processor.
Gate diagnostics use -90 dB; spectral buffers use a 0.125-second source. Other settings are init. Silent cases verify metadata/codecs only; they cannot establish DSP correctness.

| Scenario | Input | Output | Rate | Mode |
| --- | --- | --- | --- | --- |
| eight_sixtyfour_wav | 8ch wav 32 bit float | 64ch wav 32 bit float | 48000 | single |

| Module | Scenario | Result | Notes |
| --- | --- | --- | --- |
| Multiband/MultiBandDelay.c5 | eight_sixtyfour_wav | pass | audible diagnostic; 60017 frames |
