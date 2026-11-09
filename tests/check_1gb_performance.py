"""Benchmark and stress test Cecilia 5 offline renderer with very large files up to 1 GB.

Tests:
1. File size progression: 250 MB, 500 MB, 750 MB, and 1.00 GB (1,000,000,000 bytes).
2. Cross-category module matrix with 1.00 GB input soundfiles across Granular, Filters,
   Dynamics, Multiband, Pitch, Spectral, Reverbs, and Synthesis.
3. Multichannel configurations (2ch, 6ch 5.1 surround, 8ch octaphonic) from 1 GB sources.
4. Acceleration strategies: Single-pass vs. Multi-worker Time-Chunked.
5. Extended duration bounces (30s) from 1 GB input audio.

Measures throughput, coordinator-only peak RSS (excluding workers), sample finiteness, and peak dB.
Generates:
- tests/reports/large_file_1gb_performance.json
- tests/reports/large_file_1gb_performance.md
"""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import struct
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
)

MODULES_DIR = ROOT / "Resources" / "modules"


def get_peak_rss_mb():
    """Coordinator-only MiB; excludes native workers and is not a render memory bound."""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024


def make_large_wav(path, target_bytes, sr=48000, chnls=2):
    """Generate a valid IEEE float32 WAV of specified byte size efficiently."""
    bytes_per_frame = chnls * 4
    total_frames = (target_bytes - 44) // bytes_per_frame
    actual_data_bytes = total_frames * bytes_per_frame
    riff_chunk_size = actual_data_bytes + 36

    # 1 second cyclic test tone pattern
    chunk_frames = sr
    t = np.arange(chunk_frames, dtype=np.float32) / sr
    chunk_data = np.zeros((chnls, chunk_frames), dtype=np.float32)
    for c in range(chnls):
        f0 = 220.0 * (1.33 ** c)
        chunk_data[c] = 0.3 * np.sin(2 * np.pi * f0 * t) + 0.1 * np.sin(2 * np.pi * (f0 * 2.01) * t)

    interleaved_bytes = chunk_data.T.tobytes()
    bytes_per_chunk = len(interleaved_bytes)

    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", riff_chunk_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 3))  # IEEE float
        f.write(struct.pack("<H", chnls))
        f.write(struct.pack("<I", sr))
        f.write(struct.pack("<I", sr * bytes_per_frame))
        f.write(struct.pack("<H", bytes_per_frame))
        f.write(struct.pack("<H", 32))
        f.write(b"data")
        f.write(struct.pack("<I", actual_data_bytes))

        written = 0
        while written + bytes_per_chunk <= actual_data_bytes:
            f.write(interleaved_bytes)
            written += bytes_per_chunk
        remainder = actual_data_bytes - written
        if remainder > 0:
            f.write(interleaved_bytes[:remainder])

    actual_size = os.path.getsize(path)
    return str(path), actual_size, total_frames


def run_test_case(mod_rel, fixture_path, render_dur, sr, out_chnls, mode, temp_dir, timeout=60, threads=1):
    mod_path = MODULES_DIR / mod_rel
    job_id = f"lg_{mod_path.stem}_{int(render_dur)}s_{out_chnls}ch_{mode}"
    snap = audit.snapshot(mod_path, fixture_path)
    snap["output"].update(
        totalTime=render_dur,
        nchnls=out_chnls,
        gainSlider=-6.0,
    )
    if mod_path.stem in ("SpectralGate", "Vectral"):
        snap["modules"][0]["settings"]["userSliders"]["gthresh"] = [-90, 0, None, 1]

    out_file = os.path.join(temp_dir, f"{job_id}.wav")
    job = RenderJob(job_id, job_id, out_file, snap)
    settings = RenderSettings(
        sr=sr,
        nchnls=out_chnls,
        buffersize=512,
        num_threads=threads,
        accel_mode=mode,
        global_fade=0.005,
        samp_size=3,
        crossfade=0.1,
    )

    done = threading.Event()
    results = []
    mgr = OfflineRenderManager(settings, on_complete=lambda r: (results.append(r), done.set()))

    rss_before = get_peak_rss_mb()
    t0 = time.perf_counter()
    mgr.start([job])
    if not done.wait(timeout):
        mgr.cancel()
        mgr._thread.join(timeout=5)
        return {
            "module": str(mod_rel),
            "status": "timeout",
            "error": f"Timed out after {timeout}s",
            "elapsed_sec": timeout,
            "speedup": 0.0,
            "peak_rss_mb": get_peak_rss_mb(),
        }
    mgr._thread.join(timeout=5)
    t1 = time.perf_counter()
    elapsed = max(1e-4, t1 - t0)
    speedup = render_dur / elapsed
    rss_after = get_peak_rss_mb()

    if results and results[0].failed:
        return {
            "module": str(mod_rel),
            "status": "error",
            "error": str(job.error or "Unknown render error"),
            "elapsed_sec": round(elapsed, 3),
            "speedup": round(speedup, 2),
            "peak_rss_mb": round(rss_after, 1),
        }

    if not os.path.isfile(out_file):
        return {
            "module": str(mod_rel),
            "status": "error",
            "error": "Output file missing",
            "elapsed_sec": round(elapsed, 3),
            "speedup": round(speedup, 2),
            "peak_rss_mb": round(rss_after, 1),
        }

    out_size_mb = os.path.getsize(out_file) / (1024 * 1024)
    audio = _read_wav_float64(out_file)

    # Immediately delete output file to preserve APFS disk space
    try:
        os.remove(out_file)
    except OSError:
        pass

    if audio is None:
        return {
            "module": str(mod_rel),
            "status": "error",
            "error": "Failed to decode output audio",
            "elapsed_sec": round(elapsed, 3),
            "speedup": round(speedup, 2),
            "peak_rss_mb": round(rss_after, 1),
        }

    finite = bool(np.isfinite(audio).all())
    peak_val = float(np.max(np.abs(audio))) if finite else 0.0
    peak_db = 20.0 * np.log10(max(1e-6, peak_val))

    return {
        "module": str(mod_rel),
        "status": "pass" if finite else "fail_nonfinite",
        "error": None if finite else "Non-finite samples detected",
        "elapsed_sec": round(elapsed, 3),
        "speedup": round(speedup, 2),
        "peak_db": round(peak_db, 2),
        "peak_rss_mb": round(rss_after, 1),
        "out_size_mb": round(out_size_mb, 2),
        "shape": list(audio.shape),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit offline render performance with large files up to 1 GB.")
    parser.add_argument("--report-prefix", default="large_file_1gb_performance", help="Prefix for report files")
    args = parser.parse_args()

    work_dir = tempfile.mkdtemp(prefix="cec_1gb_bench_")
    print(f"Working in temporary directory: {work_dir}")

    all_results = {
        "progression": [],
        "module_matrix_1gb": [],
        "multichannel_1gb": [],
        "chunked_1gb": [],
        "extended_dur_1gb": [],
    }

    t_bench_start = time.perf_counter()

    try:
        # ---------------------------------------------------------
        # Part 1: File Size Progression (250 MB -> 500 MB -> 750 MB -> 1.00 GB)
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PART 1: FILE SIZE PROGRESSION BENCHMARK (Up to 1.00 GB)")
        print("=======================================================")
        progression_sizes = [
            (250_000_000, "250MB"),
            (500_000_000, "500MB"),
            (750_000_000, "750MB"),
            (1_000_000_000, "1.00GB"),
        ]

        for target_bytes, label in progression_sizes:
            f_path = os.path.join(work_dir, f"probe_{label}.wav")
            print(f"\nGenerating {label} audio fixture ({target_bytes / (1024*1024):.1f} MB)...")
            t_gen0 = time.perf_counter()
            _, actual_bytes, total_frames = make_large_wav(f_path, target_bytes, sr=48000, chnls=2)
            t_gen1 = time.perf_counter()
            dur_sec = total_frames / 48000.0
            print(f"Generated {actual_bytes / (1024*1024):.1f} MB ({dur_sec:.1f}s / {dur_sec/60:.1f} min) in {t_gen1 - t_gen0:.2f}s")

            # Test on StateVar2 and UltimateGrainer
            for test_mod in ["Filters/StateVar2.c5", "Time/UltimateGrainer.c5"]:
                res = run_test_case(
                    mod_rel=test_mod,
                    fixture_path=f_path,
                    render_dur=5.0,
                    sr=48000,
                    out_chnls=2,
                    mode="single",
                    temp_dir=work_dir,
                )
                res["size_tier"] = label
                res["actual_bytes"] = actual_bytes
                res["input_dur_sec"] = dur_sec
                all_results["progression"].append(res)
                print(f"  [{label}] {test_mod}: {res['speedup']}x realtime, Peak RSS={res['peak_rss_mb']}MB [{res['status']}]")

            # Remove progression file before next to save disk space
            if os.path.exists(f_path):
                os.remove(f_path)

        # ---------------------------------------------------------
        # Part 2: 1.00 GB Input File Across Representative Modules
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PART 2: REPRESENTATIVE MODULE MATRIX WITH 1.00 GB AUDIO")
        print("=======================================================")
        f_1gb = os.path.join(work_dir, "master_1gb.wav")
        print("Generating 1.00 GB master fixture (1,000,000,000 bytes)...")
        _, actual_1gb_bytes, frames_1gb = make_large_wav(f_1gb, 1_000_000_000, sr=48000, chnls=2)
        dur_1gb_sec = frames_1gb / 48000.0
        print(f"1.00 GB Master ready: {actual_1gb_bytes / (1024*1024):.1f} MB, {dur_1gb_sec:.1f} seconds ({dur_1gb_sec/60:.1f} minutes)")

        target_modules = [
            ("Time/UltimateGrainer.c5", "Granular / Particle2"),
            ("Time/Particle.c5", "Granular / Table"),
            ("Time/Pelletizer.c5", "Granular / Looper"),
            ("Filters/StateVar2.c5", "Filters / StateVar"),
            ("Filters/BrickWall.c5", "Filters / BrickWall"),
            ("Filters/AMFMFilter.c5", "Filters / Modulated"),
            ("Dynamics/Distortion.c5", "Dynamics / Distort"),
            ("Dynamics/DynamicsProcessor.c5", "Dynamics / Compressor"),
            ("Dynamics/FeedbackLooper.c5", "Dynamics / TableLooper"),
            ("Multiband/MultiBandDelay.c5", "Multiband / Delay"),
            ("Multiband/MultiBandReverb.c5", "Multiband / Reverb"),
            ("Pitch/Harmonizer.c5", "Pitch / Harmonizer"),
            ("Pitch/ChordMaker.c5", "Pitch / MultiVoice"),
            ("Pitch/PitchLooper.c5", "Pitch / TableLooper"),
            ("Spectral/SpectralWarper.c5", "Spectral / PhaseVocoder"),
            ("Spectral/SpectralDelay.c5", "Spectral / PVSpectralDelay"),
            ("Resonators&Verbs/MatrixReverb.c5", "Resonators / MatrixReverb"),
            ("Synthesis/StochGrains2.c5", "Synthesis / FileGrain"),
        ]

        for mod_rel, desc in target_modules:
            mod_path = MODULES_DIR / mod_rel
            if not mod_path.is_file():
                continue
            res = run_test_case(
                mod_rel=mod_rel,
                fixture_path=f_1gb,
                render_dur=5.0,
                sr=48000,
                out_chnls=2,
                mode="single",
                temp_dir=work_dir,
            )
            res["description"] = desc
            res["input_size_mb"] = actual_1gb_bytes / (1024 * 1024)
            all_results["module_matrix_1gb"].append(res)
            print(f"  {mod_rel:32s} ({desc:24s}): {res['speedup']:5.1f}x [{res['status']}] (Peak={res['peak_db']} dBFS, RSS={res['peak_rss_mb']} MB)")

        # ---------------------------------------------------------
        # Part 3: Multichannel Outputs with 1.00 GB Input
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PART 3: MULTICHANNEL OUTPUTS FROM 1.00 GB INPUT")
        print("=======================================================")
        for ch, ch_name in [(2, "Stereo"), (6, "5.1 Surround"), (8, "8ch Octaphonic")]:
            for sm in ["Filters/StateVar2.c5", "Time/UltimateGrainer.c5", "Pitch/Harmonizer.c5"]:
                res = run_test_case(
                    mod_rel=sm,
                    fixture_path=f_1gb,
                    render_dur=4.0,
                    sr=48000,
                    out_chnls=ch,
                    mode="single",
                    temp_dir=work_dir,
                )
                res["channels"] = ch
                res["layout"] = ch_name
                all_results["multichannel_1gb"].append(res)
                print(f"  {sm:28s} -> {ch_name:14s} ({ch}ch): {res['speedup']:5.1f}x [{res['status']}]")

        # ---------------------------------------------------------
        # Part 4: Multi-Worker Time-Chunking with 1.00 GB Input
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PART 4: TIME-CHUNKED MULTI-WORKER RENDERING (1.00 GB)")
        print("=======================================================")
        for sm in ["Filters/StateVar2.c5", "Dynamics/Distortion.c5", "Pitch/Harmonizer.c5", "Time/Particle.c5"]:
            res = run_test_case(
                mod_rel=sm,
                fixture_path=f_1gb,
                render_dur=10.0,
                sr=48000,
                out_chnls=2,
                mode="chunks",
                threads=2,
                temp_dir=work_dir,
            )
            res["strategy"] = "Time Chunks (2 workers)"
            all_results["chunked_1gb"].append(res)
            print(f"  Chunked {sm:24s} (10.0s @ 2 workers): {res['speedup']:5.1f}x [{res['status']}]")

        # ---------------------------------------------------------
        # Part 5: Extended Duration Bounce (30.0s) from 1.00 GB File
        # ---------------------------------------------------------
        print("\n=======================================================")
        print("PART 5: EXTENDED DURATION BOUNCE (30.0s) FROM 1.00 GB")
        print("=======================================================")
        for sm in ["Filters/StateVar2.c5", "Dynamics/DynamicsProcessor.c5", "Multiband/MultiBandDelay.c5"]:
            res = run_test_case(
                mod_rel=sm,
                fixture_path=f_1gb,
                render_dur=30.0,
                sr=48000,
                out_chnls=2,
                mode="single",
                temp_dir=work_dir,
                timeout=90,
            )
            res["render_duration"] = 30.0
            all_results["extended_dur_1gb"].append(res)
            print(f"  Extended {sm:28s} (30s render): {res['speedup']:5.1f}x [{res['status']}] (Time={res['elapsed_sec']}s)")

        # Clean up 1 GB master fixture
        if os.path.exists(f_1gb):
            os.remove(f_1gb)
            print("\nCleaned up 1.00 GB master test fixture.")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    t_bench_end = time.perf_counter()
    total_bench_time = t_bench_end - t_bench_start

    # Summary Statistics
    flat_results = (
        all_results["progression"]
        + all_results["module_matrix_1gb"]
        + all_results["multichannel_1gb"]
        + all_results["chunked_1gb"]
        + all_results["extended_dur_1gb"]
    )
    total_tests = len(flat_results)
    passed_tests = sum(1 for r in flat_results if r["status"] == "pass")
    failed_tests = total_tests - passed_tests
    speedups = [r["speedup"] for r in flat_results if r["status"] == "pass"]
    avg_speedup = float(np.mean(speedups)) if speedups else 0.0
    median_speedup = float(np.median(speedups)) if speedups else 0.0
    min_speedup = float(np.min(speedups)) if speedups else 0.0
    max_speedup = float(np.max(speedups)) if speedups else 0.0

    print("\n=======================================================")
    print("1 GB BENCHMARK COMPLETE")
    print(f"Total Tests: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    print(f"Speedup: Avg={avg_speedup:.1f}x, Median={median_speedup:.1f}x, Min={min_speedup:.1f}x, Max={max_speedup:.1f}x")
    print(f"Total Wall Time: {total_bench_time:.2f} seconds")
    print("=======================================================\n")

    # Save JSON and Markdown Reports
    reports_dir = ROOT / "tests" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"{args.report_prefix}.json"
    md_path = reports_dir / f"{args.report_prefix}.md"

    summary_data = {
        "summary": {
            "rss_scope": "coordinator_only_excludes_native_workers",
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "avg_speedup": round(avg_speedup, 2),
            "median_speedup": round(median_speedup, 2),
            "min_speedup": round(min_speedup, 2),
            "max_speedup": round(max_speedup, 2),
            "total_wall_time_sec": round(total_bench_time, 2),
        },
        "results": all_results,
    }

    with open(json_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    with open(md_path, "w") as f:
        f.write("# Very Large File Performance & 1 GB Stress Benchmark Report\n\n")
        f.write("> RSS measures only the coordinator and excludes native worker processes. These cases render short outputs from large inputs; use check_offline_memory.py for worker RAM and gigabyte outputs.\n\n")
        f.write("## Executive Summary\n\n")
        f.write(f"- **Max File Size Tested**: **1.00 GB** (`1,000,000,000 bytes` / 125,000,000 samples @ 48 kHz / 43.4 minutes audio).\n")
        f.write(f"- **Total Benchmark Cases**: **{total_tests}**.\n")
        f.write(f"- **Pass Rate**: **{passed_tests} / {total_tests} passed ({100*passed_tests/max(1,total_tests):.1f}% pass rate, {failed_tests} failures)**.\n")
        f.write(f"- **Average Throughput**: **{avg_speedup:.1f}x realtime** (median **{median_speedup:.1f}x**, max **{max_speedup:.1f}x**).\n")
        f.write(f"- **Total Benchmark Runtime**: **{total_bench_time:.2f} seconds**.\n\n")

        f.write("## Part 1: File Size Progression (250 MB -> 1.00 GB)\n\n")
        f.write("| Size Tier | Input File Size | Input Duration | Module | Render Dur | Speedup | Coordinator RSS (MiB) | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in all_results["progression"]:
            f.write(f"| {r['size_tier']} | {r['actual_bytes'] / (1024*1024):.1f} MB | {r['input_dur_sec']:.1f}s | `{r['module']}` | 5.0s | **{r['speedup']:.1f}x** | {r['peak_rss_mb']:.1f} MB | **{r['status'].upper()}** |\n")

        f.write("\n## Part 2: Representative Modules with 1.00 GB Audio (48 kHz, 2ch, 43.4 min source)\n\n")
        f.write("| Module | Category / Engine | Speedup | Peak dBFS | Coordinator RSS (MiB) | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in all_results["module_matrix_1gb"]:
            f.write(f"| `{r['module']}` | {r['description']} | **{r['speedup']:.1f}x** | {r['peak_db']:.2f} dB | {r['peak_rss_mb']:.1f} MB | **{r['status'].upper()}** |\n")

        f.write("\n## Part 3: Multichannel Outputs from 1.00 GB Audio\n\n")
        f.write("| Module | Channels | Layout | Speedup | Peak dBFS | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in all_results["multichannel_1gb"]:
            f.write(f"| `{r['module']}` | {r['channels']} ch | {r['layout']} | **{r['speedup']:.1f}x** | {r['peak_db']:.2f} dB | **{r['status'].upper()}** |\n")

        f.write("\n## Part 4: Multi-Worker Time-Chunked Rendering from 1.00 GB Audio\n\n")
        f.write("| Module | Strategy | Render Duration | Speedup | Peak dBFS | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in all_results["chunked_1gb"]:
            f.write(f"| `{r['module']}` | {r['strategy']} | 10.0s | **{r['speedup']:.1f}x** | {r['peak_db']:.2f} dB | **{r['status'].upper()}** |\n")

        f.write("\n## Part 5: Extended Duration Bounces (30.0s) from 1.00 GB Audio\n\n")
        f.write("| Module | Render Duration | Elapsed Time | Speedup | Peak dBFS | Status |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in all_results["extended_dur_1gb"]:
            f.write(f"| `{r['module']}` | {r['render_duration']:.1f}s | {r['elapsed_sec']:.2f}s | **{r['speedup']:.1f}x** | {r['peak_db']:.2f} dB | **{r['status'].upper()}** |\n")

    print(f"Reports saved to:\n  - {json_path}\n  - {md_path}")


if __name__ == "__main__":
    main()

