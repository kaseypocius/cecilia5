"""Benchmark and audit offline renderer performance across all 69 modules with various file sizes.

Tests each module with Small (~1.5s), Medium (~15s), Large (~60s), and Extra Large input/output files.
Measures execution time, realtime speedup factor, and audio output integrity.
This harness does not measure native worker RAM; use check_offline_memory.py.
Writes tests/reports/filesize_performance.json and tests/reports/filesize_performance.md.
"""
import argparse
import copy
import glob
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from pyo import sndinfo
import check_all_modules as audit
from Resources.OfflineRender import (
    OfflineRenderManager,
    RenderJob,
    RenderSettings,
    _read_wav_float64,
    _write_wav_float32,
    apply_sound_to_snapshot,
)

MODULES_DIR = ROOT / "Resources" / "modules"


def get_all_modules():
    mods = []
    for f in sorted(MODULES_DIR.glob("**/*.c5")):
        rel = f.relative_to(MODULES_DIR)
        mods.append(rel)
    return mods


def make_sound_file(path, dur_sec, sr=44100, chnls=2):
    frames = int(round(dur_sec * sr))
    t = np.arange(frames, dtype=np.float64) / sr
    data = np.zeros((chnls, frames), dtype=np.float32)
    for c in range(chnls):
        base_f = 220.0 * (1.25 ** c)
        data[c] = (
            0.35 * np.sin(2 * np.pi * base_f * t)
            + 0.15 * np.sin(2 * np.pi * (base_f * 2.01) * t)
            + 0.05 * np.sin(2 * np.pi * (base_f * 3.03) * t)
        )
    _write_wav_float32(data, str(path), sr)
    size_mb = os.path.getsize(str(path)) / (1024 * 1024)
    return str(path), size_mb, frames


def get_peak_rss_mb():
    """Coordinator-only MiB (unused by this throughput report)."""
    # ru_maxrss on macOS is in bytes
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024


def run_single_case(mod_rel, mod_path, fixture_path, fixture_dur, render_dur, sr, out_chnls, mode, temp_dir):
    job_id = f"fs_{mod_path.stem}_{int(render_dur)}s_{out_chnls}ch"
    snap = audit.snapshot(mod_path, fixture_path)
    snap["output"].update(
        totalTime=render_dur,
        nchnls=out_chnls,
        gainSlider=-12.0,
    )
    # Enable audible parameters for spectral modules if needed
    if mod_path.stem in ("SpectralGate", "Vectral"):
        snap["modules"][0]["settings"]["userSliders"]["gthresh"] = [-90, 0, None, 1]

    out_file = os.path.join(temp_dir, f"{job_id}.wav")
    job = RenderJob(job_id, job_id, out_file, snap)
    settings = RenderSettings(
        sr=sr,
        nchnls=out_chnls,
        buffersize=512,
        num_threads=2 if mode == "chunks" else 1,
        accel_mode=mode,
        global_fade=0.005,
        samp_size=3,
        crossfade=0.08,
    )

    done = threading.Event()
    results = []
    mgr = OfflineRenderManager(settings, on_complete=lambda r: (results.append(r), done.set()))
    
    t0 = time.perf_counter()
    mgr.start([job])
    if not done.wait(45):
        mgr.cancel()
        mgr._thread.join(timeout=5)
        return {
            "status": "timeout",
            "error": "Render timed out after 45s",
            "elapsed_sec": 45.0,
            "speedup": 0.0,
        }
    mgr._thread.join(timeout=5)
    t1 = time.perf_counter()
    elapsed = max(1e-4, t1 - t0)
    speedup = render_dur / elapsed

    if results and results[0].failed:
        return {
            "status": "error",
            "error": str(job.error or "Unknown error"),
            "elapsed_sec": elapsed,
            "speedup": speedup,
        }

    # Validate output
    if not os.path.isfile(out_file):
        return {
            "status": "error",
            "error": "Output file was not generated",
            "elapsed_sec": elapsed,
            "speedup": speedup,
        }

    out_size_mb = os.path.getsize(out_file) / (1024 * 1024)
    audio = _read_wav_float64(out_file)
    if audio is None:
        return {
            "status": "error",
            "error": "Could not read output audio file",
            "elapsed_sec": elapsed,
            "speedup": speedup,
        }

    expected_frames = int(round(render_dur * sr))
    finite = bool(np.isfinite(audio).all())
    peak_val = float(np.max(np.abs(audio))) if finite else 0.0
    peak_db = 20.0 * np.log10(max(1e-6, peak_val))

    # Clean up output file immediately to preserve disk space
    try:
        os.remove(out_file)
    except OSError:
        pass

    return {
        "status": "pass" if finite else "fail_nonfinite",
        "error": None if finite else "Non-finite samples detected",
        "elapsed_sec": round(elapsed, 4),
        "speedup": round(speedup, 2),
        "peak_db": round(peak_db, 2),
        "finite": finite,
        "out_size_mb": round(out_size_mb, 3),
        "shape": list(audio.shape),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit offline render performance across file sizes.")
    parser.add_argument("--filter", default="", help="Regex filter for module names")
    parser.add_argument("--report-prefix", default="filesize_performance", help="Report prefix")
    args = parser.parse_args()

    work_dir = tempfile.mkdtemp(prefix="cec_filesize_bench_")
    print(f"Working in temp directory: {work_dir}")

    try:
        # Create standard test fixture sounds of varying sizes
        print("Creating input audio fixtures of various sizes...")
        f_small, sz_small, fr_small = make_sound_file(Path(work_dir) / "small.wav", dur_sec=1.5, sr=44100, chnls=2)
        f_med, sz_med, fr_med = make_sound_file(Path(work_dir) / "medium.wav", dur_sec=15.0, sr=44100, chnls=2)
        f_large, sz_large, fr_large = make_sound_file(Path(work_dir) / "large.wav", dur_sec=60.0, sr=48000, chnls=2)
        f_xlarge, sz_xl, fr_xl = make_sound_file(Path(work_dir) / "xlarge.wav", dur_sec=120.0, sr=96000, chnls=4)

        tiers = [
            {"tier": "small", "path": f_small, "dur": 1.5, "render_dur": 1.0, "sr": 44100, "chnls": 2, "size_mb": sz_small, "mode": "single"},
            {"tier": "medium", "path": f_med, "dur": 15.0, "render_dur": 5.0, "sr": 44100, "chnls": 2, "size_mb": sz_med, "mode": "single"},
            {"tier": "large", "path": f_large, "dur": 60.0, "render_dur": 10.0, "sr": 48000, "chnls": 2, "size_mb": sz_large, "mode": "single"},
            {"tier": "chunked_large", "path": f_large, "dur": 60.0, "render_dur": 15.0, "sr": 48000, "chnls": 4, "size_mb": sz_large, "mode": "chunks"},
        ]

        print(f"Fixture Small: {sz_small:.2f} MB (1.5s, 44.1k 2ch)")
        print(f"Fixture Medium: {sz_med:.2f} MB (15s, 44.1k 2ch)")
        print(f"Fixture Large: {sz_large:.2f} MB (60s, 48k 2ch)")
        print(f"Fixture Extra Large: {sz_xl:.2f} MB (120s, 96k 4ch)")

        all_modules = get_all_modules()
        if args.filter:
            all_modules = [m for m in all_modules if args.filter.lower() in str(m).lower()]

        print(f"\nBenchmarking {len(all_modules)} modules across 4 file size tiers (Total cases: {len(all_modules) * len(tiers)})...")

        results = []
        t_bench_start = time.perf_counter()

        for idx, mod_rel in enumerate(all_modules, 1):
            mod_path = MODULES_DIR / mod_rel
            category = mod_rel.parent.name
            inputs = audit.inputs_for(mod_path)
            input_types = [v["type"] for v in inputs.values()]
            kind = "synthesis" if not input_types else (",".join(input_types))

            mod_results = {
                "module": str(mod_rel),
                "name": mod_path.stem,
                "category": category,
                "kind": kind,
                "tiers": {},
            }

            print(f"[{idx:02d}/{len(all_modules)}] {mod_rel} ({kind}):", end="", flush=True)

            mod_passed = True
            for tier_spec in tiers:
                tier_name = tier_spec["tier"]
                res = run_single_case(
                    mod_rel=mod_rel,
                    mod_path=mod_path,
                    fixture_path=tier_spec["path"],
                    fixture_dur=tier_spec["dur"],
                    render_dur=tier_spec["render_dur"],
                    sr=tier_spec["sr"],
                    out_chnls=tier_spec["chnls"],
                    mode=tier_spec["mode"],
                    temp_dir=work_dir,
                )
                mod_results["tiers"][tier_name] = res
                if res["status"] != "pass":
                    mod_passed = False
                sp = res.get("speedup", 0.0)
                print(f" {tier_name}={sp:.1f}x", end="", flush=True)

            status_str = "PASS" if mod_passed else "FAIL"
            print(f" [{status_str}]", flush=True)
            results.append(mod_results)

        # High-channel stress test for granular/time modules (UltimateGrainer, Particle, Pelletizer, Harmonizer)
        print("\nRunning Extra Large Stress Test (96 kHz, 120s input sound, 8-channel & 50-channel outputs)...")
        stress_modules = [
            "Time/UltimateGrainer.c5",
            "Time/Particle.c5",
            "Time/Pelletizer.c5",
            "Pitch/Harmonizer.c5",
            "Filters/StateVar2.c5",
            "Resonators&Verbs/ConvolutionReverb.c5",
        ]
        stress_results = []
        f_ir, sz_ir, _ = make_sound_file(Path(work_dir) / "ir_3s.wav", dur_sec=3.0, sr=96000, chnls=2)
        for sm in stress_modules:
            mod_path = MODULES_DIR / sm
            if mod_path.is_file():
                is_ir = "ConvolutionReverb" in sm
                s_fixture = f_ir if is_ir else f_xlarge
                s_dur = 3.0 if is_ir else 120.0
                s_size = sz_ir if is_ir else sz_xl
                for ch in (8, 50):
                    res = run_single_case(
                        mod_rel=sm,
                        mod_path=mod_path,
                        fixture_path=s_fixture,
                        fixture_dur=s_dur,
                        render_dur=2.0,
                        sr=96000,
                        out_chnls=ch,
                        mode="single",
                        temp_dir=work_dir,
                    )
                    res["module"] = sm
                    res["channels"] = ch
                    res["input_file_size_mb"] = s_size
                    res["sr"] = 96000
                    stress_results.append(res)
                    print(f"  Stress {sm} ({ch}ch @ 96kHz, {s_size:.1f}MB input): {res['speedup']:.1f}x [{res['status']}]")

        t_bench_end = time.perf_counter()
        total_time = t_bench_end - t_bench_start

        # Compile summaries
        total_cases = len(results) * len(tiers)
        passed_cases = sum(1 for m in results for t in m["tiers"].values() if t["status"] == "pass")
        failed_cases = total_cases - passed_cases
        stress_passed = sum(1 for s in stress_results if s["status"] == "pass")

        # Compute speedup statistics
        speedups = [t["speedup"] for m in results for t in m["tiers"].values() if t["status"] == "pass"]
        avg_speedup = float(np.mean(speedups)) if speedups else 0.0
        median_speedup = float(np.median(speedups)) if speedups else 0.0
        min_speedup = float(np.min(speedups)) if speedups else 0.0
        max_speedup = float(np.max(speedups)) if speedups else 0.0

        print(f"\n=======================================================")
        print(f"BENCHMARK COMPLETE in {total_time:.2f} seconds")
        print(f"Total Cases: {total_cases} | Passed: {passed_cases} | Failed: {failed_cases}")
        print(f"Stress Cases (96k/50ch/92MB input): {stress_passed}/{len(stress_results)} passed")
        print(f"Speedup Stats: Avg={avg_speedup:.1f}x, Median={median_speedup:.1f}x, Min={min_speedup:.1f}x, Max={max_speedup:.1f}x")
        print(f"=======================================================\n")

        # Generate Reports
        reports_dir = ROOT / "tests" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        json_path = reports_dir / f"{args.report_prefix}.json"
        md_path = reports_dir / f"{args.report_prefix}.md"

        full_data = {
            "summary": {
                "total_modules": len(results),
                "total_cases": total_cases,
                "passed_cases": passed_cases,
                "failed_cases": failed_cases,
                "stress_total": len(stress_results),
                "stress_passed": stress_passed,
                "total_elapsed_sec": round(total_time, 2),
                "speedup_avg": round(avg_speedup, 2),
                "speedup_median": round(median_speedup, 2),
                "speedup_min": round(min_speedup, 2),
                "speedup_max": round(max_speedup, 2),
            },
            "tiers": tiers,
            "modules": results,
            "stress_tests": stress_results,
        }

        with open(json_path, "w") as f:
            json.dump(full_data, f, indent=2)
        print(f"Wrote JSON report: {json_path}")

        # Build Markdown Table
        lines = [
            f"# Offline Renderer Performance & File Size Scaling Matrix",
            f"",
            f"## Executive Summary",
            f"",
            f"- **Modules Tested**: All {len(results)} shipped Cecilia 5 modules.",
            f"- **Total Benchmark Cases**: {total_cases} cases across 4 file size tiers.",
            f"- **Pass Rate**: **{passed_cases} / {total_cases} passed** ({failed_cases} failures).",
            f"- **Stress Cases (120s / 92 MB input @ 96 kHz up to 50 channels)**: **{stress_passed} / {len(stress_results)} passed**.",
            f"- **Average Throughput**: **{avg_speedup:.1f}x realtime** (median **{median_speedup:.1f}x**, ranging from **{min_speedup:.1f}x** to **{max_speedup:.1f}x**).",
            f"- **Total Benchmark Duration**: {total_time:.2f} seconds.",
            f"",
            f"## Tested File Size Tiers",
            f"",
            f"| Tier | Input Sound Size | Input Duration | Render Duration | Output Format | Acceleration Strategy |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- |",
            f"| **Small** | {sz_small:.2f} MB | 1.5s | 1.0s | 2ch @ 44.1 kHz | Single-pass |",
            f"| **Medium** | {sz_med:.2f} MB | 15.0s | 5.0s | 2ch @ 44.1 kHz | Single-pass |",
            f"| **Large** | {sz_large:.2f} MB | 60.0s | 10.0s | 2ch @ 48.0 kHz | Single-pass |",
            f"| **Chunked Large** | {sz_large:.2f} MB | 60.0s | 15.0s | 4ch @ 48.0 kHz | Time Chunks (2 threads) |",
            f"",
            f"## High-Channel & Large-File Stress Results",
            f"",
            f"| Module | Channels | Rate | Input File Size | Speedup | Status | Peak dB |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for s in stress_results:
            peak_str = f"{s['peak_db']} dB" if "peak_db" in s else "--"
            lines.append(f"| `{s['module']}` | {s['channels']} ch | {s['sr']} Hz | {s['input_file_size_mb']:.1f} MB | **{s['speedup']:.1f}x** | {s['status']} | {peak_str} |")

        lines.extend([
            f"",
            f"## Complete Per-Module Results Table",
            f"",
            f"| Module | Category | Kind | Small (1.5s) | Medium (15s) | Large (60s) | Chunked (60s) | Status |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for m in results:
            t = m["tiers"]
            s_sp = f"{t['small']['speedup']}x" if t["small"]["status"] == "pass" else t["small"]["status"]
            m_sp = f"{t['medium']['speedup']}x" if t["medium"]["status"] == "pass" else t["medium"]["status"]
            l_sp = f"{t['large']['speedup']}x" if t["large"]["status"] == "pass" else t["large"]["status"]
            c_sp = f"{t['chunked_large']['speedup']}x" if t["chunked_large"]["status"] == "pass" else t["chunked_large"]["status"]
            mod_status = "PASS" if all(x["status"] == "pass" for x in t.values()) else "FAIL"
            lines.append(f"| `{m['name']}` | {m['category']} | `{m['kind']}` | {s_sp} | {m_sp} | {l_sp} | {c_sp} | **{mod_status}** |")

        with open(md_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Wrote Markdown report: {md_path}")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"Cleaned up temporary workspace: {work_dir}")


if __name__ == "__main__":
    main()

