import copy
import os
import shutil
import sys
import tempfile
import threading
import time
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
    _read_wav_float64,
    _write_wav_float32,
)


class TestDeterministicSingleVsChunked(unittest.TestCase):
    """Test 1: Comparing offline single-pass and chunked output for deterministic processing modules."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="cec_det_test_")
        cls.sr = 44100
        cls.dur = 3.0
        cls.frames = int(cls.dur * cls.sr)
        t = np.arange(cls.frames, dtype=np.float64) / cls.sr

        # Deterministic 2-channel audio file
        cls.in_wav = os.path.join(cls.work, "det_input.wav")
        in_arr = np.zeros((2, cls.frames), dtype=np.float64)
        in_arr[0, :] = 0.6 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 440 * t)
        in_arr[1, :] = 0.6 * np.sin(2 * np.pi * 330 * t) + 0.3 * np.sin(2 * np.pi * 660 * t)
        _write_wav_float32(in_arr, cls.in_wav, cls.sr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _test_module(self, mod_rel, input_name=None, tol=3.5e-5):
        mod_path = os.path.join(ROOT, mod_rel)
        mod_name = os.path.splitext(os.path.basename(mod_rel))[0]
        snap = {
            "source_id": "m1", "source_ids": ["m1"], "connections": [], "output_connections": ["m1"],
            "positions": {"m1": [40, 40]}, "muted_ids": [], "selected_id": "m1", "view": "graph",
            "modules": [{
                "id": "m1", "module_path": mod_path, "builtin": True, "preset": "init",
                "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}
            }],
            "output": {
                "totalTime": self.dur, "nchnls": 2, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": {}
            }
        }
        if input_name:
            snap["modules"][0]["settings"]["userInputs"][input_name] = {
                "path": self.in_wav, "off" + input_name: 0, "nchnls" + input_name: 2
            }

        out_s = os.path.join(self.work, f"{mod_name}_single.wav")
        mgr_s = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=1, accel_mode="single", global_fade=0.01))
        sum_s = mgr_s.run_blocking([RenderJob("j_s", "Single", out_s, snap)])
        self.assertEqual(sum_s.failed, 0, f"Single pass failed: {sum_s.jobs[0].error}")

        # Chunked pass (cosine)
        out_c_cos = os.path.join(self.work, f"{mod_name}_chunk_cos.wav")
        mgr_c_cos = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=2, accel_mode="chunks", global_fade=0.01, crossfade=0.1, crossfade_shape="cosine"))
        sum_c_cos = mgr_c_cos.run_blocking([RenderJob("j_c_cos", "Chunk Cos", out_c_cos, snap)])
        self.assertEqual(sum_c_cos.failed, 0, f"Chunked cosine failed: {sum_c_cos.jobs[0].error}")

        # Chunked pass (equal_power)
        out_c_ep = os.path.join(self.work, f"{mod_name}_chunk_ep.wav")
        mgr_c_ep = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=2, accel_mode="chunks", global_fade=0.01, crossfade=0.1, crossfade_shape="equal_power"))
        sum_c_ep = mgr_c_ep.run_blocking([RenderJob("j_c_ep", "Chunk EP", out_c_ep, snap)])
        self.assertEqual(sum_c_ep.failed, 0, f"Chunked equal power failed: {sum_c_ep.jobs[0].error}")

        rs = _read_wav_float64(out_s)
        rc_cos = _read_wav_float64(out_c_cos)
        rc_ep = _read_wav_float64(out_c_ep)

        diff_cos = float(np.max(np.abs(rs - rc_cos)))
        diff_ep = float(np.max(np.abs(rs - rc_ep)))
        self.assertLessEqual(diff_cos, tol, f"{mod_name} cosine diff {diff_cos} exceeded tolerance {tol}")
        self.assertLessEqual(diff_ep, tol, f"{mod_name} equal_power diff {diff_ep} exceeded tolerance {tol}")

    def test_supersaw_single_vs_chunked(self):
        self._test_module("Resources/modules/Synthesis/SuperSaw.c5", tol=1e-5)

    def test_distortion_single_vs_chunked(self):
        self._test_module("Resources/modules/Dynamics/Distortion.c5", input_name="snd", tol=1e-5)

    def test_brickwall_single_vs_chunked(self):
        self._test_module("Resources/modules/Filters/BrickWall.c5", input_name="snd", tol=3.5e-5)

    def test_statevar2_single_vs_chunked(self):
        self._test_module("Resources/modules/Filters/StateVar2.c5", input_name="snd", tol=3.5e-5)


class TestStatefulAcrossChunkBoundaries(unittest.TestCase):
    """Test 2: Testing delay lines, reverbs, convolution and feedback across chunk boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="cec_stateful_test_")
        cls.sr = 44100
        cls.dur = 4.0
        cls.frames = int(cls.dur * cls.sr)
        t = np.arange(cls.frames, dtype=np.float64) / cls.sr

        # Transient burst at 0.5s to test decay tails across chunk seams (seams at ~1.33s and ~2.66s)
        cls.in_wav = os.path.join(cls.work, "burst_in.wav")
        in_arr = np.zeros((2, cls.frames), dtype=np.float64)
        burst_idx = int(0.5 * cls.sr)
        burst_len = int(0.1 * cls.sr)
        in_arr[:, burst_idx:burst_idx + burst_len] = 0.8 * np.sin(2 * np.pi * 440 * t[:burst_len])
        _write_wav_float32(in_arr, cls.in_wav, cls.sr)

        # Impulse response file for convolution
        cls.ir_wav = os.path.join(cls.work, "impulse_ir.wav")
        ir_len = int(0.5 * cls.sr)
        ir_t = np.arange(ir_len, dtype=np.float64) / cls.sr
        ir_arr = np.zeros((2, ir_len), dtype=np.float64)
        ir_arr[0, :] = np.exp(-5 * ir_t) * np.sin(2 * np.pi * 1000 * ir_t)
        ir_arr[1, :] = np.exp(-5 * ir_t) * np.cos(2 * np.pi * 1000 * ir_t)
        _write_wav_float32(ir_arr, cls.ir_wav, cls.sr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _test_stateful_module(self, mod_rel, input_name="snd", extra_inputs=None, tol=3.5e-5):
        mod_path = os.path.join(ROOT, mod_rel)
        mod_name = os.path.splitext(os.path.basename(mod_rel))[0]
        snap = {
            "source_id": "m1", "source_ids": ["m1"], "connections": [], "output_connections": ["m1"],
            "positions": {"m1": [40, 40]}, "muted_ids": [], "selected_id": "m1", "view": "graph",
            "modules": [{
                "id": "m1", "module_path": mod_path, "builtin": True, "preset": "init",
                "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}
            }],
            "output": {
                "totalTime": self.dur, "nchnls": 2, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": {}
            }
        }
        if input_name:
            snap["modules"][0]["settings"]["userInputs"][input_name] = {
                "path": self.in_wav, "off" + input_name: 0, "nchnls" + input_name: 2
            }
        if extra_inputs:
            snap["modules"][0]["settings"]["userInputs"].update(extra_inputs)

        # Single pass
        out_s = os.path.join(self.work, f"{mod_name}_single.wav")
        mgr_s = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=1, accel_mode="single", global_fade=0.01))
        sum_s = mgr_s.run_blocking([RenderJob("j_s", "Single", out_s, snap)])
        self.assertEqual(sum_s.failed, 0, f"Single failed: {sum_s.jobs[0].error}")

        # Chunked pass across 3 worker threads (multiple chunk boundaries)
        out_c = os.path.join(self.work, f"{mod_name}_chunked.wav")
        mgr_c = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=3, accel_mode="chunks", global_fade=0.01, crossfade=0.1))
        sum_c = mgr_c.run_blocking([RenderJob("j_c", "Chunked", out_c, snap)])
        self.assertEqual(sum_c.failed, 0, f"Chunked failed: {sum_c.jobs[0].error}")

        rs = _read_wav_float64(out_s)
        rc = _read_wav_float64(out_c)

        diff = float(np.max(np.abs(rs - rc)))
        rmse = float(np.sqrt(np.mean((rs - rc) ** 2)))
        self.assertLessEqual(diff, tol, f"{mod_name} max diff {diff} exceeded tolerance {tol}")
        self.assertLessEqual(rmse, tol, f"{mod_name} RMSE {rmse} exceeded tolerance {tol}")

    def test_delays_across_chunks(self):
        self._test_stateful_module("Resources/modules/Time/4Delays.c5", tol=1e-5)

    def test_multiband_reverb_across_chunks(self):
        self._test_stateful_module("Resources/modules/Multiband/MultiBandReverb.c5", tol=1e-5)

    def test_feedback_looper_across_chunks(self):
        self._test_stateful_module("Resources/modules/Dynamics/FeedbackLooper.c5", tol=1e-5)

    def test_convolution_reverb_across_chunks(self):
        extra = {"impulse": {"path": self.ir_wav, "offimpulse": 0, "nchnlsimpulse": 2}}
        self._test_stateful_module("Resources/modules/Resonators&Verbs/ConvolutionReverb.c5", extra_inputs=extra, tol=3.5e-5)


class TestMultichannelStemExportAlignment(unittest.TestCase):
    """Test 3: Checking sample alignment and channel ordering in multichannel stem exports."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="cec_stem_align_test_")
        cls.sr = 44100
        cls.dur = 2.0
        cls.frames = int(cls.dur * cls.sr)
        t = np.arange(cls.frames, dtype=np.float64) / cls.sr

        # 6-channel input
        cls.in_6ch = os.path.join(cls.work, "input_6ch.wav")
        arr_6ch = np.zeros((6, cls.frames), dtype=np.float64)
        for ch in range(6):
            arr_6ch[ch, :] = (0.2 + 0.1 * ch) * np.sin(2 * np.pi * (150 * (ch + 1)) * t)
        _write_wav_float32(arr_6ch, cls.in_6ch, cls.sr)

        # 64-channel input
        cls.in_64ch = os.path.join(cls.work, "input_64ch.wav")
        arr_64ch = np.zeros((64, cls.frames), dtype=np.float64)
        for ch in range(64):
            arr_64ch[ch, :] = 0.5 * np.sin(2 * np.pi * (100 + ch * 10) * t)
        _write_wav_float32(arr_64ch, cls.in_64ch, cls.sr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_6ch_chain_stem_alignment_single_and_chunked(self):
        disto_path = os.path.join(ROOT, "Resources/modules/Dynamics/Distortion.c5")
        bw_path = os.path.join(ROOT, "Resources/modules/Filters/BrickWall.c5")

        snap = {
            "source_id": "m1", "source_ids": ["m1"], "connections": [["m1", "m2"]], "output_connections": ["m2"],
            "positions": {"m1": [40, 40], "m2": [150, 40]}, "muted_ids": [], "selected_id": "m2", "view": "graph",
            "modules": [
                {
                    "id": "m1", "module_path": disto_path, "builtin": True, "preset": "init",
                    "settings": {"userInputs": {"snd": {"path": self.in_6ch, "offsnd": 0, "nchnlssnd": 6}},
                                 "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}
                },
                {
                    "id": "m2", "module_path": bw_path, "builtin": True, "preset": "init",
                    "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}
                }
            ],
            "output": {
                "totalTime": self.dur, "nchnls": 6, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": {}
            }
        }

        for mode in ["single", "chunks"]:
            out_master = os.path.join(self.work, f"master_6ch_{mode}.wav")
            stem_m1 = os.path.join(self.work, f"stem_m1_{mode}.wav")
            stem_m2 = os.path.join(self.work, f"stem_m2_{mode}.wav")

            mgr = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=6, num_threads=2, accel_mode=mode, global_fade=0.01))
            res = mgr.run_blocking([
                RenderJob(f"j_{mode}", f"6ch {mode}", out_master, snap, module_outputs={"m1": stem_m1, "m2": stem_m2}, master_output=True)
            ])
            self.assertEqual(res.failed, 0, f"Render failed in {mode}: {res.jobs[0].error}")

            rm = _read_wav_float64(out_master)
            r_m1 = _read_wav_float64(stem_m1)
            r_m2 = _read_wav_float64(stem_m2)

            # Sample count alignment
            self.assertEqual(rm.shape[1], self.frames, f"Master frames mismatch in {mode}")
            self.assertEqual(r_m1.shape[1], self.frames, f"Stem m1 frames mismatch in {mode}")
            self.assertEqual(r_m2.shape[1], self.frames, f"Stem m2 frames mismatch in {mode}")

            # Channel count
            self.assertEqual(rm.shape[0], 6, f"Master channel count mismatch in {mode}")
            self.assertEqual(r_m1.shape[0], 6, f"Stem m1 channel count mismatch in {mode}")
            self.assertEqual(r_m2.shape[0], 6, f"Stem m2 channel count mismatch in {mode}")

            # Channel ordering: non-silent across all 6 channels
            for ch in range(6):
                rms_ch = float(np.sqrt(np.mean(r_m1[ch] ** 2)))
                self.assertGreater(rms_ch, 0.01, f"Stem channel {ch} is silent in {mode}")

    def test_64ch_stem_export_alignment(self):
        disto_path = os.path.join(ROOT, "Resources/modules/Dynamics/Distortion.c5")
        snap_64 = {
            "source_id": "m1", "source_ids": ["m1"], "connections": [], "output_connections": ["m1"],
            "positions": {"m1": [40, 40]}, "muted_ids": [], "selected_id": "m1", "view": "graph",
            "modules": [{
                "id": "m1", "module_path": disto_path, "builtin": True, "preset": "init",
                "settings": {"userInputs": {"snd": {"path": self.in_64ch, "offsnd": 0, "nchnlssnd": 64}},
                             "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}}],
            "output": {
                "totalTime": self.dur, "nchnls": 64, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": {}
            }
        }
        out_m_64 = os.path.join(self.work, "master_64.wav")
        stem_64 = os.path.join(self.work, "stem_64.wav")
        mgr = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=64, num_threads=2, accel_mode="chunks", global_fade=0.01))
        sum_64 = mgr.run_blocking([RenderJob("j64", "64ch Stems", out_m_64, snap_64, module_outputs={"m1": stem_64}, master_output=True)])
        self.assertEqual(sum_64.failed, 0, f"64ch stem render failed: {sum_64.jobs[0].error}")

        rm = _read_wav_float64(out_m_64)
        rs = _read_wav_float64(stem_64)
        self.assertEqual(rm.shape, (64, self.frames))
        self.assertEqual(rs.shape, (64, self.frames))
        for ch in range(64):
            rms_ch = float(np.sqrt(np.mean(rs[ch] ** 2)))
            self.assertGreater(rms_ch, 0.01, f"Channel {ch} is silent in 64-channel stem export")


class TestParallelBranchRoutingSemantics(unittest.TestCase):
    """Test 4: Validating that parallel branches preserve the intended signal-routing semantics."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="cec_branch_route_test_")
        cls.sr = 44100
        cls.dur = 2.0
        cls.frames = int(cls.dur * cls.sr)
        t = np.arange(cls.frames, dtype=np.float64) / cls.sr

        cls.w1 = os.path.join(cls.work, "w1.wav")
        a1 = np.zeros((2, cls.frames), dtype=np.float64)
        a1[0, :] = 0.5 * np.sin(2 * np.pi * 200 * t)
        a1[1, :] = 0.5 * np.cos(2 * np.pi * 200 * t)
        _write_wav_float32(a1, cls.w1, cls.sr)

        cls.w2 = os.path.join(cls.work, "w2.wav")
        a2 = np.zeros((2, cls.frames), dtype=np.float64)
        a2[0, :] = 0.5 * np.sin(2 * np.pi * 500 * t)
        a2[1, :] = 0.5 * np.cos(2 * np.pi * 500 * t)
        _write_wav_float32(a2, cls.w2, cls.sr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _build_branch_snapshot(self, muted_ids=None, with_reverb_plugin=False):
        disto_path = os.path.join(ROOT, "Resources/modules/Dynamics/Distortion.c5")
        bw_path = os.path.join(ROOT, "Resources/modules/Filters/BrickWall.c5")
        plugins = {}
        if with_reverb_plugin:
            plugins["0"] = ["Reverb", [0.2, 1.0, 0.3, 1], [[0.2, 2, None, 1], [1.0, 0, None, 1], [0.3, 0, None, 1]]]

        return {
            "source_id": "m1", "source_ids": ["m1", "m2"], "connections": [], "output_connections": ["m1", "m2"],
            "positions": {"m1": [40, 40], "m2": [40, 150]}, "muted_ids": list(muted_ids or []),
            "selected_id": "m1", "view": "graph",
            "modules": [
                {"id": "m1", "module_path": disto_path, "builtin": True, "preset": "init",
                 "settings": {"userInputs": {"snd": {"path": self.w1, "offsnd": 0, "nchnlssnd": 2}},
                              "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}},
                {"id": "m2", "module_path": bw_path, "builtin": True, "preset": "init",
                 "settings": {"userInputs": {"snd": {"path": self.w2, "offsnd": 0, "nchnlssnd": 2}},
                              "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}}
            ],
            "output": {
                "totalTime": self.dur, "nchnls": 2, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": plugins
            }
        }

    def test_parallel_branches_summation_and_cable_gain(self):
        snap = self._build_branch_snapshot(muted_ids=[], with_reverb_plugin=False)
        out_s = os.path.join(self.work, "branch_sum_s.wav")
        mgr_s = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=1, accel_mode="single", global_fade=0.0))
        sum_s = mgr_s.run_blocking([RenderJob("js", "Single", out_s, snap)])
        self.assertEqual(sum_s.failed, 0)

        out_b = os.path.join(self.work, "branch_sum_b.wav")
        mgr_b = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=2, accel_mode="branches", global_fade=0.0))
        sum_b = mgr_b.run_blocking([RenderJob("jb", "Branches", out_b, snap)])
        self.assertEqual(sum_b.failed, 0)

        rs = _read_wav_float64(out_s)
        rb = _read_wav_float64(out_b)
        diff = float(np.max(np.abs(rs - rb)))
        self.assertLessEqual(diff, 3.5e-5, f"Single vs Branches summation diff {diff} exceeded tolerance")

    def test_parallel_branches_with_master_plugins(self):
        snap = self._build_branch_snapshot(muted_ids=[], with_reverb_plugin=True)
        out_s = os.path.join(self.work, "branch_rev_s.wav")
        mgr_s = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=1, accel_mode="single", global_fade=0.01))
        sum_s = mgr_s.run_blocking([RenderJob("js", "Single", out_s, snap)])
        self.assertEqual(sum_s.failed, 0)

        out_b = os.path.join(self.work, "branch_rev_b.wav")
        mgr_b = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=2, accel_mode="branches", global_fade=0.01))
        sum_b = mgr_b.run_blocking([RenderJob("jb", "Branches", out_b, snap)])
        self.assertEqual(sum_b.failed, 0)

        rs = _read_wav_float64(out_s)
        rb = _read_wav_float64(out_b)
        diff = float(np.max(np.abs(rs - rb)))
        self.assertLessEqual(diff, 3.5e-5, f"Branches with master plugin diff {diff} exceeded tolerance")

    def test_parallel_branches_muted_branch_semantics(self):
        snap = self._build_branch_snapshot(muted_ids=["m2"], with_reverb_plugin=False)
        out_s = os.path.join(self.work, "branch_mute_s.wav")
        mgr_s = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=1, accel_mode="single", global_fade=0.0))
        sum_s = mgr_s.run_blocking([RenderJob("js", "Single", out_s, snap)])
        self.assertEqual(sum_s.failed, 0)

        out_b = os.path.join(self.work, "branch_mute_b.wav")
        mgr_b = OfflineRenderManager(RenderSettings(sr=self.sr, nchnls=2, num_threads=2, accel_mode="branches", global_fade=0.0))
        sum_b = mgr_b.run_blocking([RenderJob("jb", "Branches", out_b, snap)])
        self.assertEqual(sum_b.failed, 0)

        rs = _read_wav_float64(out_s)
        rb = _read_wav_float64(out_b)
        diff = float(np.max(np.abs(rs - rb)))
        self.assertEqual(diff, 0.0, f"Muted branch diff should be exactly 0.0, got {diff}")


class TestCancellationAndProcessCleanup(unittest.TestCase):
    """Test 5: Ensuring cancellation cleans up worker processes and incomplete audio files."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="cec_cancel_unit_")

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_cancel_cleans_incomplete_files_and_terminates_workers(self):
        saw_path = os.path.join(ROOT, "Resources/modules/Synthesis/SuperSaw.c5")
        disto_path = os.path.join(ROOT, "Resources/modules/Dynamics/Distortion.c5")

        snap = {
            "source_id": "m1", "source_ids": ["m1"], "connections": [["m1", "m2"]], "output_connections": ["m2"],
            "positions": {"m1": [40, 40], "m2": [150, 40]}, "muted_ids": [], "selected_id": "m2", "view": "graph",
            "modules": [
                {"id": "m1", "module_path": saw_path, "builtin": True, "preset": "init",
                 "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}},
                {"id": "m2", "module_path": disto_path, "builtin": True, "preset": "init",
                 "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}}}
            ],
            "output": {
                "totalTime": 15.0,  # Long render to guarantee cancel hits active processing
                "nchnls": 2, "gainSlider": 0.0, "audioFileType": "wav",
                "sampSize": 3, "output_path": "", "startOffset": 0.0, "plugins": {}
            }
        }

        out_master = os.path.join(self.work, "incomplete_master.wav")
        stem_m1 = os.path.join(self.work, "incomplete_stem.wav")

        mgr = OfflineRenderManager(RenderSettings(sr=44100, nchnls=2, num_threads=2, accel_mode="chunks", global_fade=0.01))
        job = RenderJob("j_cancel", "Long Job", out_master, snap, module_outputs={"m1": stem_m1}, master_output=True)

        def cancel_after_start():
            time.sleep(0.3)
            mgr.cancel()

        canceller = threading.Thread(target=cancel_after_start)
        canceller.start()

        summary = mgr.run_blocking([job])
        canceller.join()

        # 1. Summary reflects cancellation
        self.assertTrue(summary.cancelled, "Summary should report cancelled=True")
        self.assertEqual(summary.completed, 0, "No jobs should be marked completed")

        # 2. Incomplete output files removed from disk
        self.assertFalse(os.path.exists(out_master), f"Incomplete master file {out_master} was not deleted!")
        self.assertFalse(os.path.exists(stem_m1), f"Incomplete stem file {stem_m1} was not deleted!")

        # 3. Temp directories cleaned up
        for td in mgr._temp_dirs:
            self.assertFalse(os.path.exists(td), f"Temporary chunk directory {td} was not deleted!")

        # 4. Manager can run a fresh render job immediately after cancellation
        out_next = os.path.join(self.work, "next_job.wav")
        snap_short = copy.deepcopy(snap)
        snap_short["output"]["totalTime"] = 0.5
        mgr_next = OfflineRenderManager(RenderSettings(sr=44100, nchnls=2, num_threads=1, accel_mode="single"))
        sum_next = mgr_next.run_blocking([RenderJob("j_next", "Next", out_next, snap_short, master_output=True)])
        self.assertEqual(sum_next.completed, 1, "Subsequent render job failed to complete after cancellation")
        self.assertTrue(os.path.exists(out_next), "Subsequent job did not write output file")


if __name__ == "__main__":
    unittest.main()
