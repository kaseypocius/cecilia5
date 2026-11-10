# Upstream 5.5.1 integration — November 10, 2026

Integrated upstream `master` through
`b66d3773d493a608985a284b5ef945d38f13f9f1`, using `9cfa088` as the
comparison baseline. All 122 files changed in that upstream range were
integrated, including generated documentation and release scripts.

## Result

- Session format v4 saves built-in module identifiers and absolute sound-file
  paths. Formats 1–3 remain readable. The session loader passes the current
  module root explicitly.
- `Resources/desktop.py`, the PNG icon, and the `cecilia-register-desktop`
  console entry point support upstream desktop registration.
- Application, upstream documentation and build versions are 5.5.1. Local
  feature headings identify the offline-render additions without claiming an
  upstream 5.6.0 release.
- Three-way merges preserved local code in `CeciliaLib.py`, `Session.py`, and
  `constants.py`. The changelog conflict was resolved by keeping both upstream
  release notes and all local renderer notes.
- Before/after SHA-256 checks confirmed that all 69 DSP module files,
  `Cecilia5.py`, `AudioFileIO.py`, `OfflineRender.py`,
  `OfflineRenderDialog.py`, and `RenderMemory.py` remained unchanged.
- Local packaging and routing-selection test changes were retained. Upstream
  session and chain tests were integrated. A new session regression checks
  that v4 save/load preserves stems selection and disabled master output.
- The upstream desktop test's simulated environment now uses a real temporary
  venv, avoiding the bare-symlink interpreter-path mismatch observed on
  Homebrew framework Python. No new dependencies are required.

## Validation

General discovery ran with native DSP regressions enabled and an isolated
initial preferences profile:

```sh
CECILIA_DSP_TESTS=1 cecillia/bin/python -m unittest discover -s tests -v
```

Result: **226 tests, 158 passed, 68 skipped, zero failures**, in 44.756 seconds.
All **six standalone offline-engine scenarios** also ran successfully during
discovery: single-pass, chunks, branches with stems, batch processing,
cancellation, and normalization. The desktop tests, including the real-venv
launcher check, pass.

The complete output is in [the integration test log](upstream_5_5_1_integration_tests.log).

An isolated source copy built a `cecilia-5.5.1-py3-none-any.whl` using
`pip wheel --no-deps --no-build-isolation --no-index`. Inspection confirmed
the desktop console entry point and byte-for-byte inclusion of its helper,
PNG icon and all four renderer files. No package was installed into the
working environment.

GUI integration, Finder/Dock activation, actual applet compilation/signing,
and microphone/device permissions were not exercised. No desktop launcher was
installed. README instructions describe registration after installing this
customized source build in the selected environment.

## Recovery and provenance

Original versions of affected existing files, plus a manifest with hashes of
the original Python and DSP sources, are saved at:

`/private/tmp/cecilia5-pre-upstream-integration-b5oqbosg`

The upstream checkout used for the comparison remains at
`/private/tmp/cecilia5-upstream-review-20261110`.
The workspace remains a source folder without Git metadata.
