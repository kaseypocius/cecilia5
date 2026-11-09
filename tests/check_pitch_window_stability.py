"""Repeat pitch-window renders in persistent workers; reports finite/reproducible audio."""
import argparse
import copy
import json
import re
from pathlib import Path
import tempfile
import time

import numpy as np
import check_multichannel_formats as matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeats', type=int, default=50)
    parser.add_argument('--report-prefix', default='pitch_window_stability')
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.report_prefix):
        parser.error("report-prefix must contain only letters, digits, underscores or hyphens")
    if args.repeats < 1:
        parser.error('repeats must be positive')
    sr, channels, frames = 48000, 8, 36017
    scenario = next(s for s in matrix.SCENARIOS if s[0] == 'stereo_eight_pcm32')
    server = matrix.Server(sr=sr, nchnls=channels, buffersize=256, audio='manual', duplex=0).boot()
    server.verbosity = 0
    rows = []
    start = time.monotonic()
    try:
        for relative in ('Pitch/ChordMaker.c5', 'Pitch/Harmonizer.c5', 'Multiband/MultiBandHarmonizer.c5'):
            with tempfile.TemporaryDirectory(prefix='cecilia-pitch-repeat-') as temp:
                folder = Path(temp)
                source, _ = matrix.write_fixture(folder, scenario)
                snap = matrix.make_snapshot(matrix.ROOT/'Resources/modules'/relative, source, frames, sr, channels)
                references, encoded = [], []
                for i in range(args.repeats):
                    for label, jobs in (('reference', references), ('pcm32', encoded)):
                        jobs.append(matrix.RenderJob(f'{i}_{label}', relative,
                            str(folder/f'{i}_{label}.wav'), copy.deepcopy(snap),
                            module_outputs={'a':str(folder/f'{i}_{label}_tap.wav')}))
                matrix.run_jobs(references, sr, channels, 'wav', 3, 'single')
                matrix.run_jobs(encoded, sr, channels, 'wav', 2, 'single')
                row = {'module':relative, 'renders':args.repeats*2, 'errors':[], 'max_error':0.0}
                first = None
                for i, (reference, pcm) in enumerate(zip(references, encoded)):
                    for job in (reference, pcm):
                        if job.status != 'Done':
                            row['errors'].append(f'{job.job_id}: {job.error or job.status}')
                    if reference.status != 'Done' or pcm.status != 'Done':
                        continue
                    for kind, rp, ep in (('master',reference.output_path,pcm.output_path),
                                        ('tap',reference.module_outputs['a'],pcm.module_outputs['a'])):
                        try:
                            a = matrix.validate(rp, channels, frames, sr, 'wav', 3)
                            b = matrix.validate(ep, channels, frames, sr, 'wav', 2)
                            check = matrix.compare(b, a, 2)
                            row['max_error'] = max(row['max_error'], check['max_error'])
                            if not check['pass']:
                                row['errors'].append(f'{i}/{kind}: PCM32 error {check["max_error"]}')
                            if kind == 'master':
                                if first is None:
                                    first = a.copy()
                                repeat = matrix.compare(a, first, 3)
                                row['max_error'] = max(row['max_error'], repeat['max_error'])
                                if not repeat['pass']:
                                    row['errors'].append(f'{i}: repeated master error {repeat["max_error"]}')
                        except Exception as exc:
                            row['errors'].append(f'{i}/{kind}: {exc}')
                row['status'] = 'fail' if row['errors'] else 'pass'
                rows.append(row)
                print(relative, row['status'], len(row['errors']), 'errors', flush=True)
    finally:
        server.shutdown()
    result = {'modules':len(rows), 'renders':sum(r['renders'] for r in rows),
              'failed_modules':sum(r['status']=='fail' for r in rows),
              'elapsed_seconds':round(time.monotonic()-start,2), 'results':rows}
    report = matrix.ROOT/'tests/reports'
    (report/(args.report_prefix+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    lines = ['# Pitch-window stability stress test', '',
             f"{result['renders']} renders across {len(rows)} modules; {result['failed_modules']} failed modules.", '',
             '48 kHz, stereo file input, eight-channel masters/taps, float-WAV references and PCM32 exports. Checks include exact shapes, finite samples, codec equality and repeated float-master equality.', '',
             '| Module | Renders | Status | Maximum comparison error |', '| --- | --- | --- | --- |']
    for row in rows:
        lines.append(f"| {row['module']} | {row['renders']} | {row['status']} | {row['max_error']:.9g} |")
        lines.extend('\n'+error.replace('\n',' ') for error in row['errors'])
    (report/(args.report_prefix+'.md')).write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'}),flush=True)
    return bool(result['failed_modules'])


if __name__ == '__main__':
    raise SystemExit(main())
