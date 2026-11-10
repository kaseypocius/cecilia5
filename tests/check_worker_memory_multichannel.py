"""Audit all modules with large 50-channel input and 96/192 kHz exports.

Each case renders two identical queue entries, checks every exported sample,
and samples the aggregate native-worker RSS. Results distinguish silent init
output from audible output. Fixtures/exports are temporary. No user audio is read.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from check_all_modules import snapshot
from Resources.AudioFileIO import AudioReader, AudioWriter
from Resources.OfflineRender import OfflineRenderManager, RenderJob, RenderSettings
from Resources.RenderMemory import MIB, estimate_snapshot_memory, process_rss


def run_case(module, source, folder, rate, budget, timeout, channels=50):
    snap = snapshot(module, source)
    snap['output'].update(totalTime=2.2, nchnls=channels)
    events = []
    settings = RenderSettings(sr=rate, nchnls=channels, num_threads=4, accel_mode='single',
                              buffersize=256, samp_size=3)
    jobs = [RenderJob(str(i), module.stem, str(folder/f'output_{i}.wav'), snap) for i in range(2)]
    manager = OfflineRenderManager(settings, on_progress=events.append)
    peak = active = 0
    started = time.monotonic()
    stop = threading.Event()
    reason = []
    def watch():
        nonlocal peak, active
        while not stop.wait(.025):
            pool = manager._pool
            if pool:
                with pool._handles_lock:
                    handles = list(pool._all_handles)
                    active = max(active, len(pool._active_handles))
                resident = sum(process_rss(handle._proc.pid) or 0 for handle in handles
                               if handle._proc is not None and handle._proc.poll() is None)
                peak = max(peak, resident)
            if time.monotonic()-started > timeout:
                reason.append('timeout')
                manager.cancel()
                return
    thread = threading.Thread(target=watch, daemon=True)
    thread.start()
    try:
        result = manager.run_blocking(jobs)
    finally:
        stop.set()
        thread.join(timeout=2)
    row = {'module': str(module.relative_to(ROOT/'Resources/modules')), 'sample_rate': rate,
           'input_channels': 50, 'output_channels': channels, 'input_bytes': source.stat().st_size,
           'budget_bytes': budget, 'estimated_worker_bytes': estimate_snapshot_memory(snap, channels, rate),
           'peak_pool_rss_bytes': peak, 'peak_active_workers': active,
           'elapsed_seconds': round(time.monotonic()-started, 3), 'status': 'pass',
           'errors': [job.error for job in jobs if job.error]}
    if reason or result.failed or result.cancelled or result.completed != 2:
        row['status'] = reason[0] if reason else 'error'
        return row
    peak_sample = max_error = 0.0
    with AudioReader(jobs[0].output_path) as left, AudioReader(jobs[1].output_path) as right:
        expected = (round(2.2*rate), channels, rate)
        for reader in (left, right):
            assert (reader.info.frames, reader.info.channels, reader.info.sample_rate) == expected
        for block in left.blocks():
            other = right.read(len(block))
            assert np.isfinite(block).all() and np.isfinite(other).all(), 'nonfinite samples'
            max_error = max(max_error, float(np.abs(block-other).max()))
            peak_sample = max(peak_sample, float(np.abs(block).max()))
    row.update(peak_sample=peak_sample, silent=peak_sample < 1e-7,
               repeat_max_error=max_error, repeat_matches=max_error <= 2e-6,
               cleanup_complete=manager._pool is None and not manager._temp_dirs)
    if not row['repeat_matches'] or not row['cleanup_complete']:
        row['status'] = 'error'
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', action='append', help='Relative module path; default is all modules')
    parser.add_argument('--rates', nargs='+', type=int, default=[96000, 192000])
    parser.add_argument('--input-mib', type=int, default=64)
    parser.add_argument('--budget-mib', type=int, default=8192)
    parser.add_argument('--output-channels', type=int, default=50)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--report-prefix', default='worker_memory_multichannel')
    args = parser.parse_args()
    report = ROOT/'tests/reports'
    report.mkdir(exist_ok=True)
    paths = sorted((ROOT/'Resources/modules').rglob('*.c5'))
    if args.module:
        paths = [path for path in paths if str(path.relative_to(ROOT/'Resources/modules')) in args.module]
    if not paths:
        parser.error('No matching modules')
    budget = args.budget_mib*MIB
    os.environ['CECILIA_RAM_BUDGET_BYTES'] = str(budget)
    rows = []
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
              ['Resources/RenderMemory.py', 'Resources/OfflineRender.py', 'Resources/OfflineRenderDialog.py',
               'Resources/audio.py', 'Resources/modules/Multiband/MultiBandDelay.c5']}
    with tempfile.TemporaryDirectory(prefix='cecilia-multichannel-memory-') as directory:
        folder = Path(directory)
        source = folder/'source.wav'
        frames = args.input_mib*MIB//(50*4)
        rate = 48000
        freqs = 110+20*np.arange(50)
        # 0.1-second periodic block keeps the fixture bounded while physically
        # writing the entire file. Each channel has a distinct frequency.
        block = .04*np.sin(2*np.pi*np.arange(rate//10)[:, None]*freqs/rate)
        with AudioWriter(source, rate, 50, frames) as writer:
            for start in range(0, frames, len(block)):
                writer.write(block[:min(len(block), frames-start)])
        for module in paths:
            for output_rate in args.rates:
                try:
                    row = run_case(module, source, folder, output_rate, budget, args.timeout, args.output_channels)
                except Exception as error:
                    row = {'module': str(module.relative_to(ROOT/'Resources/modules')),
                           'sample_rate': output_rate, 'status': 'error', 'errors': [str(error)]}
                rows.append(row)
                print(json.dumps(row), flush=True)
                for path in folder.glob('output_*.wav'):
                    path.unlink()
                (report/(args.report_prefix+'.json')).write_text(json.dumps(
                    {'source_hashes': hashes, 'cases': rows}, indent=2)+'\n')
    lines = ['# Worker memory: large multichannel/high-rate audit', '',
             f'Input: {args.input_mib} MiB float32, 50 channels, 48 kHz. Output: {args.output_channels} channels at '+
             '/'.join(str(rate//1000) for rate in args.rates)+' kHz, 2.2 seconds.',
             f'Two identical queue entries per case; four requested workers; {args.budget_mib} MiB shared budget.', '',
             'Every completed case checks both outputs for exact metadata, all-sample finiteness, '+
             'repeat equality (absolute tolerance 0.000002), and coordinator cleanup. '+
             'Silent init output is recorded and does not establish audible DSP correctness.', '',
             '| Module | kHz | Result | Active workers | Peak pool MiB | Seconds | Silent |',
             '| --- | ---: | --- | ---: | ---: | ---: | --- |']
    for row in rows:
        lines.append(f"| {row['module']} | {row['sample_rate']//1000} | {row['status']} | "+
                     f"{row.get('peak_active_workers', '')} | {row.get('peak_pool_rss_bytes', 0)/MIB:.1f} | "+
                     f"{row.get('elapsed_seconds', '')} | {row.get('silent', '')} |")
    passed = sum(row['status'] == 'pass' for row in rows)
    lines += ['', f'Result: {passed}/{len(rows)} cases passed. '+
              f"Silent completed cases: {sum(row.get('silent', False) for row in rows)}.", '',
              'Peak RSS samples sum all live native workers at 25 ms intervals; short peaks can be missed. '+
              'This audit covers init settings and these layouts, rather than arbitrary presets or sustained leaks.', '']
    (report/(args.report_prefix+'.md')).write_text('\n'.join(lines))
    return int(passed != len(rows))


if __name__ == '__main__':
    raise SystemExit(main())
