# Changes #

## Latest offline-render verification

The latest retest passes **all 69 shipped-module cases**: 65 with the original
init fixture and four with additional audible spectral diagnostics. Original
silent init results remain recorded; diagnostic passes do not imply those init
settings became audible. Every master, tap and branch stem has the expected
frame/channel count and finite samples. Single-pass/chunked and serial/parallel
comparisons use the unchanged absolute amplitude tolerance of **0.000002**.
The five previously non-reproducible modules also pass repeated single-pass runs.

Validation also passes **14 shipped-module correctness tests**, **14 focused
replay regressions**, **all six engine scenarios**, and general discovery with
**109 passed / 66 skipped** (175 total, replay/PCM tests enabled). GUI tests were not
enabled. The audit covers four channels at 44.1 kHz and 176,417 frames, init
settings plus the documented diagnostics, not every preset or routing topology.

The follow-up fixed the previously reproduced 65 failures and retained the
four silent init cases with separate audible diagnostics. The failing baseline
is preserved alongside the [final findings](tests/reports/offline_findings.md)
and [per-module results](tests/reports/offline_modules.md).

- Branch workers preserve full graph construction order and record raw output
  before the server gain ramp. The mixed master uses the same pyo gain, fade and
  plugin path as the serial graph, applied once.
- Offline replay seeds Python and numpy randomness. Module requests for pyo seed
  zero use the job seed (currently 1); explicit nonzero seeds and live playback
  behavior are retained.
- Each job creates fresh DSP server state inside the persistent worker process,
  preventing retained startup gain-ramp state from shifting the first samples.
- Raw branch intermediates retain the buffer-rounded warmup prefix for master
  replay. Exported module/branch stems discard that prefix. Intermediates are
  float WAV regardless of the public stem format, avoiding premature quantization.
- Scratch recordings live in manager-owned temporary directories so cancellation
  removes raw intermediates and dummy recordings as well as public partial files.
- Worker activity lifecycle hooks (`on_worker_start` / `on_worker_end`) ensure worker lanes
  (`T1..Tn`) immediately reflect active state upon task dispatch (single, chunks,
  branches, mix, and stitch phases) before the first pyo DSP buffer callback arrives.
- An asynchronous coordinator heartbeat (80 ms) continuously drives the `Elapsed` timer
  and progress events, eliminating frozen `00:00.0` indicators during heavy graph
  and granular buffer initialization.
- Worker pool shutdown waits for running tasks upon coordinator exit and suppresses
  post-completion progress events, ensuring clean cancellation and status reporting.
- Channel parallelism semantics documented: pyo Server processes all audio channels
  ($1 \le C \le 64$) within a single process graph; multithreaded acceleration
  saturates CPU worker threads via parallel batch jobs, disjoint graph branches,
  overlapping time chunks, and stem stitching.

## Multichannel Formats & Codec Verification Matrix

The multichannel and codec matrix passes **552 / 552 cases across all 69 modules** (0 failures).
Every scenario tests file metadata (frames, rate, channels, container, bit depth) and sample-accurate comparison between reference float-WAV and target codec/layout outputs:
- **`mono_stereo_wav`**: 1ch WAV 16-bit int $\to$ 2ch WAV 24-bit int (44.1 kHz, single-pass).
- **`stereo_mono_flac`**: 2ch AIFF 24-bit int $\to$ 1ch FLAC 24-bit int (48 kHz, single-pass).
- **`quad_stereo_aiff_chunks`**: 4ch FLAC 24-bit int $\to$ 2ch AIFF 24-bit int (44.1 kHz, time-chunked 2.1s).
- **`surround_quad_caf`**: 6ch WAV 32-bit float $\to$ 4ch CAF 32-bit float (48 kHz, single-pass).
- **`eight_surround_wav_chunks`**: 8ch AIFF 24-bit int $\to$ 6ch WAV 32-bit float (44.1 kHz, time-chunked 2.1s).
- **`stereo_eight_pcm32`**: 2ch WAV 32-bit float $\to$ 8ch WAV 32-bit int (48 kHz, single-pass).
- **`surround_sixteen_wav`**: 6ch CAF 32-bit float $\to$ 16ch WAV 32-bit float (44.1 kHz, single-pass).
- **`eight_sixtyfour_wav`**: 8ch WAV 32-bit float $\to$ 64ch WAV 32-bit float (48 kHz, single-pass).

Ten silent init cases are retained and supplemented with **10 passing audible
diagnostics**. General discovery passes **109 tests / 66 skipped**, and the pitch
stress suite passes **300/300 renders**. The native-window workaround changes the
effective duration by at most one sample without changing pitch. These results
cover the listed channel-count/codec pairs, not all spatial designs or presets.
See [the detailed findings](tests/reports/multichannel_findings.md).

Key format fixes include:
- **Direct Saturated PCM Writer**: Saturated 16, 24, and 32-bit integer PCM writer (`_write_wav_pcm`) preventing libsndfile overload wrap-around, with RIFF chunk byte-padding on odd mono data chunks.
- **FLAC Container Intermediate Safety**: Renders to temporary `.wav` scratch paths before converting to requested non-WAV codecs, avoiding pyo extension-based format override collisions with floating-point intermediate audio.
- **Non-Finite Sample Protection**: Strict finite rejection (`np.isfinite`) protecting exported integer and compressed files from NaN / Inf contamination.
- **ConvolutionReverb Export Coverage**: Checked configured channel counts and corrected the three integer clipping/encoding failures reproduced in this audit.
- **Pitch Shift & Harmonizer Native Kernel Edge Protection**: Expressed harmonizer windows as half-integer sample lengths (`_harmonizer_window_seconds`) across `ChordMaker.c5`, `Harmonizer.c5`, `MultiBandHarmonizer.c5`, and master `CeciliaHarmonizerPlugin`, eliminating float32 circular-buffer wrap rounding at unison and passing 300/300 renders in the pitch stability runner (`tests/check_pitch_window_stability.py`).

Exact chunk and branch replay adds CPU and temporary-storage cost; acceleration
of a single job is not guaranteed. No bundled module defaults were changed to
make the audit pass.

## Version 5.6.0 ##

- **Offline Render Studio**:
  - Added a dedicated, non-modal **Offline Render Studio** window (`OfflineRenderDialog`) for high-speed offline audio rendering without real-time playback limitations.
  - Accessible via the new `[Offline Render]` button on the main Control Panel, the menubar under `Action -> Offline Render...` (`Ctrl+Shift+R` / `Cmd+Shift+R`), or programmatically via `CeciliaLib.openOfflineRenderDialog()`.
  - Supports four specialized workflow tabs:
    - **Single Bounce**: Renders the active module or multi-module chain with precise timeline duration, optional input sound duration matching (`Use Input Sound Duration`), and configurable audio settings.
    - **Batch Presets**: Automatically renders all or selected presets for the active module into separate audio files with options to preserve current input sounds and restore saved preset duration and plugins.
    - **Batch Sound Folder**: Batch-processes an entire folder of source audio files through the current processing chain, with auto-detection or explicit input slot selection and duration matching.
    - **Render Queue**: Snapshot capture workflow allowing users to capture multiple session states, parameter variations, or durations (`+ Capture Current Session State`) and bounce them sequentially or in parallel.

- **High-Performance Multithreading Engine**:
  - Built a persistent headless worker pool with independent IPC pipe isolation, avoiding the Python GIL between workers. Throughput depends on the graph, strategy and hardware.
  - Implemented four acceleration strategies:
    - **Auto**: Automatically selects the optimal execution strategy based on job count, graph topology, and duration.
    - **Single**: Direct single-pass execution per job for maximum exactness.
    - **Parallel Branches**: Detects pairwise-disjoint signal branches feeding the Output node and renders them simultaneously across available CPU threads before mixing at the master stage.
    - **Time Chunks**: Splits long timelines into overlapping segments processed in parallel across worker threads, replaying full signal history before each retained segment, with configurable crossfade duration (10ms–2s) and unity-sum curves (`cosine`, normalized `equal_power`). Legacy preroll is unused; replay adds CPU and storage cost.
  - Added real-time worker lane status visualizations (`_WorkerLanesPanel`), dynamic progress bars with ETA, live VU meter updates, and peak level indicators.
  - Instant, non-blocking cancellation (`Cancel Render`) with automatic cleanup of partial files and temporary disk artifacts.
  - Added `Play Last Render` button to quickly audition the most recent bounce directly within the default system audio player.

- **Per-Module Output Soundfiles ("Stems") & Routing Toggles**:
  - Added the ability to output individual audio files ("stems") for any or all modules in the processing chain during offline bounces, alongside or instead of the master mix.
  - **Routing Graph Integration**:
    - Marked modules display a visual green `[STEM]` badge in the routing graph canvas.
    - Added a checkable `'Output to disk (offline stem)'` item to the right-click context menu of module nodes. Toggling immediately updates the session and synchronizes the studio dialog.
  - **Studio Dialog Controls**:
    - Added a master output toggle checkbox (`Master Mix (Final Chain Output + Master Plugins)`) to allow rendering master mix, stems only, or both.
    - Added an interactive module checklist showing index, module name, and signal role (`Source`, `Output`, `Module`).
    - Quick selection buttons: `[Select All]`, `[Select None]`, and `[Master Only]`.
    - Live dynamic preview label displaying the exact number and filenames of soundfiles to be generated (`{basename}_Master.{ext}`, `{basename}_{ModuleName}.{ext}`).
    - Clean naming convention embedding module names directly into output files (e.g. `Final_Master.wav`, `Final_Delay.wav`), with automatic instance counters for duplicate modules (e.g. `Final_Delay_1.wav`, `Final_Delay_2.wav`) and root normalization when `_Master` is provided.
    - Distinct rows in the job monitor tracking individual completion status, duration, and peak dB for each module stem.
    - Support for stems-only rendering with master output disabled.
  - **Single-Pass Audio Tapping & Chunked Stem Crossfading**:
    - Employs `pyo.Record` to tap each module's post-processed signal during the exact same offline pass with zero redundant reprocessing overhead.
    - Full support for multi-stem time-chunked multithreading, stitching both master and module stems with sample-accurate alignment.

- **Multi-Channel File Input & Granular Downmixing / Spatialization**:
  - Resolved channel mismatch and dropped-channel issues when soundfiles with more channels than the session output count ($C_{\text{in}} > C_{\text{out}}$, e.g. stereo in mono, quad/5.1 in stereo) were loaded into modules such as [`UltimateGrainer`](Resources/modules/Time/UltimateGrainer.c5), [`Particle`](Resources/modules/Time/Particle.c5), [`Pelletizer`](Resources/modules/Time/Pelletizer.c5), [`PitchLooper`](Resources/modules/Pitch/PitchLooper.c5), [`LooperBank`](Resources/modules/Pitch/LooperBank.c5), [`FeedbackLooper`](Resources/modules/Dynamics/FeedbackLooper.c5), and [`ConvolutionReverb`](Resources/modules/Resonators&Verbs/ConvolutionReverb.c5).
  - All input channels now actively generate grains, loop points, and IR reflections, folding seamlessly into the target session channel count ($1 \le C_{\text{out}} \le 64$) without losing right or surround channels.
  - Implemented engine-level stream conforming in both real-time playback ([`Resources/audio.py`](Resources/audio.py)) and offline rendering ([`Resources/OfflineRender.py`](Resources/OfflineRender.py)), ensuring that even single-module sessions guarantee exact output channel conformity.
  - Added dedicated unit tests ([`tests/test_offline_multichannel_input.py`](tests/test_offline_multichannel_input.py)) validating stereo-to-mono, quad-to-stereo, and stereo-to-64-channel conversions.

- **Offline Rendering Correctness & DSP Integrity Audits**:
  - Implemented an extensive offline correctness test suite ([`tests/test_offline_correctness.py`](tests/test_offline_correctness.py)) verifying sample-accurate DSP equivalence between offline single-pass and multithreaded acceleration modes.
  - **Deterministic Chunking Equivalence**: Verified bit-for-bit identity ($L_\infty = 0$) for memoryless/synthesis modules ([`SuperSaw`](Resources/modules/Synthesis/SuperSaw.c5), [`Distortion`](Resources/modules/Dynamics/Distortion.c5)) and float32 1-LSB tolerance ($L_\infty \le 3.05 \times 10^{-5}$) for recursive filters ([`BrickWall`](Resources/modules/Filters/BrickWall.c5), [`StateVar2`](Resources/modules/Filters/StateVar2.c5)) across chunk boundaries with both `cosine` and `equal_power` curves.
  - **Stateful DSP Across Chunk Seams**: Verified seamless continuation of long delay taps, recursive feedback loops, and reverberation/convolution tails across chunk seams without discontinuities or missing decay tails ([`4Delays`](Resources/modules/Time/4Delays.c5), [`MultiBandReverb`](Resources/modules/Multiband/MultiBandReverb.c5), [`FeedbackLooper`](Resources/modules/Dynamics/FeedbackLooper.c5), [`ConvolutionReverb`](Resources/modules/Resonators&Verbs/ConvolutionReverb.c5)).
  - **Multichannel Stem Alignment**: Confirmed exact sample frame counts ($N_{\text{stem}} \equiv N_{\text{master}}$) and active multichannel ordering across 1, 2, 6, and 64-channel stem exports.
  - **Parallel Branch Semantics**: Proved that parallel branch acceleration preserves identical 0.707 cable gain, summation, branch muting, and master plugin effects compared to full serial graphs.
  - **Instant Cancellation & Cleanup**: Validated that cancelling an in-progress render terminates worker subprocesses, deletes partial audio files and temporary slice directories from disk, and cleanly restores worker pools for immediate re-use.

- **Audio Export Formats & Bit Depths**:
  - Full support for major uncompressed and lossless audio formats: WAV (`.wav`), AIFF (`.aif`), FLAC (`.flac`), OGG (`.ogg`), CAF (`.caf`), AU (`.au`), and SD2 (`.sd2`).
  - Bit depth options: 16-bit signed integer, 24-bit signed integer, 32-bit signed integer, and 32-bit floating point, with automatic format-safe clamping for FLAC and SD2.
  - Sampling rates from 22.05 kHz to 192 kHz and channel counts from 1 (mono) up to 64 multichannel audio channels.
  - The corrected 69-module audit passes with four output channels, including audible diagnostics for four originally silent init cases. The prior 65 failures are preserved in the before-debug report. This audit does not verify all modules at 64 channels; selected 6-channel and 64-channel exports are covered by the correctness suite.

- **Preferences & Cross-Session Settings Persistence**:
  - Offline render settings now persist across application sessions in `~/.cecilia5/ceciliaPrefs.txt`.
  - Stored variables include: sample rate (`offlineSr`), channel count (`offlineNchnls`), buffer size (`offlineBufferSize`), audio file format (`offlineAudioFileType`), bit depth (`offlineSampSize`), worker thread count (`offlineThreads`), acceleration strategy (`offlineAccelMode`), chunk preroll (`offlinePreroll`), chunk crossfade (`offlineCrossfade`), crossfade curve (`offlineCrossfadeShape`), stem export toggle (`offlineExportStems`), master mix enable toggle (`offlineMasterOutput`), normalization toggle (`offlineNormalize`), and target peak dB (`offlineNormalizeTargetDb`).
  - Completely decoupled offline export settings from real-time live DAC server settings, ensuring live speaker tests do not alter high-resolution offline bounce setups.
  - Extended `Preferences -> Export` with controls for offline sample rate, channels, buffer size, worker threads, acceleration mode, preroll, crossfade, and normalization.
  - Changes in either the Offline Render Studio or Preferences window are persisted immediately to disk.

- **Post-Render Peak Normalization to Target dB**:
  - Added option to automatically normalize all rendered audio files to a user-specified dBFS peak level after offline rendering completes.
  - Interactive UI controls in the Offline Render Studio: `Normalize audio files to:` checkbox toggle and a numeric text box for specifying the target peak level in decibels (e.g., `-0.1` dBFS, `-1.0` dBFS, `0.0` dBFS).
  - Normalizes every audio file produced by the render pass, including the Master mix and all individual module stems, across Single Bounce, Batch Presets, Batch Sound Folder, and Render Queue modes.
  - Non-destructive linear peak scaling with sample-accurate peak detection across all audio channels.
  - Live progress display reflects `Normalizing` status while files are processed, and final monitor rows update to display the exact post-normalization peak dB.
  - Preference persistence in `~/.cecilia5/ceciliaPrefs.txt` via `offlineNormalize` and `offlineNormalizeTargetDb`, with companion controls added to the main Preferences -> File Export dialog.

- **VU Meter & Stability Improvements**:
  - Fixed `ValueError: math domain error` in `Widgets.py` when calculating logarithmic decibels on zero or negative peak amplitude signals.
  - Hardened VU meter rendering, graphic refresh behavior, channel peak indicators, and clipping badges to prevent heap corruption and display artifacts.

## Version 5.5.0 ##

- Added new modules:

  - Filters/Flanger: four independently enabled parallel flangers.
  - Pitch/Chorus: eight modulated delay lines with depth, feedback, and dry/wet controls.
  - Synthesis/SuperSaw: seven detuned sawtooth oscillators based on the JP-8000 Supersaw.
  - Synthesis/FrequencyModulation: classic frequency modulation synthesis.
  - Synthesis/CrossFreqMod: two oscillators that modulate each other's frequency.
  - Synthesis/SpitSideBandSynth: two-stage split-sideband synthesis.
  - Synthesis/BucketBrigadeDevice: sampler-driven, cross-fed delays with ring
    modulation and lowpass filtering.

- Added an audio routing view for combining multiple modules in one session.
  Connect modules in series or parallel, split signals between effects, and mix
  several branches at the Output node. Multiple independent sound-file,
  microphone, and synthesis sources can share the same transport and timeline.

- Each module instance has its own editor, parameters, automation, and presets.
  Switch between editors and the routing view during playback without restarting
  audio. Shared post-processing effects and master gain apply to the final mix.

- Save and reopen complete sessions as `.c5chain` files, including module
  settings, source inputs, connections, and node positions. Recent sessions are
  listed separately from recent modules.

- Added session-wide undo and redo for routing, module controls, automation
  curves, sound files, effects, presets, and output settings. Each drag or
  automation recording take is a single action, and undo/redo brings the affected
  module and control into view. History retains up to 100 actions per session.

- Routing shortcuts: double-click a module to edit it, right-click empty
  space to add a module, and use Delete or Backspace to remove a selected module
  or cable. Incompatible connections and feedback loops are rejected.

- Extended batch processing to render the complete routing graph. Preset batches
  use the currently edited module's presets, while folder batches cycle through the
  selected reference source's sound files. The Use Sound Duration option now
  applies to both batch modes.

- Right-clicking a slider label a second time now cancels MIDI learning and
  stops the learning server without removing the existing MIDI binding.

- Restored missing bundled presets and included them in distribution packages.

- Added standard Python packaging and a `cecilia` command, with installation via
  `pip install cecilia`. Python 3.11 or newer is required.

- Improved numeric-entry mouse handling and fixed duration-slider behavior,
  graph-line drawing, and sound-file popup menus that previously worked only once.

- Fixed popup-menu handling and several interface layout issues on Windows,
  slider and range-slider drawing on macOS, and drawing compatibility with
  newer wxPython versions.

- Updated the user guide and module-author documentation for routing, sessions,
  batch processing, and undo/redo. Online documentation is now hosted on GitHub
  Pages.

## Version 5.4.1 ##

- Uses latest fixes to portmidi for 64-bit Windows.

- Upgraded WxPython to version 4.1.0.

- Upgraded pyo to version 1.0.3.

## Version 5.4.0 ##

- Last fixes.

- Official release.

## Version 5.3.9 ##

- Various bug fixes.

- Added filter per grain in StochGrains.c5 an StochGrains2.c5.

- Six new modules. Filters/AutoModFilter, Filters/Binaural, Filter/StateVar2
  ResonatorsVerbs/MatrixReverb, Synthesis/WaveScanSynth and Time/Stutterer.

## Version 5.3.8 ##

- Fixed crash when opening the application when .cecilia5 folder does not exist.

- Fixed recording audio output twice (or more) on linux and Windows.

## Version 5.3.7 ##

- Track down every single segmentation fault!

- Presets are no more saved in .c5 files. They are saved in a folder, named as the module,
  in ".cecilia5/presets/".

## Version 5.3.6 ##

- Upgraded to python version 3.7.4 (64-bit), wxPython-4.0.6 and pyo 1.0.1.

## Version 5.3.5 ##

- Upgraded to python version 3.6.4, wxPython-4.0.1 and pyo 0.9.0.

- Better error handling when loading or running a cecilia5 module.
 
## Version 5.3.4 ##

- Upgraded to python version 3.6.3, wxPython-4.0.0b2 and pyo 0.8.8.

- Fixed preferences path encoding on Windows.

- Fixed unicode paths on MacOS when running as an application.

## Version 5.3.3 ##

- Upgraded to python version 3.6.2, wxPython-4.0.0b1 and pyo 0.8.7.

## Version 5.3.2 ##

- Build against wxPython-4.0.0a2.

## Version 5.3.1 ##

- Better handling of non-ascii characters in preferences file.

- Fixed standalone packaging on OSX.

- Fixed curved line not showing on module initialization.

- UltimateGrainer now allows a grain duration up to 10 seconds.

## Version 5.3.0 ##

- Migration of the application code to python3 and wxpython 3.0.3 (phoenix) completed.

- Source code cleanup (refactoring, removed dead and/or duplicated code).

- Lot of fixed bugs.

- Automatic saving of the module after creating or deleting a preset.

- Warning to save on quit.

- The app now opens with the last used module (instead of the random chooser).

- Revisited tooltip and html documentation.

- On Windows, default preferences for input/output devices should be set to WASAPI devices.

- Added ChenLee attractor to the ChaosMod plugin.

- Added various modulation waveforms to BinModulator.c5

- All modules have been tested and cleaned.

New modules:

- UltimateGrainer - A state-of-the-art granulation processing module.

- RandomAccumulator - Variable speed recording accumulator module.

- UpDistoRes - Arctangent distortion module with upsampling and resonant lowpass filter.


## Version 5.0.8 ##

- Record button now records in realtime (offline rendering is now triggered with Menubar->Action->Bounce to Disk.

- User can set the starting point by moving the cursor above the grapher.

- Drag and Drop file or folder on the input sound popup to loads sounds.

- Right-click on sound popup opens a "Recent audio files" popup.

- Sliders can be controlled with MIDI or Open Sound Control messages.

- When moving a point on the graph, Alt key clipped the position on the horizontal axis while Shift-Alt keys clipped the position on the vertical axis.

- Added two batch processing modes. Either every presets applied on the selected sound, or the current preset applied to every sounds in the folder.

- Midi notes are automatically assigned to the sampler transposition and controller 7 to the master gain. Must be activated in the preferences.


## Version 5.0.7 ##

- Disabled duration slider while playing.

- Fixed segmentation fault on preset changes.

- Added a DropFileTarget on the Grapher (for .c5 or .py files).

- Fixed opening soundfile player/editor on Windows and OSX.

- Changed delay time before a popup close itself (when loosing focus) from 500 ms to 1000 ms.

## Version 5.0.6 ##

- Fixed memory leak occuring on each run play/stop (need pyo [revision 974](https://code.google.com/p/cecilia5/source/detail?r=974)).

- Allow fraction notation in cgen (list entry in the interface).

## Version 5.0.5 ##

- Disabled printing sound info for all sounds in the selected folder.

- Added new filter module, Vocoder. (need pyo to be up-to-date with sources).

- Fixed wrong executable path generated by py2app (OSX app).

- Removed Jack and Coreaudio from driver's list in bundled app on OSX (leaved them when running from sources).

- Fixed bug: The red button doesn't turn off at the end of recording.

- cgen ignores trailing coma in poup entry.

- Fixed bug: Do not quiery for the control panel if the interface doesn't exist yet.

- Fixed bug in ListEntry widget when loading from a preset.

## Version 5.0.3 ##

- List in cgen popup window can now be entered as 'comma' or 'space' separated values.

- Fixed number of channels used by the audio Server.

- Wait for the audio Server releasing soundcard's stream before allowing to play again.

- Fixed saving .c5 file on Windows.

- Added 2 filter modules: BrickWall.c5 and BandBrickWall.c5.

## Version 5.0.2 ##

- Automatically save a preset named "last save" when saving a module. On module loading, if "last save" preset exists, it is activated.

- Fixed display of the Channels menu.

- Fixed bugs in sliders automation recording.

## Version 5.0.1 ##

- Fixed audio input/output selection.

- Fixed BaseModule.addSampler "pitch" argument.

## Version 5.0.0 ##

First beta release.

#########################################################################################

Version 5.0.9:

- L'outil de polyphonie, dans la section des popup menus, offre maintenant une sélection d'accords, plutôt que seulement des vitesses de lecture au hasard.

- Ajout d'un spectrogramme temps-réel à l'application.

- Multiple modes pour le signal source d'un module (icône juste à droite du menu de sélection du son source).
 -- mode 0 (icône de fichier): mode standard, par la lecture d'un fichier son
 -- mode 1 (icône de micro): Entrée micro temps-réel, les paramètres du sampler sont ignorés.
 -- mode 2 (icône de micro avec un "1"): La mémoire du sampler est remplie par le signal provenant de l'entrée micro, une seule fois au début de la performance. Ensuite, le sampler boucle le signal selon les paramètres définis dans l'interface.
 -- mode 3 (icône de micro entouré de flèches): La mémoire du sampler est remplie, en continu, par le signal provenant de l'entrée micro. Une mémoire à double tampons est utilisée pour éviter les clics. Le sampler agit normalement sur un signal audio constamment renouvelé.
 ** Les mode 1 et 3 ne sont pas disponibles pour les modules nécéssitant un son en RAM comme origine du processus (exemple les modules de granulation).

- Ajout d'une adresse d'envoi OSC aux sliders, pour communiquer la valeurs d'initialisation à une interface externe au début de la performance.

- Ajout de l'option menu "Use Sound Duration on Folder Batch Processing". La durée de chacun des sons contrôle la durée de l'export du son traité.

- Optimization du rafraichissement graphique du Grapher.

- Possibilité de modifier en temps réel, à l'aide des flèches au dessus du menu de sélection, l'ordre des plugins dans l'onglet "Port-Processing".

- Sans changer le nombre de canaux audio du processus, l'utilisateur peut changer, via les préférences, les premières entrée/sortie physiques (sur la carte-son) utilisées.

- Ajout du contrôle MIDI sur les sliders de la fenêtre du sampler (Clic droit sur le nom du paramètre pour lancer l'assignation d'un potentiomètre. Shift+Clic droit pour annuler l'assignation courante).

- Ajout du contrôle OSC sur les sliders de la fenêtre du sampler (Double-clic sur le nom du paramètre pour ouvrir la fenêtre de configuration).

- Nouveaux formats audio supportés: FLAC, OGG, SD2, AU, CAF.


Nouveaux modules:

- ResonatorsVerbs/ConvolutionReverb : Réverbe par convolution.

- Time/Pelletizer : Module de granulation où la fréquence de génération des grains, la hauteur et la durée sont indépendantes.

- Pitch/LooperBank : Jusqu'à 500 lectures en boucle simultannées, avec chacune leur random propre sur la hauteur et l'amplitude.

- Catégorie "Spectral", 13 modules de manipulations spectrales basées sur le vocodeur de phase.

- Amélioration d'un grand nombre de modules déjà présents.


Nouveau Plugin:

- ChaosMod : Modulation en anneaux à l'aide d'attracteurs chaotique.

Version 5.1.0:
    
Version 5.2.0:

Version 5.2.1:
