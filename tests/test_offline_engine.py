import os
import shutil
import sys
import tempfile
import time
import threading

os.environ["HOME"] = "/tmp"
sys.path.insert(0, "/Users/kasey/Downloads/cecilia5-master")

import numpy as np
from pyo import Server, DataTable, SndTable, savefileFromTable, sndinfo

from Resources.OfflineRender import (
    OfflineRenderManager,
    RenderJob,
    RenderSettings,
    apply_preset_to_snapshot,
    apply_sound_to_snapshot,
    extract_disjoint_output_branches,
    list_module_presets,
    load_preset_dict,
)

ROOT = os.path.abspath("/Users/kasey/Downloads/cecilia5-master")
STOCH = os.path.join(ROOT, "Resources/modules/Synthesis/StochGrains.c5")
SUPERSAW = os.path.join(ROOT, "Resources/modules/Synthesis/SuperSaw.c5")
BRICKWALL = os.path.join(ROOT, "Resources/modules/Filters/BrickWall.c5")
DISTO = os.path.join(ROOT, "Resources/modules/Dynamics/Distortion.c5")


def make_test_wav(path, dur=1.5, sr=44100):
    s = Server(sr=sr, nchnls=2, buffersize=256, duplex=0, audio="offline").boot()
    n = int(dur * sr)
    t = np.arange(n, dtype=np.float64) / sr
    ch0 = 0.4 * np.sin(2 * np.pi * 220.0 * t) + 0.2 * np.sin(2 * np.pi * 660.0 * t)
    ch1 = 0.4 * np.sin(2 * np.pi * 330.0 * t) + 0.2 * np.sin(2 * np.pi * 880.0 * t)
    dt = DataTable(size=n, chnls=2)
    np.asarray(dt.getBuffer(0))[:] = ch0
    np.asarray(dt.getBuffer(1))[:] = ch1
    savefileFromTable(table=dt, path=path, fileformat=0, sampletype=0)
    del dt
    s.shutdown()


def base_single_snapshot(mod_path, mod_id="m1", total_time=2.0):
    return {
        "source_id": mod_id,
        "source_ids": [mod_id],
        "connections": [],
        "output_connections": [mod_id],
        "positions": {mod_id: [40, 40]},
        "muted_ids": [],
        "selected_id": mod_id,
        "view": "graph",
        "modules": [
            {
                "id": mod_id,
                "module_path": mod_path,
                "builtin": True,
                "preset": "init",
                "settings": {
                    "userInputs": {},
                    "userSliders": {},
                    "userTogglePopups": {},
                    "userGraph": {},
                },
            }
        ],
        "output": {
            "totalTime": total_time,
            "nchnls": 2,
            "gainSlider": 0.0,
            "audioFileType": "wav",
            "sampSize": 0,
            "output_path": "",
            "startOffset": 0.0,
            "plugins": {
                "0": ["Reverb", [0.3, 1.5, 0.5, 1], [[0.3, 2, None, 1], [1.5, 0, None, 1], [0.5, 0, None, 1]]],
                "1": ["None", [0, 0, 0, 0], [[0, 0, None], [0, 0, None], [0, 0, None]]],
                "2": ["None", [0, 0, 0, 0], [[0, 0, None], [0, 0, None], [0, 0, None]]],
                "3": ["None", [0, 0, 0, 0], [[0, 0, None], [0, 0, None], [0, 0, None]]],
            },
            "userGraph": {
                "plugin_0_reverb_mix": {"data": [[0.0, 0.1], [0.5, 0.8], [1.0, 0.2]], "curved": True}
            },
        },
    }


def run_tests():
    work = tempfile.mkdtemp(prefix="cec_offline_test_")
    try:
        print("1) Testing single-pass render with Reverb plugin + curved automation...")
        out1 = os.path.join(work, "single_stoch.wav")
        snap1 = base_single_snapshot(STOCH, total_time=2.0)
        prog_events = []
        vu_events = []
        mgr1 = OfflineRenderManager(
            RenderSettings(sr=44100, nchnls=2, num_threads=2, accel_mode="single", audio_file_type="wav", samp_size=1),
            on_progress=lambda ev: prog_events.append(ev),
            on_vu=lambda rms, pdb: vu_events.append((rms, pdb)),
        )
        sum1 = mgr1.run_blocking([RenderJob("j1", "Stoch Single", out1, snap1)])
        assert sum1.completed == 1 and sum1.failed == 0, f"Single failed: {sum1.jobs[0].error}"
        info1 = sndinfo(out1)
        print("   info1:", info1, "peak_db:", sum1.max_peak_db, "prog_events:", len(prog_events), "vu_events:", len(vu_events))
        assert info1 is not None and info1[3] == 2 and info1[5] == "24 bit int"
        assert sum1.max_peak_db is not None and sum1.max_peak_db > -60.0

        print("2) Testing time-chunked overlap-crossfade render across 4 threads...")
        out2 = os.path.join(work, "chunked_supersaw.flac")
        snap2 = base_single_snapshot(SUPERSAW, total_time=8.0)
        snap2["modules"][0]["settings"]["userSliders"]["freq"] = [220.0, 1, None, 1]
        snap2["modules"][0]["settings"]["userGraph"]["freq"] = {
            "data": [[0.0, 0.2], [0.5, 0.6], [1.0, 0.3]],
            "curved": False,
        }
        mgr2 = OfflineRenderManager(
            RenderSettings(
                sr=44100, nchnls=2, num_threads=4, accel_mode="chunks",
                preroll=0.4, crossfade=0.1, crossfade_shape="cosine",
                audio_file_type="flac", samp_size=1,
            )
        )
        sum2 = mgr2.run_blocking([RenderJob("j2", "SuperSaw Chunked", out2, snap2)])
        assert sum2.completed == 1 and sum2.failed == 0, f"Chunked failed: {sum2.jobs[0].error}"
        info2 = sndinfo(out2)
        print(f"   info2: {info2}, speedup: {sum2.speedup:.1f}x, peak: {sum2.max_peak_db} dB")
        assert info2[0] == 44100 * 8, f"Expected exact 352800 frames, got {info2[0]}"

        print("3) Testing parallel chain branches + stem export + master Filter plugin...")
        in_wav = os.path.join(work, "source_tone.wav")
        make_test_wav(in_wav, dur=2.0)
        chain_snap = {
            "source_id": "src_a",
            "source_ids": ["src_a", "src_b"],
            "connections": [["src_b", "fx_b"]],
            "output_connections": ["src_a", "fx_b"],
            "positions": {"src_a": [20, 20], "src_b": [20, 120], "fx_b": [180, 120]},
            "muted_ids": [],
            "selected_id": "src_a",
            "view": "chain",
            "modules": [
                {
                    "id": "src_a",
                    "module_path": SUPERSAW,
                    "builtin": True,
                    "preset": "init",
                    "settings": {"userInputs": {}, "userSliders": {}, "userTogglePopups": {}, "userGraph": {}},
                },
                {
                    "id": "src_b",
                    "module_path": BRICKWALL,
                    "builtin": True,
                    "preset": "init",
                    "settings": {
                        "userInputs": {"snd": {"type": "csampler", "mode": 0}},
                        "userSliders": {},
                        "userTogglePopups": {},
                        "userGraph": {},
                    },
                },
                {
                    "id": "fx_b",
                    "module_path": DISTO,
                    "builtin": True,
                    "preset": "init",
                    "settings": {
                        "userInputs": {"snd": {"type": "csampler", "mode": 1}},
                        "userSliders": {},
                        "userTogglePopups": {},
                        "userGraph": {},
                    },
                },
            ],
            "output": {
                "totalTime": 2.5,
                "nchnls": 2,
                "gainSlider": -1.5,
                "audioFileType": "wav",
                "sampSize": 3,
                "output_path": "",
                "startOffset": 0.0,
                "plugins": {
                    "0": ["Filter", [1.0, 2500.0, 1.2, 1], [[1.0, 0, None, 1], [2500.0, 0, None, 1], [1.2, 0, None, 1]]],
                },
                "userGraph": {},
            },
        }
        chain_snap = apply_sound_to_snapshot(chain_snap, in_wav, input_name="snd", module_id="src_b")
        branches = extract_disjoint_output_branches(chain_snap)
        assert branches is not None and len(branches) == 2, f"Expected 2 disjoint branches, got {branches}"
        out3 = os.path.join(work, "chain_master.wav")
        mgr3 = OfflineRenderManager(
            RenderSettings(sr=48000, nchnls=2, num_threads=4, accel_mode="branches", audio_file_type="wav", samp_size=3, export_stems=True)
        )
        job3 = RenderJob("j3", "Parallel Chain", out3, chain_snap, export_stems=True)
        sum3 = mgr3.run_blocking([job3])
        assert sum3.completed == 1 and sum3.failed == 0, f"Branches failed: {job3.error}"
        info3 = sndinfo(out3)
        print("   info3:", info3, "stems:", job3.stem_paths)
        assert len(job3.stem_paths) == 2 and all(os.path.isfile(p) for p in job3.stem_paths)

        print("4) Testing parallel 6-job batch sound folder render across 4 persistent workers...")
        batch_jobs = []
        for idx in range(6):
            snd_i = os.path.join(work, f"in_{idx}.wav")
            make_test_wav(snd_i, dur=1.2 + 0.2 * idx)
            bsnap = base_single_snapshot(BRICKWALL, total_time=1.0)
            bsnap["modules"][0]["settings"]["userInputs"] = {"snd": {"type": "csampler", "mode": 0}}
            bsnap["output"]["plugins"] = {}
            bsnap = apply_sound_to_snapshot(bsnap, snd_i, input_name="snd", use_sound_dur=True)
            out_i = os.path.join(work, f"batch_out_{idx}.aif")
            batch_jobs.append(RenderJob(f"b{idx}", f"Batch {idx}", out_i, bsnap))

        mgr4 = OfflineRenderManager(
            RenderSettings(sr=44100, nchnls=2, num_threads=4, accel_mode="auto", audio_file_type="aif", samp_size=0)
        )
        sum4 = mgr4.run_blocking(batch_jobs)
        assert sum4.completed == 6 and sum4.failed == 0, f"Batch failed: {[j.error for j in sum4.jobs]}"
        print(f"   batch 6 files completed in {sum4.elapsed:.2f}s ({sum4.speedup:.1f}x realtime)")

        print("5) Testing mid-render cancellation...")
        cancel_out = os.path.join(work, "should_be_cancelled.wav")
        long_snap = base_single_snapshot(STOCH, total_time=120.0)
        mgr5 = OfflineRenderManager(
            RenderSettings(sr=96000, nchnls=2, num_threads=2, accel_mode="single", audio_file_type="wav", samp_size=0)
        )
        mgr5.start([RenderJob("jc", "Long Cancel Test", cancel_out, long_snap)])
        time.sleep(0.35)
        t_cancel = time.perf_counter()
        mgr5.cancel()
        mgr5._thread.join(timeout=3.0)
        cancel_dt = time.perf_counter() - t_cancel
        print(f"   cancelled cleanly in {cancel_dt*1000:.1f} ms; partial file exists: {os.path.exists(cancel_out)}")
        assert not mgr5.is_running
        assert not os.path.exists(cancel_out), "Partial output file should be cleaned up on cancel!"

        print("ALL 5 OFFLINE ENGINE TESTS PASSED!")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
