"""Summarize latest per-case memory audit results, flagging changed sources."""
import collections
import hashlib
import json
from offline_memory_sources import same_native_sources
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'tests/reports'


def main():
    latest={}
    for line in (REPORT/'offline_memory.jsonl').read_text().splitlines():
        row=json.loads(line)
        latest[(row['module'],row['direction'],row['target_audio_bytes'])]=row
    rows=list(latest.values())
    stale=[]
    for row in rows:
        if row['status']=='not_applicable':continue
        current={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in row['source_hashes']}
        if row.get('source_changed_during_case') or not same_native_sources(row['source_hashes'],current):stale.append(row)
    counts=collections.Counter(row['status'] for row in rows)
    planned=8*len(list((ROOT/'Resources/modules').rglob('*.c5')))
    summary={'planned_cases':planned,'recorded_cases':len(rows),'latest_status_counts':dict(counts),
             'stale_cases':len(stale),'silent_completed_cases':sum(bool((r.get('result') or {}).get('silent')) for r in rows),'results':rows}
    (REPORT/'offline_memory_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Offline module memory audit','',
           f"Recorded {len(rows)}/{planned} planned cases. Latest results: "+', '.join(f'{n} {s}' for s,n in sorted(counts.items()))+'.',
           (f'{len(stale)} cases need retesting because their sources changed. Results are provisional.' if stale or len(rows)!=planned else 'All planned cases are recorded; no cases need retesting after source changes.'),'',
           'All 69 shipped modules; 48 kHz, eight channels, float WAV, init settings. A separate process runs each native job, with an externally sampled 3 GiB RSS stop and a 120-second deadline. `memory_limit` and `timeout` mean the case did not complete; they are not passes or proof of a native crash. Input tests load the complete primary source but render only one second. Auxiliary files remain small. Output tests loop a 1 MiB primary source and normalize the entire output. A source-independent generator has no applicable input-size case. Silent outputs establish file/finite-sample behavior only.','',
           'Payloads are 1 MiB, 64 MiB, 1 GiB, and 1.125 GiB (1.208 GB), plus headers. Fixtures are physically written; logical and allocated bytes are recorded. No sparse files are used. All output samples are scanned for NaN/Inf and exact frame/channel/rate metadata is checked.','',
           '| Payload MiB | Direction | Pass | Silent passes | N/A | Timeout | Memory stop | Error | Max RSS MiB |',
           '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for size in sorted({r['target_audio_bytes'] for r in rows}):
        for direction in ('input','output'):
            group=[r for r in rows if r['target_audio_bytes']==size and r['direction']==direction]
            c=collections.Counter(r['status'] for r in group)
            peak=max([0]+[max(r.get('sampled_peak_rss_bytes',0),(r.get('result') or {}).get('child_peak_rss_bytes',0)) for r in group])
            lines.append(f"| {size/1024**2:g} | {direction} | {c['pass']} | {sum(bool((r.get('result') or {}).get('silent')) for r in group)} | {c['not_applicable']} | {c['timeout']} | {c['memory_limit']} | {c['error']} | {peak/1024**2:.1f} |")
    lines+=['','| Module | Payload MiB | Direction | Status | Silent | Seconds | Peak RSS MiB |','| --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        peak=max(row.get('sampled_peak_rss_bytes',0),(row.get('result') or {}).get('child_peak_rss_bytes',0))
        lines.append(f"| {row['module']} | {row['target_audio_bytes']/1024**2:g} | {row['direction']} | {row['status']} | {'yes' if (row.get('result') or {}).get('silent') else ''} | {row.get('elapsed_seconds',0):.2f} | {peak/1024**2:.1f} |")
    lines+=['','Pass describes the memory/file-integrity checks, not proof of audible intended DSP. Extended spectral input probes were silent; their RAM figures still include full input/analysis allocation. See `offline_memory_findings.md` for this unresolved warmup/duration limitation and separate larger-budget retries.','','Reproduce: `cecillia/bin/python tests/check_offline_memory.py`, then `cecillia/bin/python tests/summarize_offline_memory.py`. Use `--resume` to rerun only cases invalidated by source edits; `--retry-status timeout` also retries completed timeout records. Raw attempt history remains in `offline_memory.jsonl`.']
    (REPORT/'offline_memory.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'}))


if __name__=='__main__':main()
