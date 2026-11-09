"""Voice activation must cover every output channel, including mono and 8ch."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))


def probe():
    self=unittest.TestCase()
    from check_all_modules import snapshot
    from Resources.OfflineRender import _HeadlessRenderWorker,_write_wav_float32,_read_wav_float64
    with tempfile.TemporaryDirectory() as directory:
        folder=Path(directory);source=folder/'source.wav'
        t=np.arange(44100)/44100
        _write_wav_float32(np.array([.04*np.sin(2*np.pi*(137+113*c)*t) for c in range(8)]),str(source),44100)
        worker=_HeadlessRenderWorker(lambda event:None)
        for channels in (1,2,8):
            peaks=[]
            for enabled in (0,1):
                snap=snapshot(ROOT/'Resources/modules/Resonators&Verbs/DetunedResonators.c5',source)
                snap['output'].update(totalTime=.5,nchnls=channels)
                state=snap['modules'][0]['settings']
                state['userTogglePopups']={f'onoffv{i}':0 for i in range(1,9)}
                state['userTogglePopups']['onoffv8']=enabled
                state['userSliders']['drywet']=[1,0,None,1]
                output=folder/f'{channels}_{enabled}.wav'
                worker.render_snapshot({'job_id':'voices','snapshot':snap,'output_path':str(output),
                    'sr':44100,'buffersize':256,'nchnls_override':channels,'audio_file_type':'wav',
                    'samp_size':3,'global_fade':0,'scratch_dir':str(folder),'module_outputs':{}})
                audio=_read_wav_float64(str(output))
                self.assertTrue(np.isfinite(audio).all())
                peaks.append(np.max(abs(audio),axis=1))
            with self.subTest(channels=channels):
                np.testing.assert_array_equal(peaks[0],np.zeros(channels),err_msg='Muted voices still sound')
                self.assertTrue(np.all(peaks[1]>1e-7),'Voice eight is missing from an output channel')


@unittest.skipUnless(os.environ.get('CECILIA_DSP_TESTS')=='1','Set CECILIA_DSP_TESTS=1 for native DSP')
class DetunedVoiceRoutingTests(unittest.TestCase):
    def test_voice_eight_can_be_muted_and_enabled_on_every_channel(self):
        import subprocess
        completed=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--probe'],
                                 cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)


if __name__=='__main__':
    if '--probe' in sys.argv:probe()
    else:unittest.main()
