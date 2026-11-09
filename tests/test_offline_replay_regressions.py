"""Sample-level regressions; run with CECILIA_DSP_TESTS=1 and pyo/wx installed."""
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import unittest

AVAILABLE = (os.environ.get('CECILIA_DSP_TESTS') == '1'
             and all(importlib.util.find_spec(name) for name in ('pyo', 'wx', 'numpy')))


@unittest.skipUnless(AVAILABLE, 'Requires CECILIA_DSP_TESTS=1, pyo, wx and numpy')
class OfflineCorrectnessTests(unittest.TestCase):
    SR = 16000
    FRAMES = 64017  # deliberately not a multiple of the DSP buffer or chunk count

    def setUp(self):
        import numpy as np
        from Resources import OfflineRender as engine
        self.np, self.engine = np, engine
        self.temp = tempfile.TemporaryDirectory(prefix='cecilia-correctness-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        # Distinct channel signatures and impulses straddling the chunk seam.
        t = np.arange(self.FRAMES) / self.SR
        self.signal = np.array([0.04 * np.sin(2 * np.pi * f * t) for f in (137, 251, 389, 503)])
        for ch in range(4):
            self.signal[ch, self.FRAMES // 2 - 7 + ch * 5] += 0.3 + ch * 0.05
        self.source = self.folder / 'source.wav'
        engine._write_wav_float32(self.signal, str(self.source), self.SR)

    def snapshot(self, expression='self.snd', name='fixture'):
        module = self.folder / (name + '.c5')
        module.write_text('class Module(BaseModule):\n'
                          '    def __init__(self):\n'
                          '        BaseModule.__init__(self)\n'
                          '        self.snd = self.addSampler("snd")\n'
                          f'        self.out = {expression}\n'
                          'Interface = [csampler(name="snd"), cslider(name="level", min=0, max=1, init=1)]\n')
        snap = {
            'source_id': 'a', 'source_ids': ['a'], 'connections': [],
            'output_connections': ['a'], 'muted_ids': [], 'selected_id': 'a',
            'positions': {'a': [0, 0]}, 'view': 'graph',
            'modules': [{'id': 'a', 'module_path': str(module), 'builtin': False,
                         'preset': 'init', 'settings': {
                             'userInputs': {'snd': {'type': 'csampler', 'mode': 0, 'loopMode': 0}},
                             'userSliders': {}, 'userTogglePopups': {}, 'userGraph': {}}}],
            'output': {'totalTime': self.FRAMES / self.SR, 'nchnls': 4,
                       'gainSlider': 0.0, 'startOffset': 0.0, 'plugins': {}, 'userGraph': {}}}
        return self.engine.apply_sound_to_snapshot(snap, str(self.source))

    def render(self, snapshot, mode, stems=False, **overrides):
        out = str(self.folder / (mode + '.wav'))
        taps = {'a': str(self.folder / (mode + '_tap.wav'))} if stems else {}
        job = self.engine.RenderJob(mode, mode, out, snapshot, module_outputs=taps)
        settings = self.engine.RenderSettings(sr=self.SR, nchnls=4, buffersize=64,
                    num_threads=2, accel_mode=mode, preroll=0.5, crossfade=0.08,
                    global_fade=0, samp_size=3)
        for name, value in overrides.items():
            setattr(settings, name, value)
        manager = self.engine.OfflineRenderManager(settings)
        self.assertEqual(manager._choose_single_strategy(job, 1), mode)
        summary = manager.run_blocking([job])
        self.assertEqual((summary.completed, summary.failed), (1, 0), job.error)
        data = self.engine._read_wav_float64(out)
        self.assertEqual(data.shape, (4, self.FRAMES))
        self.assertTrue(self.np.isfinite(data).all())
        return data, job

    def assert_audio_equal(self, actual, expected, atol=2e-6):
        self.np.testing.assert_allclose(actual, expected, atol=atol, rtol=0)
        seam = self.FRAMES // 2
        self.np.testing.assert_allclose(actual[:, seam-128:seam+128],
                                       expected[:, seam-128:seam+128], atol=atol, rtol=0)

    def test_single_pass_has_exact_frame_count(self):
        _, job = self.render(self.snapshot(), 'single', stems=True)
        for path in [job.output_path, *job.module_outputs.values()]:
            self.assertEqual(self.engine._read_wav_float64(path).shape, (4, self.FRAMES))

    def test_single_and_chunks_match(self):
        snap = self.snapshot()
        single, _ = self.render(snap, 'single', stems=True)
        chunked, _ = self.render(snap, 'chunks', stems=True)
        self.assertGreater(float(self.np.max(abs(single))), 0.1)
        self.assert_audio_equal(chunked, single)

    def test_four_channel_tap_alignment_and_order(self):
        for mode in ('single', 'chunks'):
            with self.subTest(mode=mode):
                data, job = self.render(self.snapshot(), mode, stems=True)
                tap = self.engine._read_wav_float64(job.module_outputs['a'])
                self.assertEqual(tap.shape[0], 4)
                # Taps precede the master's startup gain ramp.
                self.assert_audio_equal(tap[:, 1024:self.FRAMES-1024], data[:, 1024:-1024])
                # Verify channel identity before the seam, after the sampler startup ramp.
                self.assert_audio_equal(data[:, 1024:16000], self.signal[:, 1024:16000])

    def test_stateful_effects_across_seams(self):
        effects = {
            'delay': ('Delay(self.snd, delay=0.037, maxdelay=1)', 2e-6),
            'feedback': ('Delay(self.snd, delay=0.037, feedback=0.35, maxdelay=1)', 2e-5),
            'reverb': ('Freeverb(self.snd, size=0.3, damp=0.5, bal=1)', 5e-4),
            'convolution': ('Convolve(self.snd, DataTable(size=513, init=[1.0] + [0.0]*510 + [0.4, -0.2]), size=513)', 2e-6),
        }
        for name, (expression, tolerance) in effects.items():
            with self.subTest(effect=name):
                snap = self.snapshot(expression, name)
                single, _ = self.render(snap, 'single')
                chunked, _ = self.render(snap, 'chunks')
                self.assertGreater(float(self.np.max(abs(single))), 1e-4)
                self.assert_audio_equal(chunked, single, atol=tolerance)

    def test_full_history_phase_randomness_and_fades(self):
        # Feedback exceeds the legacy preroll; the oscillator and noise must
        # retain the same phase/seed and fades must occur once on the timeline.
        snap = self.snapshot('Delay(self.snd, delay=0.8, feedback=0.9, maxdelay=2) + Sine(173, mul=0.01) + Noise(mul=0.005)')
        single, _ = self.render(snap, 'single', global_fade=0.03)
        for shape in ('cosine', 'equal_power'):
            with self.subTest(shape=shape):
                chunked, _ = self.render(snap, 'chunks', global_fade=0.03,
                                         crossfade_shape=shape, preroll=0)
                self.assert_audio_equal(chunked, single)

    def test_automation_remains_on_original_timeline(self):
        snap = self.snapshot('self.snd * self.level')
        snap['modules'][0]['settings']['userGraph']['level'] = {
            'data': [[0, 0.2], [0.4, 0.9], [0.6, 0.1], [1, 0.7]], 'curved': True}
        single, _ = self.render(snap, 'single')
        chunked, _ = self.render(snap, 'chunks')
        self.assert_audio_equal(chunked, single)

    def test_exact_lengths_in_integer_and_compressed_formats(self):
        from pyo import sndinfo
        for fmt, sampletype in (('wav', 0), ('aif', 1), ('flac', 1)):
            with self.subTest(format=fmt):
                out, tap = [str(self.folder / (name + '.' + fmt)) for name in ('master', 'tap')]
                job = self.engine.RenderJob(fmt, fmt, out, self.snapshot(), module_outputs={'a': tap})
                manager = self.engine.OfflineRenderManager(self.engine.RenderSettings(
                    sr=self.SR, nchnls=4, buffersize=64, accel_mode='single',
                    audio_file_type=fmt, samp_size=sampletype))
                summary = manager.run_blocking([job])
                self.assertEqual((summary.completed, summary.failed), (1, 0), job.error)
                for path in (out, tap):
                    info = sndinfo(path)
                    self.assertEqual((info[0], info[3]), (self.FRAMES, 4))

    def test_disjoint_branches_match_single_with_master_gain_and_mute(self):
        snap = self.snapshot('self.snd * 0.25')
        second = copy.deepcopy(snap['modules'][0])
        second['id'] = 'b'
        snap['modules'].append(second)
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        snap['output']['gainSlider'] = -6.0
        for muted in ([], ['b']):
            with self.subTest(muted=muted):
                snap['muted_ids'] = muted
                single, _ = self.render(snap, 'single')
                parallel, _ = self.render(snap, 'branches')
                self.assert_audio_equal(parallel, single)

    def test_random_modules_replay_and_branch_with_default_seed(self):
        snap = self.snapshot('(self.setGlobalSeed(0) or Sig(0)) + Noise(mul=0.01) + Sine(__import__("random").uniform(90, 300), mul=0.02) + self.snd * 0.1')
        single, _ = self.render(snap, 'single')
        repeated, _ = self.render(snap, 'single')
        chunked, _ = self.render(snap, 'chunks')
        self.assert_audio_equal(repeated, single)
        self.assert_audio_equal(chunked, single)
        second = copy.deepcopy(snap['modules'][0])
        second['id'] = 'b'
        snap['modules'].append(second)
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        serial, _ = self.render(snap, 'single', global_fade=0.005)
        parallel, _ = self.render(snap, 'branches', global_fade=0.005)
        self.assert_audio_equal(parallel, serial)

    def test_branch_fades_and_master_filter_match_serial(self):
        snap = self.snapshot('self.snd * 0.25')
        snap['modules'].append(dict(copy.deepcopy(snap['modules'][0]), id='b'))
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        snap['output']['gainSlider'] = -6.0
        filter_state = {'0': ['Filter', [1.0, 2500.0, 1.2, 1],
                        [[1.0, 0, None, 1], [2500.0, 0, None, 1], [1.2, 0, None, 1]]]}
        for plugins in ({}, filter_state):
            with self.subTest(plugins=bool(plugins)):
                snap['output']['plugins'] = plugins
                single, _ = self.render(snap, 'single', global_fade=0.005)
                parallel, _ = self.render(snap, 'branches', global_fade=0.005)
                self.assert_audio_equal(parallel, single)

    def test_cancel_raw_branches_removes_scratch_and_stems(self):
        snap = self.snapshot()
        snap['output']['totalTime'] = 3600
        snap['modules'].append(dict(copy.deepcopy(snap['modules'][0]), id='b'))
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        job = self.engine.RenderJob('cancel', 'cancel', str(self.folder / 'cancel.wav'),
                                    snap, export_stems=True)
        started = threading.Event()
        manager = self.engine.OfflineRenderManager(
            self.engine.RenderSettings(sr=self.SR, nchnls=4, num_threads=2, accel_mode='branches'),
            on_progress=lambda ev: started.set() if job.progress > 0 else None)
        manager.start([job])
        self.addCleanup(manager.cancel)
        self.assertTrue(started.wait(20), 'Branches did not begin rendering')
        pool = manager._pool
        directories = list(manager._temp_dirs)
        self.assertTrue(directories)
        manager.cancel()
        manager._thread.join(timeout=10)
        self.assertFalse(manager._thread.is_alive())
        with pool._handles_lock:
            processes = [handle._proc for handle in pool._all_handles]
        for proc in processes:
            self.assertIsNotNone(proc.poll())
        for path in [job.output_path, *job.stem_paths, *directories]:
            self.assertFalse(os.path.exists(path), f'Cancellation left {path}')

    def test_module_warmup_aligns_taps_and_branch_master(self):
        snap = self.snapshot('(setattr(self.server, "startoffset", 0.125) or self.snd * 0.25)')
        single, first = self.render(snap, 'single', stems=True, global_fade=0.005)
        # Copy before rendering again into the same helper paths.
        first_tap = self.engine._read_wav_float64(first.module_outputs['a'])
        chunked, second = self.render(snap, 'chunks', stems=True, global_fade=0.005)
        second_tap = self.engine._read_wav_float64(second.module_outputs['a'])
        self.assertEqual(first_tap.shape, (4, self.FRAMES))
        self.assertEqual(second_tap.shape, first_tap.shape)
        self.assert_audio_equal(chunked, single)
        self.assert_audio_equal(second_tap, first_tap)
        snap['modules'].append(dict(copy.deepcopy(snap['modules'][0]), id='b'))
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        serial, _ = self.render(snap, 'single', global_fade=0.005)
        parallel, _ = self.render(snap, 'branches', global_fade=0.005)
        self.assert_audio_equal(parallel, serial)

    def test_shared_ancestor_is_not_decomposed(self):
        snap = self.snapshot()
        snap['modules'] += [dict(snap['modules'][0], id=i) for i in ('b', 'c')]
        snap['connections'] = [['a', 'b'], ['a', 'c']]
        snap['output_connections'] = ['b', 'c']
        self.assertIsNone(self.engine.extract_disjoint_output_branches(snap))

    def test_cancel_reaps_workers_and_removes_partial_taps(self):
        snap = self.snapshot('Delay(self.snd, delay=0.1, feedback=0.9, maxdelay=1)')
        snap['output']['totalTime'] = 3600
        out, tap = (str(self.folder / name) for name in ('cancel.wav', 'cancel_tap.wav'))
        job = self.engine.RenderJob('cancel', 'cancel', out, snap, module_outputs={'a': tap})
        started = threading.Event()
        manager = self.engine.OfflineRenderManager(
            self.engine.RenderSettings(sr=self.SR, nchnls=4, num_threads=2, accel_mode='chunks'),
            on_progress=lambda ev: started.set() if job.progress > 0 else None)
        manager.start([job])
        self.addCleanup(manager.cancel)
        self.assertTrue(started.wait(20), 'Workers did not begin rendering')
        pool = manager._pool
        with pool._handles_lock:
            processes = [handle._proc for handle in pool._all_handles]
        directories = list(manager._temp_dirs)
        self.assertTrue(processes)
        manager.cancel()
        manager._thread.join(timeout=10)
        self.assertFalse(manager._thread.is_alive())
        self.assertFalse(manager.is_running)
        for proc in processes:
            self.assertIsNotNone(proc.poll(), f'Worker {proc.pid} survived cancellation')
        for path in [out, tap, *directories]:
            self.assertFalse(os.path.exists(path), f'Cancellation left {path}')


if __name__ == '__main__':
    unittest.main()
