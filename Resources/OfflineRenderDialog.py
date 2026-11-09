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

Dedicated Offline Render Mode Dialog with Multithread Support for Cecilia 5.
"""

import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import wx

import Resources.CeciliaLib as CeciliaLib
from .constants import (
    AUDIO_FILE_FORMATS,
    BACKGROUND_COLOUR,
    BIT_DEPTHS,
    BUFFER_SIZES,
    BUTTON_BACK_COLOUR,
    CONTROLLABEL_BACK_COLOUR,
    GRADIENT_DARK_COLOUR,
    LABEL_FONT,
    SAMPLE_RATES,
    SECTION_TITLE_COLOUR,
    SECTION_TITLE_FONT,
    TEXT_LABELFORWIDGET_COLOUR,
    TEXT_LABELFORWIDGET_FONT,
    TITLE_BACK_COLOUR,
    TR_BORDER_COLOUR,
    TR_PLAY_NORMAL_COLOUR,
    WHITE_COLOUR,
)
from .OfflineRender import (
    OfflineRenderManager,
    RenderJob,
    RenderSettings,
    RenderSummary,
    apply_preset_to_snapshot,
    apply_sound_to_snapshot,
    extract_disjoint_output_branches,
    list_module_presets,
    load_preset_dict,
)

ACCEL_LABELS = [
    ("Auto (Branches / Chunks)", "auto"),
    ("Single Pass (Exact Stateful)", "single"),
    ("Parallel Chain Branches", "branches"),
    ("Time-Chunked (Full History)", "chunks"),
]

XFADE_LABELS = [
    ("Cosine (Unity Sum)", "cosine"),
    ("Equal-Power (Normalized)", "equal_power"),
]

BIT_DEPTH_ORDER = [
    ("16 bits int", 0),
    ("24 bits int", 1),
    ("32 bits int", 2),
    ("32 bits float", 3),
]

FORMAT_ORDER = ["wav", "aif", "flac", "ogg", "caf", "au", "sd2"]


def _fmt_time(seconds: Optional[float]) -> str:
    if seconds is None or seconds < 0 or not (seconds < 360000):
        return "--:--"
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins:02d}:{secs:04.1f}"


class _StudioProgressBar(wx.Panel):
    """Smooth custom-drawn dark-studio progress bar matching Cecilia5's aesthetic."""

    def __init__(self, parent, height: int = 20):
        super().__init__(parent, size=(-1, height), style=wx.BORDER_NONE)
        self.SetMinSize((-1, height))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self._fraction = 0.0
        self._label = "Ready"
        self._accent = "#2EA043"
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, lambda evt: (self.Refresh(False), evt.Skip()))

    def set_state(self, fraction: float, label: str, accent: str = "#2EA043"):
        self._fraction = max(0.0, min(1.0, float(fraction)))
        self._label = label
        self._accent = accent
        self.Refresh(False)

    def _on_paint(self, _evt):
        w, h = self.GetClientSize()
        if w <= 0 or h <= 0:
            return
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBrush(wx.Brush("#22252A"))
        dc.SetPen(wx.Pen("#666666", 1))
        dc.DrawRectangle(0, 0, w, h)

        fill_w = int(round((w - 2) * self._fraction))
        if fill_w > 0:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.Brush(self._accent))
            dc.DrawRectangle(1, 1, fill_w, h - 2)

        dc.SetFont(wx.Font(LABEL_FONT, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dc.SetTextForeground(WHITE_COLOUR)
        dc.DrawLabel(self._label, wx.Rect(8, 0, w - 16, h), wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        pct_txt = f"{self._fraction * 100.0:5.1f}%"
        dc.DrawLabel(pct_txt, wx.Rect(8, 0, w - 16, h), wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)


class _WorkerLanesPanel(wx.Panel):
    """Visual per-thread activity lanes showing concurrent worker utilization."""

    def __init__(self, parent, num_threads: int = 4):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self._workers: List[Dict[str, Any]] = []
        self.set_thread_count(num_threads)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, lambda evt: (self.Refresh(False), evt.Skip()))

    def set_thread_count(self, count: int):
        n = max(1, int(count))
        self._workers = [{"active": False, "label": "Idle", "fraction": 0.0} for _ in range(n)]
        cols = 2 if n > 2 else 1
        rows = (n + cols - 1) // cols
        h = max(26, rows * 20 + 8)
        self.SetMinSize((-1, h))
        if self.GetParent():
            self.GetParent().Layout()
        self.Refresh(False)

    def update_workers(self, workers: List[Dict[str, Any]]):
        if len(workers) != len(self._workers):
            self.set_thread_count(len(workers))
        self._workers = workers
        self.Refresh(False)

    def _on_paint(self, _evt):
        w, h = self.GetClientSize()
        if w <= 0 or h <= 0:
            return
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBrush(wx.Brush("#2B2F36"))
        dc.SetPen(wx.Pen("#555555", 1))
        dc.DrawRectangle(0, 0, w, h)

        n = max(1, len(self._workers))
        cols = 2 if n > 2 else 1
        rows = (n + cols - 1) // cols
        pad = 6
        gap_x = 8
        lane_w = max(40, (w - 2 * pad - (cols - 1) * gap_x) // cols)
        lane_h = 15

        dc.SetFont(wx.Font(max(8, LABEL_FONT - 1), wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        for idx, st in enumerate(self._workers):
            r = idx // cols
            c = idx % cols
            x = pad + c * (lane_w + gap_x)
            y = 4 + r * 20
            if y + lane_h > h - 2:
                break

            dc.SetBrush(wx.Brush("#1D2025"))
            dc.SetPen(wx.Pen("#444952", 1))
            dc.DrawRectangle(x, y, lane_w, lane_h)

            active = bool(st.get("active", False))
            frac = max(0.0, min(1.0, float(st.get("fraction", 0.0))))
            if active and frac > 0.0:
                fw = int(round((lane_w - 2) * frac))
                dc.SetPen(wx.TRANSPARENT_PEN)
                dc.SetBrush(wx.Brush("#3B78B5"))
                dc.DrawRectangle(x + 1, y + 1, fw, lane_h - 2)

            lbl = st.get("label", "Idle")
            txt = f"T{idx + 1}: {lbl}"
            if len(txt) > 34:
                txt = txt[:31] + "..."
            dc.SetTextForeground(WHITE_COLOUR if active else "#8C939E")
            dc.DrawLabel(txt, wx.Rect(x + 5, y, lane_w - 10, lane_h), wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)


class OfflineRenderDialog(wx.Frame):
    """Non-modal Offline Render Mode Studio Window for Cecilia 5."""

    _instance: Optional["OfflineRenderDialog"] = None

    @classmethod
    def open_dialog(cls, parent=None, mode: str = "single",
                    auto_output_path: Optional[str] = None,
                    auto_start: bool = False) -> "OfflineRenderDialog":
        if parent is None:
            parent = CeciliaLib.getVar("interface") or CeciliaLib.getVar("mainFrame")
        if cls._instance is not None and bool(cls._instance):
            dlg = cls._instance
            dlg.sync_from_session()
            dlg.select_mode(mode)
            dlg.Show()
            dlg.Raise()
        else:
            dlg = cls(parent, initial_mode=mode)
            cls._instance = dlg
            dlg.Show()
            dlg.Raise()

        if auto_output_path:
            dlg.single_path_ctrl.SetValue(auto_output_path)
            _, req_ext = os.path.splitext(auto_output_path)
            ext_map = {
                ".wav": "wav", ".wave": "wav",
                ".aif": "aif", ".aiff": "aif",
                ".flac": "flac", ".ogg": "ogg",
                ".caf": "caf", ".au": "au", ".sd2": "sd2",
            }
            mapped_fmt = ext_map.get(req_ext.lower())
            if mapped_fmt:
                idx = dlg.choice_format.FindString(mapped_fmt)
                if idx != wx.NOT_FOUND:
                    dlg.choice_format.SetSelection(idx)
        if auto_start and not dlg.is_rendering:
            wx.CallAfter(dlg.on_start_render, None)
        return dlg

    def __init__(self, parent, initial_mode: str = "single"):
        style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT
        super().__init__(parent, title="Cecilia 5 — Offline Render Mode", size=(760, 780), style=style)
        self.SetMinSize((680, 680))
        self.SetBackgroundColour(BACKGROUND_COLOUR)

        self._manager: Optional[OfflineRenderManager] = None
        self._queued_items: List[Dict[str, Any]] = []
        self._module_checklist_ids: List[str] = []
        self._list_item_map: Dict[int, List[tuple]] = {}
        self._last_output_path: str = ""
        self._progress_dirty = False
        self._latest_progress: Optional[Dict[str, Any]] = None

        self._build_ui()
        self.sync_from_session()
        self.select_mode(initial_mode)
        self.CentreOnParent()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    @property
    def is_rendering(self) -> bool:
        return self._manager is not None and self._manager.is_running

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _make_section_header(self, parent, title: str) -> wx.Panel:
        hdr = wx.Panel(parent, style=wx.BORDER_NONE)
        hdr.SetBackgroundColour(TITLE_BACK_COLOUR)
        sz = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(hdr, label=title)
        lbl.SetFont(wx.Font(SECTION_TITLE_FONT - 2, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        lbl.SetForegroundColour(SECTION_TITLE_COLOUR)
        sz.Add(lbl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hdr.SetSizer(sz)
        return hdr

    def _lbl(self, parent, text: str, bold: bool = False) -> wx.StaticText:
        st = wx.StaticText(parent, label=text)
        weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
        st.SetFont(wx.Font(TEXT_LABELFORWIDGET_FONT, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight))
        st.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        return st

    def _build_ui(self):
        root = wx.Panel(self)
        root.SetBackgroundColour(BACKGROUND_COLOUR)
        main_sz = wx.BoxSizer(wx.VERTICAL)

        # 1. Top Banner + Mode Selector Bar
        banner = wx.Panel(root)
        banner.SetBackgroundColour(TITLE_BACK_COLOUR)
        bsz = wx.BoxSizer(wx.HORIZONTAL)
        title_lbl = wx.StaticText(banner, label="OFFLINE RENDER STUDIO")
        title_lbl.SetFont(wx.Font(SECTION_TITLE_FONT, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title_lbl.SetForegroundColour(SECTION_TITLE_COLOUR)
        bsz.Add(title_lbl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        bsz.AddStretchSpacer(1)

        cpu_cnt = os.cpu_count() or 4
        cpu_lbl = wx.StaticText(banner, label=f"Multithread Engine • {cpu_cnt} CPU Cores Detected")
        cpu_lbl.SetFont(wx.Font(LABEL_FONT, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        cpu_lbl.SetForegroundColour("#9AA4B2")
        bsz.Add(cpu_lbl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        banner.SetSizer(bsz)
        main_sz.Add(banner, 0, wx.EXPAND)

        # Mode Notebook
        self.notebook = wx.Notebook(root)
        self.notebook.SetBackgroundColour(BACKGROUND_COLOUR)
        self.page_single = self._build_single_tab(self.notebook)
        self.page_presets = self._build_presets_tab(self.notebook)
        self.page_folder = self._build_folder_tab(self.notebook)
        self.page_queue = self._build_queue_tab(self.notebook)
        self.notebook.AddPage(self.page_single, "Single Bounce")
        self.notebook.AddPage(self.page_presets, "Batch Presets")
        self.notebook.AddPage(self.page_folder, "Batch Sound Folder")
        self.notebook.AddPage(self.page_queue, "Render Queue")
        main_sz.Add(self.notebook, 0, wx.EXPAND | wx.ALL, 8)

        # 2. Engine, Multithreading & Audio Format Settings
        main_sz.Add(self._make_section_header(root, "MULTITHREADING & AUDIO FORMAT"), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        settings_panel = self._build_settings_panel(root)
        main_sz.Add(settings_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # 3. Live Progress, Worker Lanes & Job Monitor
        main_sz.Add(self._make_section_header(root, "RENDER MONITOR"), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        monitor_panel = self._build_monitor_panel(root)
        main_sz.Add(monitor_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # 4. Action Bar
        footer = wx.Panel(root)
        footer.SetBackgroundColour(GRADIENT_DARK_COLOUR)
        fsz = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_sync = wx.Button(footer, label="Sync Session")
        self.btn_sync.Bind(wx.EVT_BUTTON, lambda _e: self.sync_from_session())
        fsz.Add(self.btn_sync, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_play_last = wx.Button(footer, label="Play Last Render")
        self.btn_play_last.Enable(False)
        self.btn_play_last.Bind(wx.EVT_BUTTON, self._on_play_last)
        fsz.Add(self.btn_play_last, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        fsz.AddStretchSpacer(1)

        self.btn_cancel = wx.Button(footer, label="Cancel Render")
        self.btn_cancel.Enable(False)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel_render)
        fsz.Add(self.btn_cancel, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.btn_start = wx.Button(footer, label="Start Offline Render")
        self.btn_start.SetDefault()
        self.btn_start.Bind(wx.EVT_BUTTON, self.on_start_render)
        fsz.Add(self.btn_start, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        btn_close = wx.Button(footer, label="Close")
        btn_close.Bind(wx.EVT_BUTTON, self._on_close)
        fsz.Add(btn_close, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        footer.SetSizer(fsz)
        main_sz.Add(footer, 0, wx.EXPAND)

        root.SetSizer(main_sz)

    def _build_single_tab(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour(BACKGROUND_COLOUR)
        sz = wx.BoxSizer(wx.VERTICAL)

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        row1.Add(self._lbl(p, "Output File:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.single_path_ctrl = wx.TextCtrl(p, value="")
        self.single_path_ctrl.Bind(wx.EVT_TEXT, lambda _e: self._update_module_stems_preview())
        row1.Add(self.single_path_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        btn_browse = wx.Button(p, label="Browse...")
        btn_browse.Bind(wx.EVT_BUTTON, self._on_browse_single_output)
        row1.Add(btn_browse, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(row1, 0, wx.EXPAND | wx.ALL, 8)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row2.Add(self._lbl(p, "Duration (sec):", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.single_dur_spin = wx.SpinCtrlDouble(p, min=0.05, max=3600.0, initial=30.0, inc=0.5, size=(110, -1))
        self.single_dur_spin.SetDigits(2)
        row2.Add(self.single_dur_spin, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        btn_use_snd_dur = wx.Button(p, label="Use Input Sound Duration")
        btn_use_snd_dur.Bind(wx.EVT_BUTTON, self._on_use_input_sound_dur)
        row2.Add(btn_use_snd_dur, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 14)

        self.chk_export_stems = wx.CheckBox(p, label="Also export branch stems (disjoint parallel outputs)")
        self.chk_export_stems.SetValue(bool(CeciliaLib.getVar("offlineExportStems") or False))
        self.chk_export_stems.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        self.chk_export_stems.Bind(wx.EVT_CHECKBOX, self._on_export_stems_toggled)
        row2.Add(self.chk_export_stems, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(row2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.single_chain_info = self._lbl(p, "")
        self.single_chain_info.SetForegroundColour("#B8C4D4")
        sz.Add(self.single_chain_info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # Dedicated Section: Individual Module Output Soundfiles (Toggles)
        stems_box = wx.StaticBox(p, label=" Module Outputs to Disk (Individual Stems) ")
        stems_box.SetForegroundColour(SECTION_TITLE_COLOUR)
        stems_sz = wx.StaticBoxSizer(stems_box, wx.VERTICAL)

        top_stems = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_master_output = wx.CheckBox(stems_box, label="Master Mix (Final Chain Output + Master Plugins)")
        cur_master = bool(CeciliaLib.getVar("offlineMasterOutput")) if CeciliaLib.getVar("offlineMasterOutput") is not None else True
        self.chk_master_output.SetValue(cur_master)
        self.chk_master_output.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        self.chk_master_output.Bind(wx.EVT_CHECKBOX, self._on_master_output_toggled)
        top_stems.Add(self.chk_master_output, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        btn_all = wx.Button(stems_box, label="Select All", size=(85, 22))
        btn_none = wx.Button(stems_box, label="Select None", size=(85, 22))
        btn_master = wx.Button(stems_box, label="Master Only", size=(95, 22))
        btn_all.Bind(wx.EVT_BUTTON, lambda _e: self._set_all_module_stems(True))
        btn_none.Bind(wx.EVT_BUTTON, lambda _e: self._set_all_module_stems(False))
        btn_master.Bind(wx.EVT_BUTTON, self._on_master_only_clicked)
        top_stems.Add(btn_all, 0, wx.RIGHT, 4)
        top_stems.Add(btn_none, 0, wx.RIGHT, 4)
        top_stems.Add(btn_master, 0)
        stems_sz.Add(top_stems, 0, wx.EXPAND | wx.ALL, 6)

        self.module_checklist = wx.CheckListBox(stems_box, size=(-1, 75))
        self.module_checklist.Bind(wx.EVT_CHECKLISTBOX, self._on_module_checklist_toggled)
        stems_sz.Add(self.module_checklist, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.module_stems_preview = self._lbl(stems_box, "")
        self.module_stems_preview.SetForegroundColour("#A0B4C8")
        stems_sz.Add(self.module_stems_preview, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 6)

        sz.Add(stems_sz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        p.SetSizer(sz)
        return p

    def _build_presets_tab(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour(BACKGROUND_COLOUR)
        sz = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        self.presets_mod_lbl = self._lbl(p, "Presets to Render:", bold=True)
        top.Add(self.presets_mod_lbl, 1, wx.ALIGN_CENTER_VERTICAL)
        btn_all = wx.Button(p, label="Select All", size=(85, -1))
        btn_none = wx.Button(p, label="Select None", size=(90, -1))
        btn_ref = wx.Button(p, label="Refresh", size=(75, -1))
        btn_all.Bind(wx.EVT_BUTTON, lambda _e: self._set_all_presets(True))
        btn_none.Bind(wx.EVT_BUTTON, lambda _e: self._set_all_presets(False))
        btn_ref.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_preset_list())
        top.Add(btn_all, 0, wx.RIGHT, 4)
        top.Add(btn_none, 0, wx.RIGHT, 4)
        top.Add(btn_ref, 0)
        sz.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.preset_checklist = wx.CheckListBox(p, size=(-1, 78))
        sz.Add(self.preset_checklist, 1, wx.EXPAND | wx.ALL, 6)

        out_row = wx.BoxSizer(wx.HORIZONTAL)
        out_row.Add(self._lbl(p, "Output Folder:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.preset_dir_ctrl = wx.TextCtrl(p, value="")
        out_row.Add(self.preset_dir_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        btn_dir = wx.Button(p, label="Browse...")
        btn_dir.Bind(wx.EVT_BUTTON, lambda _e: self._browse_dir(self.preset_dir_ctrl))
        out_row.Add(btn_dir, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        out_row.Add(self._lbl(p, "Prefix:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.preset_prefix_ctrl = wx.TextCtrl(p, value="", size=(110, -1))
        out_row.Add(self.preset_prefix_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(out_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        opt_row = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_preset_globals = wx.CheckBox(p, label="Use each preset's saved duration & plugins")
        self.chk_preset_globals.SetValue(True)
        self.chk_preset_globals.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        self.chk_preset_keep_snd = wx.CheckBox(p, label="Keep current input sound file")
        self.chk_preset_keep_snd.SetValue(True)
        self.chk_preset_keep_snd.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        opt_row.Add(self.chk_preset_globals, 0, wx.RIGHT, 16)
        opt_row.Add(self.chk_preset_keep_snd, 0)
        sz.Add(opt_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        p.SetSizer(sz)
        return p

    def _build_folder_tab(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour(BACKGROUND_COLOUR)
        sz = wx.BoxSizer(wx.VERTICAL)

        in_row = wx.BoxSizer(wx.HORIZONTAL)
        in_row.Add(self._lbl(p, "Source Sound Folder:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.folder_in_ctrl = wx.TextCtrl(p, value="")
        self.folder_in_ctrl.Bind(wx.EVT_TEXT, lambda _e: self._update_folder_count())
        in_row.Add(self.folder_in_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        btn_in = wx.Button(p, label="Browse...")
        btn_in.Bind(wx.EVT_BUTTON, self._on_browse_source_folder)
        in_row.Add(btn_in, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(in_row, 0, wx.EXPAND | wx.ALL, 8)

        out_row = wx.BoxSizer(wx.HORIZONTAL)
        out_row.Add(self._lbl(p, "Output Folder:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.folder_out_ctrl = wx.TextCtrl(p, value="")
        out_row.Add(self.folder_out_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        btn_out = wx.Button(p, label="Browse...")
        btn_out.Bind(wx.EVT_BUTTON, lambda _e: self._browse_dir(self.folder_out_ctrl))
        out_row.Add(btn_out, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        out_row.Add(self._lbl(p, "Suffix:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.folder_suffix_ctrl = wx.TextCtrl(p, value="_rendered", size=(95, -1))
        out_row.Add(self.folder_suffix_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(out_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        opt_row = wx.BoxSizer(wx.HORIZONTAL)
        opt_row.Add(self._lbl(p, "Target Input Slot:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.folder_input_choice = wx.Choice(p, choices=["(auto)"])
        self.folder_input_choice.SetSelection(0)
        opt_row.Add(self.folder_input_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)

        self.chk_folder_snd_dur = wx.CheckBox(p, label="Match output duration to each sound file")
        self.chk_folder_snd_dur.SetValue(bool(CeciliaLib.getVar("useSoundDur")))
        self.chk_folder_snd_dur.SetForegroundColour(TEXT_LABELFORWIDGET_COLOUR)
        opt_row.Add(self.chk_folder_snd_dur, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 14)

        self.folder_count_lbl = self._lbl(p, "0 audio files selected")
        self.folder_count_lbl.SetForegroundColour("#B8C4D4")
        opt_row.Add(self.folder_count_lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(opt_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        p.SetSizer(sz)
        return p

    def _build_queue_tab(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour(BACKGROUND_COLOUR)
        sz = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(self._lbl(p, "Item Name:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.queue_name_ctrl = wx.TextCtrl(p, value="variation_01", size=(140, -1))
        top.Add(self.queue_name_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        btn_add = wx.Button(p, label="+ Capture Current Session State")
        btn_add.Bind(wx.EVT_BUTTON, self._on_add_queue_item)
        top.Add(btn_add, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        btn_rm = wx.Button(p, label="Remove")
        btn_rm.Bind(wx.EVT_BUTTON, self._on_remove_queue_item)
        top.Add(btn_rm, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)

        btn_clr = wx.Button(p, label="Clear")
        btn_clr.Bind(wx.EVT_BUTTON, self._on_clear_queue)
        top.Add(btn_clr, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        self.queue_list = wx.ListCtrl(p, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 72))
        self.queue_list.InsertColumn(0, "Name", width=160)
        self.queue_list.InsertColumn(1, "Duration", width=80)
        self.queue_list.InsertColumn(2, "Modules", width=150)
        self.queue_list.InsertColumn(3, "Output File", width=290)
        sz.Add(self.queue_list, 1, wx.EXPAND | wx.ALL, 6)

        dir_row = wx.BoxSizer(wx.HORIZONTAL)
        dir_row.Add(self._lbl(p, "Queue Output Folder:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.queue_dir_ctrl = wx.TextCtrl(p, value="")
        dir_row.Add(self.queue_dir_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        btn_qdir = wx.Button(p, label="Browse...")
        btn_qdir.Bind(wx.EVT_BUTTON, lambda _e: self._browse_dir(self.queue_dir_ctrl))
        dir_row.Add(btn_qdir, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(dir_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        p.SetSizer(sz)
        return p

    def _build_settings_panel(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour("#3E4147")
        sz = wx.BoxSizer(wx.VERTICAL)

        max_cores = max(1, (os.cpu_count() or 4) * 2)
        default_threads = int(CeciliaLib.getVar("offlineThreads") or min(8, os.cpu_count() or 4))

        # Row 1: Threads + Acceleration strategy + Chunk options
        r1 = wx.BoxSizer(wx.HORIZONTAL)
        r1.Add(self._lbl(p, "Worker Threads:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        thread_choices = [str(i) for i in range(1, max_cores + 1)]
        self.choice_threads = wx.Choice(p, choices=thread_choices)
        self.choice_threads.SetStringSelection(str(min(max_cores, max(1, default_threads))))
        self.choice_threads.Bind(wx.EVT_CHOICE, self._on_threads_changed)
        r1.Add(self.choice_threads, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 14)

        r1.Add(self._lbl(p, "Single-Render Strategy:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.choice_accel = wx.Choice(p, choices=[lbl for lbl, _ in ACCEL_LABELS])
        cur_accel = CeciliaLib.getVar("offlineAccelMode") or "auto"
        accel_idx = next((i for i, (_, k) in enumerate(ACCEL_LABELS) if k == cur_accel), 0)
        self.choice_accel.SetSelection(accel_idx)
        self.choice_accel.Bind(wx.EVT_CHOICE, self._on_accel_changed)
        r1.Add(self.choice_accel, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(r1, 0, wx.EXPAND | wx.ALL, 7)

        # Row 2: Time-chunk preroll & crossfade
        r2 = wx.BoxSizer(wx.HORIZONTAL)
        r2.Add(self._lbl(p, "Chunk Preroll (s):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        cur_preroll = float(CeciliaLib.getVar("offlinePreroll") if CeciliaLib.getVar("offlinePreroll") is not None else 0.5)
        self.spin_preroll = wx.SpinCtrlDouble(
            p, min=0.0, max=10.0, initial=cur_preroll, inc=0.1, size=(80, -1)
        )
        self.spin_preroll.SetDigits(2)
        self.spin_preroll.SetToolTip("Chunks replay the full signal history to preserve DSP state. Legacy preroll is unused.")
        self.spin_preroll.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_preroll_changed)
        r2.Add(self.spin_preroll, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        r2.Add(self._lbl(p, "Crossfade (s):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        cur_xfade = float(CeciliaLib.getVar("offlineCrossfade") if CeciliaLib.getVar("offlineCrossfade") is not None else 0.1)
        self.spin_xfade = wx.SpinCtrlDouble(
            p, min=0.01, max=2.0, initial=cur_xfade, inc=0.02, size=(80, -1)
        )
        self.spin_xfade.SetDigits(2)
        self.spin_xfade.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_xfade_changed)
        r2.Add(self.spin_xfade, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        r2.Add(self._lbl(p, "Crossfade Curve:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_xfade_shape = wx.Choice(p, choices=[lbl for lbl, _ in XFADE_LABELS])
        cur_xshape = str(CeciliaLib.getVar("offlineCrossfadeShape") or "cosine")
        xshape_idx = next((i for i, (_, k) in enumerate(XFADE_LABELS) if k == cur_xshape), 0)
        self.choice_xfade_shape.SetSelection(xshape_idx)
        self.choice_xfade_shape.Bind(wx.EVT_CHOICE, self._on_xfade_shape_changed)
        r2.Add(self.choice_xfade_shape, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(r2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 7)

        # Row 3: Format, Bit depth, Sample Rate, Channels, Buffer size
        r3 = wx.BoxSizer(wx.HORIZONTAL)
        r3.Add(self._lbl(p, "Format:", bold=True), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_format = wx.Choice(p, choices=FORMAT_ORDER)
        cur_fmt = str(CeciliaLib.getVar("offlineAudioFileType") or CeciliaLib.getVar("audioFileType") or "wav")
        self.choice_format.SetStringSelection(cur_fmt if cur_fmt in FORMAT_ORDER else "wav")
        self.choice_format.Bind(wx.EVT_CHOICE, self._on_format_changed)
        r3.Add(self.choice_format, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        r3.Add(self._lbl(p, "Bit Depth:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_bitdepth = wx.Choice(p, choices=[lbl for lbl, _ in BIT_DEPTH_ORDER])
        cur_bd = int(CeciliaLib.getVar("offlineSampSize") if CeciliaLib.getVar("offlineSampSize") is not None else (CeciliaLib.getVar("sampSize") or 0))
        bd_idx = next((i for i, (_, v) in enumerate(BIT_DEPTH_ORDER) if v == cur_bd), 0)
        self.choice_bitdepth.SetSelection(bd_idx)
        self.choice_bitdepth.Bind(wx.EVT_CHOICE, self._on_bitdepth_changed)
        r3.Add(self.choice_bitdepth, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        r3.Add(self._lbl(p, "Sample Rate:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_sr = wx.Choice(p, choices=SAMPLE_RATES)
        cur_sr = str(CeciliaLib.getVar("offlineSr") or CeciliaLib.getVar("sr") or 44100)
        self.choice_sr.SetStringSelection(cur_sr if cur_sr in SAMPLE_RATES else "44100")
        self.choice_sr.Bind(wx.EVT_CHOICE, self._on_sr_changed)
        r3.Add(self.choice_sr, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        r3.Add(self._lbl(p, "Chnls:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_nchnls = wx.Choice(p, choices=[str(x) for x in range(1, 65)])
        cur_nchnls = str(CeciliaLib.getVar("offlineNchnls") or CeciliaLib.getVar("nchnls") or 2)
        if cur_nchnls in [str(x) for x in range(1, 65)]:
            self.choice_nchnls.SetStringSelection(cur_nchnls)
        else:
            self.choice_nchnls.SetStringSelection("2")
        self.choice_nchnls.Bind(wx.EVT_CHOICE, self._on_nchnls_changed)
        r3.Add(self.choice_nchnls, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        r3.Add(self._lbl(p, "Buffer:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.choice_buf = wx.Choice(p, choices=BUFFER_SIZES)
        cur_buf = str(CeciliaLib.getVar("offlineBufferSize") or CeciliaLib.getVar("bufferSize") or "512")
        self.choice_buf.SetStringSelection(cur_buf if cur_buf in BUFFER_SIZES else "512")
        self.choice_buf.Bind(wx.EVT_CHOICE, self._on_buf_changed)
        r3.Add(self.choice_buf, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(r3, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 7)

        # Row 4: Normalization (checkbox toggle + target peak in text box)
        r4 = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_normalize = wx.CheckBox(p, label="Normalize audio files to:")
        self.chk_normalize.SetForegroundColour(WHITE_COLOUR)
        cur_norm = bool(int(CeciliaLib.getVar("offlineNormalize") or 0))
        self.chk_normalize.SetValue(cur_norm)
        self.chk_normalize.Bind(wx.EVT_CHECKBOX, self._on_normalize_toggled)
        r4.Add(self.chk_normalize, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        cur_norm_db = float(CeciliaLib.getVar("offlineNormalizeTargetDb") if CeciliaLib.getVar("offlineNormalizeTargetDb") is not None else -0.1)
        self.txt_normalize_db = wx.TextCtrl(p, value=f"{cur_norm_db:.1f}", size=(65, -1))
        self.txt_normalize_db.Enable(cur_norm)
        self.txt_normalize_db.Bind(wx.EVT_TEXT, self._on_normalize_changed)
        r4.Add(self.txt_normalize_db, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)

        lbl_db = self._lbl(p, "dBFS")
        r4.Add(lbl_db, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 14)

        tip_norm = self._lbl(p, "(Scales all output audio files to target peak level after render)")
        tip_norm.SetForegroundColour("#8C939E")
        r4.Add(tip_norm, 0, wx.ALIGN_CENTER_VERTICAL)

        sz.Add(r4, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 7)

        p.SetSizer(sz)
        self._update_chunk_controls_enabled()
        return p

    def _build_monitor_panel(self, parent) -> wx.Panel:
        p = wx.Panel(parent)
        p.SetBackgroundColour("#36393F")
        sz = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        self.progress_bar = _StudioProgressBar(p, height=22)
        top.Add(self.progress_bar, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.peak_badge = wx.StaticText(p, label="Peak: --.-- dB", size=(125, 22), style=wx.ALIGN_CENTER_HORIZONTAL)
        self.peak_badge.SetFont(wx.Font(LABEL_FONT, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.peak_badge.SetBackgroundColour("#22252A")
        self.peak_badge.SetForegroundColour("#D0D7DE")
        top.Add(self.peak_badge, 0, wx.ALIGN_CENTER_VERTICAL)
        sz.Add(top, 0, wx.EXPAND | wx.ALL, 6)

        init_threads = int(self.choice_threads.GetStringSelection() or 4)
        self.worker_lanes = _WorkerLanesPanel(p, num_threads=init_threads)
        sz.Add(self.worker_lanes, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.jobs_list = wx.ListCtrl(p, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.jobs_list.SetBackgroundColour("#25282D")
        self.jobs_list.SetForegroundColour(WHITE_COLOUR)
        self.jobs_list.InsertColumn(0, "Job", width=155)
        self.jobs_list.InsertColumn(1, "Status", width=130)
        self.jobs_list.InsertColumn(2, "Audio Dur", width=80)
        self.jobs_list.InsertColumn(3, "Peak", width=85)
        self.jobs_list.InsertColumn(4, "Wall Time", width=80)
        self.jobs_list.InsertColumn(5, "Output File", width=200)
        sz.Add(self.jobs_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        p.SetSizer(sz)
        return p

    # ------------------------------------------------------------------
    # State Synchronization & Helpers
    # ------------------------------------------------------------------

    def select_mode(self, mode: str):
        mapping = {"single": 0, "presets": 1, "folder": 2, "queue": 3}
        self.notebook.SetSelection(mapping.get(mode, 0))

    def sync_from_session(self):
        if self.is_rendering:
            return
        total_time = float(CeciliaLib.getVar("totalTime") or 30.0)
        self.single_dur_spin.SetValue(total_time)

        # Retain offline export format, bit depth, sr, nchnls, buffer, threads etc.
        # Fall back to session values only if offline setting is not yet set.
        fmt = str(CeciliaLib.getVar("offlineAudioFileType") or CeciliaLib.getVar("audioFileType") or "wav")
        if fmt in FORMAT_ORDER:
            self.choice_format.SetStringSelection(fmt)
        bd = int(CeciliaLib.getVar("offlineSampSize") if CeciliaLib.getVar("offlineSampSize") is not None else (CeciliaLib.getVar("sampSize") or 0))
        bd_idx = next((i for i, (_, v) in enumerate(BIT_DEPTH_ORDER) if v == bd), 0)
        self.choice_bitdepth.SetSelection(bd_idx)

        sr_str = str(CeciliaLib.getVar("offlineSr") or CeciliaLib.getVar("sr") or 44100)
        if sr_str in SAMPLE_RATES:
            self.choice_sr.SetStringSelection(sr_str)
        nchnls_str = str(CeciliaLib.getVar("offlineNchnls") or CeciliaLib.getVar("nchnls") or 2)
        if nchnls_str in [str(x) for x in range(1, 65)]:
            self.choice_nchnls.SetStringSelection(nchnls_str)
        buf_str = str(CeciliaLib.getVar("offlineBufferSize") or CeciliaLib.getVar("bufferSize") or "512")
        if buf_str in BUFFER_SIZES:
            self.choice_buf.SetStringSelection(buf_str)

        cur_threads = str(CeciliaLib.getVar("offlineThreads") or min(8, os.cpu_count() or 4))
        if self.choice_threads.FindString(cur_threads) != wx.NOT_FOUND:
            self.choice_threads.SetStringSelection(cur_threads)

        cur_accel = CeciliaLib.getVar("offlineAccelMode") or "auto"
        accel_idx = next((i for i, (_, k) in enumerate(ACCEL_LABELS) if k == cur_accel), 0)
        self.choice_accel.SetSelection(accel_idx)

        if CeciliaLib.getVar("offlinePreroll") is not None:
            self.spin_preroll.SetValue(float(CeciliaLib.getVar("offlinePreroll")))
        if CeciliaLib.getVar("offlineCrossfade") is not None:
            self.spin_xfade.SetValue(float(CeciliaLib.getVar("offlineCrossfade")))
        cur_xshape = str(CeciliaLib.getVar("offlineCrossfadeShape") or "cosine")
        xshape_idx = next((i for i, (_, k) in enumerate(XFADE_LABELS) if k == cur_xshape), 0)
        self.choice_xfade_shape.SetSelection(xshape_idx)

        if CeciliaLib.getVar("offlineExportStems") is not None:
            self.chk_export_stems.SetValue(bool(CeciliaLib.getVar("offlineExportStems")))
        if CeciliaLib.getVar("offlineMasterOutput") is not None:
            self.chk_master_output.SetValue(bool(CeciliaLib.getVar("offlineMasterOutput")))

        if hasattr(self, "chk_normalize"):
            cur_norm = bool(int(CeciliaLib.getVar("offlineNormalize") or 0))
            self.chk_normalize.SetValue(cur_norm)
            if hasattr(self, "txt_normalize_db"):
                self.txt_normalize_db.Enable(cur_norm)
                cur_db = float(CeciliaLib.getVar("offlineNormalizeTargetDb") if CeciliaLib.getVar("offlineNormalizeTargetDb") is not None else -0.1)
                self.txt_normalize_db.SetValue(f"{cur_db:.1f}")

        self._update_chunk_controls_enabled()

        default_dir = (
            CeciliaLib.getVar("saveAudioFilePath", unicode=True)
            or CeciliaLib.getVar("prefferedPath", unicode=True)
            or os.path.expanduser("~")
        )
        if os.path.isfile(default_dir):
            default_dir = os.path.dirname(default_dir)
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")

        mod_name = CeciliaLib.getVar("currentModuleName") or "cecilia_render"
        ext = self.choice_format.GetStringSelection()

        if not self.single_path_ctrl.GetValue():
            cp = CeciliaLib.getControlPanel() if CeciliaLib.getVar("interface") else None
            existing_out = getattr(cp, "outputFilename", "") if cp else ""
            if existing_out:
                self.single_path_ctrl.SetValue(existing_out)
            else:
                self.single_path_ctrl.SetValue(os.path.join(default_dir, f"{mod_name}_render.{ext}"))

        if not self.preset_dir_ctrl.GetValue():
            self.preset_dir_ctrl.SetValue(os.path.join(default_dir, f"{mod_name}_presets"))
        if not self.preset_prefix_ctrl.GetValue():
            self.preset_prefix_ctrl.SetValue(f"{mod_name}_")

        if not self.folder_out_ctrl.GetValue():
            self.folder_out_ctrl.SetValue(os.path.join(default_dir, f"{mod_name}_batch"))
        if not self.queue_dir_ctrl.GetValue():
            self.queue_dir_ctrl.SetValue(os.path.join(default_dir, "cecilia_queue"))

        self._refresh_preset_list()
        self._refresh_input_slots()
        self._refresh_chain_branch_status()
        self._refresh_module_stems_list()

    def _refresh_module_stems_list(self):
        if not hasattr(self, "module_checklist"):
            return
        modules = CeciliaLib.session.modules if hasattr(CeciliaLib, "session") else []
        stem_ids = set(getattr(CeciliaLib.session, "offline_stem_ids", []) or [])
        master_enabled = getattr(CeciliaLib.session, "master_output_enabled", True)
        if hasattr(self, "chk_master_output"):
            self.chk_master_output.SetValue(master_enabled)

        self._module_checklist_ids = []
        items = []
        source_ids = set(getattr(CeciliaLib.session, "source_ids", []) or [])
        sink_ids = set(getattr(CeciliaLib.session, "sink_ids", []) or [])
        for idx, mod in enumerate(modules):
            mod_name = os.path.splitext(os.path.basename(getattr(mod, "path", "") or getattr(mod, "name", "Module")))[0]
            role = "Source" if mod.id in source_ids else ("Output" if mod.id in sink_ids else "Module")
            label = f"{idx + 1:02d} — {mod_name} ({role})"
            items.append(label)
            self._module_checklist_ids.append(mod.id)

        self.module_checklist.Set(items)
        for i, mid in enumerate(self._module_checklist_ids):
            self.module_checklist.Check(i, mid in stem_ids)
        self._update_module_stems_preview()

    def _on_master_output_toggled(self, _evt):
        en = bool(self.chk_master_output.GetValue())
        CeciliaLib.setVar("offlineMasterOutput", int(en))
        if hasattr(CeciliaLib, "session") and hasattr(CeciliaLib.session, "set_master_output_enabled"):
            CeciliaLib.session.set_master_output_enabled(en)
        self._update_module_stems_preview()
        self._save_offline_prefs()

    def _on_module_checklist_toggled(self, evt):
        idx = evt.GetInt()
        if 0 <= idx < len(self._module_checklist_ids):
            mid = self._module_checklist_ids[idx]
            is_chk = self.module_checklist.IsChecked(idx)
            if hasattr(CeciliaLib, "session") and hasattr(CeciliaLib.session, "set_offline_stem"):
                CeciliaLib.session.set_offline_stem(mid, is_chk)
        self._update_module_stems_preview()
        if CeciliaLib.getVar("interface") is not None:
            try:
                rg = getattr(CeciliaLib.getVar("interface"), "grid", None) or getattr(CeciliaLib.getVar("interface"), "routing_graph", None)
                if rg is not None:
                    rg.Refresh(False)
            except Exception:
                pass

    def _set_all_module_stems(self, checked: bool):
        for i in range(self.module_checklist.GetCount()):
            self.module_checklist.Check(i, checked)
            if i < len(self._module_checklist_ids) and hasattr(CeciliaLib, "session") and hasattr(CeciliaLib.session, "set_offline_stem"):
                CeciliaLib.session.set_offline_stem(self._module_checklist_ids[i], checked)
        self._update_module_stems_preview()
        if CeciliaLib.getVar("interface") is not None:
            try:
                rg = getattr(CeciliaLib.getVar("interface"), "grid", None) or getattr(CeciliaLib.getVar("interface"), "routing_graph", None)
                if rg is not None:
                    rg.Refresh(False)
            except Exception:
                pass

    def _on_master_only_clicked(self, _evt):
        self.chk_master_output.SetValue(True)
        CeciliaLib.setVar("offlineMasterOutput", 1)
        if hasattr(CeciliaLib, "session") and hasattr(CeciliaLib.session, "set_master_output_enabled"):
            CeciliaLib.session.set_master_output_enabled(True)
        self._set_all_module_stems(False)
        self._save_offline_prefs()

    def _split_base_and_root(self, base_path: str, ext: str) -> Tuple[str, str, str, str]:
        """
        Splits a base output path into:
        (dir_name, clean_root, master_path, clean_ext)
        where:
          - clean_root is the base filename without extension and without a trailing '_Master'
          - master_path is os.path.join(dir_name, f"{clean_root}_Master.{clean_ext}")
        Examples:
          'Final.wav', 'wav' -> ('...', 'Final', '.../Final_Master.wav', 'wav')
          'Final_Master.wav', 'wav' -> ('...', 'Final', '.../Final_Master.wav', 'wav')
          'Final', 'aif' -> ('...', 'Final', '.../Final_Master.aif', 'aif')
        """
        dir_name = os.path.dirname(os.path.abspath(base_path)) if base_path else os.path.expanduser("~")
        file_name = os.path.basename(base_path) if base_path else f"render.{ext}"
        stem, cur_ext = os.path.splitext(file_name)
        clean_ext = (cur_ext[1:] if cur_ext.startswith(".") and cur_ext[1:] else ext).lower()

        # Strip existing _Master or _master suffix to get clean root
        if stem.lower().endswith("_master"):
            clean_root = stem[:-7]
        else:
            clean_root = stem

        if not clean_root:
            clean_root = "render"

        master_path = os.path.join(dir_name, f"{clean_root}_Master.{clean_ext}")
        return dir_name, clean_root, master_path, clean_ext

    def _get_master_output_path(self, base_path: str, ext: str) -> str:
        _, _, master_path, _ = self._split_base_and_root(base_path, ext)
        return master_path

    def _get_selected_module_stems(self, base_path: str, ext: str) -> Dict[str, str]:
        selected: Dict[str, str] = {}
        if not base_path:
            return selected
        dir_name, clean_root, _, clean_ext = self._split_base_and_root(base_path, ext)

        checked_mods: List[Tuple[str, str]] = []
        for i, mid in enumerate(self._module_checklist_ids):
            if i < self.module_checklist.GetCount() and self.module_checklist.IsChecked(i):
                mod = (
                    CeciliaLib.session.get_module(mid)
                    if (hasattr(CeciliaLib, "session") and hasattr(CeciliaLib.session, "get_module"))
                    else next((m for m in getattr(getattr(CeciliaLib, "session", None), "modules", []) if m.id == mid), None)
                )
                mod_name = os.path.splitext(os.path.basename(getattr(mod, "path", "") or "Module"))[0] if mod else f"module_{i+1}"
                checked_mods.append((mid, mod_name))

        from collections import Counter
        name_counts = Counter(name for _, name in checked_mods)
        seen_counts: Dict[str, int] = {}

        for mid, mod_name in checked_mods:
            if name_counts[mod_name] > 1:
                seen_counts[mod_name] = seen_counts.get(mod_name, 0) + 1
                stem_file = f"{clean_root}_{mod_name}_{seen_counts[mod_name]}.{clean_ext}"
            else:
                stem_file = f"{clean_root}_{mod_name}.{clean_ext}"
            selected[mid] = os.path.join(dir_name, stem_file)

        return selected

    def _update_module_stems_preview(self):
        if not hasattr(self, "module_stems_preview"):
            return
        master_on = bool(self.chk_master_output.GetValue()) if hasattr(self, "chk_master_output") else True
        stem_indices = [i for i in range(self.module_checklist.GetCount()) if self.module_checklist.IsChecked(i)] if hasattr(self, "module_checklist") else []
        total_files = (1 if master_on else 0) + len(stem_indices)
        if total_files == 0:
            self.module_stems_preview.SetLabel("No output selected. Enable Master Mix or select at least one module stem.")
            self.module_stems_preview.SetForegroundColour("#E06C75")
            return

        out_path = self.single_path_ctrl.GetValue().strip() if hasattr(self, "single_path_ctrl") else ""
        ext = self.choice_format.GetStringSelection() if hasattr(self, "choice_format") else "wav"
        _, _, master_path, clean_ext = self._split_base_and_root(out_path or f"render.{ext}", ext)
        stems_dict = self._get_selected_module_stems(out_path or f"render.{clean_ext}", clean_ext)
        names = []
        if master_on:
            names.append(os.path.basename(master_path))
        for p in stems_dict.values():
            names.append(os.path.basename(p))

        lbl = f"Outputs ({total_files} file{'s' if total_files != 1 else ''}): " + ", ".join(names)
        if len(lbl) > 130:
            lbl = lbl[:127] + "..."
        self.module_stems_preview.SetLabel(lbl)
        self.module_stems_preview.SetForegroundColour("#A0B4C8")

    def _refresh_preset_list(self):
        mod_name = CeciliaLib.getVar("currentModuleName") or ""
        self.presets_mod_lbl.SetLabel(f"Presets for '{mod_name or 'None'}':")
        presets = list_module_presets(mod_name, include_init=True) if mod_name else []
        self.preset_checklist.Set(presets)
        for i in range(len(presets)):
            self.preset_checklist.Check(i, True)

    def _set_all_presets(self, checked: bool):
        for i in range(self.preset_checklist.GetCount()):
            self.preset_checklist.Check(i, checked)

    def _refresh_input_slots(self):
        slots = ["(auto)"]
        if CeciliaLib.session.modules:
            src = CeciliaLib.session.source or CeciliaLib.session.modules[0]
            for w in src.interface:
                if w.get("type") in ("cfilein", "csampler"):
                    slots.append(w["name"])
        self.folder_input_choice.Set(slots)
        self.folder_input_choice.SetSelection(0)

    def _refresh_chain_branch_status(self):
        if not CeciliaLib.session.modules:
            self.single_chain_info.SetLabel("No module loaded.")
            self.chk_export_stems.Enable(False)
            return
        try:
            snap = CeciliaLib.captureSession()
            branches = extract_disjoint_output_branches(snap)
        except Exception:
            branches = None
        n_mods = len(CeciliaLib.session.modules)
        if branches and len(branches) >= 2:
            self.single_chain_info.SetLabel(
                f"Chain graph: {n_mods} modules • {len(branches)} independent Output branches ready for parallel rendering."
            )
            self.chk_export_stems.Enable(True)
        else:
            self.single_chain_info.SetLabel(
                f"Active session: {n_mods} module{'s' if n_mods != 1 else ''}. "
                "Time chunks preserve full signal history; later chunks repeat earlier processing."
            )
            self.chk_export_stems.SetValue(False)
            self.chk_export_stems.Enable(False)

    def _on_threads_changed(self, _evt):
        n = int(self.choice_threads.GetStringSelection() or 4)
        CeciliaLib.setVar("offlineThreads", n)
        if not self.is_rendering:
            self.worker_lanes.set_thread_count(n)
        self._save_offline_prefs()

    def _on_accel_changed(self, _evt):
        idx = self.choice_accel.GetSelection()
        mode = ACCEL_LABELS[idx][1] if 0 <= idx < len(ACCEL_LABELS) else "auto"
        CeciliaLib.setVar("offlineAccelMode", mode)
        self._update_chunk_controls_enabled()
        self._save_offline_prefs()

    def _on_preroll_changed(self, _evt):
        val = float(self.spin_preroll.GetValue())
        CeciliaLib.setVar("offlinePreroll", val)
        self._save_offline_prefs()

    def _on_xfade_changed(self, _evt):
        val = float(self.spin_xfade.GetValue())
        CeciliaLib.setVar("offlineCrossfade", val)
        self._save_offline_prefs()

    def _on_xfade_shape_changed(self, _evt):
        idx = max(0, self.choice_xfade_shape.GetSelection())
        shape = XFADE_LABELS[idx][1] if 0 <= idx < len(XFADE_LABELS) else "cosine"
        CeciliaLib.setVar("offlineCrossfadeShape", shape)
        self._save_offline_prefs()

    def _update_chunk_controls_enabled(self):
        idx = self.choice_accel.GetSelection()
        mode = ACCEL_LABELS[idx][1] if 0 <= idx < len(ACCEL_LABELS) else "auto"
        en = mode in ("auto", "chunks")
        self.spin_preroll.Enable(False)
        self.spin_xfade.Enable(en)
        self.choice_xfade_shape.Enable(en)

    def _on_format_changed(self, _evt):
        ext = self.choice_format.GetStringSelection()
        CeciliaLib.setVar("offlineAudioFileType", ext)
        cur = self.single_path_ctrl.GetValue().strip()
        if cur:
            base, _ = os.path.splitext(cur)
            self.single_path_ctrl.SetValue(f"{base}.{ext}")
        # Clamp bit depth UI notice for FLAC/SD2
        if ext in ("flac", "sd2") and self.choice_bitdepth.GetSelection() > 1:
            self.choice_bitdepth.SetSelection(1)
            self._on_bitdepth_changed(None)
        self._update_module_stems_preview()
        self._save_offline_prefs()

    def _on_bitdepth_changed(self, _evt):
        idx = max(0, self.choice_bitdepth.GetSelection())
        bd_val = BIT_DEPTH_ORDER[idx][1] if 0 <= idx < len(BIT_DEPTH_ORDER) else 0
        CeciliaLib.setVar("offlineSampSize", bd_val)
        self._save_offline_prefs()

    def _on_sr_changed(self, _evt):
        try:
            sr_val = int(self.choice_sr.GetStringSelection() or 44100)
            CeciliaLib.setVar("offlineSr", sr_val)
            self._save_offline_prefs()
        except Exception:
            pass

    def _on_nchnls_changed(self, _evt):
        try:
            nchnls_val = int(self.choice_nchnls.GetStringSelection() or 2)
            CeciliaLib.setVar("offlineNchnls", nchnls_val)
            self._save_offline_prefs()
        except Exception:
            pass

    def _on_buf_changed(self, _evt):
        buf_val = self.choice_buf.GetStringSelection() or "512"
        CeciliaLib.setVar("offlineBufferSize", buf_val)
        self._save_offline_prefs()

    def _on_export_stems_toggled(self, _evt):
        en = bool(self.chk_export_stems.GetValue())
        CeciliaLib.setVar("offlineExportStems", int(en))
        self._save_offline_prefs()

    def _on_normalize_toggled(self, _evt):
        en = bool(self.chk_normalize.GetValue())
        self.txt_normalize_db.Enable(en)
        CeciliaLib.setVar("offlineNormalize", int(en))
        self._save_offline_prefs()

    def _on_normalize_changed(self, _evt):
        val_str = self.txt_normalize_db.GetValue().strip()
        try:
            val = float(val_str)
            val = min(0.0, max(-90.0, val))
            CeciliaLib.setVar("offlineNormalizeTargetDb", val)
            self._save_offline_prefs()
        except (ValueError, TypeError):
            pass

    def _persist_current_settings(self):
        if hasattr(self, "choice_threads"):
            try:
                CeciliaLib.setVar("offlineThreads", int(self.choice_threads.GetStringSelection() or 4))
            except Exception:
                pass
        if hasattr(self, "choice_accel"):
            try:
                idx = max(0, self.choice_accel.GetSelection())
                CeciliaLib.setVar("offlineAccelMode", ACCEL_LABELS[idx][1])
            except Exception:
                pass
        if hasattr(self, "spin_preroll"):
            try:
                CeciliaLib.setVar("offlinePreroll", float(self.spin_preroll.GetValue()))
            except Exception:
                pass
        if hasattr(self, "spin_xfade"):
            try:
                CeciliaLib.setVar("offlineCrossfade", float(self.spin_xfade.GetValue()))
            except Exception:
                pass
        if hasattr(self, "choice_xfade_shape"):
            try:
                idx = max(0, self.choice_xfade_shape.GetSelection())
                CeciliaLib.setVar("offlineCrossfadeShape", XFADE_LABELS[idx][1])
            except Exception:
                pass
        if hasattr(self, "choice_format"):
            try:
                CeciliaLib.setVar("offlineAudioFileType", self.choice_format.GetStringSelection())
            except Exception:
                pass
        if hasattr(self, "choice_bitdepth"):
            try:
                idx = max(0, self.choice_bitdepth.GetSelection())
                CeciliaLib.setVar("offlineSampSize", BIT_DEPTH_ORDER[idx][1])
            except Exception:
                pass
        if hasattr(self, "choice_sr"):
            try:
                CeciliaLib.setVar("offlineSr", int(self.choice_sr.GetStringSelection() or 44100))
            except Exception:
                pass
        if hasattr(self, "choice_nchnls"):
            try:
                CeciliaLib.setVar("offlineNchnls", int(self.choice_nchnls.GetStringSelection() or 2))
            except Exception:
                pass
        if hasattr(self, "choice_buf"):
            try:
                CeciliaLib.setVar("offlineBufferSize", self.choice_buf.GetStringSelection() or "512")
            except Exception:
                pass
        if hasattr(self, "chk_export_stems"):
            try:
                CeciliaLib.setVar("offlineExportStems", int(bool(self.chk_export_stems.GetValue())))
            except Exception:
                pass
        if hasattr(self, "chk_master_output"):
            try:
                CeciliaLib.setVar("offlineMasterOutput", int(bool(self.chk_master_output.GetValue())))
            except Exception:
                pass
        if hasattr(self, "chk_normalize"):
            try:
                CeciliaLib.setVar("offlineNormalize", int(bool(self.chk_normalize.GetValue())))
            except Exception:
                pass
        if hasattr(self, "txt_normalize_db"):
            try:
                val = float(self.txt_normalize_db.GetValue().strip())
                val = min(0.0, max(-90.0, val))
                CeciliaLib.setVar("offlineNormalizeTargetDb", val)
            except Exception:
                pass

    def _save_offline_prefs(self):
        try:
            self._persist_current_settings()
            CeciliaLib.writeVarToDisk()
        except Exception:
            pass

    def _on_browse_single_output(self, _evt):
        ext = self.choice_format.GetStringSelection()
        cur = self.single_path_ctrl.GetValue().strip()
        default_dir = os.path.dirname(cur) if cur else os.path.expanduser("~")
        default_file = os.path.basename(cur) if cur else f"render.{ext}"
        with wx.FileDialog(
            self,
            message="Select Offline Render Output File",
            defaultDir=default_dir,
            defaultFile=default_file,
            wildcard=f"{ext.upper()} Audio (*.{ext})|*.{ext}|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                if not path.lower().endswith(f".{ext}"):
                    path = f"{path}.{ext}"
                self.single_path_ctrl.SetValue(path)
                CeciliaLib.setVar("saveAudioFilePath", os.path.dirname(path))
                self._update_module_stems_preview()

    def _browse_dir(self, target_ctrl: wx.TextCtrl):
        cur = target_ctrl.GetValue().strip() or os.path.expanduser("~")
        with wx.DirDialog(self, "Choose Folder", defaultPath=cur, style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                target_ctrl.SetValue(dlg.GetPath())

    def _on_browse_source_folder(self, _evt):
        cur = self.folder_in_ctrl.GetValue().strip() or (
            CeciliaLib.getVar("openAudioFilePath", unicode=True) or os.path.expanduser("~")
        )
        with wx.DirDialog(self, "Choose Source Sound Folder", defaultPath=cur, style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                folder = dlg.GetPath()
                self.folder_in_ctrl.SetValue(folder)
                CeciliaLib.setVar("openAudioFilePath", folder)
                self.folder_out_ctrl.SetValue(os.path.join(folder, "cecilia_rendered"))
                self._update_folder_count()

    def _scan_valid_sounds(self, folder: str) -> List[str]:
        if not folder or not os.path.isdir(folder):
            return []
        from pyo import sndinfo

        valid = []
        for entry in sorted(os.listdir(folder)):
            if entry.startswith("."):
                continue
            full = os.path.join(folder, entry)
            if os.path.isfile(full) and sndinfo(full) is not None:
                valid.append(full)
        return valid

    def _update_folder_count(self):
        files = self._scan_valid_sounds(self.folder_in_ctrl.GetValue().strip())
        self.folder_count_lbl.SetLabel(f"{len(files)} valid audio file{'s' if len(files) != 1 else ''} found")

    def _on_use_input_sound_dur(self, _evt):
        if not CeciliaLib.session.modules:
            return
        snap = CeciliaLib.captureSession()
        for mod in snap.get("modules", []):
            if mod["id"] in snap.get("source_ids", []):
                for name, info in mod.get("settings", {}).get("userInputs", {}).items():
                    dur = float(info.get("dur" + name, 0.0) or 0.0)
                    if dur > 0:
                        self.single_dur_spin.SetValue(dur)
                        return
        CeciliaLib.showErrorDialog("No Input Sound", "Load a source sound file first to read its duration.")

    def _on_add_queue_item(self, _evt):
        if not CeciliaLib.session.modules:
            CeciliaLib.showErrorDialog("Empty Session", "Load a Cecilia module before capturing a queue item.")
            return
        snap = CeciliaLib.captureSession()
        err = self._validate_snapshot_inputs(snap)
        if err:
            CeciliaLib.showErrorDialog("Missing Sound Input", err)
            return
        ext = self.choice_format.GetStringSelection()
        raw_name = self.queue_name_ctrl.GetValue().strip() or f"variation_{len(self._queued_items) + 1:02d}"
        safe_name = "".join(c if c not in '/\\:*?"<>|' else "_" for c in raw_name)
        qdir = self.queue_dir_ctrl.GetValue().strip() or os.path.expanduser("~")
        out_path = os.path.join(qdir, f"{safe_name}.{ext}")
        dur = float(snap["output"]["totalTime"])
        mods_str = " + ".join(os.path.splitext(os.path.basename(m["module_path"]))[0] for m in snap["modules"])

        self._queued_items.append({"name": safe_name, "snapshot": snap, "output_path": out_path})
        idx = self.queue_list.InsertItem(self.queue_list.GetItemCount(), safe_name)
        self.queue_list.SetItem(idx, 1, f"{dur:.2f}s")
        self.queue_list.SetItem(idx, 2, mods_str)
        self.queue_list.SetItem(idx, 3, out_path)

        # Auto-increment variation name
        self.queue_name_ctrl.SetValue(f"variation_{len(self._queued_items) + 1:02d}")

    def _on_remove_queue_item(self, _evt):
        sel = self.queue_list.GetFirstSelected()
        if sel != -1 and 0 <= sel < len(self._queued_items):
            self._queued_items.pop(sel)
            self.queue_list.DeleteItem(sel)

    def _on_clear_queue(self, _evt):
        self._queued_items.clear()
        self.queue_list.DeleteAllItems()

    # ------------------------------------------------------------------
    # Job Building & Validation
    # ------------------------------------------------------------------

    def _validate_snapshot_inputs(self, snapshot: Dict[str, Any], allow_missing_primary: bool = False) -> Optional[str]:
        source_ids = set(snapshot.get("source_ids") or [])
        muted_ids = set(snapshot.get("muted_ids") or [])
        for idx_m, mod in enumerate(snapshot.get("modules", [])):
            if mod["id"] in muted_ids:
                continue
            uinputs = mod.get("settings", {}).get("userInputs", {})
            if not uinputs:
                continue
            for in_idx, (name, info) in enumerate(uinputs.items()):
                is_primary = in_idx == 0
                is_source = mod["id"] in source_ids
                if allow_missing_primary and is_source and is_primary:
                    continue
                required = (not is_primary) or (is_source and int(info.get("mode", 0) or 0) == 0)
                if required:
                    path = info.get("path", "")
                    if not path or not os.path.isfile(path):
                        mod_lbl = os.path.splitext(os.path.basename(mod["module_path"]))[0]
                        return f"Module '{mod_lbl}' requires a valid audio file for input '{name}'."
        return None

    def _collect_settings(self) -> RenderSettings:
        n_threads = int(self.choice_threads.GetStringSelection() or 4)
        accel_key = ACCEL_LABELS[max(0, self.choice_accel.GetSelection())][1]
        preroll = float(self.spin_preroll.GetValue())
        xfade = float(self.spin_xfade.GetValue())
        xshape = XFADE_LABELS[max(0, self.choice_xfade_shape.GetSelection())][1]
        fmt = self.choice_format.GetStringSelection()
        bd_val = BIT_DEPTH_ORDER[max(0, self.choice_bitdepth.GetSelection())][1]
        sr = int(self.choice_sr.GetStringSelection() or 44100)
        nchnls = int(self.choice_nchnls.GetStringSelection() or 2)
        buf = int(self.choice_buf.GetStringSelection() or 512)
        gfade = float(CeciliaLib.getVar("globalFade") or 0.005)

        norm_en = bool(self.chk_normalize.GetValue()) if hasattr(self, "chk_normalize") else bool(int(CeciliaLib.getVar("offlineNormalize") or 0))
        try:
            norm_db = float(self.txt_normalize_db.GetValue().strip()) if hasattr(self, "txt_normalize_db") else float(CeciliaLib.getVar("offlineNormalizeTargetDb") or -0.1)
            norm_db = min(0.0, max(-90.0, norm_db))
        except (ValueError, TypeError):
            norm_db = -0.1

        # Persist offline render preferences
        self._persist_current_settings()
        self._save_offline_prefs()

        return RenderSettings(
            sr=sr,
            nchnls=nchnls,
            buffersize=buf,
            audio_file_type=fmt,
            samp_size=bd_val,
            global_fade=gfade,
            num_threads=n_threads,
            accel_mode=accel_key,
            chunk_min_dur=float(CeciliaLib.getVar("offlineChunkMinDur") or 8.0),
            preroll=preroll,
            crossfade=xfade,
            crossfade_shape=xshape,
            export_stems=bool(self.chk_export_stems.GetValue() and self.chk_export_stems.IsEnabled()),
            normalize=norm_en,
            normalize_target_db=norm_db,
        )

    def _build_jobs(self, settings: RenderSettings) -> Optional[List[RenderJob]]:
        if not CeciliaLib.session.modules:
            CeciliaLib.showErrorDialog("No Active Module", "Open a Cecilia module or chain session first.")
            return None

        tab_idx = self.notebook.GetSelection()
        ext = settings.audio_file_type
        jobs: List[RenderJob] = []

        if tab_idx == 0:  # Single Bounce
            out_path = self.single_path_ctrl.GetValue().strip()
            if not out_path:
                CeciliaLib.showErrorDialog("Missing Output File", "Choose an output file path for Single Bounce.")
                return None
            dir_name, clean_root, master_path, clean_ext = self._split_base_and_root(out_path, ext)
            master_out = bool(self.chk_master_output.GetValue())
            module_outs = self._get_selected_module_stems(out_path, clean_ext)
            if not master_out and not module_outs:
                CeciliaLib.showErrorDialog(
                    "No Outputs Selected",
                    "Enable either the Master Mix or at least one Module Output Stem to render.",
                )
                return None

            snap = CeciliaLib.captureSession()
            err = self._validate_snapshot_inputs(snap)
            if err:
                CeciliaLib.showErrorDialog("Missing Sound Input", err)
                return None
            dur = float(self.single_dur_spin.GetValue())
            snap["output"]["totalTime"] = dur
            snap["output"]["nchnls"] = settings.nchnls
            jobs.append(
                RenderJob(
                    job_id=uuid.uuid4().hex[:8],
                    title=os.path.basename(master_path),
                    output_path=master_path,
                    snapshot=snap,
                    duration_override=dur,
                    export_stems=settings.export_stems,
                    master_output=master_out,
                    module_outputs=module_outs,
                    normalize=settings.normalize,
                    normalize_target_db=settings.normalize_target_db,
                )
            )

        elif tab_idx == 1:  # Batch Presets
            checked = [
                self.preset_checklist.GetString(i)
                for i in range(self.preset_checklist.GetCount())
                if self.preset_checklist.IsChecked(i)
            ]
            if not checked:
                CeciliaLib.showErrorDialog("No Presets Selected", "Check at least one preset to render.")
                return None
            out_dir = self.preset_dir_ctrl.GetValue().strip()
            if not out_dir:
                CeciliaLib.showErrorDialog("Missing Output Folder", "Select an output folder for Batch Presets.")
                return None
            prefix = self.preset_prefix_ctrl.GetValue().strip()
            mod_name = CeciliaLib.getVar("currentModuleName") or ""
            init_preset = CeciliaLib.getVar("initPreset")
            base_snap = CeciliaLib.captureSession()
            use_globals = bool(self.chk_preset_globals.GetValue())
            keep_snd = bool(self.chk_preset_keep_snd.GetValue())
            master_out = bool(self.chk_master_output.GetValue())

            for idx, pname in enumerate(checked):
                pdata = load_preset_dict(mod_name, pname, init_preset=init_preset) or {}
                psnap = apply_preset_to_snapshot(
                    base_snap, pdata, preset_name=pname,
                    restore_globals=use_globals, remember_sound=keep_snd,
                )
                err = self._validate_snapshot_inputs(psnap)
                if err:
                    CeciliaLib.showErrorDialog("Missing Sound Input", f"Preset '{pname}': {err}")
                    return None
                safe_p = "".join(c if c not in '/\\:*?"<>|' else "_" for c in pname)
                base_fname = f"{prefix}{idx + 1:02d}_{safe_p}"
                fpath_base = os.path.join(out_dir, f"{base_fname}.{ext}")
                dir_name, clean_root, master_path, clean_ext = self._split_base_and_root(fpath_base, ext)
                m_outs = self._get_selected_module_stems(fpath_base, clean_ext)
                jobs.append(
                    RenderJob(
                        job_id=uuid.uuid4().hex[:8],
                        title=f"{pname}",
                        output_path=master_path,
                        snapshot=psnap,
                        master_output=master_out,
                        module_outputs=m_outs,
                        normalize=settings.normalize,
                        normalize_target_db=settings.normalize_target_db,
                    )
                )

        elif tab_idx == 2:  # Batch Sound Folder
            in_dir = self.folder_in_ctrl.GetValue().strip()
            files = self._scan_valid_sounds(in_dir)
            if not files:
                CeciliaLib.showErrorDialog(
                    "No Audio Files Found",
                    "Select a source folder containing valid audio files (.wav, .aif, .flac, .ogg, etc.).",
                )
                return None
            out_dir = self.folder_out_ctrl.GetValue().strip()
            if not out_dir:
                CeciliaLib.showErrorDialog("Missing Output Folder", "Select an output folder for Batch Sound Folder.")
                return None
            suffix = self.folder_suffix_ctrl.GetValue()
            slot_sel = self.folder_input_choice.GetStringSelection()
            input_name = None if slot_sel == "(auto)" else slot_sel
            use_snd_dur = bool(self.chk_folder_snd_dur.GetValue())
            master_out = bool(self.chk_master_output.GetValue())

            base_snap = CeciliaLib.captureSession()
            err = self._validate_snapshot_inputs(base_snap, allow_missing_primary=True)
            if err:
                CeciliaLib.showErrorDialog("Missing Auxiliary Input", err)
                return None

            for fpath in files:
                stem_name = os.path.splitext(os.path.basename(fpath))[0]
                try:
                    fsnap = apply_sound_to_snapshot(
                        base_snap, fpath, input_name=input_name, use_sound_dur=use_snd_dur
                    )
                except Exception as exc:
                    CeciliaLib.showErrorDialog("Batch Input Error", str(exc))
                    return None
                base_name = f"{stem_name}{suffix}"
                fpath_base = os.path.join(out_dir, f"{base_name}.{ext}")
                if os.path.abspath(fpath_base) == os.path.abspath(fpath):
                    fpath_base = os.path.join(out_dir, f"{stem_name}_cecilia.{ext}")
                dir_name, clean_root, master_path, clean_ext = self._split_base_and_root(fpath_base, ext)
                m_outs = self._get_selected_module_stems(fpath_base, clean_ext)
                jobs.append(
                    RenderJob(
                        job_id=uuid.uuid4().hex[:8],
                        title=os.path.basename(fpath),
                        output_path=master_path,
                        snapshot=fsnap,
                        master_output=master_out,
                        module_outputs=m_outs,
                        normalize=settings.normalize,
                        normalize_target_db=settings.normalize_target_db,
                    )
                )

        else:  # Render Queue
            if not self._queued_items:
                CeciliaLib.showErrorDialog(
                    "Empty Render Queue",
                    "Click '+ Capture Current Session State' to add one or more variations to the queue first.",
                )
                return None
            qdir = self.queue_dir_ctrl.GetValue().strip() or os.path.expanduser("~")
            master_out = bool(self.chk_master_output.GetValue())
            for item in self._queued_items:
                qsnap = item["snapshot"]
                base_name = item["name"]
                fpath_base = os.path.join(qdir, f"{base_name}.{ext}")
                dir_name, clean_root, master_path, clean_ext = self._split_base_and_root(fpath_base, ext)
                m_outs = self._get_selected_module_stems(fpath_base, clean_ext)
                jobs.append(
                    RenderJob(
                        job_id=uuid.uuid4().hex[:8],
                        title=item["name"],
                        output_path=master_path,
                        snapshot=qsnap,
                        master_output=master_out,
                        module_outputs=m_outs,
                        normalize=settings.normalize,
                        normalize_target_db=settings.normalize_target_db,
                    )
                )

        return jobs

    # ------------------------------------------------------------------
    # Execution & Live Thread-Safe GUI Callbacks
    # ------------------------------------------------------------------

    def _set_controls_rendering(self, rendering: bool):
        self.btn_start.Enable(not rendering)
        self.btn_cancel.Enable(rendering)
        self.btn_sync.Enable(not rendering)
        self.notebook.Enable(not rendering)
        self.choice_threads.Enable(not rendering)
        self.choice_accel.Enable(not rendering)
        self.choice_format.Enable(not rendering)
        self.choice_bitdepth.Enable(not rendering)
        self.choice_sr.Enable(not rendering)
        self.choice_nchnls.Enable(not rendering)
        self.choice_buf.Enable(not rendering)
        if hasattr(self, "chk_normalize"):
            self.chk_normalize.Enable(not rendering)
        if hasattr(self, "txt_normalize_db"):
            self.txt_normalize_db.Enable(not rendering and (self.chk_normalize.GetValue() if hasattr(self, "chk_normalize") else True))
        if not rendering:
            self._update_chunk_controls_enabled()
        else:
            self.spin_preroll.Enable(False)
            self.spin_xfade.Enable(False)
            self.choice_xfade_shape.Enable(False)

    def on_start_render(self, _evt):
        if self.is_rendering:
            return
        audio_srv = CeciliaLib.getVar("audioServer")
        if audio_srv is not None and audio_srv.isAudioServerRunning():
            CeciliaLib.stopCeciliaSound()

        settings = self._collect_settings()
        jobs = self._build_jobs(settings)
        if not jobs:
            return

        # Reset monitor table and row map
        self.jobs_list.DeleteAllItems()
        self._list_item_map = {}
        row_counter = 0
        for idx, job in enumerate(jobs):
            dur_val = float(job.duration_override or job.snapshot["output"]["totalTime"])
            entries = []
            if job.master_output:
                title = job.title if not job.module_outputs else f"{job.title} [Master]"
                row = self.jobs_list.InsertItem(row_counter, title)
                self.jobs_list.SetItem(row, 1, "Queued")
                self.jobs_list.SetItem(row, 2, f"{dur_val:.2f}s")
                self.jobs_list.SetItem(row, 3, "--")
                self.jobs_list.SetItem(row, 4, "--")
                self.jobs_list.SetItem(row, 5, job.output_path)
                entries.append(("master", row, job.output_path))
                row_counter += 1

            for mid, mpath in job.module_outputs.items():
                stem_title = f"{os.path.basename(mpath)} [Stem]"
                row = self.jobs_list.InsertItem(row_counter, stem_title)
                self.jobs_list.SetItem(row, 1, "Queued")
                self.jobs_list.SetItem(row, 2, f"{dur_val:.2f}s")
                self.jobs_list.SetItem(row, 3, "--")
                self.jobs_list.SetItem(row, 4, "--")
                self.jobs_list.SetItem(row, 5, mpath)
                entries.append((mid, row, mpath))
                row_counter += 1

            self._list_item_map[idx] = entries

        total_rows = row_counter
        self.worker_lanes.set_thread_count(settings.num_threads)
        self.progress_bar.set_state(0.0, f"Starting {len(jobs)} job{'s' if len(jobs) != 1 else ''} ({total_rows} output file{'s' if total_rows != 1 else ''}) on {settings.num_threads} threads...")
        self._update_peak_badge(None)
        self._set_controls_rendering(True)

        # Reset main Control Panel VU peak before starting
        if CeciliaLib.getVar("interface") is not None:
            cp = CeciliaLib.getVar("interface").getControlPanel()
            if cp is not None:
                cp.resetMeter()

        self._manager = OfflineRenderManager(
            settings=settings,
            on_progress=self._on_worker_progress_bg,
            on_job_update=self._on_job_update_bg,
            on_vu=self._on_vu_bg,
            on_complete=self._on_complete_bg,
        )
        self._manager.start(jobs)

    def on_cancel_render(self, _evt):
        if self._manager is not None and self._manager.is_running:
            self.progress_bar.set_state(self.progress_bar._fraction, "Cancelling active workers...", accent="#B8860B")
            self.btn_cancel.Enable(False)
            self._manager.cancel()

    def _on_worker_progress_bg(self, ev: Dict[str, Any]):
        self._latest_progress = ev
        if not self._progress_dirty:
            self._progress_dirty = True
            wx.CallAfter(self._flush_progress_ui)

    def _flush_progress_ui(self):
        self._progress_dirty = False
        if not self or self._latest_progress is None:
            return
        ev = self._latest_progress
        frac = float(ev.get("overall_fraction", 0.0))
        done_n = int(ev.get("completed_jobs", 0))
        tot_n = int(ev.get("total_jobs", 1))
        elapsed = float(ev.get("elapsed", 0.0))
        eta = ev.get("eta")
        lbl = f"Rendering {done_n}/{tot_n} • Elapsed {_fmt_time(elapsed)} • ETA {_fmt_time(eta)}"
        memory_limit = ev.get("memory_worker_limit")
        if memory_limit is not None:
            lbl += f" • RAM budget: up to {int(memory_limit)} worker(s)"
        if self.is_rendering:
            self.progress_bar.set_state(frac, lbl, accent="#2EA043")
        self.worker_lanes.update_workers(ev.get("workers", []))
        if ev.get("peak_db") is not None:
            self._update_peak_badge(ev["peak_db"])

    def _on_job_update_bg(self, idx: int, job: RenderJob):
        snap_copy = (
            idx,
            job.status,
            job.rendered_duration,
            job.peak_db,
            job.elapsed,
            job.output_path,
            job.error,
            dict(job.module_results),
        )
        wx.CallAfter(self._apply_job_row, *snap_copy)

    def _apply_job_row(self, idx: int, status: str, dur: float, peak_db: Optional[float],
                       elapsed: float, out_path: str, error: Optional[str],
                       module_results: Optional[Dict[str, Dict[str, Any]]] = None):
        if not self:
            return
        disp_status = f"Error: {error[:40]}" if (status == "Error" and error) else status

        entries = self._list_item_map.get(idx)
        if entries:
            for kind, row_idx, target_path in entries:
                if row_idx >= self.jobs_list.GetItemCount():
                    continue
                if kind == "master":
                    self.jobs_list.SetItem(row_idx, 1, disp_status)
                    if dur > 0:
                        self.jobs_list.SetItem(row_idx, 2, f"{dur:.2f}s")
                    if peak_db is not None:
                        self.jobs_list.SetItem(row_idx, 3, f"{peak_db:+.2f} dB")
                    if elapsed > 0:
                        self.jobs_list.SetItem(row_idx, 4, f"{elapsed:.2f}s")
                    self.jobs_list.SetItem(row_idx, 5, target_path)
                else:
                    m_res = (module_results or {}).get(kind, {})
                    m_status = disp_status
                    m_dur = m_res.get("duration", dur)
                    m_peak = m_res.get("peak_db")
                    self.jobs_list.SetItem(row_idx, 1, m_status)
                    if m_dur > 0:
                        self.jobs_list.SetItem(row_idx, 2, f"{m_dur:.2f}s")
                    if m_peak is not None:
                        self.jobs_list.SetItem(row_idx, 3, f"{m_peak:+.2f} dB")
                    if elapsed > 0:
                        self.jobs_list.SetItem(row_idx, 4, f"{elapsed:.2f}s")
                    self.jobs_list.SetItem(row_idx, 5, target_path)
        else:
            if idx >= self.jobs_list.GetItemCount():
                return
            self.jobs_list.SetItem(idx, 1, disp_status)
            if dur > 0:
                self.jobs_list.SetItem(idx, 2, f"{dur:.2f}s")
            if peak_db is not None:
                self.jobs_list.SetItem(idx, 3, f"{peak_db:+.2f} dB")
            if elapsed > 0:
                self.jobs_list.SetItem(idx, 4, f"{elapsed:.2f}s")
            self.jobs_list.SetItem(idx, 5, out_path)

    def _on_vu_bg(self, rms: List[float], _peak_db: float):
        if CeciliaLib.getVar("interface") is not None:
            cp = CeciliaLib.getVar("interface").getControlPanel()
            if cp is not None and cp.vuMeter is not None:
                cp.vuMeter.setRms(*rms)

    def _update_peak_badge(self, peak_db: Optional[float]):
        if peak_db is None or peak_db <= -89.9:
            self.peak_badge.SetLabel("Peak: --.-- dB")
            self.peak_badge.SetBackgroundColour("#22252A")
            self.peak_badge.SetForegroundColour("#D0D7DE")
            return
        self.peak_badge.SetLabel(f"Peak: {peak_db:+.2f} dB")
        if peak_db > 0.0:
            self.peak_badge.SetBackgroundColour("#8B1E1E")
            self.peak_badge.SetForegroundColour("#FFFFFF")
        elif peak_db > -3.0:
            self.peak_badge.SetBackgroundColour("#7A5C12")
            self.peak_badge.SetForegroundColour("#FFFFFF")
        else:
            self.peak_badge.SetBackgroundColour("#1F5A33")
            self.peak_badge.SetForegroundColour("#FFFFFF")

    def _on_complete_bg(self, summary: RenderSummary):
        wx.CallAfter(self._apply_complete_ui, summary)

    def _apply_complete_ui(self, summary: RenderSummary):
        if not self:
            return
        self._set_controls_rendering(False)
        n_threads = int(self.choice_threads.GetStringSelection() or 4)
        self.worker_lanes.set_thread_count(n_threads)

        if summary.max_peak_db is not None:
            self._update_peak_badge(summary.max_peak_db)

        # Update main ControlPanel output file + peak label so Play/Edit/Recycle tools work immediately
        if CeciliaLib.getVar("interface") is not None:
            cp = CeciliaLib.getVar("interface").getControlPanel()
            if cp is not None and cp.vuMeter is not None:
                cp.vuMeter.amplitude = [0.0] * cp.vuMeter.nchnls
                cp.vuMeter.Refresh(False)
        done_jobs = [
            j for j in summary.jobs
            if j.status == "Done" and (
                (j.master_output and os.path.isfile(j.output_path))
                or any(os.path.isfile(p) for p in j.module_outputs.values())
            )
        ]
        if done_jobs:
            last_j = done_jobs[-1]
            if last_j.master_output and os.path.isfile(last_j.output_path):
                self._last_output_path = last_j.output_path
            elif last_j.module_outputs:
                first_stem = next((p for p in last_j.module_outputs.values() if os.path.isfile(p)), "")
                if first_stem:
                    self._last_output_path = first_stem
            if self._last_output_path:
                self.btn_play_last.Enable(True)
                CeciliaLib.setVar("outputFile", self._last_output_path)
                if CeciliaLib.getVar("interface") is not None:
                    cp = CeciliaLib.getVar("interface").getControlPanel()
                    if cp is not None:
                        cp.outputFilename = self._last_output_path
                        cp.filenameLabel.setLabel(
                            CeciliaLib.shortenName(os.path.basename(self._last_output_path), cp.charNumForLabel)
                        )
                        if summary.max_peak_db is not None and summary.max_peak_db > -89.9:
                            norm_peak = max(0.0, (summary.max_peak_db + 90.0) / 90.0)
                            if cp.vuMeter is not None:
                                cp.vuMeter.peak = norm_peak
                            cp.updatePeak(norm_peak)

        if summary.cancelled:
            self.progress_bar.set_state(
                summary.completed / max(1, len(summary.jobs)),
                f"Cancelled ({summary.completed}/{len(summary.jobs)} completed in {summary.elapsed:.2f}s)",
                accent="#9E6A03",
            )
        elif summary.failed > 0:
            first_err = next((j.error for j in summary.jobs if j.error), "Render error")
            self.progress_bar.set_state(
                summary.completed / max(1, len(summary.jobs)),
                f"Finished with {summary.failed} error(s) • {summary.completed}/{len(summary.jobs)} succeeded",
                accent="#A4262C",
            )
            CeciliaLib.showErrorDialog("Offline Render Error", first_err)
        else:
            self.progress_bar.set_state(
                1.0,
                f"Completed {summary.completed} render{'s' if summary.completed != 1 else ''} in "
                f"{summary.elapsed:.2f}s ({summary.speedup:.1f}x realtime)",
                accent="#2EA043",
            )

    def _on_play_last(self, _evt):
        if self._last_output_path and os.path.isfile(self._last_output_path):
            CeciliaLib.listenSoundfile(self._last_output_path)

    def _on_close(self, _evt):
        if self.is_rendering:
            with wx.MessageDialog(
                self,
                "An offline render is currently running. Cancel the active render and close?",
                "Offline Render in Progress",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            ) as dlg:
                if dlg.ShowModal() != wx.ID_YES:
                    return
            if self._manager is not None:
                self._manager.cancel()
        self._save_offline_prefs()
        OfflineRenderDialog._instance = None
        self.Destroy()
