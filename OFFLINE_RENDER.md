# Cecilia 5 — Offline Render Mode & Stem Export Studio

Cecilia 5 includes an **Offline Render Mode** with a multi-threaded audio engine, multiple workflow modes, and **individual module stem rendering**.

---

## 1. Overview & Key Capabilities

- **High-Speed Rendering**: Renders complex DSP graphs, filters, and synthesis modules at up to **10×–25× real-time**, free from real-time audio driver limitations or buffer underruns.
- **Multithreading Support**: Distributes render jobs, disjoint graph branches, or overlapping time-sliced chunks across multiple CPU threads.
- **Per-Module Output Soundfiles ("Stems")**: Capture isolated audio from any module in the chain directly to disk alongside or instead of the master mix.
- **Visual Graph Feedback**: Module nodes marked for offline stem export display a green `[STEM]` badge in the interactive routing canvas.
- **4 Studio Workflows**: Single Bounce, Batch Presets, Batch Sound Folder, and Render Queue.
- **Uncompressed & Lossless Formats**: WAV, AIFF, FLAC, OGG, CAF, AU, and SD2, with sample bit depths up to 32-bit floating point and up to 36 audio channels.
- **Live Monitoring & Audition**: Real-time worker lane visualization, peak dB measurement, live VU meter updates, and one-click playback of rendered files.

---

## 2. Launching the Offline Render Studio

The Offline Render Studio is non-modal and can be opened through multiple avenues:

1. **Top Control Panel**: Click the **`[Offline Render]`** button situated next to the transport controls.
2. **Menu Bar**: Select **`Action -> Offline Render...`** (or press `Ctrl+Shift+R` / `Cmd+Shift+R`).
3. **API / Scripts**: Call `CeciliaLib.openOfflineRenderDialog(mode="single")`.

---

## 3. Workflow Modes

### Single Bounce
Bounces the current module or multi-module chain session to a single destination audio file.
- **Timeline Duration**: Custom duration in seconds, or click **`Use Input Sound Duration`** to automatically inherit the source file length.
- **Branch Stems**: In multi-branch graph topologies, optionally export independent parallel branches feeding the Output node.

### Batch Presets
Batch-renders multiple presets for the currently active module:
- Checklist with **`Select All`**, **`Select None`**, and **`Refresh`** buttons.
- Target folder selection and filename prefix.
- Options to preserve the currently loaded input audio file and restore preset-specific global settings (duration, master plugins).

### Batch Sound Folder
Processes an entire folder of input audio files through the current processing graph:
- Source and output folder selection.
- Automatic or manual input slot selection for modules with multiple audio inputs (`cfilein` / `csampler`).
- Option to match each output file's duration to its corresponding input audio file.

### Render Queue
Capture-and-render queue for auditioning parameter variations and arrangements:
- Click **`+ Capture Current Session State`** to snapshot the current parameters, curves, and duration.
- Modify sliders, graph curves, or presets and capture additional variations.
- Render all queued items in parallel with full progress tracking.

---

## 4. Individual Module Output Soundfiles ("Stems")

You can configure Cecilia to output separate soundfiles for each module in the chain during offline rendering.

```
                    ┌──────────────┐
                    │  StochGrains │ ───► [STEM 01: song_01_StochGrains.wav]
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Harmonizer  │ ───► [STEM 02: song_02_Harmonizer.wav]
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Master Mix  │ ───► [MASTER:  song.wav]
                    └──────────────┘
```

### Enabling Stems via Routing Graph
- Right-click any module node in the routing canvas.
- Toggle **`Output to disk (offline stem)`**.
- A green **`[STEM]`** badge appears on the module node.
- The Offline Render Studio checklist automatically updates to reflect your selection.

### Enabling Stems via Offline Render Studio
In the **Module Outputs to Disk (Individual Stems)** panel:
- **Master Mix Checkbox**: `[x] Master Mix (Final Chain Output + Master Plugins)` enables or disables the final output file.
- **Module Checklist**: Lists every module in the session with its order and role (e.g. `01 — StochGrains (Source)`, `02 — Harmonizer (Output)`).
- **Quick Buttons**:
  - `Select All`: Marks all modules for stem export.
  - `Select None`: Clears all module stem selections.
  - `Master Only`: Re-enables Master Mix and clears all module stems.
- **Dynamic Output Preview**: Displays the exact number of files and filenames to be generated before rendering starts.

### File Naming Convention
Offline bounce files embed the target module name directly into their filename:
- **Master Mix**: `{basename}_Master.{ext}` (e.g., `Final_Master.wav`)
- **Module Stems**: `{basename}_{ModuleName}.{ext}` (e.g., `Final_Delay.wav`, `Final_StochGrains.wav`)
- **Duplicate Module Disambiguation**: When multiple instances of the same module appear in a chain (e.g. two Delays), instance counters avoid filename collisions: `{basename}_{ModuleName}_{idx}.{ext}` (e.g., `Final_Delay_1.wav`, `Final_Delay_2.wav`).

If the user explicitly inputs an output path ending with `_Master` (such as `Final_Master.wav`), the base root is automatically recognized as `Final`, avoiding redundant suffixes like `Final_Master_Master.wav` and ensuring module stems are cleanly saved as `Final_Delay.wav`.

### Stems-Only Rendering
If you uncheck **Master Mix**, the engine skips rendering the final mix file and produces only the selected module stems. The **`Play Last Render`** button will automatically audition the first rendered stem.

---

## 5. Multithreading Engine & Acceleration Strategies

The offline engine uses a persistent worker pool (`_WorkerPool`) that runs headless rendering instances (`_HeadlessRenderWorker`) inside isolated worker processes to bypass the Python GIL.

### Acceleration Strategies

| Strategy | Description | Best Suited For |
| :--- | :--- | :--- |
| **Auto** | Dynamically chooses between Single, Parallel Branches, or Time Chunks based on job count, graph topology, and render duration. | General production use |
| **Single** | Renders jobs directly in a single pass per job. When multiple jobs are queued, jobs run across worker threads in parallel. | Short renders or exact bit-for-bit single passes |
| **Parallel Branches** | Decomposes pairwise-disjoint graph branches into separate render tasks running on distinct threads, summing them at the master mix. | Complex routing graphs with parallel synthesizer or effect branches |
| **Time Chunks** | Slices long timelines into overlapping time segments rendered concurrently across CPU threads, then crossfades and stitches them. | Long renders (>8s) requiring maximum acceleration |

### Time-Chunk Configuration
- **Preroll (sec)**: Pre-renders audio prior to the slice start time (0.0 to 10.0s) so filters, reverbs, and feedback delays warm up to steady state.
- **Crossfade (sec)**: Overlap crossfade duration (0.01 to 2.0s) between stitched chunks.
- **Crossfade Shape**: Select between `cosine`, `linear`, or `equal_power` crossfade curves.

---

## 6. Supported Audio Formats

| Format | Extensions | Supported Bit Depths |
| :--- | :--- | :--- |
| **WAV** | `.wav`, `.wave` | 16-bit, 24-bit, 32-bit int, 32-bit float |
| **AIFF** | `.aif`, `.aiff` | 16-bit, 24-bit, 32-bit int, 32-bit float |
| **FLAC** | `.flac` | 16-bit, 24-bit int |
| **OGG** | `.ogg` | 16-bit, 24-bit int, 32-bit float |
| **CAF** | `.caf` | 16-bit, 24-bit, 32-bit int, 32-bit float |
| **AU** | `.au` | 16-bit, 24-bit, 32-bit int, 32-bit float |
| **SD2** | `.sd2` | 16-bit, 24-bit int |

Supported sample rates range from **22,050 Hz** to **192,000 Hz**, with channel counts from **1 (mono)** up to **36 surround channels**.

---

## 7. Preferences Integration & Cross-Session Persistence

All offline render settings are fully decoupled from real-time audio DAC server settings and persist across application restarts in `~/.cecilia5/ceciliaPrefs.txt`.

### Persisted Offline Settings

| Setting | Preference Key | Values / Choices | Description |
| :--- | :--- | :--- | :--- |
| **Sample Rate** | `offlineSr` | `22050`, `44100`, `48000`, `88200`, `96000` | Render sample rate independent of live DAC hardware SR |
| **Channel Count** | `offlineNchnls` | `1` to `36` channels | Output channel configuration (Mono, Stereo, Quad, 5.1, etc.) |
| **Buffer Size** | `offlineBufferSize` | `8` to `2048` | Processing buffer size (e.g. 512, 1024, 2048 for high throughput) |
| **File Format** | `offlineAudioFileType` | `wav`, `aif`, `flac`, `ogg`, `caf`, `au`, `sd2` | Export container format |
| **Bit Depth** | `offlineSampSize` | `16 bits int`, `24 bits int`, `32 bits int`, `32 bits float` | Audio sample bit depth |
| **Worker Threads** | `offlineThreads` | `1` up to $2\times$ CPU cores | Number of background worker processes |
| **Acceleration Strategy** | `offlineAccelMode` | `auto`, `single`, `branches`, `chunks` | Single, Parallel Branches, or Time Chunks |
| **Chunk Preroll** | `offlinePreroll` | `0.0` to `10.0` seconds | Pre-roll time for stateful filters & reverbs |
| **Chunk Crossfade** | `offlineCrossfade` | `0.01` to `2.0` seconds | Overlap crossfade duration between slices |
| **Crossfade Curve** | `offlineCrossfadeShape` | `cosine`, `equal_power` | Crossfade interpolation curve |
| **Branch Stem Export** | `offlineExportStems` | `0` or `1` | Remember branch stems export toggle |
| **Master Mix Output** | `offlineMasterOutput` | `0` or `1` | Remember Master Mix render state |

### Synchronization Behavior
- **Immediate Disk Persistence**: Changes made in the Offline Render Studio or in **`Preferences -> Export`** are saved immediately to disk.
- **Session Decoupling**: Adjusting live audio DAC settings (such as testing low-latency 256 buffer on 2-channel laptop speakers) will never overwrite your high-resolution offline bounce preferences (such as 96 kHz, 6-channel 24-bit FLAC).
- **Session Sync**: Clicking **`Sync Session`** updates session-dependent properties (timeline duration, presets, module list) while preserving your custom offline export preferences.

---

## 8. Verification & Test Suites

The offline render subsystem includes comprehensive unit, headless persistence, and GUI integration tests:

```sh
# Run the offline engine multiprocessing suite
python3 tests/test_offline_engine.py

# Run the cross-session persistence test suite
python3 tests/test_offline_persistence.py

# Run the full studio GUI & stem export integration suite
python3 tests/test_offline_ui.py
```

