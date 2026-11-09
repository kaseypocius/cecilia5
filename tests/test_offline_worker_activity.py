"""Worker activity contracts without a display or native DSP.

A controlled subprocess handle blocks before reporting DSP progress. The real
worker pool/coordinator must still expose activity and an advancing elapsed time.
"""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from Resources import OfflineRender as engine


class ControlledWork:
    def __init__(self, held_command='render'):
        self.held_command = held_command
        self.entered = threading.Event()
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.active = set()

    def handle_class(self):
        control = self

        class Handle:
            def __init__(self, worker_index):
                self.worker_index = worker_index
                self._closed = False
                self._lock = threading.Lock()
                self._proc = SimpleNamespace(pid=0, poll=lambda: 0 if self._closed else None)

            def execute(self, cmd, spec, cancel_event, on_progress=None, **kwargs):
                with self._lock:
                    with control.lock:
                        control.active.add(self.worker_index)
                    try:
                        if cmd == control.held_command:
                            control.entered.set()
                            while not control.release.wait(.01):
                                if cancel_event.is_set() or self._closed:
                                    raise InterruptedError('Controlled cancellation')
                        if cancel_event.is_set() or self._closed:
                            raise InterruptedError('Controlled cancellation')
                        if on_progress:
                            on_progress(self.worker_index, {'fraction':1.0,'rms':[.1], 'peak_db':-20.0})
                        duration = spec.get('duration_override', spec.get('total_time', 8.0))
                        return {'duration':duration,'frames':round(duration*spec['sr']),
                                'peak_db':-20.0,'module_results':{}}
                    finally:
                        with control.lock:
                            control.active.discard(self.worker_index)

            def terminate(self):
                self._closed = True

            def close(self):
                self._closed = True

        return Handle


class WorkerActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cecilia-activity-tests-')
        self.addCleanup(self.temp.cleanup)

    def snapshot(self, branches=False):
        snap = {'source_id':'a','source_ids':['a'],'connections':[],
            'output_connections':['a'],'positions':{'a':[0,0]},'muted_ids':[],
            'modules':[{'id':'a','module_path':'fixture.c5','builtin':False,'preset':'init',
                        'settings':{'userInputs':{},'userSliders':{},'userTogglePopups':{},'userGraph':{}}}],
            'output':{'totalTime':8.0,'nchnls':64,'gainSlider':0.0,'startOffset':0,
                      'plugins':{},'userGraph':{}}}
        if branches:
            snap['modules'].append(dict(copy.deepcopy(snap['modules'][0]), id='b'))
            snap['source_ids'].append('b')
            snap['output_connections'].append('b')
        return snap

    def start_controlled(self, mode, held_command='render'):
        control = ControlledWork(held_command)
        self.patch = patch.object(engine, '_SubprocessWorkerHandle', control.handle_class())
        self.patch.start()
        self.addCleanup(self.patch.stop)
        events = []
        done = threading.Event()
        summaries = []
        manager = engine.OfflineRenderManager(
            engine.RenderSettings(sr=16000,nchnls=64,num_threads=4,accel_mode=mode,samp_size=3),
            on_progress=lambda ev: events.append((time.monotonic(), copy.deepcopy(ev))),
            on_complete=lambda result: (summaries.append(result), done.set()))
        job = engine.RenderJob('activity', 'Activity fixture',
                               str(Path(self.temp.name)/'master.wav'), self.snapshot(mode=='branches'))
        def cleanup():
            control.release.set()
            manager.cancel()
            manager._thread.join(timeout=3)
        self.addCleanup(cleanup)
        manager.start([job])
        self.assertTrue(control.entered.wait(3), f'{held_command} task did not start')
        return control, manager, job, events, done, summaries

    @staticmethod
    def wait_for(predicate, timeout=.6):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():
                return True
            time.sleep(.01)
        return predicate()

    def assert_visible_activity(self, events):
        self.assertTrue(self.wait_for(lambda: bool(events) and any(
            worker.get('active') for worker in events[-1][1].get('workers',[]))),
            'Busy worker task is invisible: the latest progress event still shows all lanes idle')

    def test_single_startup_visible_before_dsp_progress(self):
        _, _, _, events, _, _ = self.start_controlled('single')
        self.assert_visible_activity(events)

    def test_chunk_startup_visible_before_dsp_progress(self):
        _, _, _, events, _, _ = self.start_controlled('chunks')
        self.assert_visible_activity(events)

    def test_branch_startup_visible_before_dsp_progress(self):
        _, _, _, events, _, _ = self.start_controlled('branches')
        self.assert_visible_activity(events)

    def test_stitch_phase_reports_active_worker(self):
        _, _, job, events, _, _ = self.start_controlled('chunks', 'stitch')
        self.assertIn('stitch', job.status.lower())
        self.assert_visible_activity(events)

    def test_mix_phase_reports_active_worker(self):
        _, _, job, events, _, _ = self.start_controlled('branches', 'mix_branches')
        self.assertIn('mix', job.status.lower())
        self.assert_visible_activity(events)

    def test_elapsed_updates_while_no_dsp_progress_arrives(self):
        _, _, _, events, _, _ = self.start_controlled('single')
        initial_elapsed = events[-1][1].get('elapsed',0.0)
        self.assertTrue(self.wait_for(lambda: bool(events) and
            events[-1][1].get('elapsed',0.0) >= initial_elapsed+.2, timeout=1.6),
            'Elapsed time freezes while a worker is preparing audio')
        self.assertTrue(all(ev.get('overall_fraction',0)==0 for _,ev in events),
                        'A heartbeat must not invent rendered audio progress')

    def test_completion_and_cancellation_clear_lanes(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                control, manager, job, events, done, summaries = self.start_controlled('chunks')
                if cancel:
                    manager.cancel()
                else:
                    control.release.set()
                self.assertTrue(done.wait(3))
                manager._thread.join(timeout=3)
                self.assertFalse(manager._thread.is_alive())
                self.assertEqual(summaries[0].cancelled, cancel)
                self.assertFalse(any(w.get('active') for w in events[-1][1].get('workers',[])))
                count = len(events)
                time.sleep(.15)
                self.assertEqual(len(events), count, 'Progress notifications continued after completion')

    def test_channel_count_does_not_mean_channel_parallelism(self):
        snapshot = self.snapshot()
        job = engine.RenderJob('strategy','Strategy','unused.wav',snapshot)
        manager = engine.OfflineRenderManager(engine.RenderSettings(
            nchnls=64,num_threads=8,accel_mode='single'))
        self.assertEqual(manager._choose_single_strategy(job,1),'single')
        snapshot['output']['totalTime']=1.0
        manager.settings.accel_mode='auto'
        self.assertEqual(manager._choose_single_strategy(job,1),'single')

    def test_ui_coalescing_applies_latest_worker_state(self):
        from Resources.OfflineRenderDialog import OfflineRenderDialog
        panel = SimpleNamespace(_latest_progress=None,_progress_dirty=False,
            _flush_progress_ui=Mock(),is_rendering=True,
            progress_bar=Mock(),worker_lanes=Mock(),_update_peak_badge=Mock())
        first = {'workers':[{'active':False,'label':'Idle','fraction':0.0}]}
        last = {'workers':[{'active':True,'label':'Preparing','fraction':0.0}],
                'overall_fraction':0,'completed_jobs':0,'total_jobs':1,'elapsed':.5,'eta':None}
        with patch('Resources.OfflineRenderDialog.wx.CallAfter') as queued:
            OfflineRenderDialog._on_worker_progress_bg(panel,first)
            OfflineRenderDialog._on_worker_progress_bg(panel,last)
            queued.assert_called_once()
        OfflineRenderDialog._flush_progress_ui(panel)
        panel.worker_lanes.update_workers.assert_called_once_with(last['workers'])


if __name__ == '__main__':
    unittest.main()
