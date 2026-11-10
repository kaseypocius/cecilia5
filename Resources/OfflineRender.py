"""
This file is part of Cecilia 5.

Cecilia 5 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Cecilia 5 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Cecilia 5.  If not, see <http://www.gnu.org/licenses/>.

Multithreaded Offline Render Engine & Headless Worker Pool for Cecilia 5.
"""

import concurrent.futures
import copy
import gc
import json
import math
import os
import queue
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
import xmlrpc.client as xmlrpclib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

EVENT_PREFIX = "\x02CEC_OFFLINE:"

# Exact parameter specifications matching Resources/Plugins.py:
# plugin_name -> list of (knob_name_template, mini, maxi, init, log)
PLUGIN_SPECS: Dict[str, List[Tuple[str, float, float, float, bool]]] = {
    "Reverb": [
        ("plugin_%d_reverb_mix", 0.0, 1.0, 0.25, False),
        ("plugin_%d_reverb_time", 0.01, 10.0, 1.0, False),
        ("plugin_%d_reverb_damp", 0.0, 1.0, 0.5, False),
    ],
    "WGVerb": [
        ("plugin_%d_wgreverb_mix", 0.0, 1.0, 0.25, False),
        ("plugin_%d_wgreverb_feed", 0.0, 1.0, 0.7, False),
        ("plugin_%d_wgreverb_lp", 100.0, 15000.0, 5000.0, True),
    ],
    "Filter": [
        ("plugin_%d_filter_level", 0.0, 2.0, 1.0, False),
        ("plugin_%d_filter_freq", 20.0, 18000.0, 1000.0, True),
        ("plugin_%d_filter_q", 0.5, 10.0, 1.0, False),
    ],
    "Para EQ": [
        ("plugin_%d_eq_freq", 20.0, 18000.0, 1000.0, True),
        ("plugin_%d_eq_q", 0.5, 10.0, 1.0, False),
        ("plugin_%d_eq_gain", -48.0, 18.0, -3.0, False),
    ],
    "3 Bands EQ": [
        ("plugin_%d_eq3b_low", -60.0, 18.0, 0.0, False),
        ("plugin_%d_eq3b_mid", -60.0, 18.0, 0.0, False),
        ("plugin_%d_eq3b_high", -60.0, 18.0, 0.0, False),
    ],
    "Chorus": [
        ("plugin_%d_chorus_mix", 0.0, 1.0, 0.5, False),
        ("plugin_%d_chorus_depth", 0.001, 5.0, 0.2, False),
        ("plugin_%d_chorus_feed", 0.0, 1.0, 0.5, False),
    ],
    "Compress": [
        ("plugin_%d_comp_thresh", -80.0, 0.0, -20.0, False),
        ("plugin_%d_comp_ratio", 0.125, 20.0, 3.0, False),
        ("plugin_%d_comp_gain", -36.0, 36.0, 0.0, False),
    ],
    "Gate": [
        ("plugin_%d_gate_thresh", -120.0, 0.0, -70.0, False),
        ("plugin_%d_gate_rise", 0.0005, 0.5, 0.005, True),
        ("plugin_%d_gate_fall", 0.0005, 0.5, 0.01, True),
    ],
    "Disto": [
        ("plugin_%d_disto_drive", 0.0, 1.0, 0.7, False),
        ("plugin_%d_disto_slope", 0.0, 1.0, 0.7, False),
        ("plugin_%d_disto_gain", -60.0, 0.0, -12.0, False),
    ],
    "AmpMod": [
        ("plugin_%d_ampmod_freq", 0.01, 1000.0, 8.0, True),
        ("plugin_%d_ampmod_amp", 0.0, 1.0, 1.0, False),
        ("plugin_%d_ampmod_stereo", 0.0, 0.5, 0.0, False),
    ],
    "Phaser": [
        ("plugin_%d_phaser_freq", 20.0, 1000.0, 100.0, True),
        ("plugin_%d_phaser_q", 1.0, 20.0, 5.0, False),
        ("plugin_%d_phaser_spread", 0.5, 2.0, 1.1, False),
    ],
    "Delay": [
        ("plugin_%d_delay_delay", 0.01, 1.0, 0.1, False),
        ("plugin_%d_delay_feed", 0.0, 0.999, 0.0, False),
        ("plugin_%d_delay_mix", 0.0, 1.0, 0.5, False),
    ],
    "Flange": [
        ("plugin_%d_flange_depth", 0.001, 0.99, 0.5, False),
        ("plugin_%d_flange_freq", 0.001, 20.0, 1.0, True),
        ("plugin_%d_flange_feed", 0.0, 0.999, 0.5, False),
    ],
    "Harmonizer": [
        ("plugin_%d_harmonizer_transpo", -24.0, 24.0, -7.0, False),
        ("plugin_%d_harmonizer_feed", 0.0, 0.999, 0.0, False),
        ("plugin_%d_harmonizer_mix", 0.0, 1.0, 0.5, False),
    ],
    "Resonators": [
        ("plugin_%d_resonators_freq", 20.0, 1000.0, 80.0, True),
        ("plugin_%d_resonators_spread", 0.25, 4.0, 2.01, False),
        ("plugin_%d_resonators_mix", 0.0, 1.0, 0.33, False),
    ],
    "DeadReson": [
        ("plugin_%d_deadresonators_freq", 20.0, 1000.0, 80.0, True),
        ("plugin_%d_deadresonators_detune", 0.0, 1.0, 0.5, False),
        ("plugin_%d_deadresonators_mix", 0.0, 1.0, 0.33, False),
    ],
    "ChaosMod": [
        ("plugin_%d_chaosmod_freq", 0.001, 1.0, 0.025, True),
        ("plugin_%d_chaosmod_amp", 0.0, 1.0, 0.5, False),
        ("plugin_%d_chaosmod_amp", 0.0, 1.0, 1.0, False),
    ],
}

ACCEL_MODES = ("auto", "single", "branches", "chunks")
CROSSFADE_SHAPES = ("cosine", "equal_power")


@dataclass
class RenderSettings:
    sr: int = 44100
    nchnls: int = 2
    buffersize: int = 512
    audio_file_type: str = "wav"
    samp_size: int = 0
    global_fade: float = 0.005
    num_threads: int = 4
    accel_mode: str = "auto"  # 'auto' | 'single' | 'branches' | 'chunks'
    chunk_min_dur: float = 8.0
    preroll: float = 0.5  # Legacy preference; exact chunks replay from the origin.
    crossfade: float = 0.1
    crossfade_shape: str = "cosine"  # 'cosine' | 'equal_power'
    export_stems: bool = False
    normalize: bool = False
    normalize_target_db: float = -0.1


@dataclass
class RenderJob:
    job_id: str
    title: str
    output_path: str
    snapshot: Dict[str, Any]
    duration_override: Optional[float] = None
    export_stems: bool = False
    normalize: bool = False
    normalize_target_db: float = -0.1
    master_output: bool = True
    module_outputs: Dict[str, str] = field(default_factory=dict)
    status: str = "Queued"
    progress: float = 0.0
    peak_db: Optional[float] = None
    elapsed: float = 0.0
    rendered_duration: float = 0.0
    error: Optional[str] = None
    stem_paths: List[str] = field(default_factory=list)
    module_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class RenderSummary:
    completed: int = 0
    failed: int = 0
    cancelled: bool = False
    elapsed: float = 0.0
    total_audio_seconds: float = 0.0
    max_peak_db: Optional[float] = None
    jobs: List[RenderJob] = field(default_factory=list)

    @property
    def speedup(self) -> float:
        if self.elapsed <= 1e-6:
            return 0.0
        return self.total_audio_seconds / self.elapsed


# ============================================================================
# Pure Snapshot Manipulation Utilities (Safe to call on GUI or Worker threads)
# ============================================================================

def clamp_sampletype_for_format(fileformat: int, sampletype: int) -> int:
    """SD2 (4) and FLAC (5) only support 16-bit (0) or 24-bit (1) integer."""
    if fileformat in (4, 5) and sampletype > 1:
        return 1
    if fileformat == 7 and sampletype > 3:
        return 0
    return sampletype


def amp_to_db(peak_amp: float) -> float:
    if peak_amp <= 1e-9:
        return -90.0
    return 20.0 * math.log10(peak_amp)


def _read_wav_float64(path: str) -> Optional[np.ndarray]:
    """Fast pure-numpy RIFF WAVE reader returning `(nchnls, frames)` float64, or None if non-standard."""
    try:
        with open(path, "rb") as f:
            riff = f.read(12)
            if len(riff) < 12 or riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
                return None
            audio_fmt = None
            nchnls = 0
            bits = 0
            data_bytes = None
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                cid, csize = hdr[:4], struct.unpack("<I", hdr[4:8])[0]
                if cid == b"fmt ":
                    fmt_buf = f.read(csize)
                    audio_fmt, nchnls, _sr, _br, _ba, bits = struct.unpack("<HHIIHH", fmt_buf[:16])
                    if audio_fmt == 0xFFFE and len(fmt_buf) >= 40:
                        audio_fmt = struct.unpack("<H", fmt_buf[24:26])[0]
                elif cid == b"data":
                    data_bytes = f.read(csize)
                    break
                else:
                    f.seek(csize, os.SEEK_CUR)
                if csize & 1:
                    f.seek(1, os.SEEK_CUR)
            if data_bytes is None or nchnls < 1:
                return None
            if audio_fmt == 3 and bits == 32:
                arr = np.frombuffer(data_bytes, dtype="<f4").astype(np.float64)
            elif audio_fmt == 3 and bits == 64:
                arr = np.frombuffer(data_bytes, dtype="<f8").copy()
            elif audio_fmt == 1 and bits == 16:
                arr = np.frombuffer(data_bytes, dtype="<i2").astype(np.float64) / 32768.0
            elif audio_fmt == 1 and bits == 32:
                arr = np.frombuffer(data_bytes, dtype="<i4").astype(np.float64) / 2147483648.0
            elif audio_fmt == 1 and bits == 24:
                raw = np.frombuffer(data_bytes, dtype=np.uint8)
                usable = (len(raw) // 3) * 3
                b = raw[:usable].reshape(-1, 3)
                signed = (
                    b[:, 0].astype(np.int32)
                    | (b[:, 1].astype(np.int32) << 8)
                    | (b[:, 2].astype(np.int8).astype(np.int32) << 16)
                )
                arr = signed.astype(np.float64) / 8388608.0
            else:
                return None
            frames = len(arr) // nchnls
            return arr[: frames * nchnls].reshape(frames, nchnls).T.copy()
    except Exception:
        return None


def _write_wav_float32(arr: np.ndarray, path: str, sr: int):
    _save_multichannel_audio(arr, path, sr, 0, 3)


def _write_wav_pcm(arr: np.ndarray, path: str, sr: int, bits: int):
    _save_multichannel_audio(arr, path, sr, 0, {16:0, 24:1, 32:2}[bits])


def _save_multichannel_audio(arr: np.ndarray, path: str, sr: int, fileformat: int, sampletype: int):
    """Encode channel-major samples without whole-file interleaving or lists."""
    from .AudioFileIO import AudioWriter, BLOCK_SAMPLES

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    channels, frames = arr.shape
    block_frames = max(1, BLOCK_SAMPLES // channels)
    with AudioWriter(path, sr, channels, frames, fileformat, sampletype) as destination:
        for start in range(0, frames, block_frames):
            destination.write(arr[:, start:start + block_frames].T)


def normalize_audio_file(
    path: str,
    target_db: float = -0.1,
    sr: Optional[int] = None,
    fileformat: Optional[int] = None,
    sampletype: Optional[int] = None,
) -> float:
    """Normalize peak amplitude of an audio file to `target_db`.

    Returns the new peak dB level (or -90.0 if the file was pure silence).
    """
    from .AudioFileIO import AudioReader, AudioWriter, audio_peak

    if not os.path.isfile(path):
        return -90.0
    peak = audio_peak(path)
    if peak <= 1e-9:
        return -90.0
    gain = 10.0 ** (target_db / 20.0) / peak
    fd, temporary = tempfile.mkstemp(prefix=".cec_normalize_", suffix=".tmp", dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with AudioReader(path) as source:
            info = source.info
            kwargs = {"native_format":info.format} if fileformat is None and sampletype is None else {}
            with AudioWriter(temporary, sr or info.sample_rate, info.channels, info.frames,
                             fileformat if fileformat is not None else 0,
                             sampletype if sampletype is not None else 3, **kwargs) as destination:
                for block in source.blocks():
                    destination.write(block * gain)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return round(amp_to_db(10.0 ** (target_db / 20.0)), 2)

def list_module_presets(module_name: str, include_init: bool = True) -> List[str]:
    from .constants import PRESETS_PATH
    names = ["init"] if include_init else []
    preset_dir = os.path.join(PRESETS_PATH, module_name)
    if os.path.isdir(preset_dir):
        for entry in sorted(os.listdir(preset_dir)):
            if not entry.startswith(".") and os.path.isfile(os.path.join(preset_dir, entry)):
                names.append(entry)
    return names


def load_preset_dict(module_name: str, preset_name: str,
                     init_preset: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    from .constants import PRESETS_PATH
    if preset_name == "init":
        return copy.deepcopy(init_preset) if init_preset is not None else {}
    preset_file = os.path.join(PRESETS_PATH, module_name, preset_name)
    if not os.path.isfile(preset_file):
        return None
    with open(preset_file, "r", encoding="utf-8") as stream:
        result, _ = xmlrpclib.loads(stream.read())
        return copy.deepcopy(result[0])


def apply_preset_to_snapshot(
    snapshot: Dict[str, Any],
    preset_data: Dict[str, Any],
    preset_name: str = "init",
    module_id: Optional[str] = None,
    restore_globals: bool = True,
    remember_sound: bool = True,
) -> Dict[str, Any]:
    """Return a new session snapshot with `preset_data` applied to target module."""
    snap = copy.deepcopy(snapshot)
    if not snap.get("modules"):
        return snap
    target_id = module_id or snap.get("selected_id") or snap["modules"][0]["id"]
    mod_entry = next((m for m in snap["modules"] if m["id"] == target_id), snap["modules"][0])
    mod_entry["preset"] = preset_name
    settings = mod_entry.setdefault("settings", {})

    if preset_data:
        if "userSliders" in preset_data:
            cur_sliders = settings.setdefault("userSliders", {})
            for k, v in preset_data["userSliders"].items():
                cur_sliders[k] = copy.deepcopy(v)

        if "userTogglePopups" in preset_data:
            cur_togs = settings.setdefault("userTogglePopups", {})
            for k, v in preset_data["userTogglePopups"].items():
                cur_togs[k] = copy.deepcopy(v)

        if "userInputs" in preset_data and preset_data["userInputs"]:
            cur_inputs = settings.setdefault("userInputs", {})
            for name, info in preset_data["userInputs"].items():
                existing = cur_inputs.get(name, {})
                existing_path = existing.get("path", "")
                new_path = info.get("path", "")
                if not remember_sound:
                    if new_path and os.path.isfile(new_path):
                        cur_inputs[name] = {**existing, **copy.deepcopy(info)}
                else:
                    if not existing_path and new_path and os.path.isfile(new_path):
                        cur_inputs[name] = {**existing, **copy.deepcopy(info)}
                    else:
                        # Keep current sound file path/info, apply loop/gain/transp settings
                        merged = copy.deepcopy(existing)
                        for k, val in info.items():
                            if k == "path" or k.startswith(("sr", "dur", "nchnls", "off")):
                                continue
                            merged[k] = copy.deepcopy(val)
                        cur_inputs[name] = merged

        if "userGraph" in preset_data:
            cur_graph = settings.setdefault("userGraph", {})
            out_graph = snap["output"].setdefault("userGraph", {})
            for line_name, line_state in preset_data["userGraph"].items():
                if line_name.startswith("plugin_"):
                    if restore_globals:
                        out_graph[line_name] = copy.deepcopy(line_state)
                else:
                    cur_graph[line_name] = copy.deepcopy(line_state)

        if restore_globals and len(snap["modules"]) <= 1:
            out = snap["output"]
            if "totalTime" in preset_data:
                out["totalTime"] = float(preset_data["totalTime"])
            if "nchnls" in preset_data:
                out["nchnls"] = int(preset_data["nchnls"])
            if "gainSlider" in preset_data:
                out["gainSlider"] = float(preset_data["gainSlider"])
            if "plugins" in preset_data:
                out["plugins"] = {str(k): copy.deepcopy(v) for k, v in preset_data["plugins"].items()}
    elif preset_name == "init":
        # Reset userGraph curves if no explicit init_preset dictionary was supplied
        settings["userGraph"] = {}

    return snap


def apply_sound_to_snapshot(
    snapshot: Dict[str, Any],
    sound_path: str,
    input_name: Optional[str] = None,
    module_id: Optional[str] = None,
    use_sound_dur: bool = False,
) -> Dict[str, Any]:
    """Return a new session snapshot with `sound_path` loaded into the target input."""
    from pyo import sndinfo

    info = sndinfo(sound_path)
    if info is None:
        raise ValueError(f"Unsupported or unreadable audio file: {sound_path}")
    nsamps, dur, sr, chnls, _fmt, _bits = info

    snap = copy.deepcopy(snapshot)
    if not snap.get("modules"):
        return snap

    source_ids = snap.get("source_ids") or [snap["modules"][0]["id"]]
    target_mod_id = module_id or snap.get("source_id") or source_ids[0]
    mod_entry = next((m for m in snap["modules"] if m["id"] == target_mod_id), snap["modules"][0])
    user_inputs = mod_entry.setdefault("settings", {}).setdefault("userInputs", {})
    if not user_inputs:
        raise ValueError(f"Module '{os.path.basename(mod_entry['module_path'])}' has no sound inputs.")

    target_inputs = [input_name] if (input_name and input_name in user_inputs) else list(user_inputs.keys())[:1]
    for name in target_inputs:
        slot = user_inputs[name]
        prev_off = float(slot.get("off" + name, 0.0) or 0.0)
        slot["path"] = os.path.abspath(sound_path)
        slot["mode"] = 0
        slot["sr" + name] = sr
        slot["dur" + name] = dur
        slot["nchnls" + name] = chnls
        slot["off" + name] = min(max(0.0, prev_off), max(0.0, dur))
        if slot.get("type") == "csampler":
            loop_in = list(slot.get("loopIn", [0.0, 0, 0, False, None, 1, 0.0, dur, None, None]))
            loop_out = list(slot.get("loopOut", [dur, 0, 0, False, None, 1, 0.0, dur, None, None]))
            loop_in[0] = 0.0
            if len(loop_in) >= 8:
                loop_in[6], loop_in[7] = 0.0, dur
            loop_out[0] = dur
            if len(loop_out) >= 8:
                loop_out[6], loop_out[7] = 0.0, dur
            slot["loopIn"] = loop_in
            slot["loopOut"] = loop_out

    if use_sound_dur and dur > 0:
        snap["output"]["totalTime"] = float(dur)

    return snap


def _eval_normalized_curve(points: List[List[float]], u: float, curved: bool) -> float:
    if not points:
        return 0.0
    if u <= points[0][0]:
        return float(points[0][1])
    if u >= points[-1][0]:
        return float(points[-1][1])
    for i in range(len(points) - 1):
        x0, y0 = float(points[i][0]), float(points[i][1])
        x1, y1 = float(points[i + 1][0]), float(points[i + 1][1])
        if x0 <= u <= x1:
            dx = x1 - x0
            if dx <= 1e-12:
                return y1
            frac = (u - x0) / dx
            if curved:
                frac = (1.0 - math.cos(math.pi * frac)) * 0.5
            return y0 + (y1 - y0) * frac
    return float(points[-1][1])


def _slice_graph_entry(entry: Optional[Dict[str, Any]], u0: float, u1: float) -> Optional[Dict[str, Any]]:
    if not entry or "data" not in entry or not entry["data"]:
        return copy.deepcopy(entry)
    pts = sorted(([float(p[0]), float(p[1])] for p in entry["data"]), key=lambda p: p[0])
    curved = bool(entry.get("curved", False))
    span = max(1e-9, u1 - u0)

    if curved:
        # Sample curved segments densely so mid-segment cosine derivatives are preserved exactly.
        num_samples = 128
        sampled = []
        for i in range(num_samples + 1):
            frac = i / num_samples
            u = u0 + frac * span
            sampled.append([frac, _eval_normalized_curve(pts, u, True)])
        return {"data": sampled, "curved": False}

    y_start = _eval_normalized_curve(pts, u0, False)
    y_end = _eval_normalized_curve(pts, u1, False)
    sliced = [[0.0, y_start]]
    for x, y in pts:
        if u0 + 1e-9 < x < u1 - 1e-9:
            sliced.append([(x - u0) / span, y])
    sliced.append([1.0, y_end])
    return {"data": sliced, "curved": False}


def slice_snapshot_time_window(
    snapshot: Dict[str, Any],
    win_start: float,
    win_end: float,
    full_duration: float,
) -> Dict[str, Any]:
    """Create a self-contained snapshot covering `[win_start, win_end]` of `[0, full_duration]`."""
    snap = copy.deepcopy(snapshot)
    win_dur = max(0.001, win_end - win_start)
    u0 = max(0.0, min(1.0, win_start / max(1e-6, full_duration)))
    u1 = max(u0 + 1e-6, min(1.0, win_end / max(1e-6, full_duration)))

    out = snap["output"]
    base_offset = float(out.get("startOffset", 0.0) or 0.0)
    out["startOffset"] = 0.0
    out["totalTime"] = win_dur

    if out.get("userGraph"):
        out["userGraph"] = {
            k: _slice_graph_entry(v, u0, u1)
            for k, v in out["userGraph"].items()
            if v is not None
        }

    abs_advance = base_offset + win_start
    for mod in snap.get("modules", []):
        settings = mod.get("settings", {})
        if settings.get("userGraph"):
            settings["userGraph"] = {
                k: _slice_graph_entry(v, u0, u1)
                for k, v in settings["userGraph"].items()
                if v is not None
            }
        # Advance non-looping file tables / samplers if needed
        for name, info in settings.get("userInputs", {}).items():
            if info.get("mode", 0) != 0:
                continue
            dur_file = float(info.get("dur" + name, 0.0) or 0.0)
            if info.get("type") == "csampler" and int(info.get("loopMode", 1)) == 0 and dur_file > 0:
                loop_in = list(info.get("loopIn", [0.0, 0, 0]))
                if not loop_in[1]:  # static start point, non-looping
                    loop_in[0] = min(dur_file, float(loop_in[0]) + abs_advance)
                    info["loopIn"] = loop_in

    return snap


def has_active_master_plugins(snapshot: Dict[str, Any]) -> bool:
    plugins = snapshot.get("output", {}).get("plugins") or {}
    for entry in plugins.values():
        if not entry or entry[0] == "None":
            continue
        params = entry[1] if len(entry) > 1 else [0, 0, 0, 0]
        if len(params) >= 4 and int(params[3]) != 0:
            return True
    return False


def extract_disjoint_output_branches(snapshot: Dict[str, Any]) -> Optional[List[Tuple[str, Dict[str, Any], bool]]]:
    """If the session has >= 2 pairwise-disjoint branches feeding Output, return isolated snapshots.

    Returns a list of `(branch_label, branch_snapshot, is_muted)` tuples, or None if not decomposable.
    """
    modules = snapshot.get("modules") or []
    out_conns = list(snapshot.get("output_connections") or [])
    if len(modules) < 2 or len(out_conns) < 2:
        return None

    connections = [tuple(edge) for edge in (snapshot.get("connections") or [])]
    source_ids = set(snapshot.get("source_ids") or [])
    muted_ids = set(snapshot.get("muted_ids") or [])
    mod_by_id = {m["id"]: m for m in modules}
    order_index = {m["id"]: idx for idx, m in enumerate(modules)}

    # Reachable from sources
    reachable = set(source_ids)
    changed = True
    while changed:
        changed = False
        for a, b in connections:
            if a in reachable and b not in reachable:
                reachable.add(b)
                changed = True

    audible_outputs = [oid for oid in out_conns if oid in reachable and oid in mod_by_id]
    if len(audible_outputs) < 2:
        return None

    branch_sets: List[Tuple[str, set]] = []
    for oid in audible_outputs:
        anc = {oid}
        stack = [oid]
        while stack:
            cur = stack.pop()
            for a, b in connections:
                if b == cur and a in reachable and a not in anc:
                    anc.add(a)
                    stack.append(a)
        if not (anc & source_ids):
            continue
        branch_sets.append((oid, anc))

    if len(branch_sets) < 2:
        return None

    # Check pairwise disjointness of ancestor node sets
    seen_nodes: set = set()
    for _oid, anc in branch_sets:
        if seen_nodes & anc:
            return None
        seen_nodes |= anc

    branches: List[Tuple[str, Dict[str, Any], bool]] = []
    for idx, (oid, anc) in enumerate(branch_sets):
        ordered_ids = sorted(anc, key=lambda i: order_index[i])
        b_mods = [copy.deepcopy(mod_by_id[i]) for i in ordered_ids]
        b_sources = [i for i in snapshot.get("source_ids", []) if i in anc]
        b_conns = [[a, b] for a, b in connections if a in anc and b in anc]
        # Note: in multi-output mode (audio.py line 1894), muting the output node mutes the branch to 0.
        branch_muted = oid in muted_ids
        b_muted = [i for i in snapshot.get("muted_ids", []) if i in anc and i != oid]

        b_snap = copy.deepcopy(snapshot)
        b_snap["modules"] = b_mods
        b_snap["source_ids"] = b_sources
        b_snap["source_id"] = b_sources[0]
        b_snap["selected_id"] = oid
        b_snap["connections"] = b_conns
        b_snap["output_connections"] = [oid]
        b_snap["muted_ids"] = b_muted
        b_snap["positions"] = {k: v for k, v in (snapshot.get("positions") or {}).items() if k in anc}
        # Strip master plugins & gain/fade on intermediate stem; applied once on mixed master
        b_snap["output"]["plugins"] = {}
        b_snap["output"]["userGraph"] = {}
        b_snap["output"]["gainSlider"] = 0.0

        mod_name = os.path.splitext(os.path.basename(mod_by_id[oid]["module_path"]))[0]
        branches.append((f"branch_{idx + 1}_{mod_name}", b_snap, branch_muted))

    return branches


# ============================================================================
# Headless Worker Subprocess Implementation (pyo offline DSP without wx GUI)
# ============================================================================

class _MockGraphLine:
    def __init__(self, name: str, label: str, yrange: Tuple[float, float],
                 log: bool, size: int, total_time: float,
                 init_points: List[Tuple[float, float]],
                 slider: Any = None, suffix: str = "", curved: bool = False):
        self.name = name
        self.label = label
        self.yrange = (float(yrange[0]), float(yrange[1]))
        self.log = bool(log)
        self.size = int(size)
        self.slider = slider
        self.suffix = suffix
        self.curved = bool(curved)
        self._total_time = float(total_time)
        self.data = [[float(x), float(y)] for x, y in init_points]

    def apply_state(self, state: Optional[Dict[str, Any]], total_time: float):
        self._total_time = float(total_time)
        if not state or "data" not in state:
            return
        y0, y1 = self.yrange
        pts = []
        if self.log and y0 > 0 and y1 > 0:
            ly0, ly1 = math.log10(y0), math.log10(y1)
            for p in state["data"]:
                x = float(p[0]) * total_time
                y = math.pow(10.0, float(p[1]) * (ly1 - ly0) + ly0)
                pts.append([x, y])
        else:
            span = y1 - y0
            for p in state["data"]:
                x = float(p[0]) * total_time
                y = float(p[1]) * span + y0
                pts.append([x, y])
        if pts:
            pts[0][0] = 0.0
            pts[-1][0] = total_time
            self.data = pts
        self.curved = bool(state.get("curved", False))

    def getData(self):
        return [list(p) for p in self.data]

    def getCurved(self):
        return self.curved

    def getName(self):
        return self.name

    def getLabel(self):
        return self.label

    def getYrange(self):
        return self.yrange

    def getLog(self):
        return self.log


class _MockPlotter:
    def __init__(self, lines: List[_MockGraphLine]):
        self._lines = lines

    def getData(self):
        return self._lines


class _MockCursorPanel:
    def setTime(self, t):
        pass


class _MockGrapher:
    def __init__(self, lines: List[_MockGraphLine]):
        self.plotter = _MockPlotter(lines)
        self.cursorPanel = _MockCursorPanel()

    def getPlotter(self):
        return self.plotter

    def setTotalTime(self, total_time: float):
        pass


class _MockSlider:
    def __init__(self, name: str, mini: float, maxi: float, init: Any,
                 log: bool, play: int = 0, widget_type: str = "slider",
                 cname: Optional[str] = None):
        self.name = name
        self.cname = cname or name
        self.mini = float(mini)
        self.maxi = float(maxi)
        self.value = copy.deepcopy(init)
        self.log = bool(log)
        self.play = int(bool(play))
        self.widget_type = widget_type
        self.openSndCtrl = None
        self.OSCOut = None

    def getName(self):
        return self.name

    def getCName(self):
        return self.cname

    def getValue(self):
        return copy.deepcopy(self.value)

    def setValue(self, val):
        self.value = copy.deepcopy(val)

    def setOneValue(self, val, which):
        if isinstance(self.value, list) and 0 <= which < len(self.value):
            self.value[which] = val

    def getMinValue(self):
        return self.mini

    def getMaxValue(self):
        return self.maxi

    def getLog(self):
        return self.log

    def getPlay(self):
        return self.play

    def getRec(self):
        return 0

    def getWithMidi(self):
        return False

    def getMidiCtl(self):
        return None

    def getMidiChannel(self):
        return 1

    def getWithOSC(self):
        return False

    def getOpenSndCtrl(self):
        return ()

    def getPath(self):
        return ""


class _MockTogglePopup:
    def __init__(self, typ: str, name: str, value: Any, values: Optional[List[str]] = None):
        self.type = typ
        self.name = name
        self.values = list(values) if values else []
        self.value = value

    def getName(self):
        return self.name

    def getValue(self):
        if self.type == "popup":
            idx = int(self.value)
            if self.values:
                idx = max(0, min(len(self.values) - 1, idx))
            return idx
        return copy.deepcopy(self.value)

    def getLabel(self):
        if self.type == "popup" and self.values:
            return self.values[self.getValue()]
        return str(self.value)

    def getFullValue(self):
        return self.getValue(), self.getLabel()


class _MockSamplerFrame:
    def __init__(self, sliders: List[_MockSlider]):
        self.loopInSlider = sliders[0]
        self.loopOutSlider = sliders[1]
        self.loopXSlider = sliders[2]
        self.gainSlider = sliders[3]
        self.transpSlider = sliders[4]
        self.sliderlist = sliders


class _MockInputWidget:
    def __init__(self, name: str, kind: str, info: Dict[str, Any]):
        self.name = name
        self.kind = kind  # 'cfilein' | 'csampler'
        self.mode = int(info.get("mode", 0) or 0)
        # Live mic modes (1, 2, 3) when not connected to upstream are coerced to silence table if offline
        self.offset = float(info.get("off" + name, 0.0) or 0.0)
        dur = float(info.get("dur" + name, 1.0) or 1.0)
        self.sampler_info = {
            "loopMode": int(info.get("loopMode", 1)),
            "startFromLoop": int(info.get("startFromLoop", 0)),
            "xfadeshape": int(info.get("xfadeshape", 0)),
            "loopIn": self._clean_sampler_param(info.get("loopIn"), 0.0, 0.0, dur, True),
            "loopOut": self._clean_sampler_param(info.get("loopOut"), dur, 0.0, dur, True),
            "loopX": self._clean_sampler_param(info.get("loopX"), 1.0, 0.0, 50.0, False),
            "gain": self._clean_sampler_param(info.get("gain"), 0.0, -48.0, 18.0, False),
            "transp": self._clean_sampler_param(info.get("transp"), 0.0, -48.0, 48.0, False),
        }
        self._sliders = [
            _MockSlider(name, 0.0, max(dur, 0.001), self.sampler_info["loopIn"][0], False,
                        self.sampler_info["loopIn"][1], cname=name + "start"),
            _MockSlider(name, 0.0, max(dur, 0.001), self.sampler_info["loopOut"][0], False,
                        self.sampler_info["loopOut"][1], cname=name + "end"),
            _MockSlider(name, 0.0, 50.0, self.sampler_info["loopX"][0], False,
                        self.sampler_info["loopX"][1], cname=name + "xfade"),
            _MockSlider(name, -48.0, 18.0, self.sampler_info["gain"][0], False,
                        self.sampler_info["gain"][1], cname=name + "gain"),
            _MockSlider(name, -48.0, 48.0, self.sampler_info["transp"][0], False,
                        self.sampler_info["transp"][1], cname=name + "trans"),
        ]
        self._frame = _MockSamplerFrame(self._sliders)

    @staticmethod
    def _clean_sampler_param(raw: Any, default_val: float, mini: float, maxi: float, has_range: bool) -> List[Any]:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            val, play = default_val, 0
        else:
            val, play = float(raw[0]), int(bool(raw[1]))
        # Disable rec, midi, and OSC in headless offline workers
        if has_range:
            return [val, play, 0, False, None, 1, mini, maxi, None, None]
        return [val, play, 0, False, None, 1, None, None]

    def getName(self):
        return self.name

    def getMode(self):
        return self.mode

    def getOffset(self):
        return self.offset

    def getSamplerInfo(self):
        return self.sampler_info

    def getSamplerSliders(self):
        return self._sliders

    def getSamplerFrame(self):
        return self._frame


class _MockModuleInputs:
    def __init__(self, cfilein_list: List[_MockInputWidget]):
        self.cfileinList = cfilein_list

    def getCfileinList(self):
        return self.cfileinList

    def getCfileinFromName(self, name: str):
        for item in self.cfileinList:
            if item.name == name:
                return item
        return None


class _MockPlugin:
    def __init__(self, name: str, order: int, params: List[Any], states: List[Any]):
        self.name = name
        self.order = order
        specs = PLUGIN_SPECS[name]
        self.params = [
            float(params[0]) if len(params) > 0 else specs[0][3],
            float(params[1]) if len(params) > 1 else specs[1][3],
            float(params[2]) if len(params) > 2 else specs[2][3],
            int(params[3]) if len(params) > 3 else 1,
        ]
        self.knobs: List[_MockSlider] = []
        for idx in range(3):
            tmpl, mini, maxi, init, log = specs[idx]
            st = states[idx] if idx < len(states) and isinstance(states[idx], (list, tuple)) else [self.params[idx], 0, None, 1]
            # In Plugins.py, play state == 2 means Play automation (1 means Rec)
            play = 1 if (len(st) > 1 and st[1] == 2) else 0
            val = float(st[0]) if len(st) > 0 else init
            self.params[idx] = val
            self.knobs.append(_MockSlider(tmpl % order, mini, maxi, val, log, play, widget_type="plugin_knob"))

    def getName(self):
        return self.name

    def getParams(self):
        return list(self.params)

    def getKnobs(self):
        return self.knobs


class _WorkerProgressReporter:
    """Receives pyo offline Server time & RMS callbacks and emits throttled JSON events."""
    def __init__(self, job_id: str, total_time: float, nchnls: int, emit_fn: Callable[[Dict[str, Any]], None]):
        self.job_id = job_id
        self.total_time = max(0.001, float(total_time))
        self.nchnls = int(nchnls)
        self.emit_fn = emit_fn
        self.last_emit = 0.0
        self.current_time = 0.0
        self.last_rms: List[float] = [0.0] * self.nchnls
        self.max_peak_amp = 0.0

    def setTime(self, *args):
        if len(args) >= 4:
            self.current_time = args[1] * 60.0 + args[2] + args[3] * 0.001
            now = time.monotonic()
            if now - self.last_emit >= 0.04:
                self.last_emit = now
                frac = min(1.0, max(0.0, self.current_time / self.total_time))
                self.emit_fn({
                    "type": "progress",
                    "job_id": self.job_id,
                    "time": round(self.current_time, 4),
                    "fraction": round(frac, 4),
                    "rms": self.last_rms[:self.nchnls],
                    "peak_db": round(amp_to_db(self.max_peak_amp), 2),
                })

    def setRms(self, *args):
        if not args:
            return
        vals = [max(0.0, float(a)) if not math.isnan(a) else 0.0 for a in args[:self.nchnls]]
        if vals:
            self.last_rms = vals
            local_max = max(vals)
            if local_max > self.max_peak_amp:
                self.max_peak_amp = local_max


def _check_func_points(func: List[Any], total_time: float) -> List[Tuple[float, float]]:
    pts = [(float(p[0]) * total_time, float(p[1])) for p in func]
    if pts:
        pts[0] = (0.0, pts[0][1])
        pts[-1] = (total_time, pts[-1][1])
    return pts


def _convert_gen_list(val: Any) -> List[Any]:
    def _parse_num(x):
        try:
            f = float(x)
            return int(f) if f.is_integer() else f
        except Exception:
            return float(x)

    if isinstance(val, (list, tuple)):
        return [_parse_num(x) for x in val]
    if isinstance(val, str):
        parts = val.split(", ") if ", " in val else val.split(" ")
        return [_parse_num(eval(p)) for p in parts if p.strip()]
    return [1]


class _HeadlessRenderWorker:
    """Persistent headless pyo offline server inside a worker subprocess."""

    def __init__(self, emit_fn: Callable[[Dict[str, Any]], None]):
        self.emit_fn = emit_fn
        import Resources.CeciliaLib as CeciliaLib
        import Resources.audio as audio_mod
        from pyo import Server

        self.CeciliaLib = CeciliaLib
        self.audio_mod = audio_mod

        # Silence GUI dialogs / deferred wx callbacks inside headless worker
        CeciliaLib.callAfter = lambda *a, **kw: None
        self._last_error: Optional[str] = None

        def _capture_err(title, msg):
            self._last_error = f"{title}: {msg}"

        CeciliaLib.showErrorDialog = _capture_err
        CeciliaLib.resetControls = lambda: None
        CeciliaLib.setVar("useMidi", 0)
        CeciliaLib.setVar("automaticMidiBinding", 0)
        CeciliaLib.setVar("showSpectrum", 0)
        CeciliaLib.setVar("interface", None)

        # Create lightweight AudioServer shell backed by an offline pyo Server
        srv_shell = audio_mod.AudioServer.__new__(audio_mod.AudioServer)
        srv_shell.amp = 1.0
        srv_shell.server = Server(sr=44100, nchnls=2, buffersize=512, duplex=0, audio="offline")
        srv_shell.server.verbosity = 0
        srv_shell.ampCallable = None
        srv_shell.timeOpened = False
        srv_shell.recording = False
        srv_shell.withTimer = False
        srv_shell.withSpectrum = False
        srv_shell.runtimeModules = []
        srv_shell.output = None
        srv_shell.pluginObjs = [None] * audio_mod.NUM_OF_PLUGINS
        srv_shell.out = None
        srv_shell.spectrum = None
        srv_shell.moduleMuteSignals = {}
        srv_shell.pluginDict = {
            "Reverb": audio_mod.CeciliaReverbPlugin,
            "WGVerb": audio_mod.CeciliaWGReverbPlugin,
            "Filter": audio_mod.CeciliaFilterPlugin,
            "Para EQ": audio_mod.CeciliaEQPlugin,
            "Chorus": audio_mod.CeciliaChorusPlugin,
            "3 Bands EQ": audio_mod.CeciliaEQ3BPlugin,
            "Compress": audio_mod.CeciliaCompressPlugin,
            "Gate": audio_mod.CeciliaGatePlugin,
            "Disto": audio_mod.CeciliaDistoPlugin,
            "AmpMod": audio_mod.CeciliaAmpModPlugin,
            "Phaser": audio_mod.CeciliaPhaserPlugin,
            "Delay": audio_mod.CeciliaDelayPlugin,
            "Flange": audio_mod.CeciliaFlangePlugin,
            "Harmonizer": audio_mod.CeciliaHarmonizerPlugin,
            "Resonators": audio_mod.CeciliaResonatorsPlugin,
            "DeadReson": audio_mod.CeciliaDeadResonPlugin,
            "ChaosMod": audio_mod.CeciliaChaosModPlugin,
        }
        CeciliaLib.setVar("audioServer", srv_shell)
        self.srv_shell = srv_shell

    def _populate_module_state(self, instance, mod_entry: Dict[str, Any],
                               total_time: float, is_first: bool,
                               output_cfg: Dict[str, Any]):
        from .constants import POLY_CHORDS

        settings = mod_entry.get("settings", {})
        user_inputs_cfg = copy.deepcopy(settings.get("userInputs", {}))
        user_sliders_cfg = settings.get("userSliders", {})
        user_togs_cfg = settings.get("userTogglePopups", {})
        user_graph_cfg = settings.get("userGraph", {})

        cfilein_list: List[_MockInputWidget] = []
        user_samplers: List[_MockInputWidget] = []
        sampler_sliders: List[_MockSlider] = []
        user_sliders: List[_MockSlider] = []
        user_togs: List[_MockTogglePopup] = []
        graph_lines: List[_MockGraphLine] = []

        # 1. Inputs (cfilein / csampler)
        for w in instance.interface:
            wtype = w.get("type")
            if wtype in ("cfilein", "csampler"):
                name = w["name"]
                info = user_inputs_cfg.setdefault(name, {"type": wtype, "mode": 0, "path": "", "off" + name: 0.0})
                info.setdefault("type", wtype)
                info.setdefault("off" + name, 0.0)
                mock_in = _MockInputWidget(name, wtype, info)
                cfilein_list.append(mock_in)
                if wtype == "csampler":
                    user_samplers.append(mock_in)
                    sampler_sliders.extend(mock_in.getSamplerSliders())

        # 2. Sliders / Ranges / Splitters
        for w in instance.interface:
            wtype = w.get("type")
            if wtype in ("cslider", "crange", "csplitter"):
                name = w["name"]
                mini, maxi = float(w["min"]), float(w["max"])
                init = copy.deepcopy(w["init"])
                up = bool(w.get("up", False))
                log = w.get("rel", "lin") == "log" and mini != 0 and maxi != 0
                func = w.get("func")
                if wtype == "cslider":
                    init_play = 1 if (func is not None and not up) else 0
                    st = user_sliders_cfg.get(name)
                    val = st[0] if st else init
                    play = int(bool(st[1])) if (st and len(st) > 1 and not up) else init_play
                    sl = _MockSlider(name, mini, maxi, val, log, play, widget_type="slider")
                    user_sliders.append(sl)
                    if not up:
                        pts = _check_func_points(func if func is not None else [(0, init), (1, init)], total_time)
                        line = _MockGraphLine(name, w.get("label", name), (mini, maxi), log, 8192, total_time, pts, slider=sl)
                        if name in user_graph_cfg:
                            line.apply_state(user_graph_cfg[name], total_time)
                        graph_lines.append(line)
                elif wtype == "crange":
                    init_play = 1 if (func and (func[0] is not None or func[1] is not None) and not up) else 0
                    st = user_sliders_cfg.get(name)
                    val = list(st[0]) if st else list(init)
                    play = int(bool(st[1])) if (st and len(st) > 1 and not up) else init_play
                    sl = _MockSlider(name, mini, maxi, val, log, play, widget_type="range")
                    user_sliders.append(sl)
                    if not up:
                        for j, end in enumerate(("min", "max")):
                            f_sub = func[j] if (func and j < len(func) and func[j] is not None) else [(0, init[j]), (1, init[j])]
                            pts = _check_func_points(f_sub, total_time)
                            lbl = f"{w.get('label', name)} {end}"
                            line = _MockGraphLine(name, lbl, (mini, maxi), log, 8192, total_time, pts, slider=sl, suffix=end)
                            gkey = name + end
                            if gkey in user_graph_cfg:
                                line.apply_state(user_graph_cfg[gkey], total_time)
                            elif name in user_graph_cfg and j == 0:
                                line.apply_state(user_graph_cfg[name], total_time)
                            graph_lines.append(line)
                elif wtype == "csplitter":
                    st = user_sliders_cfg.get(name)
                    val = list(st[0]) if st else list(init)
                    sl = _MockSlider(name, mini, maxi, val, log, 0, widget_type="splitter")
                    user_sliders.append(sl)

        # Include sampler sliders in grapher (not in userSliders, which BaseModule._setWidgetValues maps to self._sliders)
        for ssl in sampler_sliders:
            pts = _check_func_points([(0, ssl.getValue()), (1, ssl.getValue())], total_time)
            line = _MockGraphLine(
                ssl.getCName(), ssl.getCName(), (ssl.getMinValue(), ssl.getMaxValue()),
                False, 8192, total_time, pts, slider=ssl, suffix="sampler"
            )
            if ssl.getCName() in user_graph_cfg:
                line.apply_state(user_graph_cfg[ssl.getCName()], total_time)
            graph_lines.append(line)

        # 3. Standalone cgraph widgets
        for w in instance.interface:
            if w.get("type") == "cgraph":
                name = w["name"]
                mini, maxi = float(w["min"]), float(w["max"])
                log = w.get("rel", "lin") == "log" and mini != 0 and maxi != 0
                pts = _check_func_points(w.get("func", [(0, mini), (1, mini)]), total_time)
                line = _MockGraphLine(
                    name, w.get("label", name), (mini, maxi), log,
                    int(w.get("size", 8192)), total_time, pts, curved=bool(w.get("curved", False))
                )
                if name in user_graph_cfg:
                    line.apply_state(user_graph_cfg[name], total_time)
                graph_lines.append(line)

        # 4. Toggles, Popups, Buttons, Gens, Poly
        for w in instance.interface:
            wtype = w.get("type")
            name = w["name"]
            if wtype == "cpopup":
                values = list(w.get("value", [""]))
                init_lbl = w.get("init", values[0])
                init_idx = values.index(init_lbl) if init_lbl in values else 0
                val = int(user_togs_cfg.get(name, init_idx))
                user_togs.append(_MockTogglePopup("popup", name, val, values))
            elif wtype == "ctoggle":
                val = int(user_togs_cfg.get(name, w.get("init", 0)))
                user_togs.append(_MockTogglePopup("toggle", name, val))
            elif wtype == "cbutton":
                user_togs.append(_MockTogglePopup("button", name, 0))
            elif wtype == "cgen":
                raw_val = user_togs_cfg.get(name, w.get("init", [1]))
                user_togs.append(_MockTogglePopup("gen", name, _convert_gen_list(raw_val)))
            elif wtype == "cpoly":
                minv, maxv = int(w.get("min", 1)), int(w.get("max", 10))
                voices = [str(v) for v in range(minv, maxv + 1)]
                init_v = str(w.get("init", voices[0]))
                init_v_idx = voices.index(init_v) if init_v in voices else 0
                num_name = name + "num"
                user_togs.append(_MockTogglePopup("popup", num_name, int(user_togs_cfg.get(num_name, init_v_idx)), voices))
                chord_keys = sorted(POLY_CHORDS.keys())
                init_c_idx = chord_keys.index("00 - None") if "00 - None" in chord_keys else 0
                user_togs.append(_MockTogglePopup("popup", name, int(user_togs_cfg.get(name, init_c_idx)), chord_keys))

        # 5. Shared post-processing plugin lines on first module's grapher
        mock_plugins = [None] * self.audio_mod.NUM_OF_PLUGINS
        if is_first:
            plugins_cfg = output_cfg.get("plugins") or {}
            fx_graphs = output_cfg.get("userGraph") or {}
            for order in range(self.audio_mod.NUM_OF_PLUGINS):
                entry = plugins_cfg.get(str(order))
                if not entry or entry[0] == "None" or entry[0] not in PLUGIN_SPECS:
                    mock_plugins[order] = None
                    continue
                pl_name = entry[0]
                params = entry[1] if len(entry) > 1 else [0, 0, 0, 1]
                states = entry[2] if len(entry) > 2 else []
                mpl = _MockPlugin(pl_name, order, params, states)
                mock_plugins[order] = mpl
                for knob in mpl.getKnobs():
                    pts = _check_func_points([(0, knob.getValue()), (1, knob.getValue())], total_time)
                    kline = _MockGraphLine(
                        knob.getName(), knob.getName(),
                        (knob.getMinValue(), knob.getMaxValue()),
                        knob.getLog(), 8192, total_time, pts, slider=knob
                    )
                    if knob.getName() in fx_graphs and fx_graphs[knob.getName()] is not None:
                        kline.apply_state(fx_graphs[knob.getName()], total_time)
                    graph_lines.append(kline)
            self.CeciliaLib.setVar("plugins", mock_plugins)

        instance.inputs = _MockModuleInputs(cfilein_list)
        instance.state["userInputs"] = user_inputs_cfg
        instance.state["userSamplers"] = user_samplers
        instance.state["samplerSliders"] = sampler_sliders
        instance.state["userSliders"] = user_sliders
        instance.state["userTogglePopups"] = user_togs
        instance.state["grapher"] = _MockGrapher(graph_lines)

    def render_snapshot(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        from .constants import AUDIO_FILE_FORMATS
        from .Session import ChainSession, instance_context, mix_signals
        from pyo import Fader, Interp, Mix, Record, Server, Sig, SigTo, sndinfo

        t0 = time.perf_counter()
        job_id = spec["job_id"]
        snapshot = spec["snapshot"]
        output_path = spec["output_path"]
        sr = int(spec["sr"])
        buffersize = int(spec["buffersize"])
        file_type = spec["audio_file_type"]
        fileformat = AUDIO_FILE_FORMATS.get(file_type, 0)
        sampletype = clamp_sampletype_for_format(fileformat, int(spec["samp_size"]))
        global_fade = float(spec.get("global_fade", 0.005))
        force_mix_voices = bool(spec.get("force_mix_voices", False))
        seed_offset = int(spec.get("seed_offset", 1))
        # Replay jobs use the same Python and numpy randomness as the reference.
        # Workers are isolated processes, so this cannot perturb the GUI RNG.
        random.seed(seed_offset)
        np.random.seed(seed_offset)
        raw_output = bool(spec.get("raw_output", False))

        out_cfg = snapshot["output"]
        total_time = float(spec.get("duration_override") or out_cfg["totalTime"])
        render_time = float(spec.get("render_duration", total_time))
        nchnls = int(spec.get("nchnls_override") or out_cfg["nchnls"])
        gain_db = float(out_cfg.get("gainSlider", 0.0))
        start_offset = float(out_cfg.get("startOffset", 0.0) or 0.0)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        CeciliaLib = self.CeciliaLib
        CeciliaLib.setVar("sr", sr)
        CeciliaLib.setVar("nchnls", nchnls)
        CeciliaLib.setVar("bufferSize", str(buffersize))
        CeciliaLib.setVar("totalTime", total_time)
        CeciliaLib.setVar("globalFade", global_fade)
        CeciliaLib.setVar("startOffset", start_offset)
        CeciliaLib.setVar("audioFileType", file_type)
        CeciliaLib.setVar("sampSize", sampletype)
        CeciliaLib.setVar("outputFile", output_path)
        CeciliaLib.setVar("toDac", False)
        CeciliaLib.setVar("plugins", [None] * self.audio_mod.NUM_OF_PLUGINS)

        srv = self.srv_shell.server
        if srv.getIsBooted():
            srv.shutdown()
        # A reinitialized server retains its previous amplitude-ramp state.
        # Fresh DSP state is required for identical startup samples on replay.
        srv = Server(sr=sr, nchnls=nchnls, buffersize=buffersize, duplex=0, audio="offline")
        self.srv_shell.server = srv
        srv.verbosity = 0
        srv.boot()
        srv.globalseed = seed_offset

        master_output = bool(spec.get("master_output", True))
        public_output_path = output_path
        public_module_outputs = dict(spec.get("module_outputs", {}))
        module_outputs = dict(public_module_outputs)
        encode_public = fileformat != 0 or sampletype != 3
        scratch_dir = spec.get("scratch_dir") or os.path.dirname(os.path.abspath(output_path))
        if encode_public:
            output_path = os.path.join(scratch_dir, f"cec_float_{uuid.uuid4().hex}.wav")
            module_outputs = {mid: os.path.join(scratch_dir, f"cec_float_{uuid.uuid4().hex}.wav")
                              for mid in public_module_outputs}
        temp_dummy_out = None
        record_dest = output_path
        if not master_output or raw_output:
            temp_dummy_out = os.path.join(spec.get("scratch_dir", tempfile.gettempdir()), f"cec_dummy_{uuid.uuid4().hex[:8]}.wav")
            record_dest = temp_dummy_out

        reporter = _WorkerProgressReporter(job_id, render_time, nchnls, self.emit_fn)
        srv._server.setTimeCallable(reporter)
        srv._server.setAmpCallable(reporter)
        srv.recordOptions(dur=render_time, filename=record_dest, fileformat=0, sampletype=3)
        self.srv_shell.setAmp(gain_db)

        # Build headless ChainSession
        chain = ChainSession()
        compiled_instances = []
        for idx, mod_entry in enumerate(snapshot["modules"]):
            mod_path = mod_entry["module_path"]
            inst = self.srv_shell.compileModule(mod_path, bool(mod_entry.get("builtin", False)), mod_entry["id"])
            self._populate_module_state(inst, mod_entry, total_time, is_first=(idx == 0), output_cfg=out_cfg)
            compiled_instances.append(inst)

        chain.modules = compiled_instances
        chain.restore_routing(snapshot)
        CeciliaLib.session = chain

        self._last_error = None
        module_recorders = []
        try:
            instances = chain.active_modules()
            if not instances:
                raise RuntimeError("No active module connected to Output.")
            signals = {}
            output_signals = {}
            self.srv_shell.moduleMuteSignals = {}
            self.srv_shell.runtimeModules = []
            for instance in instances:
                upstream = [signals[a] for a, b in chain.connections if b == instance.id and a in signals]
                instance.upstream = mix_signals(upstream) if upstream else None
                with instance_context(instance):
                    current_mod = instance.module_class.__new__(instance.module_class)
                    instance.state["currentModule"] = current_mod
                    self.srv_shell.runtimeModules.append(current_mod)
                    # Seed 0 means clock-based randomness in live mode. Offline
                    # replay must instead use the job seed; explicit seeds stay intact.
                    current_mod.setGlobalSeed = lambda value, _seed=seed_offset: setattr(
                        srv, "globalseed", int(value) or _seed)
                    instance.module_class.__init__(current_mod)
                    current_mod._setWidgetValues()
                    mod_out = current_mod.out
                    mod_out_len = len(mod_out) if hasattr(mod_out, "__len__") else 1
                    processed = (
                        mod_out
                        if (len(instances) == 1 and not force_mix_voices and mod_out_len == nchnls)
                        else Mix(mod_out, voices=nchnls)
                    )
                    bypass = instance.upstream if upstream else Sig([0] * nchnls)
                    muted = int(instance.id in chain.muted_ids)
                    fade = SigTo(value=muted, time=0.02, init=muted)
                    self.srv_shell.moduleMuteSignals[instance.id] = fade
                    signals[instance.id] = Interp(processed, bypass, fade)
                    output_bypass = bypass if len(chain.output_connections) == 1 else processed * 0
                    output_signals[instance.id] = Interp(processed, output_bypass, fade)

                    if instance.id in module_outputs:
                        mod_out_path = module_outputs[instance.id]
                        os.makedirs(os.path.dirname(os.path.abspath(mod_out_path)), exist_ok=True)
                        mod_sig = processed
                        sig_len = len(mod_sig) if hasattr(mod_sig, "__len__") else 1
                        if sig_len != nchnls:
                            mod_sig = Mix(mod_sig, voices=nchnls)
                        if global_fade > 0.0:
                            if not hasattr(self.srv_shell, "globalamp"):
                                self.srv_shell.globalamp = Fader(fadein=global_fade, fadeout=global_fade, dur=total_time).play()
                            mod_sig = mod_sig * self.srv_shell.globalamp
                        mod_rec = Record(
                            mod_sig,
                            filename=mod_out_path,
                            chnls=nchnls,
                            fileformat=0,
                            sampletype=3,
                            buffering=1,
                        )
                        module_recorders.append((instance.id, mod_out_path, mod_rec))

            output_ids = spec.get("output_ids", chain.output_connections)
            self.srv_shell.out = Sig(
                mix_signals([output_signals[i] for i in output_ids if i in output_signals])
            )
            with instance_context(chain.modules[0]):
                self.srv_shell._loadOutputPlugins()

            if global_fade > 0.0:
                if not hasattr(self.srv_shell, "globalamp"):
                    self.srv_shell.globalamp = Fader(fadein=global_fade, fadeout=global_fade, dur=total_time).play()
                if len(chain.modules) > 1:
                    self.srv_shell.output.mul = self.srv_shell.globalamp
                else:
                    self.srv_shell.out.mul = self.srv_shell.globalamp

            if raw_output:
                # Branch intermediates must precede the server's startup gain
                # ramp. That ramp, master gain and fades run once in the mixer.
                raw_rec = Record(self.srv_shell.output, filename=output_path,
                                 chnls=nchnls, fileformat=0,
                                 sampletype=3, buffering=1)
                module_recorders.append(("__branch__", output_path, raw_rec))

            if start_offset > 0.0:
                srv.startoffset = start_offset

            srv.start()
        finally:
            if srv.getIsStarted():
                srv.stop()
            for _mid, _mpath, rec in module_recorders:
                try:
                    rec.stop()
                except Exception:
                    pass
            module_recorders.clear()
            signals = None
            output_signals = None
            current_mod = None
            processed = None
            bypass = None
            fade = None
            output_bypass = None
            self.srv_shell.cleanup_module()
            gc.collect()
            if srv.getIsBooted():
                srv.shutdown()

        # pyo Record runs during server warmup; the server's own file writer
        # starts afterward. Derive the actual buffer-rounded prefix from the
        # two recordings instead of rounding a requested offset ourselves.
        recorded_info = sndinfo(record_dest)
        recorded_frames = recorded_info[0] if recorded_info else 0
        warmup_frames = 0
        tap_paths = list(module_outputs.values()) + ([output_path] if raw_output else [])
        for path in tap_paths:
            tap_info = sndinfo(path)
            if tap_info:
                warmup_frames = max(warmup_frames, tap_info[0] - recorded_frames)

        if temp_dummy_out and os.path.exists(temp_dummy_out):
            try:
                os.remove(temp_dummy_out)
            except OSError:
                pass

        # pyo records complete DSP buffers, including a padded final buffer.
        # Trim every destination before reporting metadata or stitching chunks.
        expected_frames = max(1, int(round(render_time * sr)))
        if master_output:
            # Raw branch intermediates retain warmup so master effects, fades
            # and the gain ramp can replay the same history as the serial graph.
            self._trim_audio_file(output_path, sr, nchnls,
                                  expected_frames + (warmup_frames if raw_output else 0),
                                  fileformat, sampletype, force_reencode=encode_public,
                                  output_path=public_output_path)
        for mid, path in module_outputs.items():
            self._trim_audio_file(path, sr, nchnls, expected_frames,
                                  fileformat, sampletype, discard_frames=warmup_frames,
                                  force_reencode=encode_public, output_path=public_module_outputs[mid])
        if raw_output and spec.get("raw_export_path"):
            public_format = AUDIO_FILE_FORMATS.get(spec["export_audio_file_type"], 0)
            public_sampletype = clamp_sampletype_for_format(public_format, spec["export_samp_size"])
            self._trim_audio_file(output_path, sr, nchnls, expected_frames, public_format,
                                  public_sampletype, discard_frames=warmup_frames,
                                  force_reencode=True, output_path=spec["raw_export_path"], keep_source=True)

        output_path = public_output_path
        module_outputs = public_module_outputs
        module_results = {}
        for mid, mpath in module_outputs.items():
            if os.path.isfile(mpath):
                minfo = sndinfo(mpath)
                mframes = minfo[0] if minfo else 0
                mdur = minfo[1] if minfo else total_time
                from .AudioFileIO import audio_peak
                m_peak = round(amp_to_db(audio_peak(mpath)), 2)
                module_results[mid] = {
                    "path": mpath,
                    "frames": mframes,
                    "duration": mdur,
                    "peak_db": m_peak,
                }

        info = sndinfo(output_path) if master_output else None
        frames = info[0] if info else 0
        actual_dur = info[1] if info else total_time
        master_peak = round(amp_to_db(reporter.max_peak_amp), 2) if master_output else (
            max((res["peak_db"] for res in module_results.values()), default=-90.0)
        )
        if master_output and sampletype in (0, 1, 2):
            master_peak = min(master_peak, 0.0)
        elapsed = time.perf_counter() - t0
        return {
            "type": "done",
            "job_id": job_id,
            "output_path": output_path if master_output else (
                next(iter(module_outputs.values()), "")
            ),
            "frames": frames,
            "duration": actual_dur,
            "peak_db": master_peak,
            "elapsed": round(elapsed, 4),
            "master_output": master_output,
            "module_results": module_results,
            "warmup_frames": warmup_frames,
        }

    def _trim_audio_file(self, path, sr, nchnls, frames, fileformat, sampletype,
                         discard_frames=0, force_reencode=False, output_path=None, keep_source=False):
        from .AudioFileIO import AudioReader, AudioWriter, encoding_temp_prefix

        destination = output_path or path
        with AudioReader(path) as source:
            info = source.info
            if info.frames < frames + discard_frames:
                raise RuntimeError(f"Incomplete render: {path} (expected {frames + discard_frames} frames)")
            if info.frames == frames and not discard_frames and not force_reencode and destination == path:
                return
            fd, temporary = tempfile.mkstemp(prefix=encoding_temp_prefix(destination), suffix=".tmp",
                                             dir=os.path.dirname(os.path.abspath(destination)))
            os.close(fd)
            try:
                with AudioWriter(temporary, sr, info.channels, frames, fileformat, sampletype) as target:
                    for block in source.blocks(discard_frames, frames):
                        target.write(block)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)
        if destination != path and not keep_source:
            os.remove(path)

    def _read_audio_channels(self, path: str, sr: int, nchnls: int) -> np.ndarray:
        """Read an audio file into `(avail_chnls, frames)` float64 without dangling C memoryviews."""
        fast = _read_wav_float64(path)
        if fast is not None:
            return fast
        from pyo import SndTable

        srv = self.srv_shell.server
        if srv.getIsBooted():
            srv.shutdown()
        srv.reinit(sr=sr, nchnls=nchnls, buffersize=512, duplex=0, audio="offline")
        srv.boot()
        try:
            tbl = SndTable(path)
            avail_ch = len(tbl)
            ch_arrays = [np.array(tbl[ch].getTable(), dtype=np.float64) for ch in range(avail_ch)]
            del tbl
            gc.collect()
            return np.vstack(ch_arrays)
        finally:
            if srv.getIsBooted():
                srv.shutdown()

    def stitch_time_chunks(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Stitch overlap-crossfaded time chunks into final output file with exact sample alignment."""
        from .constants import AUDIO_FILE_FORMATS

        t0 = time.perf_counter()
        job_id = spec["job_id"]
        chunks = spec["chunks"]
        output_path = spec["output_path"]
        sr = int(spec["sr"])
        nchnls = int(spec["nchnls"])
        total_frames = int(spec["total_frames"])
        xfade_frames = int(spec["xfade_frames"])
        xfade_shape = spec.get("crossfade_shape", "cosine")
        global_fade = float(spec.get("global_fade", 0.005))
        file_type = spec["audio_file_type"]
        fileformat = AUDIO_FILE_FORMATS.get(file_type, 0)
        sampletype = clamp_sampletype_for_format(fileformat, int(spec["samp_size"]))

        from contextlib import ExitStack
        from .AudioFileIO import AudioReader, AudioWriter, BLOCK_SAMPLES

        peak_amp = 0.0
        fade_samps = min(total_frames // 2, int(round(global_fade * sr)))
        with ExitStack() as stack:
            readers = [stack.enter_context(AudioReader(c["path"])) for c in chunks]
            writer = stack.enter_context(AudioWriter(output_path, sr, nchnls, total_frames,
                                                     fileformat, sampletype))
            for start in range(0, total_frames, max(1, BLOCK_SAMPLES // nchnls)):
                stop = min(total_frames, start + max(1, BLOCK_SAMPLES // nchnls))
                accum = np.zeros((stop-start, nchnls), dtype=np.float64)
                for idx, (cinfo, reader) in enumerate(zip(chunks, readers)):
                    a, b = int(cinfo["a_frame"]), int(cinfo["b_frame"])
                    lo, hi = max(start, a), min(stop, b)
                    if lo >= hi:
                        continue
                    offset = int(cinfo["discard_frames"]) + lo-a
                    available = max(0, min(hi-lo, reader.info.frames-offset))
                    if not available:
                        continue
                    reader.seek(offset)
                    raw = reader.read(available)
                    seg = raw[:, np.minimum(np.arange(nchnls), reader.info.channels-1)]
                    positions = np.arange(lo-a, lo-a+available)
                    if xfade_frames > 0 and b-a >= xfade_frames:
                        for enabled, incoming in ((idx > 0, True), (idx < len(chunks)-1, False)):
                            if not enabled:
                                continue
                            indices = positions if incoming else positions-(b-a-xfade_frames)
                            mask = (indices >= 0) & (indices < xfade_frames)
                            u = indices[mask] / max(1, xfade_frames-1)
                            if xfade_shape == "equal_power":
                                out, ins = np.cos(0.5*np.pi*u), np.sin(0.5*np.pi*u)
                                weights = (ins if incoming else out)/(out+ins)
                            else:
                                weights = 0.5*(1.0 + (-1 if incoming else 1)*np.cos(np.pi*u))
                            seg[mask] *= weights[:, None]
                    accum[lo-start:lo-start+available] += seg
                if fade_samps > 1 and (start < fade_samps or stop > total_frames - fade_samps):
                    positions = np.arange(start, stop)
                    weights = np.minimum(1.0, np.minimum(positions, total_frames-1-positions)/(fade_samps-1))
                    accum *= weights[:, None]
                if accum.size:
                    peak_amp = max(peak_amp, float(np.max(np.abs(accum))))
                writer.write(accum)

        elapsed = time.perf_counter() - t0
        return {
            "type": "done",
            "job_id": job_id,
            "output_path": output_path,
            "frames": total_frames,
            "duration": total_frames / float(sr),
            "peak_db": round(amp_to_db(peak_amp), 2),
            "elapsed": round(elapsed, 4),
        }

    def mix_and_master_branches(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Mix rendered parallel chain branches (0.707 multi-cable rule) and run optional master plugins."""
        from .constants import AUDIO_FILE_FORMATS
        from .Session import ChainSession, instance_context
        from pyo import Fader, Server, Sig, SfPlayer, sndinfo

        t0 = time.perf_counter()
        job_id = spec["job_id"]
        branch_files: List[Optional[str]] = spec["branch_files"]
        total_cables = int(spec["total_cables"])
        snapshot = spec["snapshot"]
        output_path = spec["output_path"]
        sr = int(spec["sr"])
        nchnls = int(spec["nchnls"])
        buffersize = int(spec["buffersize"])
        total_time = float(spec["total_time"])
        global_fade = float(spec.get("global_fade", 0.005))
        file_type = spec["audio_file_type"]
        fileformat = AUDIO_FILE_FORMATS.get(file_type, 0)
        sampletype = clamp_sampletype_for_format(fileformat, int(spec["samp_size"]))
        gain_db = float(snapshot["output"].get("gainSlider", 0.0))
        cable_gain = 0.707 if total_cables > 1 else 1.0

        total_frames = max(1, int(round(total_time * sr)))
        warmup_frames = int(spec.get("warmup_frames", 0))
        srv = self.srv_shell.server

        temp_mixed_wav = None
        try:
            from contextlib import ExitStack
            from .AudioFileIO import AudioReader, AudioWriter, BLOCK_SAMPLES
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            fd, temp_mixed_wav = tempfile.mkstemp(prefix="cec_branch_mix_", suffix=".wav", dir=spec.get("scratch_dir"))
            os.close(fd)
            length = total_frames + warmup_frames
            with ExitStack() as stack:
                readers = [stack.enter_context(AudioReader(path)) for path in branch_files
                           if path and os.path.isfile(path)]
                writer = stack.enter_context(AudioWriter(temp_mixed_wav, sr, nchnls, length))
                for start in range(0, length, max(1, BLOCK_SAMPLES // nchnls)):
                    count = min(length-start, max(1, BLOCK_SAMPLES // nchnls))
                    mixed = np.zeros((count, nchnls), dtype=np.float64)
                    for reader in readers:
                        available = min(count, max(0, reader.info.frames-start))
                        if available:
                            raw = reader.read(available)
                            mixed[:available] += raw[:, np.minimum(np.arange(nchnls), reader.info.channels-1)] * cable_gain
                    writer.write(mixed)

            CeciliaLib = self.CeciliaLib
            CeciliaLib.setVar("sr", sr)
            CeciliaLib.setVar("nchnls", nchnls)
            CeciliaLib.setVar("bufferSize", str(buffersize))
            CeciliaLib.setVar("totalTime", total_time)
            CeciliaLib.setVar("globalFade", global_fade)
            CeciliaLib.setVar("startOffset", 0.0)
            CeciliaLib.setVar("outputFile", output_path)
            CeciliaLib.setVar("toDac", False)

            if srv.getIsBooted():
                srv.shutdown()
            srv = Server(sr=sr, nchnls=nchnls, buffersize=buffersize, duplex=0, audio="offline")
            self.srv_shell.server = srv
            srv.verbosity = 0
            srv.boot()
            reporter = _WorkerProgressReporter(job_id, total_time, nchnls, self.emit_fn)
            srv._server.setTimeCallable(reporter)
            srv._server.setAmpCallable(reporter)
            rendered_path = os.path.join(spec.get("scratch_dir") or os.path.dirname(os.path.abspath(output_path)),
                                         f"cec_master_{uuid.uuid4().hex}.wav")
            srv.recordOptions(dur=total_time, filename=rendered_path, fileformat=0, sampletype=3)
            self.srv_shell.setAmp(gain_db)

            first_mod = snapshot["modules"][0]
            inst = self.srv_shell.compileModule(first_mod["module_path"], bool(first_mod.get("builtin", False)), first_mod["id"])
            self._populate_module_state(inst, first_mod, total_time, is_first=True, output_cfg=snapshot["output"])
            chain = ChainSession()
            chain.modules = [inst]
            CeciliaLib.session = chain

            stem_reader = SfPlayer(temp_mixed_wav, speed=1, loop=False, interp=1).play()
            self.srv_shell.out = Sig(stem_reader)
            with instance_context(inst):
                self.srv_shell._loadOutputPlugins()
            if global_fade > 0.0:
                self.srv_shell.globalamp = Fader(fadein=global_fade, fadeout=global_fade, dur=total_time).play()
                self.srv_shell.output.mul = self.srv_shell.globalamp
            if warmup_frames:
                srv.startoffset = warmup_frames / float(sr)
            srv.start()
            if srv.getIsStarted():
                srv.stop()
            stem_reader = None
            self.srv_shell.cleanup_module()
            gc.collect()
            if srv.getIsBooted():
                srv.shutdown()
            peak_amp = reporter.max_peak_amp
        finally:
            if srv.getIsBooted():
                gc.collect()
                srv.shutdown()
            if temp_mixed_wav and os.path.exists(temp_mixed_wav):
                try:
                    os.remove(temp_mixed_wav)
                except OSError:
                    pass

        self._trim_audio_file(rendered_path, sr, nchnls, total_frames, fileformat, sampletype,
                              force_reencode=(fileformat != 0 or sampletype != 3), output_path=output_path)
        info = sndinfo(output_path)
        frames = info[0] if info else total_frames
        elapsed = time.perf_counter() - t0
        return {
            "type": "done",
            "job_id": job_id,
            "output_path": output_path,
            "frames": frames,
            "duration": frames / float(sr),
            "peak_db": min(0.0, round(amp_to_db(peak_amp), 2)) if sampletype in (0, 1, 2)
                       else round(amp_to_db(peak_amp), 2),
            "elapsed": round(elapsed, 4),
        }


def worker_main(argv: Optional[List[str]] = None) -> int:
    """Entrypoint for persistent headless offline worker subprocess."""
    def emit(payload: Dict[str, Any]):
        sys.stderr.write(EVENT_PREFIX + json.dumps(payload, allow_nan=False) + "\n")
        sys.stderr.flush()

    try:
        worker = _HeadlessRenderWorker(emit)
    except Exception as exc:
        emit({"type": "fatal", "error": str(exc), "traceback": traceback.format_exc()})
        return 1

    emit({"type": "ready"})

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception as exc:
            emit({"type": "error", "job_id": "", "error": f"Invalid JSON command: {exc}"})
            continue

        cmd = msg.get("cmd")
        if cmd == "quit":
            break
        job_id = msg.get("spec", {}).get("job_id", "")
        try:
            if cmd == "render":
                res = worker.render_snapshot(msg["spec"])
                emit(res)
            elif cmd == "stitch":
                res = worker.stitch_time_chunks(msg["spec"])
                emit(res)
            elif cmd == "mix_branches":
                res = worker.mix_and_master_branches(msg["spec"])
                emit(res)
            else:
                emit({"type": "error", "job_id": job_id, "error": f"Unknown worker cmd: {cmd}"})
        except Exception as exc:
            emit({
                "type": "error",
                "job_id": job_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })

    return 0


# ============================================================================
# Multithreaded Worker Subprocess Pool & OfflineRenderManager
# ============================================================================

class _SubprocessWorkerHandle:
    """Thread-safe wrapper around a persistent headless worker subprocess."""

    def __init__(self, worker_index: int):
        self.worker_index = worker_index
        self._proc: Optional[subprocess.Popen] = None
        self._events: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._lock = threading.Lock()
        self._shutdown_lock = threading.RLock()
        self._reader_threads = []
        self._closed = False
        self._start()

    def _build_cmd(self) -> Tuple[List[str], str, Dict[str, str]]:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["CECILIA_OFFLINE_WORKER"] = "1"
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = project_root + (os.pathsep + existing_pp if existing_pp else "")
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--offline-worker"]
        else:
            cmd = [sys.executable, "-m", "Resources.OfflineRender", "--worker"]
        return cmd, project_root, env

    def _start(self):
        cmd, cwd, env = self._build_cmd()
        self._proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._reader_threads = [
            threading.Thread(target=self._read_stdout, daemon=True),
            threading.Thread(target=self._read_stderr, daemon=True),
        ]
        for thread in self._reader_threads:
            thread.start()

        # Wait for ready signal
        msg = self._events.get(timeout=15.0)
        if msg.get("type") == "fatal":
            raise RuntimeError(f"Offline worker failed to initialize: {msg.get('error')}\n{msg.get('traceback', '')}")

    def _read_stdout(self):
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for _line in proc.stdout:
                pass
        except Exception:
            pass

    def _read_stderr(self):
        proc = self._proc
        if proc is None or proc.stderr is None:
            return
        stderr_tail: List[str] = []
        try:
            for line in proc.stderr:
                if line.startswith(EVENT_PREFIX):
                    payload_str = line[len(EVENT_PREFIX):].strip()
                    try:
                        self._events.put(json.loads(payload_str))
                    except Exception:
                        pass
                else:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("Pyo "):
                        stderr_tail.append(stripped)
                        if len(stderr_tail) > 25:
                            stderr_tail.pop(0)
        except Exception:
            pass
        finally:
            self._events.put({"type": "eof", "stderr": "\n".join(stderr_tail)})

    def execute(
        self,
        cmd: str,
        spec: Dict[str, Any],
        cancel_event: threading.Event,
        on_progress: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if self._closed or cancel_event.is_set():
                raise InterruptedError("Render cancelled.")
            if self._proc is None or self._proc.poll() is not None:
                self._events = queue.Queue()
                self._start()

            assert self._proc is not None and self._proc.stdin is not None
            payload = json.dumps({"cmd": cmd, "spec": spec}, allow_nan=False) + "\n"
            self._proc.stdin.write(payload)
            self._proc.stdin.flush()

            last_memory_check = 0.0
            while True:
                now = time.monotonic()
                memory_limit = getattr(self, "memory_limit_bytes", None)
                if memory_limit and now-last_memory_check >= 0.1:
                    from .RenderMemory import process_rss
                    shared_usage = getattr(self, 'shared_memory_usage', None)
                    resident = shared_usage() if shared_usage else process_rss(self._proc.pid)
                    last_memory_check = now
                    if resident is not None and resident > memory_limit:
                        # Keep this pool slot reusable after rejecting one large job.
                        with self._shutdown_lock:
                            proc = self._proc
                            if proc.poll() is None:
                                proc.terminate()
                                try:
                                    proc.wait(timeout=0.5)
                                except subprocess.TimeoutExpired:
                                    proc.kill()
                                    proc.wait()
                            self._close_pipes()
                        scope = "Offline workers exceeded the shared render memory budget " if shared_usage else "Offline worker exceeded its memory budget "
                        raise MemoryError(scope +
                                          f"({resident/1024**3:.1f} GiB resident; "
                                          f"limit {memory_limit/1024**3:.1f} GiB). "
                                          "Use fewer workers, reduce input length/channel count, "
                                          "or increase the render RAM budget if memory is available.")
                if cancel_event.is_set():
                    self.terminate()
                    raise InterruptedError("Render cancelled.")
                try:
                    ev = self._events.get(timeout=0.05)
                except queue.Empty:
                    continue

                etype = ev.get("type")
                if etype == "progress":
                    if on_progress is not None:
                        on_progress(self.worker_index, ev)
                elif etype == "done":
                    return ev
                elif etype == "error":
                    detail = ev.get("error", "Unknown render error")
                    tb = ev.get("traceback", "")
                    raise RuntimeError(f"{detail}\n{tb}".strip())
                elif etype == "eof":
                    if cancel_event.is_set():
                        raise InterruptedError("Render cancelled.")
                    extra = ev.get("stderr", "")
                    raise RuntimeError(f"Offline worker exited unexpectedly. {extra}".strip())

    def _close_pipes(self):
        proc = self._proc
        if proc is None:
            return
        for thread in self._reader_threads:
            thread.join(timeout=1.0)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()

    def terminate(self):
        with self._shutdown_lock:
            self._closed = True
            proc = self._proc
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                except ProcessLookupError:
                    proc.wait()
            self._close_pipes()

    def close(self):
        with self._shutdown_lock:
            self._closed = True
            proc = self._proc
            if proc is not None and proc.poll() is None:
                try:
                    if proc.stdin:
                        proc.stdin.write('{"cmd": "quit"}\n')
                        proc.stdin.flush()
                    proc.wait(timeout=1.0)
                except Exception:
                    self.terminate()
            self._close_pipes()


class _WorkerPool:
    """Pool of persistent `_SubprocessWorkerHandle` driven by a `ThreadPoolExecutor`."""

    def __init__(self, max_workers: int):
        self.max_workers = max(1, int(max_workers))
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="CeciliaOfflineWorker"
        )
        self._available: "queue.Queue[_SubprocessWorkerHandle]" = queue.Queue()
        self._all_handles: List[_SubprocessWorkerHandle] = []
        self._active_handles = set()
        self._handles_lock = threading.Lock()
        self._memory_lock = threading.Lock()
        self._next_idx = 0
        self._shutting_down = False

    def _shared_memory_usage(self, caller):
        """Count all live pool processes; choose one active victim if over budget.

        A worker may use idle peers' allowance. Selecting the largest active
        worker avoids several concurrent guard loops killing every worker for
        the same aggregate overage. Idle resident memory is included too.
        """
        from .RenderMemory import process_rss
        with self._memory_lock:
            with self._handles_lock:
                handles = list(self._all_handles)
                active = set(self._active_handles)
            residents = {}
            for handle in handles:
                proc = getattr(handle, '_proc', None)
                if proc is not None and proc.poll() is None:
                    resident = process_rss(proc.pid)
                    if resident is not None:
                        residents[handle] = resident
            total = sum(residents.values())
            if total <= self.memory_limit_bytes:
                return total
            candidates = [handle for handle in residents if handle in active]
            victim = max(candidates, key=residents.get, default=None)
            return total if caller is victim else 0

    def _acquire(self, cancel_event: threading.Event) -> _SubprocessWorkerHandle:
        if cancel_event.is_set() or self._shutting_down:
            raise InterruptedError("Render cancelled.")
        try:
            return self._available.get_nowait()
        except queue.Empty:
            pass

        with self._handles_lock:
            if len(self._all_handles) < self.max_workers:
                idx = self._next_idx
                self._next_idx += 1
            else:
                idx = None

        if idx is not None:
            handle = _SubprocessWorkerHandle(idx)
            with self._handles_lock:
                self._all_handles.append(handle)
                cancelled = self._shutting_down or cancel_event.is_set()
            if cancelled:
                handle.terminate()
                raise InterruptedError("Render cancelled.")
            return handle

        while not cancel_event.is_set() and not self._shutting_down:
            try:
                return self._available.get(timeout=0.05)
            except queue.Empty:
                continue
        raise InterruptedError("Render cancelled.")

    def _release(self, handle: _SubprocessWorkerHandle):
        if not self._shutting_down and not handle._closed:
            self._available.put(handle)

    def submit_task(
        self,
        cmd: str,
        spec: Dict[str, Any],
        cancel_event: threading.Event,
        on_progress: Optional[Callable[[int, Dict[str, Any]], None]] = None,
        on_worker_start: Optional[Callable[[int], None]] = None,
        on_worker_end: Optional[Callable[[int], None]] = None,
    ) -> concurrent.futures.Future:
        def _task():
            reservations = getattr(self, 'memory_reservations', None)
            amount = None
            handle = None
            try:
                if reservations is not None:
                    from .RenderMemory import estimate_snapshot_memory, MIB
                    estimate = (estimate_snapshot_memory(spec['snapshot'],
                                int(spec.get('nchnls_override') or spec['snapshot']['output']['nchnls']), spec.get('sr'))
                                if cmd == 'render' else 256*MIB)
                    amount = reservations.acquire(estimate, cancel_event)
                handle = self._acquire(cancel_event)
                with self._handles_lock:
                    self._active_handles.add(handle)
                if on_worker_start:
                    on_worker_start(handle.worker_index)
                handle.memory_limit_bytes = getattr(self, "memory_limit_bytes", None)
                if handle.memory_limit_bytes:
                    handle.shared_memory_usage = lambda: self._shared_memory_usage(handle)
                return handle.execute(cmd, spec, cancel_event, on_progress=on_progress)
            finally:
                if handle is not None:
                    with self._handles_lock:
                        self._active_handles.discard(handle)
                    if on_worker_end:
                        on_worker_end(handle.worker_index)
                    self._release(handle)
                if amount is not None:
                    reservations.release(amount)

        return self.executor.submit(_task)

    def cancel_all(self):
        self._shutting_down = True
        with self._handles_lock:
            handles = list(self._all_handles)
        for h in handles:
            h.terminate()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def shutdown(self):
        self._shutting_down = True
        with self._handles_lock:
            handles = list(self._all_handles)
        for h in handles:
            h.close()
        self.executor.shutdown(wait=True)


class OfflineRenderManager:
    """High-level multithreaded offline render coordinator.

    Supports:
      - Multi-job parallel batch/queue rendering across `settings.num_threads` workers
      - Single-render multithreaded acceleration:
          * Parallel disjoint chain branch rendering (+ optional per-branch stem export)
          * Overlap-crossfaded time-chunked rendering across `settings.num_threads` workers
      - Non-blocking background execution, live progress/ETA/VU callbacks, and instant cancel.
    """

    def __init__(
        self,
        settings: RenderSettings,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_job_update: Optional[Callable[[int, RenderJob], None]] = None,
        on_vu: Optional[Callable[[List[float], float], None]] = None,
        on_complete: Optional[Callable[[RenderSummary], None]] = None,
    ):
        self.settings = copy.deepcopy(settings)
        self.on_progress = on_progress
        self.on_job_update = on_job_update
        self.on_vu = on_vu
        self.on_complete = on_complete

        self.cancel_event = threading.Event()
        self._pool: Optional[_WorkerPool] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = False
        self._temp_dirs: List[str] = []
        self._active_outputs: set = set()
        self._initial_output_stats: Dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, jobs: List[RenderJob]):
        if self._running:
            raise RuntimeError("Offline render is already running.")
        self._running = True
        self.cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run_coordinator, args=(jobs,), daemon=True, name="CeciliaOfflineCoordinator"
        )
        self._thread.start()

    def run_blocking(self, jobs: List[RenderJob]) -> RenderSummary:
        done_q: "queue.Queue[RenderSummary]" = queue.Queue()
        prev_cb = self.on_complete

        def _capture(summary: RenderSummary):
            if prev_cb:
                prev_cb(summary)
            done_q.put(summary)

        self.on_complete = _capture
        self.start(jobs)
        return done_q.get()

    def cancel(self):
        self.cancel_event.set()
        pool = self._pool
        if pool is not None:
            pool.cancel_all()

    def _make_temp_dir(self) -> str:
        d = tempfile.mkdtemp(prefix="cecilia5_offline_")
        with self._lock:
            self._temp_dirs.append(d)
        return d

    @staticmethod
    def _output_signature(path):
        try:
            info = os.stat(path)
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        except OSError:
            return None

    def _track_output(self, path):
        """Called with the coordinator lock held before dispatch."""
        if path not in self._initial_output_stats:
            self._initial_output_stats[path] = self._output_signature(path)
        self._active_outputs.add(path)

    def _cleanup_temps(self, cancelled: bool):
        with self._lock:
            dirs = list(self._temp_dirs)
            self._temp_dirs.clear()
            incomplete = list(self._active_outputs) if cancelled else []
            initial = dict(self._initial_output_stats)
            self._initial_output_stats.clear()
            self._active_outputs.clear()
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
        for fpath in incomplete:
            if fpath:
                # SIGTERM cannot execute the encoder's finally block. Remove
                # only temporary encodes belonging to this incomplete output.
                from .AudioFileIO import encoding_temp_prefix
                from pathlib import Path
                parent = Path(os.path.dirname(os.path.abspath(fpath)))
                for temporary in parent.glob(encoding_temp_prefix(fpath) + "*.tmp"):
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
            if fpath and os.path.exists(fpath):
                if initial.get(fpath) is not None and self._output_signature(fpath) == initial[fpath]:
                    continue  # The worker never modified the previous destination.
                try:
                    os.remove(fpath)
                except OSError:
                    pass

    def _choose_single_strategy(self, job: RenderJob, num_jobs: int) -> str:
        """Select execution strategy for a job: 'single', 'branches', or 'chunks'."""
        threads = max(1, self.settings.num_threads)
        mode = self.settings.accel_mode

        if job.module_outputs:
            total_dur = float(job.duration_override or job.snapshot["output"]["totalTime"])
            if mode == "chunks" or (mode == "auto" and total_dur >= max(self.settings.chunk_min_dur, 4.0)):
                min_seg = max(1.0, 2.0 * self.settings.crossfade + 0.5)
                return "chunks" if total_dur >= min_seg * 2 else "single"
            return "single"

        if job.export_stems or self.settings.export_stems:
            if extract_disjoint_output_branches(job.snapshot) is not None:
                return "branches"

        if threads <= 1 or mode == "single":
            return "single"

        # When running a multi-job batch that already saturates threads, prefer exact single-pass per job
        # unless user explicitly requested 'branches' or 'chunks'.
        if mode == "auto" and num_jobs >= threads:
            return "single"

        total_dur = float(job.duration_override or job.snapshot["output"]["totalTime"])
        can_branch = extract_disjoint_output_branches(job.snapshot) is not None

        if mode == "branches":
            return "branches" if can_branch else "single"
        if mode == "chunks":
            min_seg = max(1.0, 2.0 * self.settings.crossfade + 0.5)
            return "chunks" if total_dur >= min_seg * 2 else "single"

        # mode == 'auto'
        if can_branch:
            return "branches"
        if total_dur >= max(self.settings.chunk_min_dur, 4.0):
            return "chunks"
        return "single"

    def _run_coordinator(self, jobs: List[RenderJob]):
        t_start = time.perf_counter()
        from .RenderMemory import (render_memory_budget, estimate_snapshot_memory,
                                   worker_limit, batch_worker_limit, process_rss, MemoryReservations)
        rss_monitoring_available = process_rss(os.getpid()) is not None
        memory_budget = render_memory_budget()
        memory_estimates = [estimate_snapshot_memory(job.snapshot, int(self.settings.nchnls or
                            job.snapshot["output"]["nchnls"]), self.settings.sr) for job in jobs]
        independent = all(self._choose_single_strategy(job, len(jobs)) == "single" for job in jobs)
        limit_function = batch_worker_limit if independent and len(jobs) > 1 else worker_limit
        num_threads = limit_function(memory_estimates, max(1, int(self.settings.num_threads)), memory_budget)
        usable_threads = min(max(1, int(self.settings.num_threads)), max(1, len(jobs))) if independent else max(1, int(self.settings.num_threads))
        memory_worker_limit = num_threads if num_threads < usable_threads else None
        if independent:
            # Unused pool slots must not reserve RAM away from the one active job.
            num_threads = min(num_threads, max(1, len(jobs)))
        pool = _WorkerPool(num_threads)
        pool.memory_limit_bytes = memory_budget
        pool.memory_reservations = MemoryReservations(memory_budget)
        self._pool = pool

        total_jobs = len(jobs)
        worker_states: Dict[int, Dict[str, Any]] = {
            i: {"active": False, "label": "Idle", "fraction": 0.0}
            for i in range(num_threads)
        }
        job_progress = [0.0] * total_jobs
        max_peak_db: Optional[float] = None
        state_lock = threading.Lock()
        coordinator_active = True

        def emit_overall():
            if not self.on_progress:
                return
            with state_lock:
                if not coordinator_active:
                    return
                overall_frac = sum(job_progress) / max(1, total_jobs)
                done_cnt = sum(1 for j in jobs if j.status == "Done")
                elapsed = time.perf_counter() - t_start
                eta = (elapsed / overall_frac * (1.0 - overall_frac)) if overall_frac > 0.02 else None
                workers_copy = [dict(worker_states[i]) for i in range(num_threads)]
                peak_copy = max_peak_db
            self.on_progress({
                "overall_fraction": min(1.0, max(0.0, overall_frac)),
                "completed_jobs": done_cnt,
                "total_jobs": total_jobs,
                "elapsed": elapsed,
                "eta": eta,
                "peak_db": peak_copy,
                "workers": workers_copy,
                "memory_worker_limit": memory_worker_limit,
                "memory_budget_bytes": memory_budget,
                "memory_estimate_bytes": max(memory_estimates, default=0),
            })

        def set_worker_active(widx: int, label: str):
            with state_lock:
                worker_states[widx] = {"active": True, "label": label, "fraction": 0.0}
            emit_overall()

        def set_worker_idle(widx: int):
            with state_lock:
                worker_states[widx] = {"active": False, "label": "Idle", "fraction": 0.0}
            emit_overall()

        def notify_job(idx: int):
            if self.on_job_update:
                self.on_job_update(idx, jobs[idx])
            emit_overall()

        def handle_subprogress(job_idx: int, sub_idx: int, sub_count: int, sub_label: str,
                               worker_idx: int, ev: Dict[str, Any]):
            nonlocal max_peak_db
            sub_frac = float(ev.get("fraction", 0.0))
            rms = ev.get("rms", [])
            pdb = ev.get("peak_db")
            with state_lock:
                # Approximate blended job progress
                prev = job_progress[job_idx]
                est = min(0.98, max(prev, (sub_idx + sub_frac) / max(1, sub_count) if sub_count == 1 else prev))
                if sub_count == 1:
                    job_progress[job_idx] = est
                    jobs[job_idx].progress = est
                worker_states[worker_idx] = {
                    "active": True,
                    "label": sub_label,
                    "fraction": sub_frac,
                }
                if pdb is not None and pdb > -89.9:
                    if max_peak_db is None or pdb > max_peak_db:
                        max_peak_db = pdb
            if self.on_vu and rms:
                self.on_vu(rms, pdb if pdb is not None else -90.0)
            emit_overall()

        def execute_job(job_idx: int, job: RenderJob):
            nonlocal max_peak_db
            if self.cancel_event.is_set():
                job.status = "Cancelled"
                notify_job(job_idx)
                return

            j_t0 = time.perf_counter()
            strategy = self._choose_single_strategy(job, total_jobs)
            if (num_threads == 1 and self.settings.accel_mode == "auto"
                    and not (job.export_stems or self.settings.export_stems)):
                strategy = "single"
            total_dur = float(job.duration_override or job.snapshot["output"]["totalTime"])
            nchnls = int(self.settings.nchnls or job.snapshot["output"]["nchnls"])
            sr = int(self.settings.sr)
            buffersize = int(self.settings.buffersize)

            if memory_estimates[job_idx] > memory_budget and not rss_monitoring_available:
                job.status = "Error"
                job.error = ("Offline input tables exceed the render memory budget "
                             f"(estimated {memory_estimates[job_idx]/1024**3:.1f} GiB; "
                             f"budget {memory_budget/1024**3:.1f} GiB). "
                             "Resident-memory monitoring is unavailable on this system, "
                             "so an oversized estimate cannot be tried safely. "
                             "Reduce input length or channel count before rendering.")
                job.elapsed = time.perf_counter() - j_t0
                notify_job(job_idx)
                return

            with self._lock:
                if job.master_output:
                    self._track_output(job.output_path)
                for sp in job.module_outputs.values():
                    self._track_output(sp)

            job.status = f"Rendering ({strategy})" if strategy != "single" else "Rendering"
            notify_job(job_idx)

            try:
                if strategy == "single":
                    spec = {
                        "job_id": job.job_id,
                        "snapshot": job.snapshot,
                        "output_path": job.output_path,
                        "duration_override": total_dur,
                        "nchnls_override": nchnls,
                        "sr": sr,
                        "buffersize": buffersize,
                        "audio_file_type": self.settings.audio_file_type,
                        "samp_size": self.settings.samp_size,
                        "global_fade": self.settings.global_fade,
                        "master_output": job.master_output,
                        "scratch_dir": self._make_temp_dir(),
                        "module_outputs": job.module_outputs,
                    }
                    fut = pool.submit_task(
                        "render",
                        spec,
                        self.cancel_event,
                        on_progress=lambda widx, ev: handle_subprogress(job_idx, 0, 1, job.title, widx, ev),
                        on_worker_start=lambda widx: set_worker_active(widx, job.title),
                        on_worker_end=set_worker_idle,
                    )
                    res = fut.result()
                    job.module_results = res.get("module_results", {})
                    job.stem_paths = [info["path"] for info in job.module_results.values()]

                elif strategy == "branches":
                    branches = extract_disjoint_output_branches(job.snapshot)
                    assert branches is not None
                    tmp_dir = self._make_temp_dir()
                    want_stems = job.export_stems or self.settings.export_stems
                    base_no_ext, out_ext = os.path.splitext(job.output_path)

                    sub_fracs = [0.0] * len(branches)

                    def on_branch_prog(b_i: int, b_lbl: str, widx: int, ev: Dict[str, Any]):
                        nonlocal max_peak_db
                        sf = float(ev.get("fraction", 0.0))
                        pdb = ev.get("peak_db")
                        with state_lock:
                            sub_fracs[b_i] = sf
                            blended = 0.90 * (sum(sub_fracs) / len(sub_fracs))
                            job_progress[job_idx] = blended
                            jobs[job_idx].progress = blended
                            worker_states[widx] = {"active": True, "label": f"{job.title} [{b_lbl}]", "fraction": sf}
                            if pdb is not None and pdb > -89.9:
                                if max_peak_db is None or pdb > max_peak_db:
                                    max_peak_db = pdb
                        if self.on_vu and ev.get("rms"):
                            self.on_vu(ev["rms"], pdb if pdb is not None else -90.0)
                        emit_overall()

                    branch_futures = []
                    branch_files: List[Optional[str]] = [None] * len(branches)
                    for b_i, (b_lbl, b_snap, b_muted) in enumerate(branches):
                        if b_muted:
                            sub_fracs[b_i] = 1.0
                            continue
                        export_path = None
                        if want_stems:
                            export_path = f"{base_no_ext}_{b_lbl}{out_ext}"
                            job.stem_paths.append(export_path)
                            with self._lock:
                                self._track_output(export_path)
                        stem_path = os.path.join(tmp_dir, f"{b_lbl}.wav")
                        branch_files[b_i] = stem_path
                        context_snapshot = copy.deepcopy(job.snapshot)
                        context_snapshot["output"]["plugins"] = {}
                        context_snapshot["output"]["userGraph"] = {}
                        context_snapshot["output"]["gainSlider"] = 0.0
                        bspec = {
                            "job_id": f"{job.job_id}_b{b_i}",
                            "snapshot": context_snapshot,
                            "output_ids": b_snap["output_connections"],
                            "raw_output": True,
                            "scratch_dir": tmp_dir,
                            "output_path": stem_path,
                            "duration_override": total_dur,
                            "nchnls_override": nchnls,
                            "sr": sr,
                            "buffersize": buffersize,
                            "audio_file_type": "wav",
                            "samp_size": 3,
                            "raw_export_path": export_path,
                            "export_audio_file_type": self.settings.audio_file_type,
                            "export_samp_size": self.settings.samp_size,
                            "global_fade": 0.0,
                            "force_mix_voices": True,
                        }
                        fut = pool.submit_task(
                            "render",
                            bspec,
                            self.cancel_event,
                            on_progress=lambda widx, ev, _bi=b_i, _bl=b_lbl: on_branch_prog(_bi, _bl, widx, ev),
                            on_worker_start=lambda widx, _bl=b_lbl: set_worker_active(widx, f"{job.title} [{_bl}]"),
                            on_worker_end=set_worker_idle,
                        )
                        branch_futures.append(fut)

                    branch_results = [fut.result() for fut in branch_futures]
                    warmup_frames = max((res.get("warmup_frames", 0) for res in branch_results), default=0)

                    job.status = "Mixing branches"
                    notify_job(job_idx)
                    mix_spec = {
                        "job_id": job.job_id,
                        "branch_files": branch_files,
                        "warmup_frames": warmup_frames,
                        "scratch_dir": tmp_dir,
                        "total_cables": len(branches),
                        "snapshot": job.snapshot,
                        "output_path": job.output_path,
                        "sr": sr,
                        "nchnls": nchnls,
                        "buffersize": buffersize,
                        "total_time": total_dur,
                        "global_fade": self.settings.global_fade,
                        "audio_file_type": self.settings.audio_file_type,
                        "samp_size": self.settings.samp_size,
                    }
                    res = pool.submit_task(
                        "mix_branches",
                        mix_spec,
                        self.cancel_event,
                        on_worker_start=lambda widx: set_worker_active(widx, f"{job.title} [mixing]"),
                        on_worker_end=set_worker_idle,
                    ).result()

                else:  # strategy == "chunks"
                    xfade_s = max(0.01, float(self.settings.crossfade))
                    max_k = max(2, min(num_threads, int(total_dur / max(1.5, 2.0 * xfade_s + 0.5))))
                    total_frames = max(1, int(round(total_dur * sr)))
                    half_xfade = int(round(0.5 * xfade_s * sr))
                    xfade_frames = 2 * half_xfade

                    tmp_dir = self._make_temp_dir()
                    chunk_meta = []
                    sub_fracs = [0.0] * max_k

                    def on_chunk_prog(c_i: int, widx: int, ev: Dict[str, Any]):
                        nonlocal max_peak_db
                        sf = float(ev.get("fraction", 0.0))
                        pdb = ev.get("peak_db")
                        with state_lock:
                            sub_fracs[c_i] = sf
                            blended = 0.92 * (sum(sub_fracs) / max_k)
                            job_progress[job_idx] = blended
                            jobs[job_idx].progress = blended
                            worker_states[widx] = {
                                "active": True,
                                "label": f"{job.title} [chunk {c_i + 1}/{max_k}]",
                                "fraction": sf,
                            }
                            if pdb is not None and pdb > -89.9:
                                if max_peak_db is None or pdb > max_peak_db:
                                    max_peak_db = pdb
                        if self.on_vu and ev.get("rms"):
                            self.on_vu(ev["rms"], pdb if pdb is not None else -90.0)
                        emit_overall()

                    chunk_futures = []
                    for k in range(max_k):
                        s_k = int(round(k * total_frames / max_k))
                        e_k = total_frames if k == max_k - 1 else int(round((k + 1) * total_frames / max_k))
                        a_k = 0 if k == 0 else max(0, s_k - half_xfade)
                        b_k = total_frames if k == max_k - 1 else min(total_frames, e_k + half_xfade)
                        # Replay the original timeline to reconstruct arbitrary DSP state.
                        # A bounded preroll cannot preserve feedback, convolution tails,
                        # oscillator phase, automation or stochastic module history.
                        p_k = a_k
                        c_snap = copy.deepcopy(job.snapshot)
                        c_path = os.path.join(tmp_dir, f"chunk_{k:03d}.wav")
                        chunk_meta.append({
                            "path": c_path,
                            "discard_frames": p_k,
                            "a_frame": a_k,
                            "b_frame": b_k,
                        })
                        cspec = {
                            "job_id": f"{job.job_id}_c{k}",
                            "snapshot": c_snap,
                            "output_path": c_path,
                            "duration_override": total_dur,
                            "render_duration": b_k / float(sr),
                            "nchnls_override": nchnls,
                            "sr": sr,
                            "buffersize": buffersize,
                            "audio_file_type": "wav",
                            "samp_size": 3,  # 32-bit float intermediate
                            "global_fade": self.settings.global_fade,
                            "seed_offset": 1,
                            "scratch_dir": tmp_dir,
                            "master_output": job.master_output,
                            "module_outputs": {
                                mid: os.path.join(tmp_dir, f"chunk_{k:03d}_{mid}.wav")
                                for mid in job.module_outputs
                            },
                        }
                        fut = pool.submit_task(
                            "render",
                            cspec,
                            self.cancel_event,
                            on_progress=lambda widx, ev, _ci=k: on_chunk_prog(_ci, widx, ev),
                            on_worker_start=lambda widx, _ci=k: set_worker_active(widx, f"{job.title} [chunk {_ci + 1}/{max_k}]"),
                            on_worker_end=set_worker_idle,
                        )
                        chunk_futures.append(fut)

                    for fut in chunk_futures:
                        fut.result()

                    job.status = "Stitching chunks"
                    notify_job(job_idx)
                    if job.master_output:
                        stitch_spec = {
                            "job_id": job.job_id,
                            "chunks": chunk_meta,
                            "output_path": job.output_path,
                            "sr": sr,
                            "nchnls": nchnls,
                            "total_frames": total_frames,
                            "xfade_frames": xfade_frames,
                            "crossfade_shape": self.settings.crossfade_shape,
                            "global_fade": 0.0,
                            "audio_file_type": self.settings.audio_file_type,
                            "samp_size": self.settings.samp_size,
                        }
                        res = pool.submit_task(
                            "stitch",
                            stitch_spec,
                            self.cancel_event,
                            on_worker_start=lambda widx: set_worker_active(widx, f"{job.title} [stitching master]"),
                            on_worker_end=set_worker_idle,
                        ).result()
                    else:
                        res = {
                            "peak_db": -90.0,
                            "duration": total_dur,
                            "frames": total_frames,
                        }

                    for mid, final_stem_path in job.module_outputs.items():
                        mod_stitch_spec = {
                            "job_id": f"{job.job_id}_{mid}",
                            "chunks": [
                                {
                                    "path": os.path.join(tmp_dir, f"chunk_{k:03d}_{mid}.wav"),
                                    "discard_frames": cm["discard_frames"],
                                    "a_frame": cm["a_frame"],
                                    "b_frame": cm["b_frame"],
                                }
                                for k, cm in enumerate(chunk_meta)
                            ],
                            "output_path": final_stem_path,
                            "sr": sr,
                            "nchnls": nchnls,
                            "total_frames": total_frames,
                            "xfade_frames": xfade_frames,
                            "crossfade_shape": self.settings.crossfade_shape,
                            "global_fade": 0.0,
                            "audio_file_type": self.settings.audio_file_type,
                            "samp_size": self.settings.samp_size,
                        }
                        m_res = pool.submit_task(
                            "stitch",
                            mod_stitch_spec,
                            self.cancel_event,
                            on_worker_start=lambda widx, _mid=mid: set_worker_active(widx, f"{job.title} [stitching {_mid}]"),
                            on_worker_end=set_worker_idle,
                        ).result()
                        job.module_results[mid] = {
                            "path": final_stem_path,
                            "frames": m_res.get("frames", total_frames),
                            "duration": m_res.get("duration", total_dur),
                            "peak_db": m_res.get("peak_db", -90.0),
                        }
                    job.stem_paths = list(job.module_outputs.values())

                with self._lock:
                    self._active_outputs.discard(job.output_path)
                    self._initial_output_stats.pop(job.output_path, None)
                    for sp in job.stem_paths:
                        self._active_outputs.discard(sp)
                        self._initial_output_stats.pop(sp, None)

                job.module_results = res.get("module_results", job.module_results)
                if not job.master_output and job.module_results:
                    job.peak_db = max((m["peak_db"] for m in job.module_results.values()), default=-90.0)
                else:
                    job.peak_db = res.get("peak_db")

                want_normalize = bool(job.normalize if hasattr(job, 'normalize') and job.normalize else self.settings.normalize)
                if want_normalize and not self.cancel_event.is_set():
                    job.status = "Normalizing"
                    notify_job(job_idx)
                    target_db = float(getattr(job, 'normalize_target_db', None) or self.settings.normalize_target_db)
                    from .constants import AUDIO_FILE_FORMATS
                    fmt_code = AUDIO_FILE_FORMATS.get(self.settings.audio_file_type, 0)
                    st_code = clamp_sampletype_for_format(fmt_code, int(self.settings.samp_size))

                    if job.master_output and job.output_path and os.path.isfile(job.output_path):
                        try:
                            norm_peak = normalize_audio_file(
                                job.output_path,
                                target_db=target_db,
                                sr=sr,
                                fileformat=fmt_code,
                                sampletype=st_code,
                            )
                            job.peak_db = norm_peak
                        except Exception:
                            pass

                    norm_stem_peaks = []
                    for mid, mod_info in (job.module_results or {}).items():
                        mpath = mod_info.get("path")
                        if mpath and os.path.isfile(mpath):
                            try:
                                m_peak = normalize_audio_file(
                                    mpath,
                                    target_db=target_db,
                                    sr=sr,
                                    fileformat=fmt_code,
                                    sampletype=st_code,
                                )
                                mod_info["peak_db"] = m_peak
                                norm_stem_peaks.append(m_peak)
                            except Exception:
                                pass

                    for sp in (job.stem_paths or []):
                        if sp and os.path.isfile(sp):
                            already_done = any(m.get("path") == sp for m in (job.module_results or {}).values())
                            if not already_done:
                                try:
                                    sp_peak = normalize_audio_file(
                                        sp,
                                        target_db=target_db,
                                        sr=sr,
                                        fileformat=fmt_code,
                                        sampletype=st_code,
                                    )
                                    norm_stem_peaks.append(sp_peak)
                                except Exception:
                                    pass

                    if not job.master_output and norm_stem_peaks:
                        job.peak_db = max(norm_stem_peaks)

                job.status = "Done"
                job.progress = 1.0
                job.rendered_duration = float(res.get("duration", total_dur))
                job.elapsed = time.perf_counter() - j_t0
                with state_lock:
                    job_progress[job_idx] = 1.0
                    if job.peak_db is not None and (max_peak_db is None or job.peak_db > max_peak_db):
                        max_peak_db = job.peak_db
                notify_job(job_idx)

            except InterruptedError:
                job.status = "Cancelled"
                job.elapsed = time.perf_counter() - j_t0
                notify_job(job_idx)
            except Exception as exc:
                if self.cancel_event.is_set():
                    job.status = "Cancelled"
                else:
                    job.status = "Error"
                    job.error = str(exc)
                job.elapsed = time.perf_counter() - j_t0
                notify_job(job_idx)

        heartbeat_stop = threading.Event()

        def _heartbeat():
            while not heartbeat_stop.wait(0.08):
                if self.cancel_event.is_set():
                    break
                emit_overall()

        hb_thread = threading.Thread(target=_heartbeat, daemon=True, name="CeciliaOfflineHeartbeat")
        hb_thread.start()

        try:
            # Dispatch jobs concurrently across coordinator threads (up to num_threads concurrent jobs)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(max(1, total_jobs), num_threads),
                thread_name_prefix="CeciliaJobCoord",
            ) as job_exec:
                futs = [job_exec.submit(execute_job, idx, job) for idx, job in enumerate(jobs)]
                for f in futs:
                    try:
                        f.result()
                    except Exception:
                        pass
        finally:
            heartbeat_stop.set()
            hb_thread.join(timeout=1.0)
            cancelled = self.cancel_event.is_set()
            pool.shutdown()
            self._cleanup_temps(cancelled=cancelled or any(j.status == "Error" for j in jobs))
            self._pool = None
            self._running = False
            with state_lock:
                for i in range(num_threads):
                    worker_states[i] = {"active": False, "label": "Idle", "fraction": 0.0}
            emit_overall()
            with state_lock:
                coordinator_active = False

        elapsed_total = time.perf_counter() - t_start
        completed = sum(1 for j in jobs if j.status == "Done")
        failed = sum(1 for j in jobs if j.status == "Error")
        audio_secs = sum(j.rendered_duration for j in jobs if j.status == "Done")
        summary = RenderSummary(
            completed=completed,
            failed=failed,
            cancelled=self.cancel_event.is_set(),
            elapsed=elapsed_total,
            total_audio_seconds=audio_secs,
            max_peak_db=max_peak_db,
            jobs=jobs,
        )
        if self.on_complete:
            self.on_complete(summary)


if __name__ == "__main__":
    if "--worker" in sys.argv:
        sys.exit(worker_main(sys.argv[1:]))
