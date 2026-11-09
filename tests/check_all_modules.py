"""Audit every shipped module through real offline workers.

Run: cecillia/bin/python tests/check_all_modules.py
Writes tests/reports/offline_modules.json and offline_modules.md.
Audio stays in a temporary directory; each job has a bounded wait.
"""
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from Resources.OfflineRender import (OfflineRenderManager, RenderJob, RenderSettings,
    _read_wav_float64, _write_wav_float32, apply_sound_to_snapshot)

SR = 44100
FRAMES = 4 * SR + 17
CHANNELS = 4
TOLERANCE = 2e-6
REPEAT_MODULES = {'Pitch/RandomAccumulator.c5', 'Resonators&Verbs/WGuideBank.c5',
                  'Synthesis/StochGrains.c5', 'Synthesis/StochGrains2.c5', 'Time/Stutterer.c5'}
SILENT_DIAGNOSTICS = {'Spectral/BinWarper.c5', 'Spectral/SpectralWarper.c5',
                      'Spectral/SpectralGate.c5', 'Spectral/Vectral.c5'}


def inputs_for(path):
    """Read declarative input names without executing module source in the test host."""
    tree = ast.parse(path.read_text())
    interface = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'Interface' for t in node.targets))
    inputs = {}
    for node in ast.walk(interface):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('csampler', 'cfilein'):
            name = next(ast.literal_eval(k.value) for k in node.keywords if k.arg == 'name')
            inputs[name] = {'type': node.func.id, 'mode': 0, 'loopMode': 0}
    return inputs


def snapshot(path, sound):
    snap = {'source_id': 'a', 'source_ids': ['a'], 'connections': [],
        'output_connections': ['a'], 'positions': {'a': [0, 0]}, 'muted_ids': [],
        'selected_id': 'a', 'view': 'graph',
        'modules': [{'id': 'a', 'module_path': str(path), 'builtin': True, 'preset': 'init',
                     'settings': {'userInputs': inputs_for(path), 'userSliders': {},
                                  'userTogglePopups': {}, 'userGraph': {}}}],
        'output': {'totalTime': FRAMES / SR, 'nchnls': CHANNELS, 'gainSlider': -6,
                   'startOffset': 0, 'plugins': {}, 'userGraph': {}}}
    for name in snap['modules'][0]['settings']['userInputs']:
        snap = apply_sound_to_snapshot(snap, str(sound), input_name=name)
    return snap


def render(snap, mode, folder, label, taps=True, stems=False):
    output = folder / (label + '.wav')
    paths = {m['id']: str(folder / (label + '_' + m['id'] + '.wav'))
             for m in snap['modules']} if taps else {}
    job = RenderJob(label, label, str(output), snap, module_outputs=paths, export_stems=stems)
    settings = RenderSettings(sr=SR, nchnls=CHANNELS, buffersize=256, num_threads=2,
                              accel_mode=mode, global_fade=0.005, samp_size=3, crossfade=0.08)
    done = threading.Event()
    summaries = []
    manager = OfflineRenderManager(settings, on_complete=lambda result: (summaries.append(result), done.set()))
    strategy = manager._choose_single_strategy(job, 1)
    if strategy != mode:
        raise AssertionError(f'{mode} silently fell back to {strategy}')
    manager.start([job])
    if not done.wait(60):
        manager.cancel()
        manager._thread.join(timeout=10)
        raise TimeoutError(f'{label} exceeded 60 seconds')
    manager._thread.join(timeout=10)
    result = summaries[0]
    if result.completed != 1 or result.failed:
        raise RuntimeError(job.error or f'{label}: {job.status}')
    arrays = {}
    for name, path in {'master': str(output), **paths, **{
            f'branch_{i}': p for i, p in enumerate(job.stem_paths) if p not in paths.values()}}.items():
        data = _read_wav_float64(path)
        if data is None or data.shape != (CHANNELS, FRAMES):
            raise AssertionError(f'{name}: shape {None if data is None else data.shape}, expected {(CHANNELS, FRAMES)}')
        if not np.isfinite(data).all():
            raise AssertionError(f'{name}: nonfinite audio')
        arrays[name] = data
    return arrays


def compare(a, b):
    error = abs(a - b)
    seam = FRAMES // 2
    return {'max_error': float(error.max()),
            'seam_max_error': float(error[:, seam-2048:seam+2048].max()),
            'rms_error': float(np.sqrt(np.mean(error * error))),
            'pass': bool(np.all(error <= TOLERANCE))}


def check_module(path, sound, folder, diagnostic=False):
    row = {'module': str(path.relative_to(ROOT / 'Resources/modules')), 'checks': {}, 'errors': []}
    snap = snapshot(path, sound)
    if diagnostic and path.stem in ('SpectralGate', 'Vectral'):
        snap['modules'][0]['settings']['userSliders']['gthresh'] = [-90, 0, None, 1]
    single = None
    try:
        single = render(snap, 'single', folder, 'single')
        row['peak'] = float(abs(single['master']).max())
        row['checks']['single_master_and_tap_format'] = True
    except Exception as exc:
        row['errors'].append('single: ' + str(exc))
    try:
        chunk = render(snap, 'chunks', folder, 'chunks')
        row['checks']['chunk_master_and_tap_format'] = True
        if single is not None:
            for name in ('master', 'a'):
                row['checks']['chunks_' + name] = compare(chunk[name], single[name])
            if row['module'] in REPEAT_MODULES or any(not row['checks']['chunks_' + name]['pass'] for name in ('master', 'a')):
                repeated = render(snap, 'single', folder, 'repeat')
                row['checks']['single_reproducibility'] = compare(repeated['master'], single['master'])
    except Exception as exc:
        row['errors'].append('chunks: ' + str(exc))
    branch = copy.deepcopy(snap)
    branch['modules'].append(dict(copy.deepcopy(branch['modules'][0]), id='b'))
    branch['source_ids'].append('b')
    branch['output_connections'].append('b')
    branch['positions']['b'] = [0, 100]
    try:
        serial = render(branch, 'single', folder, 'serial_branches', taps=False)
        parallel = render(branch, 'branches', folder, 'parallel_branches', taps=False, stems=True)
        row['checks']['branch_stem_formats'] = len(parallel) == 3
        row['checks']['parallel_routing'] = compare(serial['master'], parallel['master'])
    except Exception as exc:
        row['errors'].append('branches: ' + str(exc))
    row['status'] = 'fail' if row['errors'] or any(
        (not value if isinstance(value, bool) else not value['pass'])
        for value in row['checks'].values()) else ('inconclusive' if row.get('peak', 0) < 1e-8 else 'pass')
    return row


def write_report(rows, elapsed):
    folder = ROOT / 'tests/reports'
    folder.mkdir(exist_ok=True)
    summary = {'modules': len(rows), 'passed': sum(r['status'] in ('pass', 'pass_with_diagnostic') for r in rows),
               'failed': sum(r['status'] == 'fail' for r in rows),
               'inconclusive': sum(r['status'] == 'inconclusive' for r in rows), 'elapsed_seconds': round(elapsed, 2),
               'sample_rate': SR, 'frames': FRAMES, 'channels': CHANNELS,
               'absolute_tolerance': TOLERANCE, 'results': rows}
    (folder / 'offline_modules.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['# Shipped module offline audit', '',
             f"{summary['passed']}/{len(rows)} passed all checks; {summary['failed']} failed; {summary['inconclusive']} inconclusive (silent). {elapsed:.1f} seconds. Four previously silent modules also receive audible diagnostic fixtures.", '',
             f'{SR} Hz, {CHANNELS} channels, {FRAMES} frames, init settings, absolute tolerance {TOLERANCE:g}.', '',
             'Checks: exact lengths/channels and finite audio for masters/taps/stems; single/chunk sample equality; disjoint-branch sum equality.',
             'Channel identity is checked by single/chunk equality; this does not establish intended spatial behavior for every effect.',
             'This covers init settings, not every preset or routing topology. Reproducibility failures are reported rather than ignored.', '',
             '| Module | Result | Details |', '| --- | --- | --- |']
    for row in rows:
        details = list(row['errors'])
        if 'diagnostic' in row:
            diag = row['diagnostic']
            details.append('audible diagnostic: ' + diag['status'] + '; ' + row['diagnostic_fixture'])
            details.extend(diag['errors'])
            for name, value in diag['checks'].items():
                if isinstance(value, dict) and not value['pass']:
                    details.append(f"diagnostic {name}: max {value['max_error']:.6g}")
        for name, value in row['checks'].items():
            if isinstance(value, dict) and not value['pass']:
                details.append(f"{name}: max {value['max_error']:.6g}, seam {value['seam_max_error']:.6g}")
            elif value is False:
                details.append(name)
        if row.get('peak', 1) < 1e-8:
            details.append('original init fixture silent; see audible diagnostic' if 'diagnostic' in row else 'silent init output; equality is inconclusive')
        details = [v.replace('|', '/').replace('\n', ' ') for v in details]
        lines.append(f"| {row['module']} | {row['status']} | {'; '.join(details)} |")
    (folder / 'offline_modules.md').write_text('\n'.join(lines) + '\n')
    return summary


def main():
    start = time.monotonic()
    rows = []
    modules = sorted((ROOT / 'Resources/modules').rglob('*.c5'))
    with tempfile.TemporaryDirectory(prefix='cecilia-all-modules-') as temp:
        folder = Path(temp)
        t = np.arange(FRAMES + SR) / SR
        signal = np.array([0.06 * np.sin(2*np.pi*f*t) + 0.025*np.sin(2*np.pi*(f*3)*t)
                           for f in (137, 251, 389, 503)])
        for ch in range(CHANNELS):
            signal[ch, FRAMES//2 - 13 + 7*ch] += 0.4
        source = folder / 'source.wav'
        _write_wav_float32(signal, str(source), SR)
        diagnostic_source = folder / 'diagnostic_source.wav'
        # Buffers must fill before a four-second render finishes. Lower gate
        # thresholds for audible tests without changing the modules' defaults.
        _write_wav_float32(signal[:, :SR//2] * 3, str(diagnostic_source), SR)
        for index, path in enumerate(modules):
            work = folder / str(index)
            work.mkdir()
            try:
                row = check_module(path, source, work)
                if row['module'] in SILENT_DIAGNOSTICS:
                    diag = check_module(path, diagnostic_source, work, diagnostic=True)
                    row['diagnostic'] = diag
                    row['diagnostic_fixture'] = '0.5-second source, 3x amplitude' + (
                        ', gate threshold -90 dB' if path.stem in ('SpectralGate', 'Vectral') else '')
                    if row['status'] == 'inconclusive':
                        row['status'] = 'pass_with_diagnostic' if diag['status'] == 'pass' else diag['status']
                    elif diag['status'] == 'fail':
                        row['status'] = 'fail'
            except Exception as exc:
                row = {'module': str(path.relative_to(ROOT / 'Resources/modules')),
                       'status': 'fail', 'checks': {}, 'errors': [str(exc)]}
            rows.append(row)
            print(f"{index+1}/{len(modules)} {row['module']}: {row['status']}", flush=True)
            write_report(rows, time.monotonic() - start)
            # Avoid accumulating hundreds of rendered files during the audit.
            for audio in work.glob('*.wav'):
                audio.unlink()
    result = write_report(rows, time.monotonic() - start)
    print(f"Passed {result['passed']}/{result['modules']}; failed {result['failed']}", flush=True)
    return bool(result['failed'] or result['inconclusive'])


if __name__ == '__main__':
    sys.exit(main())
