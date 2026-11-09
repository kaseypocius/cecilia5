# Cecilia 5 — The Audio Processing Toolbox

<p align="center">
  <img src="doc-en/source/images/Cecilia_splash.png" alt="Cecilia 5 Splash" />
</p>

Cecilia is an advanced audio signal processing environment built on Python, wxPython, and the [pyo](https://github.com/belangeo/pyo) DSP engine. It offers an intuitive graphical interface (automation grapher, logarithmic sliders, toggles, popup menus) for synthesis, spectral processing, and audio manipulation.

Cecilia comes with a rich library of original built-in modules for pitch shifting, filtering, time stretching, dynamics processing, resonators, and sound synthesis.

---

## What's New in Version 5.6.0

- **Offline Render Studio**: A dedicated non-modal render studio (`Ctrl+Shift+R` / `Cmd+Shift+R` or via the Control Panel `[Offline Render]` button) featuring:
  - **Single Bounce**: Faster-than-realtime timeline bouncing with input sound duration matching.
  - **Batch Presets**: Batch-render all or selected module presets.
  - **Batch Sound Folder**: Process whole folders of audio files through your current processing chain.
  - **Render Queue**: Capture parameter snapshots and render variations sequentially or in parallel.
- **Multithreading Acceleration Engine**:
  - Headless multiprocessing pool for offline rendering; throughput depends on the module, strategy and hardware.
  - 4 acceleration strategies: **Auto**, **Single-Pass**, **Parallel Branches**, and **Time Chunks** (with full-history replay and overlap crossfade curves).
  - Real-time worker lane visualization, ETA progress, and live VU meter feedback.
- **Per-Module Output Soundfiles ("Stems")**:
  - Export individual audio tracks for every module in your signal chain during offline bounces.
  - Visual **`[STEM]`** badges in the routing graph and context menu toggles (`Output to disk (offline stem)`).
  - Master Mix toggle to output full mixes, stems only, or both.
- **VU Meter & Stability Improvements**:
  - Hardened VU meter routines against logarithmic math domain errors on zero/negative amplitude values.
  - Enhanced peak hold and clipping badge rendering.

For complete release details, see [whatsnew.md](whatsnew.md) and the [Offline Render Guide](OFFLINE_RENDER.md).

---

## Audio Routing & Chain Sessions

Combine multiple modules in one session:
- Connect modules in series or parallel, split signals between effects, and mix independent branches at the Output node.
- Multiple independent sound-file, microphone, and synthesis sources share the same transport and timeline.
- Save and reload sessions as `.c5chain` files with full session-wide undo/redo history.

---

## Installation

### Requirements
- **Python**: 3.11 or higher
- **Dependencies**: `pyo`, `wxPython`, `numpy`

### Install with pip
```sh
pip install cecilia
cecilia
```

### Run from Source
1. Clone or download the repository:
   ```sh
   git clone https://github.com/belangeo/cecilia5.git
   cd cecilia5
   ```
2. Install dependencies:
   ```sh
   python3 -m pip install --user pyo wxPython numpy
   ```
3. Launch the application:
   ```sh
   python3 Cecilia5.py
   ```

---

## Testing

```sh
# Run session model & unit tests
python3 -m unittest discover -s tests -v

# Run offline multithread engine test suite
python3 tests/test_offline_engine.py

# Run sample-level correctness tests
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_correctness.py -v

# Audit all shipped modules (includes audible spectral diagnostics)
cecillia/bin/python tests/check_all_modules.py

# Run focused replay regressions
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_replay_regressions.py -v

# Test the all-module layout/codec matrix
cecillia/bin/python tests/check_multichannel_formats.py --report-prefix multichannel_formats_final

# Run full studio GUI & stem export integration test suite
python3 tests/test_offline_ui.py
```

The latest format retest passes **552/552 cases across all 69 modules**, plus
**10 audible diagnostics** for silent init cases and **300 repeated pitch-module
renders**. General discovery passes with **109 passed / 66 skipped**. Integer
exports now saturate safely, float scratch paths avoid FLAC container conflicts,
and harmonizer windows avoid the reproduced unison boundary instability.
See the [format findings](tests/reports/multichannel_findings.md),
[final matrix](tests/reports/multichannel_formats_final.md), and
[earlier routing results](tests/reports/offline_modules.md).

For commands and scope, see [tests/README.md](tests/README.md). Exact chunks replay
signal history; branch workers reconstruct full graph context and apply master
processing once. Both cost additional CPU and temporary storage, so a single-job
speedup is not guaranteed. Offline seed zero resolves to the replay job seed;
live playback and explicit nonzero module seeds retain their existing behavior.

---

## Documentation

- **Offline Render & Stems Guide**: [OFFLINE_RENDER.md](OFFLINE_RENDER.md)
- **Changelog & Release Notes**: [whatsnew.md](whatsnew.md)
- **Online User Documentation**: [https://belangeo.github.io/cecilia5/](https://belangeo.github.io/cecilia5/)

