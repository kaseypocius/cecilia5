"""Spectral analysis must not consume the audible performance timeline."""
import ast
import argparse
import copy
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def audio_method(name, namespace):
    tree = ast.parse((ROOT/'Resources/audio.py').read_text())
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<spectral timing>', 'exec'), namespace)
    return namespace[name]


class SpectralTimingTests(unittest.TestCase):
    def test_live_timer_excludes_analysis_before_stopping_playback(self):
        panel = SimpleNamespace(setTime=Mock(), closeBounceToDiskDialog=Mock())
        cursor = SimpleNamespace(setTime=Mock())
        values = {'grapher': SimpleNamespace(cursorPanel=cursor),
                  'interface': SimpleNamespace(controlPanel=panel), 'totalTime': 4}
        lib = SimpleNamespace(getVar=values.get, getControlPanel=lambda: panel,
                              callAfter=Mock(), stopCeciliaSound=Mock())
        method = audio_method('setTime', {'CeciliaLib': lib})
        server = SimpleNamespace(timeOpened=True, analysis_warmup=8.0)
        method(server, 0, 0, 6, 0)
        panel.setTime.assert_called_with(0, 0, 0, 0)
        lib.callAfter.assert_not_called()
        method(server, 0, 0, 9, 250)
        panel.setTime.assert_called_with(1.25, 0, 1, 25)
        lib.callAfter.assert_not_called()
        method(server, 0, 0, 12, 0)
        self.assertIn(((lib.stopCeciliaSound,), {}), lib.callAfter.call_args_list)

    def test_non_buffer_graph_has_no_added_analysis_delay(self):
        instance = SimpleNamespace(id='a', module_class=type('Module', (), {}), state={})
        lib = SimpleNamespace(session=SimpleNamespace(connections=[]),
            getVar={'sr': 48000, 'bufferSize': '256', 'totalTime': 4}.get)
        method = audio_method('_plan_spectral_analysis', {'CeciliaLib': lib, 'math': math})
        server = SimpleNamespace()
        method(server, [instance])
        self.assertEqual(server.analysis_warmup, 0)
        self.assertEqual(server.analysis_readers, [])

    def test_later_live_controls_do_not_repeat_the_analysis_delay(self):
        method = audio_method('_schedule_spectral_start',
                              {'CallAfter': lambda function, time: function()})
        server = SimpleNamespace(analysis_warmup=8, analysis_control_start=8,
                                 analysis_readers=[], runtimeModules=[])
        method(server)
        self.assertEqual(server.analysis_control_start, 0)


class SpectralCleanupTests(unittest.TestCase):
    def check_cleanup(self, mode, failure=False):
        """Exercise the real CLI lifetime with files left by each audit mode."""
        tree = ast.parse((ROOT/'tests/check_spectral_audio.py').read_text())
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        with tempfile.TemporaryDirectory(prefix='cecilia-cleanup-test-') as directory:
            root = Path(directory)
            modules = root/'Resources/modules/Spectral'
            modules.mkdir(parents=True)
            (modules/'BinWarper.c5').write_text('')
            generated = []

            def fixtures(folder):
                folder.mkdir(parents=True)
                path = folder/'input.wav'
                path.write_bytes(b'fixture')
                generated.append(path)
                return [path]

            def render(snap, folder, label):
                folder.mkdir(parents=True, exist_ok=True)
                files = {name: str(folder/(name+'.wav')) for name in ['master', 'tap']}
                for path in files.values():
                    Path(path).write_bytes(b'partial render')
                    generated.append(Path(path))
                if failure:
                    raise RuntimeError('render failed after writing audio')
                return {'master': {'audible': True}}, files

            def audit(sources):
                render(None, sources[0].parent.parent/'outputs', 'audit')
                return [{'status': 'pass'}]

            namespace = {'ROOT': root, 'argparse': argparse, 'tempfile': tempfile,
                         'Path': Path, 'json': json, 'hashlib': hashlib,
                         'fixtures': fixtures, 'module_snapshot': lambda *args: {},
                         'render': render, 'live_render': render,
                         'full_audit': lambda modules, sources, *args: audit(sources),
                         'functional_audit': lambda sources, report: audit(sources)}
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<spectral CLI>', 'exec'), namespace)
            args = ['spectral-audit'] + ([mode] if mode else [])
            with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
                if failure and mode in ('--full', '--functional'):
                    with self.assertRaisesRegex(RuntimeError, 'render failed'):
                        namespace['main']()
                else:
                    self.assertEqual(namespace['main'](), int(failure))
            self.assertEqual(len(generated), 3)
            self.assertTrue(all(not path.exists() for path in generated))
            self.assertFalse(generated[0].parent.parent.exists())
            self.assertEqual(list(root.rglob('*.wav')), [])
            if mode in ('', '--live'):
                report = json.loads((root/'tests/reports/spectral_audio_probe.json').read_text())
                self.assertEqual(report[0]['status'], 'error' if failure else 'audible')

    def test_cli_removes_generated_audio_after_success(self):
        for mode in ['', '--live', '--full', '--functional']:
            with self.subTest(mode=mode):
                self.check_cleanup(mode)

    def test_cli_removes_partial_audio_after_failure(self):
        for mode in ['', '--live', '--full', '--functional']:
            with self.subTest(mode=mode):
                self.check_cleanup(mode, failure=True)


def probe(mode):
    import numpy as np
    sys.path.insert(0, str(ROOT/'tests'))
    from check_spectral_audio import fixtures, module_snapshot, render, live_render, load_samples
    with tempfile.TemporaryDirectory(prefix='cecilia-spectral-regression-') as directory:
        folder = Path(directory)
        os.environ['HOME'] = str(folder)
        sources = fixtures(folder/'inputs')
        if mode == 'warpers':
            for name in ['BinWarper', 'SpectralWarper']:
                snap = module_snapshot(ROOT/'Resources/modules/Spectral'/(name+'.c5'), sources)
                first, files = render(snap, folder, name)
                reference = load_samples(files['master'])
                reference_tap = load_samples(files['a'])
                second, files = render(snap, folder, name+'_chunks', mode='chunks')
                chunked = load_samples(files['master'])
                chunked_tap = load_samples(files['a'])
                live, _ = live_render(snap, folder, name+'_live')
                assert all(row['master']['audible'] for row in [first, second, live]), name
                np.testing.assert_allclose(reference, chunked, atol=2e-6, rtol=0)
                np.testing.assert_allclose(reference_tap, chunked_tap, atol=2e-6, rtol=0)
        elif mode == 'graphs':
            from Resources.OfflineRender import OfflineRenderManager, RenderSettings, RenderJob
            first = ROOT/'Resources/modules/Spectral/SpectralWarper.c5'
            snap = module_snapshot(first, sources)
            other = module_snapshot(ROOT/'Resources/modules/Filters/StateVar2.c5', sources)['modules'][0]
            other['id'] = 'b'
            snap['modules'].append(other)
            snap['source_ids'].append('b')
            snap['output_connections'].append('b')
            for index, plugins in enumerate([{}, {'0': ['Filter', [1.0, 2500, 1.2, 1],
                    [[1.0, 0, None, 1], [2500, 1, None, 1], [1.2, 0, None, 1]]]}]):
                snap['output']['plugins'] = plugins
                snap['output']['userGraph'] = {'plugin_0_filter_freq': {
                    'data': [[0, .2], [.5, .9], [1, .3]], 'curved': True}} if plugins else {}
                measured, files = render(snap, folder, 'mixed_'+str(index))
                reference = load_samples(files['master'])
                assert all(value['audible'] for value in measured.values()), measured
                job = RenderJob('branches', 'branches', str(folder/f'branches_{index}.wav'), snap, export_stems=True)
                result = OfflineRenderManager(RenderSettings(sr=48000, nchnls=2, num_threads=2, buffersize=256,
                    accel_mode='branches', samp_size=3)).run_blocking([job])
                assert result.completed == 1 and not result.failed, job.error
                np.testing.assert_allclose(reference, load_samples(job.output_path), atol=2e-6, rtol=0)
            snap['output']['plugins'] = {}
            snap['output']['userGraph'] = {}
            # A second buffer must record after its upstream buffer is ready.
            second = module_snapshot(ROOT/'Resources/modules/Spectral/BinWarper.c5', sources)['modules'][0]
            second['id'] = 'b'
            snap['modules'][1] = second
            snap['source_ids'] = ['a']
            snap['connections'] = [['a', 'b']]
            snap['output_connections'] = ['b']
            for runner in [render, live_render]:
                measured, _ = runner(snap, folder, 'series_'+runner.__name__)
                assert measured['master']['audible'], measured


@unittest.skipUnless(os.environ.get('CECILIA_DSP_TESTS') == '1', 'Set CECILIA_DSP_TESTS=1 for native audio')
class SpectralNativeTests(unittest.TestCase):
    def run_probe(self, mode):
        completed = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--probe', mode],
                                   cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(completed.returncode, 0, completed.stdout+completed.stderr)

    def test_long_source_warpers_are_audible_live_and_offline(self):
        self.run_probe('warpers')

    def test_mixed_branches_and_serial_buffers_are_audible(self):
        self.run_probe('graphs')


if __name__ == '__main__':
    if '--probe' in sys.argv:
        probe(sys.argv[-1])
    else:
        unittest.main()
