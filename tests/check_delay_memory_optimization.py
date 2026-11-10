"""Compare baseline and optimized MultiBandDelay with a 1 GiB/50ch source.

Run with --baseline-root pointing to the unmodified source snapshot. Children
load that root explicitly; all fixtures and outputs are temporary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from Resources.AudioFileIO import AudioReader, AudioWriter


def child(root, source, folder, rate, label):
    sys.path.insert(0, str(root))
    # This file imports only the unchanged AudioFileIO before selecting root.
    import Resources
    Resources.__path__ = [str(root/'Resources')]
    from Resources.OfflineRender import OfflineRenderManager, RenderSettings, RenderJob, apply_sound_to_snapshot
    from Resources.RenderMemory import process_rss
    module = root/'Resources/modules/Multiband/MultiBandDelay.c5'
    snap = {'modules': [{'id': 'a', 'module_path': str(module), 'builtin': True,
                        'settings': {'userInputs': {'snd': {'type': 'csampler', 'mode': 0}},
                                     'userSliders': {}, 'userTogglePopups': {}, 'userGraph': {}}}],
            'source_id': 'a', 'source_ids': ['a'], 'connections': [], 'output_connections': ['a'],
            'positions': {}, 'muted_ids': [], 'selected_id': 'a', 'view': 'graph',
            'output': {'totalTime': 2.2, 'nchnls': 50, 'gainSlider': -6, 'plugins': {}}}
    snap = apply_sound_to_snapshot(snap, str(source), input_name='snd')
    manager = OfflineRenderManager(RenderSettings(sr=rate, nchnls=50, num_threads=4,
                                   accel_mode='single', samp_size=3, buffersize=256))
    jobs = [RenderJob(str(i), label, str(folder/f'{label}_{rate}_{i}.wav'), snap) for i in range(2)]
    stop = threading.Event()
    peak_pool = peak_worker = active = 0
    def watch():
        nonlocal peak_pool, peak_worker, active
        while not stop.wait(.025):
            pool = manager._pool
            if pool:
                with pool._handles_lock:
                    handles = list(pool._all_handles)
                    active = max(active, len(getattr(pool, '_active_handles', [])))
                values = [process_rss(h._proc.pid) or 0 for h in handles
                          if h._proc and h._proc.poll() is None]
                peak_pool = max(peak_pool, sum(values))
                peak_worker = max([peak_worker, *values])
                if not hasattr(pool, '_active_handles'):
                    active = max(active, len(values))
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    start = time.monotonic()
    try:
        result = manager.run_blocking(jobs)
    finally:
        stop.set()
        watcher.join(timeout=2)
    row = {'version': label, 'sample_rate': rate, 'completed': result.completed,
           'errors': [job.error for job in jobs if job.error], 'peak_pool_rss_bytes': peak_pool,
           'peak_worker_rss_bytes': peak_worker, 'peak_active_workers': active,
           'elapsed_seconds': round(time.monotonic()-start, 3)}
    print(json.dumps(row), flush=True)
    return int(result.completed != 2 or result.failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--input-mib', type=int, default=1024)
    parser.add_argument('--report-prefix', default='delay_memory_optimization')
    parser.add_argument('--child', nargs=5)
    args = parser.parse_args()
    if args.child:
        root, source, folder, rate, label = args.child
        return child(Path(root), Path(source), Path(folder), int(rate), label)
    if args.baseline_root is None:
        parser.error('--baseline-root is required')
    rows = []
    comparisons = []
    with tempfile.TemporaryDirectory(prefix='cecilia-delay-memory-comparison-') as directory:
        folder = Path(directory)
        source = folder/'source.wav'
        frames = args.input_mib*1024**2//(50*4)
        rate = 48000
        block = .04*np.sin(2*np.pi*np.arange(rate//10)[:, None]*(110+20*np.arange(50))/rate)
        with AudioWriter(source, rate, 50, frames) as writer:
            for start in range(0, frames, len(block)):
                writer.write(block[:min(len(block), frames-start)])
        for rate in (96000, 192000):
            for label, root in [('baseline', args.baseline_root.resolve()), ('optimized', ROOT)]:
                env = os.environ.copy()
                env.update(HOME=str(folder), PYTHONDONTWRITEBYTECODE='1', CECILIA_RAM_BUDGET_GB='8')
                env.pop('CECILIA_RAM_BUDGET_BYTES', None)
                result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--child',
                                         str(root), str(source), str(folder), str(rate), label],
                                        cwd=root, env=env, capture_output=True, text=True, timeout=240)
                parsed = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                assert parsed, result.stdout+result.stderr
                row = parsed[-1]
                rows.append(row)
                print(json.dumps(row), flush=True)
                assert result.returncode == 0, result.stdout+result.stderr
            maximum = 0.0
            for index in range(2):
                with AudioReader(folder/f'baseline_{rate}_{index}.wav') as left, \
                     AudioReader(folder/f'optimized_{rate}_{index}.wav') as right:
                    assert (left.info.frames, left.info.channels, left.info.sample_rate) == (round(2.2*rate), 50, rate)
                    assert left.info == right.info
                    for block in left.blocks():
                        other = right.read(len(block))
                        assert np.isfinite(block).all() and np.isfinite(other).all()
                        maximum = max(maximum, float(np.abs(block-other).max()))
            comparisons.append({'sample_rate': rate, 'max_error': maximum, 'pass': maximum <= 2e-6})
            print(json.dumps(comparisons[-1]), flush=True)
            for path in folder.glob('*_*_*.wav'):
                path.unlink()
    report = {'input_mib': args.input_mib, 'input_channels': 50, 'budget_gib': 8,
              'measurements': rows, 'comparisons': comparisons}
    report['source_hashes'] = {label: {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in ['Resources/OfflineRender.py', 'Resources/RenderMemory.py', 'Resources/audio.py',
                     'Resources/modules/Multiband/MultiBandDelay.c5']}
        for label, root in [('baseline', args.baseline_root), ('optimized', ROOT)]}
    (ROOT/'tests/reports'/(args.report_prefix+'.json')).write_text(json.dumps(report, indent=2)+'\n')
    return int(not all(row['pass'] for row in comparisons))


if __name__ == '__main__':
    raise SystemExit(main())
