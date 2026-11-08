# Cecilia 5 Test Suites

## Unit and Session Model Tests
Run the session model and unit tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

## Offline Render Multithread Engine Tests
Run the headless offline render engine test suite (exercises worker multiprocessing pools, single-pass rendering, time-chunked overlap crossfading, parallel branch decomposition, multi-stem tapping, batch rendering, and clean cancellation):

```sh
python3 tests/test_offline_engine.py
```

## GUI & Studio Integration Tests
To include the full GUI integration tests (including the Offline Render Studio dialog, Routing Graph `[STEM]` badges and context menu toggles, ControlPanel buttons, batch preset tabs, render queue, and live VU meters), install Cecilia's normal wxPython and pyo dependencies and run with an available desktop display:

```sh
CECILIA_GUI_TESTS=1 python3 -m unittest discover -s tests -v
```

Or run the offline render UI and studio integration test directly:

```sh
python3 tests/test_offline_ui.py
```

The integration suite creates a temporary preferences profile, module fixtures,
audio files and session files. It exercises persistent editors, running pyo
processing with a manual server, offline rendering, recording, spectrum routing,
presets, shipped module declarations, and session recovery. Physical audio and
MIDI devices require a separate manual check.
