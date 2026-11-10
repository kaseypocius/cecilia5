"""Write the memory investigation report from retained measurement artifacts."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'tests/reports'


def jsonl(name):
    path=REPORT/name
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def main():
    matrix=json.loads((REPORT/'offline_memory_summary.json').read_text())
    validation=json.loads((REPORT/'offline_memory_validation.json').read_text())
    utility=jsonl('offline_memory_utilities_final.jsonl')
    aux=jsonl('offline_memory_aux.jsonl')
    extended=jsonl('offline_memory_extended.jsonl')
    impulse=jsonl('offline_memory_impulse_10g.jsonl')
    outputs=jsonl('offline_memory_output_extended.jsonl')
    paired=jsonl('offline_memory_paired.jsonl')
    managed=json.loads((REPORT/'offline_memory_manager.json').read_text()) if (REPORT/'offline_memory_manager.json').exists() else []
    complete=matrix['recorded_cases']==matrix['planned_cases'] and matrix['stale_cases']==0
    lines=['# Offline renderer memory findings','',
        ('The standard size sweep is complete.' if complete else 'The standard size sweep is still running.')+
        f" Recorded {matrix['recorded_cases']}/{matrix['planned_cases']} cases; {matrix['stale_cases']} need retesting after source changes.",'',
        'Whole-file post-processing amplified memory, and parallel workers each loaded their own input tables. Earlier large-file reports measured coordinator-only `RUSAGE_SELF`, excluding native workers. Their sub-140-MB numbers did not bound renderer memory or test gigabyte outputs. Historical reports now state that limit.','',
        '## Changes','',
        '- Stream peak scans, normalization, trim/encoding, chunk stitching and branch accumulation in bounded blocks. Stream mixed branches through the native master graph instead of another full audio table.',
        '- Current scheduling uses up to 75% of physical RAM and 85% of available RAM, precision-aware input estimates, rate-dependent delay-bank estimates and per-task reservations. The budget is shared across the pool; aggregate native RSS replaces rigid per-worker slices. See [current worker-memory findings](worker_memory_optimization.md). The measurements below retain their original watchdog settings and source fingerprints.',
        '- Sample aggregate live-worker RSS on macOS/Linux and stop the largest active worker when the shared budget is exceeded. Oversized estimates get one monitored attempt; without telemetry, preflight rejection remains. Auto mode avoids replaying chunks with only one worker. Sampling is best-effort protection, not a hard allocation cap.',
        '- Reap stopped workers and clean incomplete destinations plus destination-specific atomic encoder files. Admission rejection and failure before any write preserve an existing destination. Cleanup compares its original file signature, including when a later queued overwrite fails.',
        '- Guard reproduced circular-read NaNs in MultiBandDelay and DetunedResonators, and fix DetunedResonators voice activation for mono/multichannel output.','',
        '## Measured post-processing memory','',
        'Original separate-process 64 MiB probes peaked at **492,601,344 bytes** during normalization and **1,080,934,400 bytes** during whole-array AIFF export. Streaming normalization measured **60,801,024 bytes** on the same fixture. The following repeatable utility checks use physically written audio and scan every output sample.','',
        '| Operation | Payload MiB | Peak RSS MiB | Seconds | Result |',
        '| --- | --- | --- | --- | --- |']
    for row in utility:
        lines.append(f"| {row['operation']} | {row['target_audio_bytes']/1024**2:g} | {row.get('peak_rss_bytes',0)/1024**2:.1f} | {row.get('elapsed_seconds',0):.2f} | {row['status']} |")
    lines += ['',
        'The branch mixer additionally compares every sample after the initial server gain ramp. AIFF24 uses three bytes per sample, so its output is smaller than the float32 source. [Raw utility results](offline_memory_utilities_final.jsonl).','',
        '## All-module size sweep','',
        'All 69 modules, 48 kHz, eight channels, float32 WAV, init settings. Input and output growth are tested separately at **1 MiB, 64 MiB, 1 GiB and 1.125 GiB (1.208 GB)**. Inputs contain physically written nonzero samples; logical and allocated bytes are retained. Large-input cases load the complete primary source and render one second; large-output cases loop a 1 MiB source. Auxiliary inputs remain small in this matrix and are tested separately.','',
        'Each child has a sampled **3 GiB RSS stop and 120-second deadline**. Output checks cover exact frame/channel/rate metadata, normalization, and every sample for NaN/Inf. Generators with no file input are not applicable to input growth. Pass means memory/file integrity only; silent outputs are visible and do not establish intended DSP. Timings include import/render/post-processing/validation and can vary with concurrent machine workload.','',
        'Latest standard counts: '+', '.join(f"**{n} {status}**" for status,n in sorted(matrix['latest_status_counts'].items()))+'.',
        f"There are {matrix.get('silent_completed_cases',0)} silent completed cases. See the [complete per-case matrix](offline_memory.md) and [raw attempt history](offline_memory.jsonl).",'',
        '## Large secondary inputs and higher allowances','',
        f"Secondary slots: {sum(r['status']=='pass' for r in aux)}/{len(aux)} completed under the standard limits. Slots include Vocoder excitation, convolution impulse/table inputs, and the second source of CrossSynth/CrossSynth2/Morphing. [Results](offline_memory_aux.jsonl).",'',
        '| Module / slot | Payload MiB | RSS allowance GiB | Peak RSS GiB | Seconds | Result | Silent |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for row in extended+impulse:
        result=row.get('result') or {}
        peak=max(row.get('sampled_peak_rss_bytes',0),result.get('child_peak_rss_bytes',0))
        lines.append(f"| {row['module']} / {row.get('input_slot') or 'primary'} | {row['target_audio_bytes']/1024**2:g} | {row['rss_limit_bytes']/1024**3:g} | {peak/1024**3:.2f} | {row['elapsed_seconds']:.2f} | {row['status']} | {'yes' if result.get('silent') else ''} |")
    lines += ['',
        'The higher-budget retries distinguish a resource allowance from a native crash. Both spectral cases complete with 6 GiB; large convolution IRs complete with 10 GiB. The latter allowance was below the measured 11.2 GiB system render budget on this 32 GiB machine. These limits are not promises for different presets, FFT sizes, precision or polyphony. [6 GiB results](offline_memory_extended.jsonl), [10 GiB IR results](offline_memory_impulse_10g.jsonl).','',
        '## Real coordinator and longer output checks','',
        '| Managed module | Requested / scheduled workers | Peak worker RSS GiB | Seconds | Result |',
        '| --- | --- | --- | --- | --- |']
    for row in managed:
        lines.append(f"| {row['module']} | {row['requested_workers']} / {row['pool_workers']} | {row['sampled_worker_peak_rss_bytes']/1024**3:.2f} | {row['elapsed_seconds']:.2f} | {row['status']} |")
    lines += ['',
        'Managed probes use 1.125 GiB inputs, chunk rendering, normalization, activity events, exact metadata, and worker/scratch cleanup. BinWarper is silent in this short probe; ConvolutionReverb is audible. [Coordinator results](offline_memory_manager.json).','',
        f"Long-output retries: {sum(r['status']=='pass' for r in outputs)}/{len(outputs)} recorded attempts completed (15 planned). At most two small-input children run together, each with a 512 MiB RSS stop and 600-second deadline. The main 120-second outcomes remain recorded separately.",'',
        '| Module | Payload MiB | Peak RSS MiB | Seconds | Result |',
        '| --- | --- | --- | --- | --- |']
    for row in outputs:
        peak=max(row.get('sampled_peak_rss_bytes',0),(row.get('result') or {}).get('child_peak_rss_bytes',0))
        lines.append(f"| {row['module']} | {row['target_audio_bytes']/1024**2:g} | {peak/1024**2:.1f} | {row['elapsed_seconds']:.2f} | {row['status']} |")
    lines += ['', 'Representative paired jobs load and render 1.125 GiB at the same time (180-second deadline, 3 GiB RSS stop). The convolution IR stays small. These three do not replace the all-module factor sweep.', '',
        '| Paired module | Peak RSS GiB | Seconds | Result |', '| --- | --- | --- | --- |']
    for row in paired:
        peak=max(row.get('sampled_peak_rss_bytes',0),(row.get('result') or {}).get('child_peak_rss_bytes',0))
        lines.append(f"| {row['module']} | {peak/1024**3:.2f} | {row['elapsed_seconds']:.2f} | {row['status']} |")
    lines += ['', '[Paired input/output results](offline_memory_paired.jsonl).']
    tests=validation['unit_tests']
    lines += ['',
        '[Long-output results](offline_memory_output_extended.jsonl). Supplemental multi-gigabyte Binaural attempts were interrupted after slow file growth; no completed gigabyte Binaural output is claimed. Process-list verification found no surviving Binaural workers.','',
        '## Correctness and remaining limits','',
        f"- Unit discovery: **{tests['passed']} passed, {tests['skipped']} skipped, {tests['failed']} failed** ({tests['total']} total). The six engine integration scenarios also pass, including cancellation and normalization. [Validation](offline_memory_validation.json), [unit log](offline_memory_unit.log), [engine log](offline_memory_engine.log).",
        '- All 69 module single/chunk/parallel audits pass at absolute tolerance 0.000002, with short audible spectral diagnostics. The current layout/codec matrix is 552/552; it combines a full sweep with a fresh eight-scenario DetunedResonators retest after that file changed between reference and encoding phases. [Routing](offline_memory_correctness.json), [codecs](offline_memory_formats_current.md).',
        '- MultiBandDelay reproduced 8 NaN failures in 150 persistent-worker jobs. DetunedResonators reproduced 13 in 150. Their guarded versions each pass 150 instrumented and 150 persistent-worker repetitions. Stage logs are retained as `offline_memory_*_stages_*.log`. [Native Delay/AllpassWG source inspected](https://github.com/belangeo/pyo/blob/master/src/objects/delaymodule.c).',
        '- MultiBandDelay moves only near-edge delay positions by at most 0.125 sample at 48 kHz with its 15-second buffer. DetunedResonators similarly guards its main period by at most 0.0078125 sample at 44.1 kHz. These small timing/pitch changes avoid the reproduced native wrap-rounding read.',
        '- **Unresolved DSP scope:** the short large-input spectral probes are silent. SpectralWarper needs buffer-fill time; BinWarper pre-analysis can advance envelopes/fades beyond a shorter performance. Warmup/performance timeline separation is not claimed fixed. RAM allocation measurements remain valid; these are not audible long-source correctness passes.',
        '- Tests cover default settings and the documented diagnostics, not every preset, spatial intent, routing topology, large-input/output pairing or persistent-process leak soak. Display-dependent checks were skipped. Standalone packaging and other operating systems still need validation.',
        '- File export and atomic replacement need disk headroom too. No fixed free-disk threshold guarantees enough RAM.','',
        '## Reproduction and source changes','',
        'Run the commands in [tests/README.md](../README.md). Primary drivers are `check_offline_memory.py`, `check_offline_aux_memory.py`, `check_offline_memory_utilities.py`, `check_offline_memory_extended.py`, `check_offline_memory_manager.py`, and `check_offline_output_extended.py`. The shared harness records child PIDs and reaps interrupted children.',
        '',
        'The directory watcher found owned source edits during this run; affected cases were repeated. Full source hashes remain in each attempt. `offline_memory_source_versions.json` accepts equivalence only when the native-pipeline AST is identical; coordinator/pool/process-handle changes are covered separately by coordinator/unit/integration checks. Audio I/O, graph, module and native helper changes still invalidate cases. `--resume` and `retest_offline_memory_stale.py` repeat invalidated cases without substituting cached passes.',
        '',
        f"Measured on {validation['platform']}, Python {validation['python']}, 32 GiB RAM. Earlier throughput reports retain notices correcting coordinator-only RSS attribution. This report is generated by `tests/write_offline_memory_findings.py`."]
    (REPORT/'offline_memory_findings.md').write_text('\n'.join(lines)+'\n')
    print(f"Wrote findings: standard {matrix['recorded_cases']}/{matrix['planned_cases']}; long output {len(outputs)}/15")


if __name__=='__main__':main()
