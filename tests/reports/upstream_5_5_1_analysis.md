# Upstream 5.5.1 analysis — November 10, 2026

**Subsequent status:** the reviewed changes have now been integrated into the
working source folder. See [integration results](upstream_5_5_1_integration.md).
The analysis below records the state before integration.

The upstream default branch is `master`. Its reviewed head is
`b66d3773d493a608985a284b5ef945d38f13f9f1` (version 5.5.1, November 9,
2026, America/Toronto).

This folder has no `.git` directory. Its November 7 file timestamps and direct
Git blob comparisons are consistent with a modified snapshot of `9cfa088`
(`Update documentation`, November 7, 2026). This is a comparison baseline,
not a verified local ancestor. Of that commit's 700 tracked files, 669 match
the local files exactly and 31 differ; none are missing. Local additions are
outside those counts.

## New upstream work

There are six commits after the comparison baseline, including one merge.

| Commit | Change | Local significance |
| --- | --- | --- |
| `23b9978` | Linux desktop registration | Adds per-user application-menu entry and PNG icon. |
| `c40f856` | Windows desktop registration | Adds Start menu shortcut using the selected environment's `pythonw.exe`. |
| `08778e4` | macOS desktop registration | Adds a native applet launcher in `~/Applications/Cecilia5.app`, with local ad hoc signing. |
| `0d5979f` | Session path fixes | Resolves built-in modules against the current installation and saves sound-file paths as absolute paths. Introduces session format v4. |
| `fcab277` | Merge desktop registration branch | Brings the launcher work into `master`. |
| `b66d377` | Version 5.5.1 | Updates application, build and documentation version strings. |

The diff covers 122 files, mostly generated documentation/version updates.
Runtime changes consist of the new `Resources/desktop.py`, its PNG icon,
session serialization changes, a one-line caller update in `CeciliaLib.py`,
and the application version. `pyproject.toml` adds `cecilia-register-desktop`.
There are no new dependencies, DSP module changes, or changes to `Cecilia5.py`
in this upstream range.

## Session compatibility and behavior

- Built-in module references are saved as identifiers such as
  `Dynamics/FeedbackLooper.c5`; loading resolves them under the current
  `MODULES_PATH`. This avoids retaining paths into an old source directory,
  Python installation, or virtual environment.
- Sound-file `path` fields are saved as absolute paths. Moving a session alone
  or launching from another working directory keeps those references valid.
  Moving the audio files themselves still requires updating their references.
- External custom module paths and output paths continue to use relative
  encoding where possible.
- The new reader accepts formats 1–4 and migrates older documents to v4 in
  memory. Legacy built-in references, including Windows separators, resolve
  against the current installation.
- The current local reader accepts only versions 1–3. A session saved by 5.5.1
  fails here with `Unsupported Cecilia chain session format or version.`
  This rejection was reproduced with a temporary v4 file.

## Relationship to the local renderer work

Upstream does not contain the local `AudioFileIO.py`, `OfflineRender.py`,
`OfflineRenderDialog.py`, or `RenderMemory.py`, or their supporting tests and
reports. Fourteen local DSP module files also differ from the comparison
baseline, including FeedbackLooper, ConvolutionReverb, SpectralWarper,
MultiBandDelay, DetunedResonators, and the harmonizer fixes. Upstream's new
commits do not touch these module files.

Replacing the application with the upstream checkout would therefore discard
the local renderer and DSP work. The suitable integration is a three-way
merge or selective application of upstream changes.

Only four files were changed both locally and upstream:

| File | Three-way merge result |
| --- | --- |
| `Resources/CeciliaLib.py` | Clean; adds the explicit modules root to `read_session`. |
| `Resources/Session.py` | Clean; retains local stems/master-output state alongside v4 path handling. |
| `Resources/constants.py` | Clean; retains the offline-worker preset-copy guard alongside version 5.5.1. |
| `whatsnew.md` | Conflict at the introductory release notes; preserve both sets of changes. |

These merge results were generated only under `/tmp`. The local source files
were not edited. Upstream's changed session and chain integration tests have
no local modifications relative to the comparison baseline. The local
packaging and routing-selection tests do have separate changes and should be
preserved.

The local README labels the work as version 5.6.0 while
`Resources/constants.py` still declares 5.5.0. Integration should deliberately
choose consistent version labeling rather than imply that upstream 5.5.1
includes the offline-render feature set.

## Verification performed

| Check | Result |
| --- | --- |
| Unmodified upstream session suite | 20/20 passed. |
| Upstream session suite against the dry-merged local model | 20/20 passed. |
| Dry-merged v4 save/load and `ChainSession.restore_routing` | Preserved `offline_stem_ids` and `master_output_enabled=False`. |
| Upstream packaging suite with canonical `/private/tmp` temporary paths | 7/7 passed. |
| Upstream desktop suite | 12/13 passed; see below. |
| Generated macOS shell launcher with a real temporary venv, spaces, apostrophes, Unicode and shell metacharacters | Passed interpreter path, environment prefix, working-directory and argument checks. |

The failing desktop test constructs a simulated environment using a bare
Python symlink. On this Homebrew Python 3.13/macOS setup, the child reports the
base interpreter path, so its exact `sys.executable` assertion fails. Repeating
the launcher check with an actual venv passes. This isolates a fixture/platform
assumption; the original upstream test remains failing in this environment.

The first packaging run also exposed `/var` versus `/private/var` string
comparisons in two existing tests. Both pass with `TMPDIR=/private/tmp`.
An initial in-memory merged-model test setup similarly used `/tmp` rather
than its canonical `/private/tmp` location; correcting the synthetic module
filename produces the 20/20 result above.

The applet compiler and code signing were mocked in launcher tests. No launcher
was installed. Finder/Dock launch behavior, microphone permissions, physical
audio/MIDI, and GUI integration were not tested. No native DSP suite was run
for this analysis because the upstream range changes no DSP implementation.

## Recommended integration

1. Merge the session path fix and updated session/chain tests first. Retain the
   local model's stems state and the renderer's early worker dispatch.
2. Add the desktop helper, icon and console entry point. For the launcher to
   run this customized source tree, its selected Python environment must be
   able to import this version of Cecilia; a separately installed upstream
   package can otherwise select different code.
3. Combine changelog entries and choose consistent version labeling. Preserve
   the local offline-render documentation, test additions and DSP changes.
4. Before deploying an integrated build, run the local session/persistence and
   renderer tests, then exercise session loading and the macOS launcher in the
   GUI. Mechanical merge success does not establish full application behavior.

Sources: [upstream comparison](https://github.com/belangeo/cecilia5/compare/9cfa088...b66d377),
[session fix](https://github.com/belangeo/cecilia5/commit/0d5979f),
[desktop implementation](https://github.com/belangeo/cecilia5/blob/b66d377/Resources/desktop.py),
[5.5.1 release notes](https://github.com/belangeo/cecilia5/blob/b66d377/whatsnew.md).
