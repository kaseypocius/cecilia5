"""All-module channel/layout and codec matrix; writes JSON and Markdown reports."""
import argparse
import copy
import json
import re
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from pyo import Server, SndTable, sndinfo
import check_all_modules as audit
from Resources.OfflineRender import (OfflineRenderManager, RenderJob, RenderSettings,
    _read_wav_float64, _save_multichannel_audio, apply_sound_to_snapshot)
from Resources.constants import AUDIO_FILE_FORMATS

# name, input channels/format/type, output channels/format/type, rate, duration, strategy
SCENARIOS = [
    ('mono_stereo_wav', 1, 'wav', 0, 2, 'wav', 1, 44100, .75, 'single'),
    ('stereo_mono_flac', 2, 'aif', 1, 1, 'flac', 1, 48000, .75, 'single'),
    ('quad_stereo_aiff_chunks', 4, 'flac', 1, 2, 'aif', 1, 44100, 2.1, 'chunks'),
    ('surround_quad_caf', 6, 'wav', 3, 4, 'caf', 3, 48000, .75, 'single'),
    ('eight_surround_wav_chunks', 8, 'aif', 1, 6, 'wav', 3, 44100, 2.1, 'chunks'),
    ('stereo_eight_pcm32', 2, 'wav', 3, 8, 'wav', 2, 48000, .75, 'single'),
    ('surround_sixteen_wav', 6, 'caf', 3, 16, 'wav', 3, 44100, .5, 'single'),
    ('eight_sixtyfour_wav', 8, 'wav', 3, 64, 'wav', 3, 48000, .25, 'single'),
]
BITS = {0: '16 bit int', 1: '24 bit int', 2: '32 bit int', 3: '32 bit float'}
FORMATS = {'wav': 'WAVE', 'aif': 'AIFF', 'flac': 'FLAC', 'caf': 'CAF'}


def read_audio(path):
    audio = _read_wav_float64(str(path))
    if audio is not None:
        return audio
    table = SndTable(str(path))
    return np.array([table[ch].getTable() for ch in range(len(table))], dtype=np.float64)


def validate(path, channels, frames, sr, fmt, sampletype):
    info = sndinfo(str(path))
    expected = (frames, sr, channels, FORMATS[fmt], BITS[sampletype])
    actual = None if info is None else (info[0], int(info[2]), info[3], info[4], info[5])
    if actual != expected:
        raise AssertionError(f'{Path(path).name}: metadata {actual}, expected {expected}')
    audio = read_audio(path)
    if audio.shape != (channels, frames) or not np.isfinite(audio).all():
        raise AssertionError(f'{Path(path).name}: invalid audio shape or nonfinite samples')
    return audio


def write_fixture(folder, scenario, short=False):
    name, inch, fmt, bit, outch, outfmt, outbit, sr, duration, mode = scenario
    frames = sr//8 if short else int(round((duration + .25) * sr))
    t = np.arange(frames) / sr
    data = np.array([.04*np.sin(2*np.pi*(137+ch*113)*t) + .02*np.sin(2*np.pi*(311+ch*173)*t)
                     for ch in range(inch)])
    for ch in range(inch):
        data[ch, min(frames-1, frames//2+ch*7)] += .25
    path = folder / (('short' if short else 'input') + '.' + fmt)
    _save_multichannel_audio(data, str(path), sr, AUDIO_FILE_FORMATS[fmt], bit)
    decoded = validate(path, inch, frames, sr, fmt, bit)
    tolerance = (2**(-(16 if bit == 0 else 24 if bit == 1 else 32)+1) if bit != 3 else 1e-7)
    error = float(abs(decoded-data).max())
    if error > tolerance:
        raise AssertionError(f'Input codec channel/sample roundtrip error {error} > {tolerance}')
    return path, error


def make_snapshot(path, source, frames, sr, outch):
    snap = audit.snapshot(path, source)
    snap['output'].update(totalTime=frames/sr, nchnls=outch, gainSlider=-24.0)
    if path.stem in ('SpectralGate', 'Vectral'):
        snap['modules'][0]['settings']['userSliders']['gthresh'] = [-90, 0, None, 1]
    return snap


def run_jobs(jobs, sr, channels, fmt, bit, mode):
    done = threading.Event()
    results = []
    lock = threading.Lock()
    finished = set()
    def progress(index, job):
        if job.status in ('Done', 'Error'):
            with lock:
                finished.add(job.job_id)
                if len(finished) % 20 == 0:
                    print(f'  {mode}/{fmt}/{channels}ch: {len(finished)}/{len(jobs)} jobs finished', flush=True)
    manager = OfflineRenderManager(RenderSettings(sr=sr, nchnls=channels, buffersize=256,
        audio_file_type=fmt, samp_size=bit, num_threads=2, accel_mode=mode,
        global_fade=.005, crossfade=.08), on_job_update=progress,
        on_complete=lambda result: (results.append(result), done.set()))
    for job in jobs:
        if manager._choose_single_strategy(job, len(jobs)) != mode:
            raise AssertionError('Requested strategy silently fell back')
    manager.start(jobs)
    if not done.wait(300):
        manager.cancel()
        manager._thread.join(timeout=10)
        raise TimeoutError(f'{mode}/{fmt} batch exceeded five minutes')
    manager._thread.join(timeout=10)
    summary = results[0]
    if summary.completed + summary.failed != len(jobs):
        raise AssertionError('Batch did not reach a terminal status for every job')
    return summary


def compare(encoded, reference, bit):
    # PCM outputs must saturate instead of wrapping outside the representable range.
    if bit != 3:
        bits = {0: 16, 1: 24, 2: 32}[bit]
        maximum = min(1-2**(-(bits-1)), float(np.nextafter(np.float32(1), np.float32(0))))
        expected = np.clip(reference, -1, maximum)
        tolerance = 2e-6 + 2**(-(bits-1))
    else:
        expected, tolerance = reference, 2e-6
    error = np.abs(encoded-expected)
    return {'pass': bool(np.all(error <= tolerance)), 'max_error': float(error.max()),
            'absolute_tolerance': tolerance,
            'reference_peak': float(abs(reference).max()),
            'clipped_reference_samples': int(np.count_nonzero(abs(reference) > 1)) if bit != 3 else 0}


def report(rows, start, scenarios, prefix):
    summary = {'modules': len(set(row['module'] for row in rows)), 'cases': len(rows),
        'passed': sum(r['status']=='pass' for r in rows), 'failed': sum(r['status']=='fail' for r in rows),
        'silent_cases': sum(r.get('peak',1)<1e-9 for r in rows),
        'elapsed_seconds': round(time.monotonic()-start,2), 'scenarios': scenarios, 'results': rows}
    path = ROOT / 'tests/reports'
    (path/(prefix+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
    lines = ['# All-module multichannel and codec audit', '',
        f"{summary['passed']}/{len(rows)} cases passed; {summary['failed']} failed across {summary['modules']} modules.", '',
        'Every case compares float-WAV reference master/tap audio against the requested output codec/layout, including exact frame count, rate, channels, container and bit depth.',
        'Input codecs are roundtripped with distinct per-channel signals. Comparisons preserve channel/sample positions and use PCM-aware tolerances. This is not an oracle for the spatial design of each processor.',
        'Gate diagnostics use -90 dB; spectral buffers use a 0.125-second source. Other settings are init. Silent cases verify metadata/codecs only; they cannot establish DSP correctness.', '',
        '| Scenario | Input | Output | Rate | Mode |', '| --- | --- | --- | --- | --- |']
    for v in scenarios:
        lines.append(f'| {v[0]} | {v[1]}ch {v[2]} {BITS[v[3]]} | {v[4]}ch {v[5]} {BITS[v[6]]} | {v[7]} | {v[9]} |')
    lines += ['', '| Module | Scenario | Result | Notes |', '| --- | --- | --- | --- |']
    for row in rows:
        details = list(row['errors'])
        for key,val in row.get('checks',{}).items():
            if not val['pass']: details.append(f"{key}: max error {val['max_error']:.6g}")
        if row.get('audible_diagnostic'):
            details.append('audible diagnostic; '+str(row['frames'])+' frames' + ('; four gate thresholds -80 dB' if 'MultiBandGate' in row['module'] else ''))
        if row.get('peak',1)<1e-9: details.append('silent: DSP equality inconclusive')
        if not row.get('uses_input',True):details.append('synthesis without file input; input codec not used by module')
        text='; '.join(details).replace('|','/').replace('\n',' ')
        lines.append(f"| {row['module']} | {row['scenario']} | {row['status']} | {text} |")
    (path/(prefix+'.md')).write_text('\n'.join(lines)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',action='append',choices=[s[0] for s in SCENARIOS])
    parser.add_argument('--module',default='')
    parser.add_argument('--report-prefix', default='multichannel_formats')
    parser.add_argument('--audible-diagnostics', action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.report_prefix):
        parser.error('report-prefix must contain only letters, digits, underscores or hyphens')
    scenarios=[s for s in SCENARIOS if not args.scenario or s[0] in args.scenario]
    modules=[p for p in sorted((ROOT/'Resources/modules').rglob('*.c5')) if args.module in str(p)]
    rows=[];start=time.monotonic()
    server=Server(sr=48000,nchnls=64,buffersize=256,audio='manual',duplex=0).boot()
    server.verbosity=0
    try:
        for scenario in scenarios:
            name,inch,infmt,inbit,outch,outfmt,outbit,sr,duration,mode=scenario
            frames=int(round(duration*sr))+17
            print(f'SCENARIO {name}: {inch}->{outch}ch {infmt}->{outfmt} {sr}Hz',flush=True)
            with tempfile.TemporaryDirectory(prefix='cecilia-format-matrix-') as temp:
                folder=Path(temp)
                source,source_error=write_fixture(folder,scenario)
                short_source,short_error=write_fixture(folder,scenario,short=True)
                references=[];outputs=[]
                for i,path in enumerate(modules):
                    sound=short_source if path.stem in ('BinWarper','SpectralWarper') else source
                    case_frames = frames
                    if args.audible_diagnostics and outch == 64 and path.stem in ('MultiBandDelay', 'BucketBrigadeDevice'):
                        case_frames = round(1.25*sr)+17
                    snap=make_snapshot(path,sound,case_frames,sr,outch)
                    if args.audible_diagnostics and path.stem == 'MultiBandGate':
                        for band in range(1,5):
                            snap['modules'][0]['settings']['userSliders']['thresh'+str(band)] = [-80,0,None,1]
                    for label,jobs,fmt in [('ref',references,'wav'),('encoded',outputs,outfmt)]:
                        master=str(folder/f'{i}_{label}.{fmt}');tap=str(folder/f'{i}_{label}_tap.{fmt}')
                        jobs.append(RenderJob(f'{i}_{label}',path.stem,master,copy.deepcopy(snap),module_outputs={'a':tap}))
                run_jobs(references,sr,outch,'wav',3,'single')
                run_jobs(outputs,sr,outch,outfmt,outbit,mode)
                for path,reference,encoded in zip(modules,references,outputs):
                    row={'module':str(path.relative_to(ROOT/'Resources/modules')),'scenario':name,
                        'uses_input':bool(audit.inputs_for(path)), 'input_roundtrip_error':source_error,
                        'checks':{},'errors':[],
                        'audible_diagnostic':bool(args.audible_diagnostics),
                        'frames':round(reference.snapshot['output']['totalTime']*sr)}
                    for job in (reference,encoded):
                        if job.status!='Done':row['errors'].append(job.job_id+': '+str(job.error or job.status))
                    if not row['errors']:
                        try:
                            for key,rpath,epath in [('master',reference.output_path,encoded.output_path),
                                ('tap',reference.module_outputs['a'],encoded.module_outputs['a'])]:
                                r=validate(rpath,outch,row['frames'],sr,'wav',3)
                                e=validate(epath,outch,row['frames'],sr,outfmt,outbit)
                                row['checks'][key]=compare(e,r,outbit)
                                if key=='master':row['peak']=float(abs(r).max())
                        except Exception as exc:row['errors'].append(str(exc))
                    if args.audible_diagnostics and row.get('peak',0)<1e-9:
                        row['errors'].append('Audible diagnostic remained silent.')
                    row['status']='fail' if row['errors'] or any(not c['pass'] for c in row['checks'].values()) else 'pass'
                    rows.append(row)
                    print(f"  {row['module']}: {row['status']}",flush=True)
                    if row['status'] == 'fail':
                        print('  FAILURE ' + json.dumps(row), flush=True)
                report(rows,start,scenarios,args.report_prefix)
    finally:
        server.shutdown()
    summary=report(rows,start,scenarios,args.report_prefix)
    print(f"FINAL: {summary['passed']}/{summary['cases']} passed; {summary['failed']} failed",flush=True)
    return bool(summary['failed'])

if __name__=='__main__':
    sys.exit(main())
