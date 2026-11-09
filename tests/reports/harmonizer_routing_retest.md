# Harmonizer routing retest

Single-pass/chunked masters/taps and serial/parallel branch sums were rerun after the shared native-window boundary correction. Four channels, 44.1 kHz, 176,417 frames; unchanged absolute tolerance 0.000002.

| Module | Result |
| --- | --- |
| Pitch/ChordMaker.c5 | pass |
| Pitch/Harmonizer.c5 | pass |
| Multiband/MultiBandHarmonizer.c5 | pass |
