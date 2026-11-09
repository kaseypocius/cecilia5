import os
import sys
import time
import shutil
import tempfile
import numpy as np

# Use /tmp as HOME so test never touches user's real ~/.cecilia5
TEST_HOME = tempfile.mkdtemp(prefix="cecilia_ui_home_")
os.environ["HOME"] = TEST_HOME

sys.path.insert(0, "/Users/kasey/Downloads/cecilia5-master")

import wx
from pyo import sndinfo
from Resources.constants import MODULES_PATH, ID_OFFLINE_RENDER
from Resources.Variables import loadBitmaps
from Resources import audio, CeciliaMainFrame, PreferencePanel, ChainUI
import Resources.CeciliaLib as CeciliaLib
from Resources.OfflineRender import _write_wav_float32


def pump_events(seconds=0.05):
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        wx.Yield()
        time.sleep(0.01)


def wait_until(predicate, timeout=30.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        pump_events(0.03)
        if predicate():
            return True
    return False


def main():
    out_dir = tempfile.mkdtemp(prefix="cecilia_ui_renders_")
    try:
        # Prepare a test input WAV
        sr = 44100
        t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
        sig = np.vstack([
            0.45 * np.sin(2 * np.pi * 220.0 * t),
            0.45 * np.sin(2 * np.pi * 330.0 * t),
        ])
        in_wav = os.path.join(out_dir, "source_tone.wav")
        _write_wav_float32(sig, in_wav, sr)

        # Boot Cecilia app components
        audioServer = audio.AudioServer()
        CeciliaLib.setVar("audioServer", audioServer)
        app = wx.App(redirect=False)

        loadBitmaps()
        wx.Log.SetLogLevel(0)
        CeciliaLib.setVar("numDisplays", 1)
        CeciliaLib.setVar("displayOffset", [(0, 0)])
        CeciliaLib.setVar("displaySize", [(1440, 900)])

        main_frame = CeciliaMainFrame.CeciliaMainFrame(None, -1)
        CeciliaLib.setVar("mainFrame", main_frame)
        app.SetTopWindow(main_frame)

        def mock_show_error(title, msg):
            print(f"[ERROR DIALOG] {title}: {msg}")
        CeciliaLib.showErrorDialog = mock_show_error

        # 1. Open StochGrains.c5 (synthesis module)
        stoch_path = os.path.join(MODULES_PATH, "Synthesis", "StochGrains.c5")
        main_frame.onOpen(stoch_path, True)
        pump_events(0.1)

        interface = CeciliaLib.getVar("interface")
        assert interface is not None, "CeciliaInterface failed to open"
        cp = interface.getControlPanel()
        assert hasattr(cp, "offlineRenderBtn"), "ControlPanel missing offlineRenderBtn"
        assert cp.offlineRenderBtn.IsEnabled(), "offlineRenderBtn should be enabled when module is loaded"

        # Verify Action menu has ID_OFFLINE_RENDER
        menu_item = interface.menubar.actionMenu.FindItemById(ID_OFFLINE_RENDER)
        assert menu_item is not None, "Action menu missing ID_OFFLINE_RENDER"
        print("[PASS] 1. CeciliaInterface + ControlPanel button + Action menu item initialized")

        # 2. Test PreferenceFrame offline export controls
        prefs = PreferencePanel.PreferenceFrame(interface)
        prefs.onPageChange(3)  # Export tab
        pump_events(0.05)
        prefs.changeOfflineThreads(0, "4")
        prefs.changeOfflineAccelMode(0, "auto")
        prefs.changeOfflinePreroll(0, "0.25")
        prefs.changeOfflineCrossfade(0, "0.05")
        assert CeciliaLib.getVar("offlineThreads") == 4
        assert CeciliaLib.getVar("offlinePreroll") == 0.25
        assert CeciliaLib.getVar("offlineCrossfade") == 0.05
        prefs.onClose()
        pump_events(0.05)
        print("[PASS] 2. PreferenceFrame Offline Render settings verified")

        # 3. Open OfflineRenderDialog via CeciliaLib helper & verify mode switching
        dlg = CeciliaLib.openOfflineRenderDialog(mode="single")
        pump_events(0.05)
        assert dlg.notebook.GetSelection() == 0

        dlg.select_mode("presets")
        assert dlg.notebook.GetSelection() == 1
        assert dlg.preset_checklist.GetCount() >= 1  # at least 'init'

        dlg.select_mode("folder")
        assert dlg.notebook.GetSelection() == 2

        dlg.select_mode("queue")
        assert dlg.notebook.GetSelection() == 3

        # 4. Run a Single Bounce (multithreaded chunks) through OfflineRenderDialog
        dlg.select_mode("single")
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)
        single_out = os.path.join(out_dir, "ui_single_bounce.wav")
        dlg.single_path_ctrl.SetValue(single_out)
        dlg.single_dur_spin.SetValue(2.5)
        dlg.choice_threads.SetStringSelection("3")
        dlg._on_threads_changed(None)
        dlg.choice_accel.SetSelection(3)  # chunks
        dlg._on_accel_changed(None)

        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Single bounce timed out"
        assert os.path.isfile(single_out), f"Expected output file {single_out}"
        info = sndinfo(single_out)
        assert abs(info[1] - 2.5) < 0.02, f"Expected 2.5s duration, got {info[1]}"
        assert cp.outputFilename == single_out, f"ControlPanel outputFilename not synced: {cp.outputFilename}"
        peak_txt = cp.peakLabel.label
        assert "dB" in peak_txt and peak_txt != "-90.00 dB", f"Unexpected PeakLabel text: {peak_txt}"
        print(f"[PASS] 3. UI Single Bounce (3-thread chunks) -> {info[0]} frames, PeakLabel='{peak_txt}'")

        # 4b. Test Batch Presets tab render
        dlg.select_mode("presets")
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)
        p_out_dir = os.path.join(out_dir, "presets_out")
        dlg.preset_dir_ctrl.SetValue(p_out_dir)
        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Batch presets timed out"
        rendered_p = sorted(os.listdir(p_out_dir))
        assert len(rendered_p) >= 1, f"Expected at least 1 rendered preset, got {rendered_p}"
        print(f"[PASS] 3b. UI Batch Presets -> {rendered_p}")

        # 5. Test Render Queue with 2 captured variations running in parallel
        dlg.select_mode("queue")
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)
        dlg.choice_accel.SetSelection(0)  # auto
        dlg._on_accel_changed(None)
        cp.setTotalTime(1.0)
        dlg._on_add_queue_item(None)
        cp.gainSlider.SetValue(-6.0)
        CeciliaLib.setVar("gainSlider", cp.gainSlider)
        dlg._on_add_queue_item(None)
        assert len(dlg._queued_items) == 2
        q_out_dir = os.path.join(out_dir, "queue_out")
        dlg.queue_dir_ctrl.SetValue(q_out_dir)

        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Render queue timed out"
        rendered_q = sorted(os.listdir(q_out_dir))
        assert len(rendered_q) == 2, f"Expected 2 queue files, got {rendered_q}"
        print(f"[PASS] 4. UI Parallel Render Queue -> {rendered_q}")

        # 6. Test 2-branch Chain UI + Stem Export through OfflineRenderDialog
        harm_path = os.path.join(MODULES_PATH, "Pitch", "Harmonizer.c5")
        added = CeciliaLib.openCeciliaFile(interface, openfile=harm_path, builtin=True, replace=False, new_session=False)
        assert added, "Failed to add Harmonizer.c5 to chain"
        inst2 = CeciliaLib.session.modules[-1]
        CeciliaLib.session.set_source(inst2, True)
        CeciliaLib.session.connect(inst2.id, None)
        ChainUI.refresh(interface)
        ChainUI.select(interface, inst2)
        pump_events(0.1)
        assert inst2.inputs.cfileinList, "Harmonizer should have cfilein"
        with CeciliaLib.instance_context(inst2):
            inst2.inputs.cfileinList[0].onLoadFile(in_wav)
        pump_events(0.05)

        # 6a. Test Individual Module Stems Selection, Routing Graph Badges & Quick Buttons
        dlg.sync_from_session()
        dlg.select_mode("single")
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)

        assert dlg.module_checklist.GetCount() == 2, f"Expected 2 modules in checklist, got {dlg.module_checklist.GetCount()}"
        # Test Quick Button: Select All
        dlg._set_all_module_stems(True)
        assert len(CeciliaLib.session.offline_stem_ids) == 2, "Both modules should be in session.offline_stem_ids"
        assert dlg.module_checklist.IsChecked(0) and dlg.module_checklist.IsChecked(1)
        # Test Quick Button: Select None
        dlg._set_all_module_stems(False)
        assert len(CeciliaLib.session.offline_stem_ids) == 0, "session.offline_stem_ids should be empty"
        assert not dlg.module_checklist.IsChecked(0) and not dlg.module_checklist.IsChecked(1)

        # Test RoutingGraph toggle_offline_stem
        rg = getattr(interface, "grid", None)
        assert rg is not None, "interface.grid (RoutingGraph) not found"
        inst1 = CeciliaLib.session.modules[0]
        rg.toggle_offline_stem(inst1.id)
        assert inst1.id in CeciliaLib.session.offline_stem_ids, "inst1 should be in offline_stem_ids after graph toggle"
        dlg.sync_from_session()
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)
        assert dlg.module_checklist.IsChecked(0), "Dialog checklist should be checked for inst1 after graph toggle"
        print("[PASS] 5a. Individual Module Stem toggles & RoutingGraph badge sync verified")

        # Select both module stems for rendering
        dlg._set_all_module_stems(True)
        dlg.chk_master_output.SetValue(True)
        dlg.chk_export_stems.SetValue(False)  # test individual module stems specifically
        mod_stems_in = os.path.join(out_dir, "test_stems.wav")
        mod_stems_master = os.path.join(out_dir, "test_stems_Master.wav")
        dlg.single_path_ctrl.SetValue(mod_stems_in)
        dlg.single_dur_spin.SetValue(1.5)

        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Module stems render timed out"

        stem_file1 = os.path.join(out_dir, "test_stems_StochGrains.wav")
        stem_file2 = os.path.join(out_dir, "test_stems_Harmonizer.wav")
        print("Files in out_dir:", sorted(os.listdir(out_dir)))
        assert os.path.isfile(mod_stems_master), f"Missing master mix file {mod_stems_master}"
        assert os.path.isfile(stem_file1), f"Missing module stem 1 file {stem_file1}"
        assert os.path.isfile(stem_file2), f"Missing module stem 2 file {stem_file2}"

        info_m = sndinfo(mod_stems_master)
        info_s1 = sndinfo(stem_file1)
        info_s2 = sndinfo(stem_file2)
        assert abs(info_m[1] - 1.5) < 0.05, f"Master dur {info_m[1]} != 1.5"
        assert abs(info_s1[1] - 1.5) < 0.05, f"Stem 1 dur {info_s1[1]} != 1.5"
        assert abs(info_s2[1] - 1.5) < 0.05, f"Stem 2 dur {info_s2[1]} != 1.5"
        assert info_m[0] == info_s1[0] == info_s2[0], "Sample frame counts should match exactly across all stems"
        print(f"[PASS] 5b. Multi-Module Stem Rendering (Master + StochGrains + Harmonizer) -> {info_m[0]} frames each")

        # 6b. Test Render with Master Output DISABLED (Module Stems Only)
        dlg.chk_master_output.SetValue(False)
        stems_only_in = os.path.join(out_dir, "stems_only_render.wav")
        stems_only_master = os.path.join(out_dir, "stems_only_render_Master.wav")
        dlg.single_path_ctrl.SetValue(stems_only_in)
        dlg.single_dur_spin.SetValue(1.0)
        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Stems-only render timed out"

        assert not os.path.isfile(stems_only_master), "Master output file should NOT exist when Master Mix is unchecked"
        only_stem1 = os.path.join(out_dir, "stems_only_render_StochGrains.wav")
        only_stem2 = os.path.join(out_dir, "stems_only_render_Harmonizer.wav")
        assert os.path.isfile(only_stem1), f"Stem 1 {only_stem1} missing in stems-only mode"
        assert os.path.isfile(only_stem2), f"Stem 2 {only_stem2} missing in stems-only mode"
        assert dlg.btn_play_last.IsEnabled(), "Play Last Render button should be enabled from stem file"
        print("[PASS] 5c. Stems-only rendering (Master disabled) verified")

        # 6c. Test 2-branch Chain Parallel Render
        dlg.chk_master_output.SetValue(True)
        dlg._set_all_module_stems(False)
        dlg.chk_export_stems.SetValue(True)
        chain_out = os.path.join(out_dir, "chain_master.wav")
        dlg.single_path_ctrl.SetValue(chain_out)
        dlg.single_dur_spin.SetValue(1.2)

        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Chain branch render timed out"
        assert os.path.isfile(chain_out), "Missing master chain output"
        stem_files = sorted(f for f in os.listdir(out_dir) if f.startswith("chain_master_branch_"))
        assert len(stem_files) == 2, f"Expected 2 branch stem files, got {stem_files}"
        print(f"[PASS] 5d. UI 2-Branch Chain Parallel Render + Stems -> {stem_files}")

        # 7. Test Batch Sound Folder tab render with Harmonizer source
        dlg.select_mode("folder")
        dlg.choice_format.SetStringSelection("wav")
        dlg._on_format_changed(None)
        snd_in_dir = os.path.join(out_dir, "sounds_in")
        os.makedirs(snd_in_dir, exist_ok=True)
        for i, fhz in enumerate([220.0, 440.0]):
            tone = np.vstack([0.3 * np.sin(2 * np.pi * fhz * t[:int(sr * 0.5)])] * 2)
            _write_wav_float32(tone, os.path.join(snd_in_dir, f"tone_{i}.wav"), sr)
        dlg.folder_in_ctrl.SetValue(snd_in_dir)
        dlg._update_folder_count()
        f_out_dir = os.path.join(out_dir, "folder_out")
        dlg.folder_out_ctrl.SetValue(f_out_dir)
        dlg.on_start_render(None)
        ok = wait_until(lambda: not dlg.is_rendering, timeout=30.0)
        pump_events(0.1)
        assert ok, "Batch sound folder timed out"
        rendered_f = sorted(os.listdir(f_out_dir))
        master_f = [f for f in rendered_f if "_branch_" not in f]
        assert len(master_f) == 2, f"Expected 2 master rendered sounds, got {master_f}"
        print(f"[PASS] 6. UI Batch Sound Folder -> {master_f} (+ {len(rendered_f) - len(master_f)} branch stems)")

        # Clean teardown
        dlg._on_close(None)
        pump_events(0.05)
        main_frame.closeInterface()
        main_frame.Destroy()
        pump_events(0.05)
        print("ALL UI + ENGINE INTEGRATION TESTS PASSED!")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(TEST_HOME, ignore_errors=True)


import unittest

@unittest.skipUnless(os.environ.get("CECILIA_GUI_TESTS") == "1", "Requires CECILIA_GUI_TESTS=1, wx, pyo and a display")
class OfflineUITests(unittest.TestCase):
    def test_offline_ui_integration(self):
        main()


if __name__ == "__main__":
    if os.environ.get("CECILIA_GUI_TESTS") == "1":
        main()
    else:
        unittest.main()
