# Spectral test audio cleanup

The spectral tests render real bundled pyo recordings using module init settings.

Every audit mode generates its inputs, exports, live captures, taps and reference files in temporary directories. They are deleted after success, failure or Ctrl+C; JSON measurements and hashes remain in the reports folder. The earlier 28 WAV examples have been removed.

The processing-response audit generates its own references, so it can run independently without saved audio from a previous test.

Run from the repository root:

```sh
cecillia/bin/python tests/check_spectral_audio.py --full
cecillia/bin/python tests/check_spectral_audio.py --functional
```

[Full findings and limits](../spectral_audio_findings.md).
