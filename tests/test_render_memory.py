import os
import tempfile
import unittest
from pathlib import Path
import numpy as np
from Resources.AudioFileIO import AudioReader, AudioWriter
from Resources.RenderMemory import estimate_snapshot_memory, worker_limit, MIB


class RenderMemoryTests(unittest.TestCase):
    def test_counts_mono_filein_replication_and_offsets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'mono.wav')
            with AudioWriter(path,1000,1,1000) as stream:
                stream.write(np.zeros((1000,1)))
            slot={'path':path,'type':'cfilein','offinput':.25}
            snap={'modules':[{'settings':{'userInputs':{'input':slot}}}]}
            self.assertEqual(estimate_snapshot_memory(snap,64),256*MIB+2*750*64*4)
            slot['type']='csampler'
            self.assertEqual(estimate_snapshot_memory(snap,64),256*MIB+2*750*4)
            slot['mode']=1
            self.assertEqual(estimate_snapshot_memory(snap,64),256*MIB)

    def test_worker_count_respects_largest_job_and_budget(self):
        self.assertEqual(worker_limit([3*1024**3],8,10*1024**3),3)
        self.assertEqual(worker_limit([256*MIB],4,10*1024**3),4)
        self.assertEqual(worker_limit([20*1024**3],8,10*1024**3),1)

    def test_native_precision_changes_table_estimate(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'input.wav')
            with AudioWriter(path, 1000, 2, 1000) as stream:
                stream.write(np.zeros((1000, 2)))
            snap = {'modules': [{'settings': {'userInputs': {'snd': {
                'path': path, 'type': 'csampler'}}}}]}
            for precision, width in [('32 bit', 4), ('64 bit', 8)]:
                lib = SimpleNamespace(getVar=lambda key: precision)
                with self.subTest(precision=precision), patch.dict(sys.modules, {'Resources.CeciliaLib': lib}):
                    self.assertEqual(estimate_snapshot_memory(snap, 2), 256*MIB+2*1000*2*width)

    def test_mixed_batch_capacity_does_not_charge_every_job_the_largest_size(self):
        from Resources.RenderMemory import batch_worker_limit
        self.assertEqual(batch_worker_limit([900*MIB, 300*MIB, 300*MIB, 300*MIB], 4, 1024*MIB), 3)
        self.assertEqual(batch_worker_limit([2048*MIB], 4, 1024*MIB), 1)


class SharedPoolMemoryTests(unittest.TestCase):
    def run_native_pool(self, allocations, budget):
        import sys
        import threading
        from unittest.mock import patch
        from Resources.OfflineRender import _WorkerPool, _SubprocessWorkerHandle, EVENT_PREFIX
        from Resources.RenderMemory import process_rss
        if process_rss(os.getpid()) is None:
            self.skipTest('Native RSS telemetry unavailable')
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder)/'child.py'
            script.write_text('import json,sys,time\n'
                + f'prefix={EVENT_PREFIX!r}\n'
                + 'print(prefix+json.dumps({"type":"ready"}),file=sys.stderr,flush=True)\n'
                + 'for line in sys.stdin:\n'
                + ' request=json.loads(line)\n'
                + ' if request["cmd"]=="quit":break\n'
                + ' allocation=bytearray(request["spec"]["bytes"])\n'
                + ' time.sleep(.5)\n'
                + ' print(prefix+json.dumps({"type":"done"}),file=sys.stderr,flush=True)\n'
                + ' del allocation\n')
            command = ([sys.executable, str(script)], folder, os.environ.copy())
            with patch.object(_SubprocessWorkerHandle, '_build_cmd', return_value=command):
                pool = _WorkerPool(2)
                pool.memory_limit_bytes = budget
                try:
                    futures = [pool.submit_task('render', {'bytes': value}, threading.Event())
                               for value in allocations]
                    results = []
                    for future in futures:
                        try:
                            results.append(future.result(timeout=5))
                        except MemoryError as error:
                            results.append(error)
                    return results
                finally:
                    pool.shutdown()

    def test_heavy_worker_can_borrow_light_workers_unused_share(self):
        results = self.run_native_pool([80*MIB, MIB], 128*MIB)
        self.assertTrue(all(isinstance(result, dict) for result in results), results)

    def test_aggregate_guard_stops_over_budget_combination(self):
        results = self.run_native_pool([80*MIB, 80*MIB], 128*MIB)
        failures = [result for result in results if isinstance(result, MemoryError)]
        self.assertEqual(len(failures), 1, results)
        self.assertIn('shared render memory budget', str(failures[0]))

    def test_cancelled_memory_waiter_returns_without_leaking_reservation(self):
        import threading
        from Resources.RenderMemory import MemoryReservations
        reservations = MemoryReservations(512*MIB)
        held = reservations.acquire(512*MIB, threading.Event())
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(InterruptedError):
            reservations.acquire(256*MIB, cancelled)
        self.assertEqual(reservations.used, held)
        reservations.release(held)
        self.assertEqual(reservations.used, 0)

    def test_mixed_queue_reserves_each_jobs_memory(self):
        import threading
        import time
        from unittest.mock import patch
        from Resources.OfflineRender import OfflineRenderManager, RenderSettings, RenderJob
        lock = threading.Lock()
        active = set()
        peak_small = [0]
        large_started = threading.Event()
        small_jobs = threading.Barrier(3)
        class Handle:
            def __init__(self, index): self.worker_index=index; self._closed=False
            def execute(self, cmd, spec, cancel_event, on_progress=None):
                name = spec['job_id']
                with lock:
                    if name == 'large':
                        assert not active, active
                    else:
                        assert 'large' not in active, active
                    active.add(name)
                    if name == 'large':
                        large_started.set()
                    peak_small[0] = max(peak_small[0], len(active-{'large'}))
                try:
                    if name == 'large': time.sleep(.1)
                    else: small_jobs.wait(timeout=3)
                    return {'duration': 1, 'peak_db': -90, 'module_results': {}}
                finally:
                    with lock: active.remove(name)
            def close(self): self._closed=True
            def terminate(self): self._closed=True
        with tempfile.TemporaryDirectory() as folder:
            jobs = []
            for name, size in [('large', 900*MIB), ('s1', 300*MIB), ('s2', 300*MIB), ('s3', 300*MIB)]:
                snap = {'modules': [], 'estimate': size, 'output': {'totalTime': 1, 'nchnls': 2}}
                jobs.append(RenderJob(name, name, str(Path(folder)/(name+'.wav')), snap))
            with patch('Resources.RenderMemory.render_memory_budget', return_value=1024*MIB), \
                 patch('Resources.RenderMemory.estimate_snapshot_memory', side_effect=lambda snap, channels, rate=None: snap['estimate']), \
                 patch('Resources.OfflineRender._SubprocessWorkerHandle', Handle):
                # The assertion concerns the queue after the large entry has
                # started. Do not rely on executor thread-start order under load.
                def dispatched(index, job):
                    if job.job_id != 'large':
                        assert large_started.wait(10), 'Large fixture did not start'
                result = OfflineRenderManager(RenderSettings(num_threads=4, accel_mode='single'),
                                               on_job_update=dispatched).run_blocking(jobs)
        self.assertEqual((result.completed, result.failed), (4, 0), [job.error for job in jobs])
        self.assertEqual(peak_small[0], 3)


class OfflineDelayCapacityTests(unittest.TestCase):
    def test_fixed_delay_buffer_includes_sample_margin_and_automation_falls_back(self):
        from Resources.RenderMemory import delay_buffer_seconds
        self.assertAlmostEqual(delay_buffer_seconds(15, [.5, .25, .33, .66], 96000), .66+4/96000)
        self.assertEqual(delay_buffer_seconds(15, [.5, None], 96000), 15)
        self.assertEqual(delay_buffer_seconds(15, [float('nan')], 96000), 15)
        self.assertEqual(delay_buffer_seconds(15, [20], 96000), 15)

    def test_live_controls_and_offline_automation_keep_full_delay_capacity(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import patch
        tree = ast.parse((Path(__file__).resolve().parents[1]/'Resources/audio.py').read_text())
        base = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'BaseModule')
        method = next(node for node in base.body if isinstance(node, ast.FunctionDef) and node.name == '_offline_delay_max_seconds')
        slider = SimpleNamespace(getName=lambda: 'delay', getValue=lambda: .5,
                                 getPlay=lambda: False, getWithMidi=lambda: False,
                                 getWithOSC=lambda: False)
        lib = SimpleNamespace(getVar=lambda key: [slider])
        namespace = {'os': os, 'CeciliaLib': lib, '__package__': 'Resources'}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<delay capacity>', 'exec'), namespace)
        capacity = namespace['_offline_delay_max_seconds']
        owner = SimpleNamespace(sr=96000)
        with patch.dict(os.environ, {'CECILIA_OFFLINE_WORKER': '0'}):
            self.assertEqual(capacity(owner, 15, 'delay'), 15)
        with patch.dict(os.environ, {'CECILIA_OFFLINE_WORKER': '1'}):
            self.assertAlmostEqual(capacity(owner, 15, 'delay'), .5+4/96000)
            slider.getPlay = lambda: True
            self.assertEqual(capacity(owner, 15, 'delay'), 15)

    def test_delay_memory_scales_with_rate_and_automated_capacity(self):
        snap = {'modules': [{'module_path': 'MultiBandDelay.c5', 'settings': {'userSliders': {}}}]}
        low = estimate_snapshot_memory(snap, 50, 48000)
        high = estimate_snapshot_memory(snap, 50, 192000)
        self.assertGreater(high, low)
        snap['modules'][0]['settings']['userSliders']['del1'] = [.5, 1]
        self.assertGreater(estimate_snapshot_memory(snap, 50, 192000), high*5)
        snap['modules'][0]['module_path'] = 'WGuideBank.c5'
        waveguides = estimate_snapshot_memory(snap, 50, 192000)-256*MIB
        self.assertEqual(waveguides, int(.8*50*50*192000*4))


class BudgetCalculationAndOverrideTests(unittest.TestCase):
    def test_default_budget_returns_reasonable_bounds(self):
        from Resources.RenderMemory import render_memory_budget
        budget = render_memory_budget()
        self.assertGreaterEqual(budget, 256 * MIB)
        total = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
        self.assertLessEqual(budget, total)

    def test_environment_variable_overrides(self):
        from unittest.mock import patch
        from Resources.RenderMemory import render_memory_budget
        # Bytes override
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_BYTES": str(12 * 1024**3)}):
            self.assertEqual(render_memory_budget(), 12 * 1024**3)
        # MB override
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_MB": "4096"}):
            self.assertEqual(render_memory_budget(), 4096 * MIB)
        # GB override
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_GB": "8.5"}):
            self.assertEqual(render_memory_budget(), int(8.5 * 1024 * MIB))
        # Minimum clamp
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_MB": "64"}):
            self.assertEqual(render_memory_budget(), 256 * MIB)

    def test_preference_overrides(self):
        import sys
        from unittest.mock import patch, MagicMock
        from Resources.RenderMemory import render_memory_budget
        mock_cecilia_lib = MagicMock()
        mock_cecilia_lib.getVar.side_effect = lambda key: 6144 if key == "offlineRamBudgetMB" else None
        with patch.dict(sys.modules, {"Resources.CeciliaLib": mock_cecilia_lib}):
            self.assertEqual(render_memory_budget(), 6144 * MIB)

    def test_fraction_override(self):
        from unittest.mock import patch
        from Resources.RenderMemory import render_memory_budget
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_FRACTION": "0.10"}):
            budget_10 = render_memory_budget()
        with patch.dict(os.environ, {"CECILIA_RAM_BUDGET_FRACTION": "0.50"}):
            budget_50 = render_memory_budget()
        self.assertGreater(budget_50, budget_10)

    def test_expanded_budget_increases_concurrency(self):
        # Comparison: 35% cap on 32GB vs 75% cap on 32GB with 3.5GB jobs
        old_budget = int(32 * 1024**3 * 0.35)  # 11.2 GB
        new_budget = int(32 * 1024**3 * 0.75)  # 24.0 GB
        job_estimate = int(3.5 * 1024**3)
        self.assertEqual(worker_limit([job_estimate], 8, old_budget), 3)
        self.assertEqual(worker_limit([job_estimate], 8, new_budget), 6)




class WorkerMemoryGuardTests(unittest.TestCase):
    def test_native_worker_is_stopped_and_same_slot_restarts(self):
        import os
        import sys
        import threading
        from unittest.mock import patch
        from Resources.OfflineRender import _SubprocessWorkerHandle, EVENT_PREFIX
        from Resources.RenderMemory import process_rss
        if process_rss(os.getpid()) is None:
            self.skipTest('Native RSS telemetry unavailable')
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'child.py'
            script.write_text('import sys,json,time\n'
                +f'prefix={EVENT_PREFIX!r}\n'
                +'print(prefix+json.dumps({"type":"ready"}),file=sys.stderr,flush=True)\n'
                +'for line in sys.stdin:\n'
                +' request=json.loads(line)\n'
                +' if request["cmd"]=="quit":break\n'
                +' allocation=bytearray(32*1024**2)\n'
                +' time.sleep(.3)\n'
                +' print(prefix+json.dumps({"type":"done"}),file=sys.stderr,flush=True)\n')
            command=([sys.executable,str(script)],folder,os.environ.copy())
            with patch.object(_SubprocessWorkerHandle,'_build_cmd',return_value=command):
                handle=_SubprocessWorkerHandle(0)
                try:
                    handle.memory_limit_bytes=20*MIB
                    pid=handle._proc.pid
                    with self.assertRaisesRegex(MemoryError,'memory budget'):
                        handle.execute('render',{},threading.Event())
                    self.assertIsNotNone(handle._proc.poll())
                    handle.memory_limit_bytes=128*MIB
                    self.assertEqual(handle.execute('render',{},threading.Event())['type'],'done')
                    self.assertNotEqual(pid,handle._proc.pid)
                finally:
                    handle.close()


class MemoryFailureCleanupTests(unittest.TestCase):
    def snapshot(self):
        return {'modules':[{'id':'a','module_path':'fixture.c5','settings':{'userInputs':{}}}],
                'output':{'totalTime':1,'nchnls':2}}

    def test_unmonitored_admission_rejection_retains_existing_destination(self):
        from unittest.mock import patch
        from Resources.OfflineRender import RenderJob, RenderSettings, OfflineRenderManager
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'existing.wav';path.write_bytes(b'keep previous render')
            job=RenderJob('reject','reject',str(path),self.snapshot())
            with patch('Resources.RenderMemory.render_memory_budget',return_value=10*MIB), \
                 patch('Resources.RenderMemory.estimate_snapshot_memory',return_value=20*MIB), \
                 patch('Resources.RenderMemory.process_rss',return_value=None):
                result=OfflineRenderManager(RenderSettings(accel_mode='single')).run_blocking([job])
            self.assertEqual(result.failed,1)
            self.assertIn('memory budget',job.error)
            self.assertEqual(path.read_bytes(),b'keep previous render')

    def test_worker_memory_failure_removes_incomplete_destination(self):
        from unittest.mock import patch
        from Resources.OfflineRender import RenderJob, RenderSettings, OfflineRenderManager
        class Handle:
            def __init__(self,index):
                self.worker_index=index;self._closed=False
            def execute(self,cmd,spec,cancel_event,on_progress=None):
                Path(spec['output_path']).write_bytes(b'incomplete')
                raise MemoryError('memory budget exceeded')
            def close(self):self._closed=True
            def terminate(self):self._closed=True
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'incomplete.wav'
            job=RenderJob('fail','fail',str(path),self.snapshot())
            with patch('Resources.OfflineRender._SubprocessWorkerHandle',Handle):
                result=OfflineRenderManager(RenderSettings(accel_mode='single')).run_blocking([job])
            self.assertEqual(result.failed,1)
            self.assertFalse(path.exists())

    def test_cancel_cleanup_removes_only_matching_atomic_encodes(self):
        from Resources.OfflineRender import OfflineRenderManager,RenderSettings
        from Resources.AudioFileIO import encoding_temp_prefix
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'out.wav'
            partial=Path(folder)/(encoding_temp_prefix(target)+'123.tmp');partial.write_bytes(b'incomplete')
            unrelated=Path(folder)/'.cec_encode_unrelated.tmp';unrelated.write_bytes(b'keep')
            manager=OfflineRenderManager(RenderSettings())
            manager._active_outputs.add(str(target))
            manager._cleanup_temps(cancelled=True)
            self.assertFalse(partial.exists())
            self.assertTrue(unrelated.exists())

    def test_single_job_does_not_reserve_memory_for_unused_workers(self):
        from unittest.mock import patch
        from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob
        class Handle:
            def __init__(self,index):self.worker_index=index;self._closed=False
            def execute(self,cmd,spec,cancel_event,on_progress=None):
                return {'duration':1,'peak_db':-90,'module_results':{}}
            def close(self):self._closed=True
            def terminate(self):self._closed=True
        observed=[]
        progress=[]
        manager=OfflineRenderManager(RenderSettings(num_threads=8,accel_mode='single'),
                    on_progress=progress.append,
                    on_job_update=lambda index,job: observed.append(
                        (manager._pool.max_workers,manager._pool.memory_limit_bytes)) if manager._pool else None)
        with tempfile.TemporaryDirectory() as folder:
            job=RenderJob('budget','budget',str(Path(folder)/'out.wav'),self.snapshot())
            with patch('Resources.RenderMemory.render_memory_budget',return_value=4*1024**3), \
                 patch('Resources.RenderMemory.estimate_snapshot_memory',return_value=2*1024**3), \
                 patch('Resources.OfflineRender._SubprocessWorkerHandle',Handle):
                result=manager.run_blocking([job])
        self.assertEqual(result.completed,1)
        self.assertTrue(observed)
        self.assertTrue(all(value==(1,4*1024**3) for value in observed))

        self.assertTrue(all(event.get('memory_worker_limit') is None for event in progress))
        self.assertTrue(all(event['memory_budget_bytes']==4*1024**3 for event in progress))



class AnalysisMemoryEstimateTests(unittest.TestCase):
    def test_spectral_and_impulse_histories_include_output_stream_replication(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'source.wav')
            with AudioWriter(path,1000,1,1000) as stream:stream.write(np.zeros((1000,1)))
            module={'module_path':'BinWarper.c5','settings':{'userInputs':{'snd':{'path':path,'type':'csampler'}}}}
            snap={'modules':[module]}
            self.assertEqual(estimate_snapshot_memory(snap,64),256*MIB+1000*64*8*3)
            module['module_path']='ConvolutionReverb.c5'
            module['settings']['userInputs']={'impulse':{'path':path,'type':'cfilein'}}
            self.assertEqual(estimate_snapshot_memory(snap,64),256*MIB+1000*64*8*4)




class DestinationPreservationTests(unittest.TestCase):
    def test_failure_preserves_untouched_destination_and_removes_partial(self):
        from unittest.mock import patch
        from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob
        for writes_partial in (False,True):
            class Handle:
                def __init__(self,index):self.worker_index=index;self._closed=False
                def execute(self,cmd,spec,cancel_event,on_progress=None):
                    if writes_partial:Path(spec['output_path']).write_bytes(b'bad')
                    raise MemoryError('memory budget exceeded before completion')
                def close(self):self._closed=True
                def terminate(self):self._closed=True
            with self.subTest(writes_partial=writes_partial),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'existing.wav';path.write_bytes(b'previous completed audio')
                snap={'modules':[{'id':'a','module_path':'fixture.c5','settings':{'userInputs':{}}}],
                      'output':{'totalTime':1,'nchnls':2}}
                job=RenderJob('failure','failure',str(path),snap)
                with patch('Resources.OfflineRender._SubprocessWorkerHandle',Handle):
                    result=OfflineRenderManager(RenderSettings(accel_mode='single')).run_blocking([job])
                self.assertEqual(result.failed,1)
                if writes_partial:self.assertFalse(path.exists())
                else:
                    self.assertTrue(path.exists(),'Untouched existing destination was deleted')
                    self.assertEqual(path.read_bytes(),b'previous completed audio')


        # A later failed overwrite must also retain the previous successful job.
        class BatchHandle:
            def __init__(self,index):self.worker_index=index;self._closed=False
            def execute(self,cmd,spec,cancel_event,on_progress=None):
                if spec['job_id']=='first':
                    Path(spec['output_path']).write_bytes(b'new completed audio')
                    return {'duration':1,'peak_db':-90,'module_results':{}}
                raise MemoryError('second job failed before writing')
            def close(self):self._closed=True
            def terminate(self):self._closed=True
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'existing.wav';path.write_bytes(b'previous audio')
            jobs=[RenderJob(name,name,str(path),snap) for name in ('first','second')]
            with patch('Resources.OfflineRender._SubprocessWorkerHandle',BatchHandle):
                result=OfflineRenderManager(RenderSettings(accel_mode='single',num_threads=1)).run_blocking(jobs)
            self.assertEqual((result.completed,result.failed),(1,1))
            self.assertEqual(path.read_bytes(),b'new completed audio')


class ConservativeEstimateTrialTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('CECILIA_DSP_TESTS')=='1','Enable native DSP tests')
    def test_estimate_above_budget_uses_one_real_monitored_worker(self):
        import os
        import sys
        from unittest.mock import patch
        from Resources.RenderMemory import process_rss
        from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob
        if process_rss(os.getpid()) is None:self.skipTest('Resident-memory monitoring unavailable')
        root=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(root/'tests'))
        from check_all_modules import snapshot
        events=[]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.wav';target=Path(directory)/'output.wav'
            with AudioWriter(source,48000,2,48000) as writer:
                t=np.arange(48000)/48000
                writer.write(np.column_stack((.1*np.sin(2*np.pi*220*t),.1*np.sin(2*np.pi*330*t))))
            snap=snapshot(root/'Resources/modules/Filters/StateVar2.c5',source)
            snap['output'].update(totalTime=.4,nchnls=2)
            manager=OfflineRenderManager(RenderSettings(sr=48000,nchnls=2,num_threads=6,
                        accel_mode='single',samp_size=3),on_progress=events.append)
            job=RenderJob('overestimate','overestimate',str(target),snap)
            with patch('Resources.RenderMemory.render_memory_budget',return_value=192*MIB), \
                 patch('Resources.RenderMemory.estimate_snapshot_memory',return_value=int(14.6*1024**3)):
                result=manager.run_blocking([job])
            self.assertEqual((result.completed,result.failed),(1,0),job.error)
            self.assertTrue(all(event.get('memory_worker_limit') is None for event in events))
            self.assertTrue(all(len(event['workers'])==1 for event in events))
            with AudioReader(target) as reader:
                self.assertEqual((reader.info.frames,reader.info.channels),(19200,2))
            self.assertIsNone(manager._pool)
            self.assertFalse(manager._temp_dirs)


class SerializedAutoRenderTests(unittest.TestCase):
    def test_memory_limited_auto_runs_one_pass_without_replayed_chunks(self):
        from unittest.mock import patch
        from Resources.OfflineRender import OfflineRenderManager,RenderSettings,RenderJob
        calls=[]
        class Handle:
            def __init__(self,index):self.worker_index=index;self._closed=False
            def execute(self,cmd,spec,cancel_event,on_progress=None):
                calls.append(cmd)
                return {'duration':8,'frames':8*44100,'peak_db':-90,'module_results':{}}
            def close(self):self._closed=True
            def terminate(self):self._closed=True
        snap={'modules':[{'id':'a','module_path':'fixture.c5','settings':{'userInputs':{}}}],
              'output':{'totalTime':8,'nchnls':2}}
        with tempfile.TemporaryDirectory() as directory:
            job=RenderJob('serial','serial',str(Path(directory)/'out.wav'),snap)
            with patch('Resources.RenderMemory.render_memory_budget',return_value=1024*MIB), \
                 patch('Resources.RenderMemory.estimate_snapshot_memory',return_value=2*1024*MIB), \
                 patch('Resources.RenderMemory.process_rss',return_value=100*MIB), \
                 patch('Resources.OfflineRender._SubprocessWorkerHandle',Handle):
                result=OfflineRenderManager(RenderSettings(num_threads=6,accel_mode='auto')).run_blocking([job])
        self.assertEqual((result.completed,result.failed),(1,0),job.error)
        self.assertEqual(calls,['render'])


if __name__=='__main__':
    unittest.main()
