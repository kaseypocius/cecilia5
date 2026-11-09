import os
import shutil
import sys
import tempfile
import unittest

os.environ["HOME"] = "/tmp"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np
from Resources.OfflineRender import (
    OfflineRenderManager,
    RenderJob,
    RenderSettings,
    _write_wav_float32,
    _read_wav_float64,
)


class MultichannelInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="cec_mc_unit_")
        cls.sr = 44100
        cls.dur = 0.5
        frames = int(cls.dur * cls.sr)
        t = np.arange(frames, dtype=np.float64) / cls.sr

        # Stereo wav
        cls.stereo_wav = os.path.join(cls.work, "test_stereo.wav")
        s_arr = np.zeros((2, frames), dtype=np.float64)
        s_arr[0, :] = 0.5 * np.sin(2 * np.pi * 300 * t)
        s_arr[1, :] = 0.5 * np.sin(2 * np.pi * 500 * t)
        _write_wav_float32(s_arr, cls.stereo_wav, cls.sr)

        # Quad wav
        cls.quad_wav = os.path.join(cls.work, "test_quad.wav")
        q_arr = np.zeros((4, frames), dtype=np.float64)
        for ch in range(4):
            q_arr[ch, :] = 0.4 * np.sin(2 * np.pi * (200 + ch * 100) * t)
        _write_wav_float32(q_arr, cls.quad_wav, cls.sr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _make_snapshot(self, mod_rel_path, in_path, in_chnls, out_chnls, input_name="sndtable"):
        return {
            "source_id": "m1",
            "source_ids": ["m1"],
            "connections": [],
            "output_connections": ["m1"],
            "positions": {"m1": [40, 40]},
            "muted_ids": [],
            "selected_id": "m1",
            "view": "graph",
            "modules": [
                {
                    "id": "m1",
                    "module_path": os.path.join(ROOT, mod_rel_path),
                    "builtin": True,
                    "preset": "init",
                    "settings": {
                        "userInputs": {
                            input_name: {
                                "path": in_path,
                                "off" + input_name: 0,
                                "nchnls" + input_name: in_chnls,
                            }
                        },
                        "userSliders": {},
                        "userTogglePopups": {},
                        "userGraph": {},
                    },
                }
            ],
            "output": {
                "totalTime": self.dur,
                "nchnls": out_chnls,
                "gainSlider": 0.0,
                "audioFileType": "wav",
                "sampSize": 0,
                "output_path": "",
                "startOffset": 0.0,
                "plugins": {},
            },
        }

    def _render_and_assert(self, test_name, mod_rel_path, in_path, in_chnls, out_chnls, input_name="sndtable"):
        out_file = os.path.join(self.work, f"{test_name}.wav")
        snap = self._make_snapshot(mod_rel_path, in_path, in_chnls, out_chnls, input_name)
        mgr = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=out_chnls, num_threads=1, accel_mode="single"))
        summary = mgr.run_blocking([RenderJob("j", test_name, out_file, snap)])
        self.assertEqual(summary.failed, 0, f"Render failed for {test_name}: {summary.jobs[0].error}")
        self.assertEqual(summary.completed, 1)

        read_arr = _read_wav_float64(out_file)
        self.assertIsNotNone(read_arr, f"Could not read rendered file {out_file}")
        self.assertEqual(
            read_arr.shape[0],
            out_chnls,
            f"Expected {out_chnls} channels, got {read_arr.shape[0]} in {test_name}",
        )
        peak = float(np.max(np.abs(read_arr)))
        self.assertGreater(peak, 0.0001, f"Rendered audio was silent for {test_name}")

    def test_ultimategrainer_stereo_to_mono(self):
        self._render_and_assert("ug_stereo_to_mono", "Resources/modules/Time/UltimateGrainer.c5", self.stereo_wav, 2, 1, "sndtable")

    def test_ultimategrainer_quad_to_stereo(self):
        self._render_and_assert("ug_quad_to_stereo", "Resources/modules/Time/UltimateGrainer.c5", self.quad_wav, 4, 2, "sndtable")

    def test_ultimategrainer_stereo_to_64ch(self):
        self._render_and_assert("ug_stereo_to_64ch", "Resources/modules/Time/UltimateGrainer.c5", self.stereo_wav, 2, 64, "sndtable")

    def test_particle_stereo_to_mono(self):
        self._render_and_assert("particle_stereo_to_mono", "Resources/modules/Time/Particle.c5", self.stereo_wav, 2, 1, "sndtable")

    def test_pelletizer_stereo_to_mono(self):
        self._render_and_assert("pelletizer_stereo_to_mono", "Resources/modules/Time/Pelletizer.c5", self.stereo_wav, 2, 1, "sndtable")

    def test_pitchlooper_stereo_to_mono(self):
        self._render_and_assert("pitchlooper_stereo_to_mono", "Resources/modules/Pitch/PitchLooper.c5", self.stereo_wav, 2, 1, "snd")

    def test_looperbank_stereo_to_mono(self):
        self._render_and_assert("looperbank_stereo_to_mono", "Resources/modules/Pitch/LooperBank.c5", self.stereo_wav, 2, 1, "snd")

    def test_feedbacklooper_stereo_to_mono(self):
        self._render_and_assert("feedbacklooper_stereo_to_mono", "Resources/modules/Dynamics/FeedbackLooper.c5", self.stereo_wav, 2, 1, "snd")


if __name__ == "__main__":
    unittest.main()

