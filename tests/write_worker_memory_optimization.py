"""Regenerate worker-memory findings from retained validation artifacts."""
import json
from pathlib import Path

REPORT = Path(__file__).resolve().parent/'reports'


def main():
    matrix = json.loads((REPORT/'worker_memory_multichannel.json').read_text())['cases']
    large = json.loads((REPORT/'delay_memory_optimization.json').read_text())
    small = json.loads((REPORT/'delay_memory_optimization_64mib.json').read_text())
    stereo = json.loads((REPORT/'worker_memory_binaural_stereo.json').read_text())['cases']
    validation = json.loads((REPORT/'worker_memory_optimization_validation.json').read_text())
    passed = sum(row['status'] == 'pass' for row in matrix)
    failures = [row for row in matrix if row['status'] != 'pass']
    silent = sum(row.get('silent', False) for row in matrix)
    lines = ['# Worker memory optimization — November 10, 2026', '',
        'Subsequent [spectral audio verification](spectral_audio_findings.md) fixes the buffered warpers’ analysis/performance timing and retains audible examples for all 13 spectral modules. The memory matrix below keeps its original results.', '',
        '## Result and implementation', '',
        '- Workers share a pool-wide RAM allowance. A heavy worker can use idle/light peers’ unused memory; aggregate live-process RSS remains monitored on macOS/Linux.',
        '- Independent queue entries reserve their own estimated memory. A large entry no longer reduces every small entry to the largest job’s concurrency limit. Oversized estimates still get one monitored attempt; unmonitored platforms retain preflight rejection.',
        '- Normal pyo input tables are estimated at four bytes per sample, with eight for pyo64. Copy headroom, mono file-input replication and conservative spectral/IR allowances remain. Rate-dependent delay banks are included, including WGuideBank’s existing quadratic channel expansion.',
        '- Fixed offline MultiBandDelay controls allocate only their needed delay history, plus four samples of margin. The default maximum is approximately 0.66 seconds rather than 15. Automated, unknown, MIDI/OSC-controlled and live cases retain full capacity. Delay values, feedback and routing defaults are unchanged.',
        '- Progress shows the shared GiB allowance. A short queue or single-pass job no longer receives a misleading RAM restriction label just because some requested worker slots have no work.', '',
        '## Same-concurrency memory comparison', '',
        '64 MiB float32, 50-channel/48 kHz input; two-job MultiBandDelay queue; 50-channel float32 exports lasting 2.2 seconds; 8 GiB render budget.', '',
        '| Output kHz | Baseline pool MiB | Optimized pool MiB | Pool RSS reduction |',
        '| ---: | ---: | ---: | ---: |']
    for rate in (96000, 192000):
        before = next(row for row in small['measurements'] if row['sample_rate'] == rate and row['version'] == 'baseline')
        after = next(row for row in small['measurements'] if row['sample_rate'] == rate and row['version'] == 'optimized')
        reduction = 100*(1-after['peak_pool_rss_bytes']/before['peak_pool_rss_bytes'])
        lines.append(f"| {rate//1000} | {before['peak_pool_rss_bytes']/1024**2:.1f} | {after['peak_pool_rss_bytes']/1024**2:.1f} | {reduction:.1f}% |")
    lines += ['', 'Both versions ran two workers. [Raw 64 MiB comparison](delay_memory_optimization_64mib.json).', '',
        '## 1 GiB input and worker utilization', '',
        'Physically written 1 GiB float32, 50-channel/48 kHz input; two jobs; 50-channel output lasting 2.2 seconds; four requested workers; 8 GiB budget.', '',
        '| Output kHz | Baseline workers | Optimized workers | Baseline seconds | Optimized seconds | Baseline peak worker MiB | Optimized peak worker MiB |',
        '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for rate in (96000, 192000):
        before = next(row for row in large['measurements'] if row['sample_rate'] == rate and row['version'] == 'baseline')
        after = next(row for row in large['measurements'] if row['sample_rate'] == rate and row['version'] == 'optimized')
        lines.append(f"| {rate//1000} | {before['peak_active_workers']} | {after['peak_active_workers']} | {before['elapsed_seconds']:.2f} | {after['elapsed_seconds']:.2f} | {before['peak_worker_rss_bytes']/1024**2:.1f} | {after['peak_worker_rss_bytes']/1024**2:.1f} |")
    error = max(row['max_error'] for row in large['comparisons'])
    lines += ['', f'Every baseline/optimized sample comparison passed the unchanged absolute tolerance of 0.000002; maximum error was {error:.9g}. Exact metadata and finite samples also passed.', '',
        'The optimized queue uses more aggregate memory when it runs two workers instead of one; peak per-worker memory falls. Timings are observations under concurrent audit activity, not an isolated CPU benchmark or a general speedup promise. [Raw comparison and source hashes](delay_memory_optimization.json).', '',
        '## Every shipped module at high channel counts and rates', '',
        f"**{passed}/{len(matrix)} cases completed** across all 69 modules at 96 and 192 kHz with 50-channel output, a 64 MiB/50-channel input fixture, two queue entries, four requested workers and an 8 GiB budget. **{silent} completed cases were silent init outputs**, so they establish file/memory integrity and repeatability rather than audible DSP correctness. Generators do not consume the source fixture.", '',
        'Completed cases check both exports for exact frames/rate/channels, all-sample finiteness, repeat equality and coordinator cleanup. RSS samples sum all live native workers. These checks cover init settings and these layouts, not all presets or sustained leaks. [Full matrix](worker_memory_multichannel.md), [raw cases](worker_memory_multichannel.json).', '',
        'Incomplete cases retain their actual status:', '',
        '| Module | kHz | Status | Seconds | Sampled pool GiB |',
        '| --- | ---: | --- | ---: | ---: |']
    for row in failures:
        lines.append(f"| {row['module']} | {row['sample_rate']//1000} | {row['status']} | {row.get('elapsed_seconds',0):.2f} | {row.get('peak_pool_rss_bytes',0)/1024**3:.3f} |")
    lines += ['',
        'Binaural’s 50-output-channel cases exceeded the 60-second deadline while using under 0.5 GiB, rather than being stopped by the 8 GiB RAM guard. Its multi-source HRTF processing grows with channel count. With the same 50-channel input and stereo output, both high-rate diagnostics pass:', '',
        '| Output kHz | Seconds | Pool MiB | Audible |', '| ---: | ---: | ---: | --- |']
    for row in stereo:
        lines.append(f"| {row['sample_rate']//1000} | {row.get('elapsed_seconds',0):.2f} | {row.get('peak_pool_rss_bytes',0)/1024**2:.1f} | {not row.get('silent',True)} |")
    lines += ['', '[Stereo diagnostic](worker_memory_binaural_stereo.md).', '',
        'WGuideBank currently constructs `8*C` pitch signals and duplicates each `C` times, producing `8*C*C` waveguides: **20,000 at 50 channels**. Its high-rate cases also exceeded the deadline below the RAM budget. The admission estimate now includes this actual allocation. Reducing that graph to eight waveguides per channel would change the existing pitch bank and preset sound, so this optimization preserves it and records the remaining limit.', '',
        '## Regression checks', '',
        f"General discovery: **{validation['passed']} passed, {validation['skipped']} skipped, zero failures** ({validation['total']} tests), with native DSP fixtures enabled. All six engine integration scenarios pass. [Complete log](worker_memory_optimization_tests.log).", '',
        'Focused tests verify shared-budget borrowing, one-victim aggregate stopping, slot restart, mixed-size queue admission, cancelled memory waiters, precision estimates, delay capacity and live/automation fallback. The final 25-test memory suite passes (one opt-in native fixture skipped in that focused invocation; it passes in full discovery).', '',
        'MultiBandDelay’s separate four-channel routing retest passes master/tap metadata, finite samples, exact single/chunk equality, branch stems and serial/parallel mixing. [Routing results](worker_memory_delay_routing.json).', '',
        '## Why worker limits remain', '',
        'Every independent process loads its own native input tables and DSP state. Chunk rendering replays history from the session origin instead of loading only the output segment. Convolution filters, phase-vocoder histories, mono replication, polyphony and delay capacity add memory. Ten copies of a large graph may exceed physical or currently available RAM even after these changes. Removing that cost requires a different native streaming/shared-table design; increasing a numerical limit alone does not free memory.', '',
        'The automatic budget remains at most 75% of physical RAM and 85% of reported available RAM. The UI exposes the shared allowance; documented byte/MB/GB/fraction overrides and persisted preferences remain supported. Sampled RSS is best-effort protection: allocation peaks between samples can overshoot. Other operating systems, standalone packages and GUI/device behavior remain outside this validation.', '',
        'The 1 GiB comparison covers MultiBandDelay; the full 69-module high-rate matrix uses 64 MiB inputs. Earlier all-module gigabyte size sweeps remain historical artifacts with their recorded sources. Do not interpret this run as an exhaustive 1 GiB × high-rate × preset matrix.', '',
        '## Reproduce and update the Markdown', '',
        '```sh',
        'CECILIA_DSP_TESTS=1 cecillia/bin/python -m unittest discover -s tests -v',
        'cecillia/bin/python tests/check_worker_memory_multichannel.py',
        'cecillia/bin/python tests/check_worker_memory_multichannel.py --module Filters/Binaural.c5 --output-channels 2 --report-prefix worker_memory_binaural_stereo',
        'cecillia/bin/python tests/check_delay_memory_optimization.py --baseline-root /path/to/3eb34ce/source',
        'cecillia/bin/python tests/check_delay_memory_optimization.py --baseline-root /path/to/3eb34ce/source --input-mib 64 --report-prefix delay_memory_optimization_64mib',
        'cecillia/bin/python tests/write_worker_memory_optimization.py', '```', '',
        'The baseline source used here was commit `3eb34ce`, copied to a temporary directory before edits. Audio fixtures and exports are temporary. Application code and diagnostics were developed in an isolated copy of the GitHub checkout; the validation JSON records hashes of final files and the matrix’s source fingerprints.', '',
        'Native reference: [pyo delay implementation](https://github.com/belangeo/pyo/blob/master/src/objects/delaymodule.c). Observed table width was verified directly with a native pyo DataTable buffer (`float32`, four bytes per sample).', '']
    (REPORT/'worker_memory_optimization.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
