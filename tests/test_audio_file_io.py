"""Streaming I/O invariants used by the offline renderer."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from Resources.AudioFileIO import AudioReader, AudioWriter, audio_peak
from Resources.OfflineRender import normalize_audio_file, _HeadlessRenderWorker


class AudioFileIOTests(unittest.TestCase):
    def test_segment_export_bounds_reads_and_preserves_channel_order(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = (str(Path(folder)/n) for n in ('source.wav','target.wav'))
            samples = np.arange(153*4,dtype=float).reshape(153,4)/1000
            with AudioWriter(source,48000,4,153) as writer:
                writer.write(samples)
            with patch('Resources.AudioFileIO.BLOCK_SAMPLES',28):
                _HeadlessRenderWorker._trim_audio_file(None,source,48000,4,99,0,3,
                                                       discard_frames=17,output_path=target,keep_source=True)
                with AudioReader(target) as reader:
                    blocks=list(reader.blocks())
                    self.assertTrue(all(len(b)<=7 for b in blocks))
                    np.testing.assert_array_equal(np.concatenate(blocks),samples[17:116].astype('float32'))
            self.assertTrue(Path(source).exists())

    def test_normalization_preserves_aiff_pcm_and_is_atomic_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'source.aif')
            with AudioWriter(path,44100,2,100,fileformat=1,sampletype=1) as writer:
                writer.write(np.full((100,2),.25))
            with AudioReader(path) as reader:
                before=reader.info
            normalize_audio_file(path,-6)
            with AudioReader(path) as reader:
                self.assertEqual(reader.info,before)
            self.assertAlmostEqual(audio_peak(path),10**(-6/20),places=6)
            original=Path(path).read_bytes()
            with patch.object(AudioWriter,'write',side_effect=OSError('injected disk failure')):
                with self.assertRaises(OSError):
                    normalize_audio_file(path,-1)
            self.assertEqual(Path(path).read_bytes(),original)
            self.assertEqual(list(Path(folder).glob('.cec_normalize_*')),[])

    def test_incomplete_write_and_nonfinite_samples_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'source.wav')
            with self.assertRaises(OSError):
                with AudioWriter(path,48000,1,5) as writer:
                    writer.write(np.ones((4,1)))
            with self.assertRaises(ValueError):
                with AudioWriter(path,48000,1,1) as writer:
                    writer.write(np.array([[np.nan]]))


if __name__=='__main__':
    unittest.main()
