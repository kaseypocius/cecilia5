# Cecilia 5 — Offline Render Mode & Stem Export Studio

Cecilia 5 includes an **Offline Render Mode** with a multi-threaded audio engine, multiple workflow modes, and **individual module stem rendering**.

---

## 1. Overview & Key Capabilities

- **High-Speed Rendering**: Renders without real-time audio driver deadlines. Throughput depends on the graph, strategy and hardware; full-history chunks repeat earlier processing.
- **Multithreading Support**: Distributes render jobs, disjoint graph branches, or overlapping time-sliced chunks across multiple CPU threads.
- **Per-Module Output Soundfiles ("Stems")**: Capture isolated audio from any module in the chain directly to disk alongside or instead of the master mix.
- **Visual Graph Feedback**: Module nodes marked for offline stem export display a green `[STEM]` badge in the interactive routing canvas.
- **4 Studio Workflows**: Single Bounce, Batch Presets, Batch Sound Folder, and Render Queue.
- **Audio Formats**: WAV, AIFF, FLAC, OGG, CAF, AU, and SD2, with sample bit depths up to 32-bit floating point and up to 64 audio channels.
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
| **Single** | Renders jobs directly in a single pass per job. When multiple jobs are queued, jobs run across worker threads in parallel. | A single-pass reference for comparing other strategies |
| **Parallel Branches** | Selects pairwise-disjoint outputs in workers that reconstruct the full graph context, then applies master processing once to their sum. | Disjoint graphs; full-context replay costs additional CPU/storage |
| **Time Chunks** | Replays each overlapping segment from the session origin, discards its prefix, then stitches the retained audio. | Stateful timelines; extra CPU/storage means acceleration is not guaranteed |

### Replay, Randomness and Warmup

Offline jobs seed Python and numpy randomness. Module requests for pyo seed zero
use the replay job seed (currently 1); explicit nonzero seeds and live playback
retain their existing behavior. Each job creates fresh DSP server state inside
the persistent worker process to reset startup gain ramps. Raw branch scratch
audio includes module-requested warmup; exported stems omit the warmup prefix.
Master gain, fades and plugins are applied once after branches are combined.
Branch workers preserve full graph construction order to reproduce random
streams, so parallel branch mode may perform more work than a single pass.

### Time-Chunk Configuration
- **Preroll (sec)**: Legacy preference retained for compatibility. Exact chunks replay from the origin; this value is unused.
- **Crossfade (sec)**: Overlap crossfade duration (0.01 to 2.0s) between stitched chunks.
- **Crossfade Shape**: `cosine` or normalized `equal_power`; both use unity-sum weights for correlated overlaps. Chunk fades and automation remain on the original timeline.

### Threading Model vs. Multichannel Processing
- **Audio Channels Run Per-Server**: In Cecilia and pyo, all $C$ audio channels (from 1 up to 64 channels) are evaluated within a single pyo server instance in each worker process. Pyo's internal DSP graph processes multichannel streams sequentially or via vector math inside that server; channel count does not divide individual audio channels across separate CPU worker threads.
- **Parallel Saturation**: Worker thread saturation is achieved by dividing work into independent units:
  - **Batch Queues**: Parallel jobs across the Batch Presets, Batch Sound Folder, or Render Queue tabs.
  - **Parallel Branches**: Concurrent execution of disjoint signal branches feeding the master output.
  - **Time Chunks**: Concurrent execution of overlapping time segments on long single bounces.
  - **Stitching & Stem Encoding**: Parallel stem generation and file export.

### Worker Activity & Heartbeat Monitoring
- **Immediate Task Visibility**: Worker lanes (`T1..Tn`) switch from `Idle` to active as soon as a worker handle is acquired for rendering, mixing, or stitching (`on_worker_start` / `on_worker_end`), ensuring workers do not appear idle during initial DSP graph preparation.
- **Asynchronous Coordinator Heartbeat**: An 80 ms coordinator heartbeat thread continuously updates the `Elapsed` timer and monitor status, preventing the UI clock from freezing during heavy initialization (such as dense granular synthesis with high channel counts).
- **Clean Shutdown & Event Suppression**: When rendering completes or is cancelled, worker pool threads are safely reaped and post-completion progress events are strictly suppressed.

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

Supported sample rates range from **22,050 Hz** to **192,000 Hz**, with channel counts from **1 (mono)** up to **64 multichannel audio channels**.

---

## 7. Post-Render Peak Normalization

Offline Render Mode includes built-in post-render peak normalization that automatically scales rendered audio files to a target peak level in dBFS:

- **Normalize Audio Files Checkbox**: `[x] Normalize audio files to:` toggles normalization on or off.
- **Target dB Amount Text Box**: Enter the desired peak level in decibels (e.g. `-0.1` dBFS, `-1.0` dBFS, `0.0` dBFS).
- **All Audio Files Normalized**: Applies to all audio files generated by the render session:
  - The **Master Mix** file (e.g., `Final_Master.wav`)
  - All selected **Module Stem Outputs** (e.g., `Final_Delay.wav`, `Final_Filter.wav`)
  - All files generated in **Batch Presets**, **Batch Sound Folder**, and **Render Queue** workflows.
- **Accurate Linear Scaling**: Peak amplitude across all channels and frames is measured, and an exact gain factor $g = 10^{\text{target\_dB} / 20.0} / \text{peak}$ is applied without distortion or clipping.
- **Live Feedback**: During normalization, the render monitor displays `Normalizing` status, and final reported peak dB values reflect the normalized output levels.

---

## 8. Preferences Integration & Cross-Session Persistence

All offline render settings are fully decoupled from real-time audio DAC server settings and persist across application restarts in `~/.cecilia5/ceciliaPrefs.txt`.

### Persisted Offline Settings

| Setting | Preference Key | Values / Choices | Description |
| :--- | :--- | :--- | :--- |
| **Sample Rate** | `offlineSr` | `22050`, `44100`, `48000`, `88200`, `96000` | Render sample rate independent of live DAC hardware SR |
| **Channel Count** | `offlineNchnls` | `1` to `64` channels | Output channel configuration (Mono, Stereo, Quad, 5.1, 7.1, 64-channel immersive/ambisonic arrays, etc.) |
| **Buffer Size** | `offlineBufferSize` | `8` to `2048` | Processing buffer size (e.g. 512, 1024, 2048 for high throughput) |
| **File Format** | `offlineAudioFileType` | `wav`, `aif`, `flac`, `ogg`, `caf`, `au`, `sd2` | Export container format |
| **Bit Depth** | `offlineSampSize` | `16 bits int`, `24 bits int`, `32 bits int`, `32 bits float` | Audio sample bit depth |
| **Worker Threads** | `offlineThreads` | `1` up to $2\times$ CPU cores | Number of background worker processes |
| **Acceleration Strategy** | `offlineAccelMode` | `auto`, `single`, `branches`, `chunks` | Single, Parallel Branches, or Time Chunks |
| **Chunk Preroll** | `offlinePreroll` | `0.0` to `10.0` seconds | Legacy value; unused by full-history replay |
| **Chunk Crossfade** | `offlineCrossfade` | `0.01` to `2.0` seconds | Overlap crossfade duration between slices |
| **Crossfade Curve** | `offlineCrossfadeShape` | `cosine`, `equal_power` | Crossfade interpolation curve |
| **Branch Stem Export** | `offlineExportStems` | `0` or `1` | Remember branch stems export toggle |
| **Master Mix Output** | `offlineMasterOutput` | `0` or `1` | Remember Master Mix render state |
| **Normalize Audio Files** | `offlineNormalize` | `0` or `1` | Remember offline normalization toggle |
| **Normalize Target dB** | `offlineNormalizeTargetDb` | Float (e.g. `-0.1`, `-1.0`, `0.0`) | Target peak level in dBFS |

### Synchronization Behavior
- **Immediate Disk Persistence**: Changes made in the Offline Render Studio or in **`Preferences -> Export`** are saved immediately to disk.
- **Session Decoupling**: Adjusting live audio DAC settings (such as testing low-latency 256 buffer on 2-channel laptop speakers) will never overwrite your high-resolution offline bounce preferences (such as 96 kHz, 6-channel 24-bit FLAC).
- **Session Sync**: Clicking **`Sync Session`** updates session-dependent properties (timeline duration, presets, module list) while preserving your custom offline export preferences.

---

## 9. Verification & Test Suites

The latest retest passes **all 69 shipped-module cases**: 65 with the original
init fixture and four with additional audible spectral diagnostics. Original
silent init results remain recorded; diagnostic passes do not imply those init
settings became audible. Every master, tap and branch stem has the expected
frame/channel count and finite samples. Single-pass/chunked and serial/parallel
comparisons use the unchanged absolute amplitude tolerance of **0.000002**.
The five previously non-reproducible modules also pass repeated single-pass runs.

Validation also passes **14 shipped-module correctness tests**, **14 focused
replay regressions**, **all six engine scenarios**, and general discovery with
**135 passed / 66 skipped** (201 total, native DSP checks enabled). GUI tests were not
enabled. The audit covers four channels at 44.1 kHz and 176,417 frames, init
settings plus the documented diagnostics, not every preset or routing topology.

The branch-fade mismatch, unseeded replay and retained startup-ramp state are
resolved in this retest. Warmup prefixes are retained internally and removed
from public stems. See [detailed findings](tests/reports/offline_findings.md),
[per-module results](tests/reports/offline_modules.md), and
[test commands](tests/README.md). The failing baseline remains available in
[the before-debug report](tests/reports/offline_modules_before_debug.md).

The offline render subsystem includes comprehensive unit, headless persistence, and GUI integration tests:

```sh
# Run the offline engine multiprocessing suite
python3 tests/test_offline_engine.py

# Run sample-level correctness tests
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_correctness.py -v

# Audit all 69 shipped modules (includes audible spectral diagnostics)
cecillia/bin/python tests/check_all_modules.py

# Audit all 69 modules across 8 multichannel layout and codec scenarios (552 cases)
cecillia/bin/python tests/check_multichannel_formats.py --report-prefix multichannel_formats_final

# Run pitch-window stability stress suite (300 renders across pitch modules)
cecillia/bin/python tests/check_pitch_window_stability.py

# Run saturated PCM export and integer alignment tests
CECILIA_DSP_TESTS=1 python3 -m unittest discover -s tests -p test_offline_pcm_exports.py -v

# Run the cross-session persistence test suite
python3 tests/test_offline_persistence.py

# Run the multichannel input and downmix test suite
python3 tests/test_offline_multichannel_input.py

# Run the full studio GUI & stem export integration suite
python3 tests/test_offline_ui.py
```

---

## 10. Multi-Channel File Inputs & Automatic Downmixing / Spatialization

Cecilia 5 now supports arbitrary channel routing between input soundfiles and output destinations ($1 \le C_{\text{in}}, C_{\text{out}} \le 64$ channels).

### Problem Diagnosis & Background
Previously, table-based and granular modules loaded soundfiles via `cfilein`:
- Mono input files ($C_{\text{in}} = 1$) were replicated across session channels in `CeciliaFilein`.
- Multi-channel input files ($C_{\text{in}} > 1$, e.g. stereo, quad, or 5.1 files) loaded as multi-table objects of length $C_{\text{in}}$.
- Granular modules such as [`UltimateGrainer`](Resources/modules/Time/UltimateGrainer.c5), [`Particle`](Resources/modules/Time/Particle.c5), and [`Pelletizer`](Resources/modules/Time/Pelletizer.c5) instantiated pyo objects (`Particle2`, `Particle`, `Granule`) that expanded each input table channel across $C_{\text{out}}$ voices, generating $C_{\text{in}} \times C_{\text{out}}$ audio streams.
- If $C_{\text{in}} > C_{\text{out}}$ (such as loading a stereo soundfile into a mono session, or a quad/5.1 soundfile into a stereo session) without explicit downmixing:
  - The module's output stream count exceeded the session's channel count ($C_{\text{out}}$).
  - In single-module sessions, the engine passed `mod.out` directly without mixing, causing DAC channel out-of-range drops and silent right/surround channels in offline stem and master renders.

### Resolution & Engine Guardrails
1. **Module-Level Mixing**:
   - [`UltimateGrainer`](Resources/modules/Time/UltimateGrainer.c5): Added `self.grmix = self.gr.mix(self.nchnls)` to fold all $C_{\text{in}} \times C_{\text{out}}$ granular streams into $C_{\text{out}}$ voices, keeping `self.gr.filtertype` intact while routing balanced and interpolated signals with exact channel counts.
   - [`Particle`](Resources/modules/Time/Particle.c5): Added `self.grmix = self.gr.mix(self.nchnls)` for balanced downmixing and spatialization.
   - [`Pelletizer`](Resources/modules/Time/Pelletizer.c5): Mixed `Granule` streams to `self.nchnls` prior to `Biquadx` filtering.
   - [`PitchLooper`](Resources/modules/Pitch/PitchLooper.c5): Added `.mix(self.nchnls)` to the summed looper voices.
   - [`LooperBank`](Resources/modules/Pitch/LooperBank.c5): Wrapped `OscBank` in `Mix(..., voices=self.nchnls)` and removed direct `.out()` in `__init__`.
   - [`FeedbackLooper`](Resources/modules/Dynamics/FeedbackLooper.c5): Applied `.mix(self.nchnls)` to `self.dry` to match the channel count of `self.filt`.
   - [`ConvolutionReverb`](Resources/modules/Resonators&Verbs/ConvolutionReverb.c5): Wrapped `CvlVerb` output in `Mix(..., voices=self.nchnls)`.

2. **Engine-Level Guardrails**:
   - In [`Resources/audio.py`](Resources/audio.py) (live playback) and [`Resources/OfflineRender.py`](Resources/OfflineRender.py) (offline rendering):
     Even in single-module chains, module output stream counts are validated against `target_nchnls`. If `mod_out_len != target_nchnls`, `Mix(mod_out, voices=target_nchnls)` is invoked automatically.
   - Stem recording via `pyo.Record` now validates and conforms any module's stream count before passing to disk recorders.

---

## 11. Offline Correctness & DSP Integrity Audits

To guarantee that offline bounces are mathematically faithful to live playback and across execution strategies, Cecilia 5 incorporates a rigorous correctness test suite ([`tests/test_offline_correctness.py`](tests/test_offline_correctness.py)):

### 1. Deterministic Single-Pass vs. Chunked Equivalence
- **Stateless & Memoryless Modules**: Processors such as [`Distortion`](Resources/modules/Dynamics/Distortion.c5) and [`SuperSaw`](Resources/modules/Synthesis/SuperSaw.c5) produce bit-for-bit identical waveforms between single-pass and multi-chunk renders ($L_\infty = 0.00\times 10^0$).
- **Linear Filters**: Recursive filter topologies such as [`BrickWall`](Resources/modules/Filters/BrickWall.c5) and [`StateVar2`](Resources/modules/Filters/StateVar2.c5) match single-pass rendering to within single-precision floating point rounding ($L_\infty \le 3.05 \times 10^{-5}$, exact 1 LSB).
- **Crossfade Symmetry**: Both normalized `equal_power` and `cosine` crossfade curves maintain unity power across chunk seams without phase cancellation or seam dips.

### 2. Delay Lines, Reverbs, Convolution, and Feedback Across Chunk Boundaries
- **Timeline Replay Architecture**: Rather than relying on truncated preroll buffers (which fail to recreate multi-second feedback loops, recursive comb delays, or non-stationary envelopes), worker lanes reconstruct DSP state by simulating the original timeline from $t=0$ up to chunk slice $b_k$.
- **Tail Continuity**: Evaluated against transient burst excitation across chunk seams:
  - [`4Delays`](Resources/modules/Time/4Delays.c5): $L_\infty = 0.00 \times 10^0$, $\text{RMSE} = 0.00 \times 10^0$.
  - [`MultiBandReverb`](Resources/modules/Multiband/MultiBandReverb.c5): $L_\infty = 0.00 \times 10^0$, $\text{RMSE} = 0.00 \times 10^0$.
  - [`FeedbackLooper`](Resources/modules/Dynamics/FeedbackLooper.c5): $L_\infty = 0.00 \times 10^0$, $\text{RMSE} = 0.00 \times 10^0$.
  - [`ConvolutionReverb`](Resources/modules/Resonators&Verbs/ConvolutionReverb.c5): $L_\infty \le 3.05 \times 10^{-5}$, $\text{RMSE} \le 2.11 \times 10^{-6}$.

### 3. Multichannel Stem Export Sample Alignment & Channel Ordering
- **Exact Frame Alignment**: Every exported stem soundfile matches the master render frame-for-frame ($N_{\text{stem}} \equiv N_{\text{master}}$) in both single-pass and chunked modes.
- **Multichannel Integrity**: Verified across 1, 2, 6 (5.1 surround), and 64-channel immersive setups; every channel index retains its distinct signal routing without channel swapping or silent tracks.

### 4. Parallel Branch Signal-Routing Semantics
- **Disjoint Subgraph Independence**: Evaluated on parallel branches feeding the output node. Linear branch summation with standard cable attenuation factor ($1/\sqrt{2} \approx 0.7071$) yields output identical to single-pass whole-graph execution ($L_\infty \le 3.05 \times 10^{-5}$).
- **Muted Branch Semantics**: Muted branch output nodes are muted cleanly to silence in both modes ($L_\infty = 0.00$).
- **Master Stage Processing**: Master effect plugins (e.g. Master Reverb) applied to mixed branch stems reproduce the single-pass master chain output exactly ($L_\infty \le 3.05 \times 10^{-5}$).

### 5. Subprocess Lifecycle, File Cleanup, and State Recovery on Cancellation
- **Immediate Process Termination**: Cancelling an in-flight render immediately signals all worker subprocesses via `proc.terminate()` (with `proc.kill()` fallback) and closes IPC pipes.
- **Artifact Purge**: All incomplete master files, stem audio files, and temporary chunk directories (`_temp_dirs`) are immediately deleted from disk.
- **Re-entrant Execution**: The coordinator pool cleanly resets its internal state, allowing subsequent render jobs to launch immediately without deadlock or orphaned processes.

---

## 12. Multichannel Layout & Codec Matrix (552 Verified Scenarios)

To check file metadata and per-channel sample preservation in selected layouts, Cecilia 5 includes an automated matrix test harness ([`tests/check_multichannel_formats.py`](tests/check_multichannel_formats.py)) testing all **69 modules** across **8 distinct multichannel and codec scenarios** (552 total test cases).

### Scenario Matrix

| Scenario | Input Configuration | Output Configuration | Sample Rate | Render Mode | Verified Cases |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`mono_stereo_wav`** | 1ch WAV (16-bit int) | 2ch WAV (24-bit int) | 44,100 Hz | Single-pass | 69 / 69 pass |
| **`stereo_mono_flac`** | 2ch AIFF (24-bit int) | 1ch FLAC (24-bit int) | 48,000 Hz | Single-pass | 69 / 69 pass |
| **`quad_stereo_aiff_chunks`** | 4ch FLAC (24-bit int) | 2ch AIFF (24-bit int) | 44,100 Hz | Time-chunked (2.1s) | 69 / 69 pass |
| **`surround_quad_caf`** | 6ch WAV (32-bit float) | 4ch CAF (32-bit float) | 48,000 Hz | Single-pass | 69 / 69 pass |
| **`eight_surround_wav_chunks`** | 8ch AIFF (24-bit int) | 6ch WAV (32-bit float) | 44,100 Hz | Time-chunked (2.1s) | 69 / 69 pass |
| **`stereo_eight_pcm32`** | 2ch WAV (32-bit float) | 8ch WAV (32-bit int) | 48,000 Hz | Single-pass | 69 / 69 pass |
| **`surround_sixteen_wav`** | 6ch CAF (32-bit float) | 16ch WAV (32-bit float) | 44,100 Hz | Single-pass | 69 / 69 pass |
| **`eight_sixtyfour_wav`** | 8ch WAV (32-bit float) | 64ch WAV (32-bit float) | 48,000 Hz | Single-pass | 69 / 69 pass |

**Overall Result**: **552 / 552 cases passed (100% pass rate; 0 failures)** across all 69 modules (see [`tests/reports/multichannel_formats_final.md`](tests/reports/multichannel_formats_final.md)).

### Format Hardening & Native Kernel Safeguards

1. **Explicit Saturated Integer PCM Writer**:
   - `_write_wav_pcm` in [`Resources/OfflineRender.py`](Resources/OfflineRender.py) performs explicit saturated integer quantization with a single rounding step:
     $$\text{quantized} = \text{clip}\left(\text{round}(x \times 2^{B-1}), -2^{B-1}, 2^{B-1}-1\right)$$
   - Avoids libsndfile wrap-around distortion when audio overloads $\pm 1.0$.
   - Includes proper RIFF chunk byte-alignment (appends null byte for odd-length PCM24 data chunks) and header chunk size accounting.

2. **Temporary Scratch Audio Containers**:
   - pyo automatically forces audio encoding format based on the filename extension. If pyo records floating-point samples to a destination ending in `.flac`, pyo's FLAC encoder crashes or fails because FLAC only supports integer samples.
   - The offline renderer now renders to `.wav` temporary scratch files (`cec_float_{uuid}.wav`) before invoking final format/codec encoding in `_save_multichannel_audio`.

3. **Rejection of Non-Finite Samples**:
   - Strict `np.isfinite(arr).all()` check prevents non-finite samples (`NaN`, `Inf`) from silently contaminating exported audio or converting to spurious integer samples.

4. **Pitch Shift & Harmonizer Circular Buffer Protection**:
   - In pyo's native C harmonizer kernel (`harmonizermodule.c`), circular buffer read pointer calculation at exact integer sample windows at unison can cause float32 wrap rounding to the upper buffer boundary, occasionally producing transient NaNs.
   - Resolved via `_harmonizer_window_seconds(value, sr)`, enforcing half-integer sample window lengths `min(1.0, (round(value * sr) - 0.5) / sr)` across [`ChordMaker`](Resources/modules/Pitch/ChordMaker.c5), [`Harmonizer`](Resources/modules/Pitch/Harmonizer.c5), [`MultiBandHarmonizer`](Resources/modules/Multiband/MultiBandHarmonizer.c5), and the master [`CeciliaHarmonizerPlugin`](Resources/audio.py).
   - Validated by the pitch stability runner ([`tests/check_pitch_window_stability.py`](tests/check_pitch_window_stability.py)) passing **300 / 300 renders** with no non-finite samples or failed comparisons (maximum comparison error 2.32830644e-10).





### Scope, diagnostics and latest regressions

The 552-case matrix retains ten silent init cases; all ten also pass separate
audible diagnostics. MultiBandGate uses -80 dB thresholds, and the two short
64-channel delay cases run for 1.25 seconds. No shipped defaults were changed.
Channel counts and reference ordering are checked; speaker placement, cross-rate
resampling, every preset, long files and hardware are not established by this run.
The tested containers are WAV/AIFF/FLAC/CAF; OGG/AU/SD2 are outside this matrix.

The harmonizer workaround adjusts the effective window by at most one sample;
pitch is unchanged and corresponding dry delays use the effective window.
General discovery passes **135 tests with 66 skipped**; all six engine scenarios
pass. See [detailed format findings](tests/reports/multichannel_findings.md) for
baseline failures, stress evidence, diagnostic commands and environment versions.

---

## 13. Large Files and Render Memory

The current audit measures native worker RAM directly. Earlier [`check_1gb_performance.py`](tests/check_1gb_performance.py) numbers use `RUSAGE_SELF` in the coordinator, which excludes its worker subprocesses. The reported 73–127 MiB therefore cannot establish bounded worker memory. Those historical tests also render short 5–30 second outputs from large inputs; their 42 passing cases do not verify gigabyte-sized outputs or all 69 modules. The historical [throughput report](tests/reports/large_file_1gb_performance.md) remains available with those limits.

### Current audit

[`tests/check_offline_memory.py`](tests/check_offline_memory.py) tests every shipped module with actual audio payloads of 1 MiB, 64 MiB, 1 GiB and **1.125 GiB (1.208 GB)**. Input and output growth are tested separately at 48 kHz/eight channels. Every native case runs in a fresh, externally monitored subprocess with a 3 GiB sampled RSS stop and a 120-second deadline. Fixtures contain physically written samples. Outputs are checked for exact length, channel count, sample rate, and finite samples throughout.

Large-input cases load the complete primary file and render one second; auxiliary inputs remain small. Large-output cases loop a small primary input. Generators without a file input are marked not applicable. These settings do not cover every preset, long impulse response, full-input spectral analysis, or sustained leak behavior in a reused native process. A timeout or memory stop is a limitation, never a pass.

The standard sweep recorded **552 cases: 507 completed file/memory checks, 28 not applicable, 13 deadline stops and four memory stops**. Thirty-five completed outputs were silent and are not audible-DSP passes. All four memory-limited spectral inputs completed with a 6 GiB allowance; the separate large impulse tests completed with 10 GiB. Fifteen longer-output retries passed; gigabyte Binaural outputs remain time-limited. See the [per-module matrix](tests/reports/offline_memory.md), [findings and fixes](tests/reports/offline_memory_findings.md), and [raw attempt history](tests/reports/offline_memory.jsonl). Source fingerprints identify cases needing repetition after concurrent edits.

### Changes to memory use

- Normalization, peak scanning, trim/re-encoding, chunk stitching and branch accumulation now process bounded blocks rather than whole-file float64 arrays/Python lists. Branch mastering streams the intermediate file through the native graph.
- Native module input tables still load complete files. Separate workers each have their own tables; mono `cfilein` can replicate a table across output channels. DSP analysis buffers require additional memory.
- The coordinator budgets up to 75% of physical RAM and 85% of reported available RAM (expanded from the prior 35% and 50% limits), estimates decoded input memory including mono replication, and schedules concurrent workers accordingly. Users can explicitly override this allocation via environment variables (`CECILIA_RAM_BUDGET_BYTES`, `CECILIA_RAM_BUDGET_MB`, `CECILIA_RAM_BUDGET_GB`, or `CECILIA_RAM_BUDGET_FRACTION`) or preferences (`offlineRamBudgetMB`, `offlineRamBudgetFraction`). Estimates control scheduling, not automatic rejection: when resident-memory monitoring is available, a job estimated above the budget is tried with one worker under the actual RSS cap. Without monitoring, that estimate is still rejected before creating output files. Auto mode uses one pass when only one worker is allowed, avoiding serial chunk replay.
- On macOS/Linux it also samples actual worker RSS and stops a worker exceeding its share of the budget. This is sampled protection, not a hard allocation cap. RAM telemetry on other platforms and standalone packaged builds remains unverified.
- Cancellation/errors remove incomplete outputs and destination-specific encoder temporary files after workers stop. Completed outputs, untouched existing destinations on failure/cancellation, and files rejected before dispatch are retained.

A 64 MiB normalization probe dropped from **492.6 MB to 60.8 MB RSS** after streaming. Physically written 1.125 GiB helper cases completed with approximately **76–87 MB RSS** for normalization/encoding/trim, **157 MB** for stitching, and **211 MB** for branch mixing/mastering; the mixer check compares every sample after its startup ramp. See [measured utility results](tests/reports/offline_memory_utilities_final.jsonl). Output sizes vary with encoding; the AIFF24 output uses three bytes per sample.

Temporary renders and atomic normalization also consume disk space. Retain headroom for intermediates and OS swap; there is no fixed free-disk threshold that guarantees a render will fit RAM. Use a single worker when memory, rather than CPU throughput, limits the job.

Three paired probes also completed with **1.125 GiB inputs and outputs simultaneously** (StateVar2, MultiBandDelay, ConvolutionReverb with a small IR), peaking around **1.26–1.35 GiB RSS**. See [paired results](tests/reports/offline_memory_paired.jsonl). The full 69-module matrix varies input/output growth separately.

### Reported 50-channel MultiBandDelay workload

A generated 6:42, 48 kHz, 50-channel source rendered to 60 seconds at 96 kHz/50 channels in **101.42 seconds**, using one monitored worker from six requested. Peak worker RSS was **5.41 GiB**, versus the conservative **14.63 GiB** estimate. Exact metadata, all-sample finiteness, and channel-specific test frequencies passed. Initialization took at least 75 seconds before the output file grew; the worker activity heartbeat remained visible. This confirms the estimate must not be a hard rejection when actual RAM monitoring is available. [Configuration, assumptions and results](tests/reports/multiband_delay_50ch_48k_96k.md).

### Repeat the checks

```sh
cecillia/bin/python tests/check_offline_memory.py
cecillia/bin/python tests/check_offline_memory.py --resume
cecillia/bin/python tests/summarize_offline_memory.py
cecillia/bin/python tests/check_offline_memory_utilities.py
CECILIA_DSP_TESTS=1 cecillia/bin/python -m unittest discover -s tests
```

Run the large-file sweep serially. Its 3 GiB stop applies per native child, not system-wide. `--resume` retains valid attempts and repeats cases invalidated by source changes. `--retry-status timeout` also repeats timeout records.
