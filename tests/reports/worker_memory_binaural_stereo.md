# Worker memory: large multichannel/high-rate audit

Input: 64 MiB float32, 50 channels, 48 kHz. Output: 2 channels at 96/192 kHz, 2.2 seconds.
Two identical queue entries per case; four requested workers; 8192 MiB shared budget.

Every completed case checks both outputs for exact metadata, all-sample finiteness, repeat equality (absolute tolerance 0.000002), and coordinator cleanup. Silent init output is recorded and does not establish audible DSP correctness.

| Module | kHz | Result | Active workers | Peak pool MiB | Seconds | Silent |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| Filters/Binaural.c5 | 96 | pass | 2 | 438.4 | 5.53 | False |
| Filters/Binaural.c5 | 192 | pass | 2 | 447.0 | 9.133 | False |

Result: 2/2 cases passed. Silent completed cases: 0.

Peak RSS samples sum all live native workers at 25 ms intervals; short peaks can be missed. This audit covers init settings and these layouts, rather than arbitrary presets or sustained leaks.
