"""Opt-in regressions for saturating PCM exports of overloaded multichannel audio."""
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

AVAILABLE = os.environ.get('CECILIA_DSP_TESTS') == '1' and all(
    importlib.util.find_spec(name) for name in ('pyo', 'wx', 'numpy'))


@unittest.skipUnless(AVAILABLE, 'Requires CECILIA_DSP_TESTS=1, pyo, wx and numpy')
class PcmExportTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        from pyo import Server
        from Resources import OfflineRender as engine
        self.np, self.engine = np, engine
        self.temp = tempfile.TemporaryDirectory(prefix='cecilia-pcm-tests-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.server = Server(sr=44100, nchnls=4, buffersize=64, audio='manual', duplex=0).boot()
        self.server.verbosity = 0
        self.addCleanup(self.server.shutdown)

    def read(self, path, frames, channels=4):
        from pyo import SndTable, sndinfo
        info = sndinfo(str(path))
        self.assertIsNotNone(info)
        self.assertEqual((info[0], info[3]), (frames, channels))
        audio = self.engine._read_wav_float64(str(path))
        if audio is None:
            table = SndTable(str(path))
            audio = self.np.array([table[ch].getTable() for ch in range(len(table))])
        self.assertTrue(self.np.isfinite(audio).all())
        return audio

    def expected(self, audio, bit):
        bits = {0: 16, 1: 24, 2: 32}[bit]
        maximum = min(1-2**(1-bits), float(self.np.nextafter(self.np.float32(1), self.np.float32(0))))
        return self.np.clip(audio, -1, maximum)

    def test_pcm_writer_saturates_without_wrapping(self):
        from Resources.constants import AUDIO_FILE_FORMATS
        audio = self.np.tile(self.np.linspace(-2, 2, 1025), (4, 1))
        for fmt, bit in (('wav', 0), ('wav', 1), ('aif', 1), ('flac', 1), ('wav', 2)):
            with self.subTest(format=fmt, bits=bit):
                path = self.folder / (f'writer_{bit}.' + fmt)
                self.engine._save_multichannel_audio(audio, str(path), 44100, AUDIO_FILE_FORMATS[fmt], bit)
                actual = self.read(path, 1025)
                self.np.testing.assert_allclose(actual, self.expected(audio, bit),
                    atol=2e-6 + 2**(1-{0:16,1:24,2:32}[bit]), rtol=0)

    def test_mono_pcm24_odd_data_chunk_is_padded(self):
        import struct
        audio = self.np.array([self.np.linspace(-0.75, 0.75, 1025)])
        path = self.folder / 'odd_mono.wav'
        self.engine._save_multichannel_audio(audio, str(path), 44100, 0, 1)
        data = path.read_bytes()
        self.assertEqual(len(data) % 2, 0)
        self.assertEqual(struct.unpack('<I', data[4:8])[0], len(data)-8)
        self.assertEqual(struct.unpack('<I', data[40:44])[0], 1025*3)
        self.np.testing.assert_allclose(self.read(path, 1025, channels=1), audio, atol=1/8388608, rtol=0)

    def test_harmonizer_window_stays_inside_circular_buffer(self):
        from Resources.audio import _harmonizer_window_seconds
        for rate in (44100, 48000, 96000, 192000):
            for requested in (.025, .05, .1, .15, .2, .25, .5, .75, 1):
                with self.subTest(rate=rate, window=requested):
                    window = _harmonizer_window_seconds(requested, rate)
                    self.assertLessEqual(abs(window-requested)*rate, 1.000001)
                    delay = float(self.np.float32(window)) * rate * 0.5
                    relative = self.np.float32(self.np.floor(delay)-delay)
                    wrapped = self.np.float32(relative+rate)
                    self.assertLess(int(wrapped)+1, rate+1)
                    self.assertGreater(abs(float(relative)), .1)

    def snapshot(self, frames):
        path = self.folder / 'overload.c5'
        path.write_text('class Module(BaseModule):\n'
                        '    def __init__(self):\n'
                        '        BaseModule.__init__(self)\n'
                        '        self.out = Sig([1.5, -1.5, 1.25, -1.25])\n'
                        'Interface = []\n')
        return {'source_id':'a','source_ids':['a'],'connections':[],
            'output_connections':['a'],'positions':{'a':[0,0]},'muted_ids':[],
            'modules':[{'id':'a','module_path':str(path),'builtin':False,'preset':'init',
                        'settings':{'userInputs':{},'userSliders':{},'userTogglePopups':{},'userGraph':{}}}],
            'output':{'totalTime':frames/44100,'nchnls':4,'gainSlider':0,'startOffset':0,
                      'plugins':{},'userGraph':{}}}

    def render(self, snap, fmt, bit, mode='single', stems=False):
        label = fmt + str(bit) + mode
        job = self.engine.RenderJob(label, label, str(self.folder/(label+'.'+fmt)), snap,
            export_stems=stems, module_outputs={} if stems else {'a':str(self.folder/(label+'_tap.'+fmt))})
        manager = self.engine.OfflineRenderManager(self.engine.RenderSettings(
            sr=44100,nchnls=4,buffersize=64,num_threads=2,accel_mode=mode,
            audio_file_type=fmt,samp_size=bit,global_fade=0))
        summary = manager.run_blocking([job])
        self.assertEqual((summary.completed, summary.failed), (1,0), job.error)
        frames = round(snap['output']['totalTime']*44100)
        return [self.read(path, frames) for path in [job.output_path, *job.stem_paths]]

    def test_integer_master_and_taps_encode_from_float(self):
        snap = self.snapshot(44100*2+17)
        reference = self.render(snap, 'wav', 3)
        for fmt, bit, mode in (('wav',0,'single'),('aif',1,'single'),('flac',1,'single'),
                                ('wav',2,'single'),('wav',0,'chunks')):
            with self.subTest(format=fmt, bit=bit, mode=mode):
                actual = self.render(snap,fmt,bit,mode)
                self.assertEqual(len(actual),len(reference))
                for got, original in zip(actual, reference):
                    self.np.testing.assert_allclose(got,self.expected(original,bit),
                        atol=2e-6+2**(1-{0:16,1:24,2:32}[bit]),rtol=0)

    def test_branch_stems_and_master_saturate(self):
        snap = self.snapshot(5513)
        snap['modules'].append(dict(copy.deepcopy(snap['modules'][0]), id='b'))
        snap['source_ids'].append('b')
        snap['output_connections'].append('b')
        reference = self.render(snap,'wav',3,'branches',stems=True)
        encoded = self.render(snap,'wav',0,'branches',stems=True)
        self.assertEqual(len(encoded),3)
        for got, original in zip(encoded,reference):
            self.np.testing.assert_allclose(got,self.expected(original,0),atol=2/32768,rtol=0)


if __name__ == '__main__':
    unittest.main()
