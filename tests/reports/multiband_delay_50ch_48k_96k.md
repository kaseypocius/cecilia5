# MultiBandDelay: 50-channel 48→96 kHz reproduction

**Passed** using generated audio matching the reported rates, channel counts and durations. This was not the user's recording. Assumptions: init parameters, Auto mode, six requested workers, float32 WAV, no normalization or stem exports.

| Check | Measured result |
| --- | --- |
| Input | 402 seconds (6:42), 48,000 Hz, 50 channels, 19,296,000 frames |
| Input bytes | 3,859,200,472 logical; 3,862,855,680 allocated |
| Output | 60 seconds, 96,000 Hz, 50 channels, 5,760,000 frames |
| Output bytes | 1,152,000,472 logical; 1,158,447,104 allocated |
| Conservative estimate | 14.63 GiB |
| Actual worker RSS limit | 11.20 GiB |
| Sampled peak worker RSS | **5.41 GiB** |
| Elapsed render time | **101.42 seconds**, excluding fixture generation |
| Scheduled workers | 1 (six requested) |
| Worker activity visible | Yes, including initialization |
| All output samples finite | Passed |
| Channel identity / pitch | Expected distinct tone in every channel; maximum frequency error 0 Hz |
| Worker/scratch cleanup | Passed; generated audio removed |
| Render sources changed during test | No |

The source holds 964,800,000 samples: 3,859,200,000 decoded float32 bytes (3.59 GiB). Four delay bands per channel mean 200 delay lines; their 15-second capacity at 96 kHz adds approximately 1.07 GiB of float32 buffers. Native loader scratch, controls and application overhead add to this baseline.

The estimator reserves double-precision input tables plus copy headroom and a 256 MiB baseline, producing 14.63 GiB—matching the screenshot's rounded 14.6 GiB. The former hard estimate rejection blocked this workload unnecessarily. The corrected coordinator tries one RSS-monitored worker, keeps the existing actual-memory cap, and uses a single pass in Auto mode.

The generated source is physically written in bounded blocks. Validation scans the entire output for non-finite samples, checks exact metadata, and measures a unique frequency in each channel over a one-second segment halfway through the output. Sample-rate conversion preserved those frequencies and their channel ordering. The fixture is synthetic; actual input content, presets, precision and export choices can change runtime and RAM use.

In this run, initialization lasted at least 75 seconds before the output file started growing. The coordinator reported an active worker throughout; lack of output-file growth during that phase did not indicate a hang.

[Raw results](multiband_delay_50ch_48k_96k.json). Reproduce with `cecillia/bin/python tests/check_multiband_delay_50ch.py`. The driver retains the system budget plus an external 11 GiB/600-second watchdog.
