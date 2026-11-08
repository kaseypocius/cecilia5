import os
import sys
import tempfile
import unittest

# Redirect HOME to temp directory so test runs inside sandbox without touching real ~/.cecilia5
TEST_HOME = tempfile.mkdtemp(prefix="cecilia_test_home_")
os.environ["HOME"] = TEST_HOME

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Resources import Variables as vars
import Resources.CeciliaLib as CeciliaLib
from Resources.constants import APP_VERSION
from Resources.OfflineRender import RenderSettings


class OfflinePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cecilia_pref_test_")
        self.pref_file = os.path.join(self.tmp_dir, "ceciliaPrefs.txt")
        self.orig_pref_file = vars.PREFERENCES_FILE
        vars.PREFERENCES_FILE = self.pref_file

    def tearDown(self):
        vars.PREFERENCES_FILE = self.orig_pref_file
        if os.path.exists(self.tmp_dir):
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_prefs_file_round_trip(self):
        """Test that all offline render settings serialize to and deserialize from ceciliaPrefs.txt with exact types."""
        # Setup distinct custom offline settings
        vars.CeciliaVar['offlineSr'] = 96000
        vars.CeciliaVar['offlineNchnls'] = 6
        vars.CeciliaVar['offlineBufferSize'] = '1024'
        vars.CeciliaVar['offlineAudioFileType'] = 'flac'
        vars.CeciliaVar['offlineSampSize'] = 1  # 24-bit int
        vars.CeciliaVar['offlineThreads'] = 7
        vars.CeciliaVar['offlineAccelMode'] = 'branches'
        vars.CeciliaVar['offlineChunkMinDur'] = 12.5
        vars.CeciliaVar['offlinePreroll'] = 0.75
        vars.CeciliaVar['offlineCrossfade'] = 0.25
        vars.CeciliaVar['offlineCrossfadeShape'] = 'equal_power'
        vars.CeciliaVar['offlineExportStems'] = 1
        vars.CeciliaVar['offlineMasterOutput'] = 0
        vars.CeciliaVar['offlineNormalize'] = 1
        vars.CeciliaVar['offlineNormalizeTargetDb'] = -1.5

        # Save to disk
        vars.writeCeciliaPrefsToFile()
        self.assertTrue(os.path.isfile(self.pref_file), "Preferences file was not created on disk")

        # Verify disk contents contains all keys
        with open(self.pref_file, 'rt') as f:
            content = f.read()

        for key in [
            'offlineSr=96000',
            'offlineNchnls=6',
            'offlineBufferSize=1024',
            'offlineAudioFileType=flac',
            'offlineSampSize=1',
            'offlineThreads=7',
            'offlineAccelMode=branches',
            'offlineChunkMinDur=12.5',
            'offlinePreroll=0.75',
            'offlineCrossfade=0.25',
            'offlineCrossfadeShape=equal_power',
            'offlineExportStems=1',
            'offlineMasterOutput=0',
            'offlineNormalize=1',
            'offlineNormalizeTargetDb=-1.5',
        ]:
            self.assertIn(key, content, f"Expected {key} in preferences file")

        # Clear in-memory offline vars
        for k in [
            'offlineSr', 'offlineNchnls', 'offlineBufferSize', 'offlineAudioFileType',
            'offlineSampSize', 'offlineThreads', 'offlineAccelMode', 'offlineChunkMinDur',
            'offlinePreroll', 'offlineCrossfade', 'offlineCrossfadeShape',
            'offlineExportStems', 'offlineMasterOutput', 'offlineNormalize', 'offlineNormalizeTargetDb'
        ]:
            if k in vars.CeciliaVar:
                del vars.CeciliaVar[k]

        # Read back from file
        vars.readCeciliaPrefsFromFile()

        self.assertEqual(vars.CeciliaVar['offlineSr'], 96000)
        self.assertEqual(vars.CeciliaVar['offlineNchnls'], 6)
        self.assertEqual(vars.CeciliaVar['offlineBufferSize'], '1024')
        self.assertEqual(vars.CeciliaVar['offlineAudioFileType'], 'flac')
        self.assertEqual(vars.CeciliaVar['offlineSampSize'], 1)
        self.assertEqual(vars.CeciliaVar['offlineThreads'], 7)
        self.assertEqual(vars.CeciliaVar['offlineAccelMode'], 'branches')
        self.assertEqual(vars.CeciliaVar['offlineChunkMinDur'], 12.5)
        self.assertEqual(vars.CeciliaVar['offlinePreroll'], 0.75)
        self.assertEqual(vars.CeciliaVar['offlineCrossfade'], 0.25)
        self.assertEqual(vars.CeciliaVar['offlineCrossfadeShape'], 'equal_power')
        self.assertEqual(vars.CeciliaVar['offlineExportStems'], 1)
        self.assertEqual(vars.CeciliaVar['offlineMasterOutput'], 0)
        self.assertEqual(vars.CeciliaVar['offlineNormalize'], 1)
        self.assertEqual(vars.CeciliaVar['offlineNormalizeTargetDb'], -1.5)

    def test_legacy_prefs_backward_compatibility(self):
        """Older preferences files without offline settings should load safely with fallback defaults."""
        legacy_content = (
            f"version={APP_VERSION}\n"
            "sr=48000\n"
            "defaultNchnls=4\n"
            "bufferSize=256\n"
            "audioFileType=aif\n"
            "sampSize=2\n"
            "defaultTotalTime=60.0\n"
            "globalFade=0.01\n"
            "interfaceSize=(1000, 700)\n"
            "interfacePosition=(50, 50)\n"
        )
        with open(self.pref_file, "wt") as f:
            f.write(legacy_content)

        # Clear in-memory offline keys
        for k in ['offlineSr', 'offlineNchnls', 'offlineBufferSize', 'offlineAudioFileType',
                  'offlineSampSize', 'offlineExportStems', 'offlineMasterOutput',
                  'offlineNormalize', 'offlineNormalizeTargetDb']:
            if k in vars.CeciliaVar:
                del vars.CeciliaVar[k]

        vars.readCeciliaPrefsFromFile()

        # Should fall back to legacy DAC/session values or safe defaults
        self.assertEqual(vars.CeciliaVar['offlineSr'], 48000)
        self.assertEqual(vars.CeciliaVar['offlineNchnls'], 4)
        self.assertEqual(vars.CeciliaVar['offlineBufferSize'], '256')
        self.assertEqual(vars.CeciliaVar['offlineAudioFileType'], 'aif')
        self.assertEqual(vars.CeciliaVar['offlineSampSize'], 2)
        self.assertEqual(vars.CeciliaVar['offlineMasterOutput'], 1)
        self.assertEqual(vars.CeciliaVar['offlineExportStems'], 0)
        self.assertEqual(vars.CeciliaVar['offlineNormalize'], 0)
        self.assertEqual(vars.CeciliaVar['offlineNormalizeTargetDb'], -0.1)

    def test_dac_and_offline_independence(self):
        """Changing live audio DAC settings must not overwrite offline export preferences."""
        vars.CeciliaVar['sr'] = 44100
        vars.CeciliaVar['nchnls'] = 2
        vars.CeciliaVar['bufferSize'] = '512'
        vars.CeciliaVar['audioFileType'] = 'wav'

        vars.CeciliaVar['offlineSr'] = 96000
        vars.CeciliaVar['offlineNchnls'] = 8
        vars.CeciliaVar['offlineBufferSize'] = '2048'
        vars.CeciliaVar['offlineAudioFileType'] = 'flac'

        # Simulate DAC server restart or device change
        CeciliaLib.setVar('sr', 48000)
        CeciliaLib.setVar('nchnls', 4)
        CeciliaLib.setVar('bufferSize', '256')

        # Offline settings should remain isolated
        self.assertEqual(CeciliaLib.getVar('offlineSr'), 96000)
        self.assertEqual(CeciliaLib.getVar('offlineNchnls'), 8)
        self.assertEqual(CeciliaLib.getVar('offlineBufferSize'), '2048')
        self.assertEqual(CeciliaLib.getVar('offlineAudioFileType'), 'flac')

    def test_preference_panel_offline_handlers(self):
        """PreferencePanel handlers should update offline settings and write to disk."""
        from Resources import PreferencePanel

        # Mock frame-like instance or test handlers directly
        class MockPrefFrame:
            changeOfflineSr = PreferencePanel.PreferenceFrame.changeOfflineSr
            changeOfflineNchnls = PreferencePanel.PreferenceFrame.changeOfflineNchnls
            changeOfflineBufferSize = PreferencePanel.PreferenceFrame.changeOfflineBufferSize
            changeOfflineThreads = PreferencePanel.PreferenceFrame.changeOfflineThreads
            changeOfflineAccelMode = PreferencePanel.PreferenceFrame.changeOfflineAccelMode
            changeOfflinePreroll = PreferencePanel.PreferenceFrame.changeOfflinePreroll
            changeOfflineCrossfade = PreferencePanel.PreferenceFrame.changeOfflineCrossfade
            changeOfflineNormalize = PreferencePanel.PreferenceFrame.changeOfflineNormalize
            changeFileType = PreferencePanel.PreferenceFrame.changeFileType
            changeSampSize = PreferencePanel.PreferenceFrame.changeSampSize

        mock = MockPrefFrame()
        mock.changeOfflineSr(0, "88200")
        mock.changeOfflineNchnls(0, "6")
        mock.changeOfflineBufferSize(0, "1024")
        mock.changeOfflineThreads(0, "5")
        mock.changeOfflineAccelMode(0, "chunks")
        mock.changeOfflinePreroll(0, "0.3")
        mock.changeOfflineCrossfade(0, "0.15")
        mock.changeOfflineNormalize(0, "-1.0 dB")
        mock.changeFileType(0, "ogg")
        mock.changeSampSize(0, "24 bits int")

        self.assertEqual(CeciliaLib.getVar('offlineSr'), 88200)
        self.assertEqual(CeciliaLib.getVar('offlineNchnls'), 6)
        self.assertEqual(CeciliaLib.getVar('offlineBufferSize'), '1024')
        self.assertEqual(CeciliaLib.getVar('offlineThreads'), 5)
        self.assertEqual(CeciliaLib.getVar('offlineAccelMode'), 'chunks')
        self.assertEqual(CeciliaLib.getVar('offlinePreroll'), 0.3)
        self.assertEqual(CeciliaLib.getVar('offlineCrossfade'), 0.15)
        self.assertEqual(CeciliaLib.getVar('offlineNormalize'), 1)
        self.assertEqual(CeciliaLib.getVar('offlineNormalizeTargetDb'), -1.0)
        self.assertEqual(CeciliaLib.getVar('offlineAudioFileType'), 'ogg')
        self.assertEqual(CeciliaLib.getVar('offlineSampSize'), 1)

        mock.changeOfflineNormalize(0, "Disabled")
        self.assertEqual(CeciliaLib.getVar('offlineNormalize'), 0)

    def test_dialog_sync_and_persistence_logic(self):
        """Test dialog persist and sync logic with mocked UI controls."""
        from Resources import OfflineRenderDialog

        # Set initial offline settings
        CeciliaLib.setVar('offlineSr', 96000)
        CeciliaLib.setVar('offlineNchnls', 6)
        CeciliaLib.setVar('offlineBufferSize', '2048')
        CeciliaLib.setVar('offlineAudioFileType', 'flac')
        CeciliaLib.setVar('offlineSampSize', 3)
        CeciliaLib.setVar('offlineThreads', 8)
        CeciliaLib.setVar('offlineAccelMode', 'chunks')
        CeciliaLib.setVar('offlinePreroll', 0.8)
        CeciliaLib.setVar('offlineCrossfade', 0.2)
        CeciliaLib.setVar('offlineCrossfadeShape', 'equal_power')
        CeciliaLib.setVar('offlineExportStems', 1)
        CeciliaLib.setVar('offlineMasterOutput', 0)

        # Mock controls
        class MockChoice:
            def __init__(self, val, choices):
                self._val = val
                self._choices = choices
                self._sel = choices.index(val) if val in choices else 0
            def GetStringSelection(self): return self._val
            def SetStringSelection(self, v):
                self._val = v
                if v in self._choices:
                    self._sel = self._choices.index(v)
            def GetSelection(self): return self._sel
            def SetSelection(self, idx):
                self._sel = idx
                if 0 <= idx < len(self._choices):
                    self._val = self._choices[idx]
            def FindString(self, s):
                return self._choices.index(s) if s in self._choices else -1
            def Enable(self, en): pass

        class MockSpin:
            def __init__(self, val): self._val = float(val)
            def GetValue(self): return self._val
            def SetValue(self, v): self._val = float(v)
            def Enable(self, en): pass

        class MockCheck:
            def __init__(self, val): self._val = bool(val)
            def GetValue(self): return self._val
            def SetValue(self, v): self._val = bool(v)
            def IsEnabled(self): return True

        class MockTextCtrl:
            def __init__(self, val=""): self._val = str(val)
            def GetValue(self): return self._val
            def SetValue(self, v): self._val = str(v)
            def Enable(self, en): pass

        class MockDialog:
            is_rendering = False
            _build_jobs = OfflineRenderDialog.OfflineRenderDialog._build_jobs
            _collect_settings = OfflineRenderDialog.OfflineRenderDialog._collect_settings
            _persist_current_settings = OfflineRenderDialog.OfflineRenderDialog._persist_current_settings
            _save_offline_prefs = OfflineRenderDialog.OfflineRenderDialog._save_offline_prefs
            _update_chunk_controls_enabled = OfflineRenderDialog.OfflineRenderDialog._update_chunk_controls_enabled
            sync_from_session = OfflineRenderDialog.OfflineRenderDialog.sync_from_session
            _refresh_preset_list = lambda self: None
            _refresh_input_slots = lambda self: None
            _refresh_chain_branch_status = lambda self: None
            _refresh_module_stems_list = lambda self: None

            def __init__(self):
                self.single_dur_spin = MockSpin(30.0)
                self.single_path_ctrl = MockTextCtrl("")
                self.preset_dir_ctrl = MockTextCtrl("")
                self.preset_prefix_ctrl = MockTextCtrl("")
                self.folder_out_ctrl = MockTextCtrl("")
                self.queue_dir_ctrl = MockTextCtrl("")
                self.choice_format = MockChoice("flac", OfflineRenderDialog.FORMAT_ORDER)
                self.choice_bitdepth = MockChoice("32 bits float", [lbl for lbl, _ in OfflineRenderDialog.BIT_DEPTH_ORDER])
                self.choice_sr = MockChoice("96000", OfflineRenderDialog.SAMPLE_RATES)
                self.choice_nchnls = MockChoice("6", [str(x) for x in range(1, 37)])
                self.choice_buf = MockChoice("2048", OfflineRenderDialog.BUFFER_SIZES)
                self.choice_threads = MockChoice("8", [str(x) for x in range(1, 33)])
                self.choice_accel = MockChoice("Time-Chunked (Overlap-Crossfade)", [lbl for lbl, _ in OfflineRenderDialog.ACCEL_LABELS])
                self.spin_preroll = MockSpin(0.8)
                self.spin_xfade = MockSpin(0.2)
                self.choice_xfade_shape = MockChoice("Equal-Power (Uncorrelated)", [lbl for lbl, _ in OfflineRenderDialog.XFADE_LABELS])
                self.chk_export_stems = MockCheck(True)
                self.chk_master_output = MockCheck(False)
                self.chk_normalize = MockCheck(True)
                self.txt_normalize_db = MockTextCtrl("-1.0")

        dlg = MockDialog()

        # 1. Test _collect_settings returns expected RenderSettings dataclass
        settings = dlg._collect_settings()
        self.assertEqual(settings.sr, 96000)
        self.assertEqual(settings.nchnls, 6)
        self.assertEqual(settings.buffersize, 2048)
        self.assertEqual(settings.audio_file_type, 'flac')
        self.assertEqual(settings.samp_size, 3)
        self.assertEqual(settings.num_threads, 8)
        self.assertEqual(settings.accel_mode, 'chunks')
        self.assertEqual(settings.preroll, 0.8)
        self.assertEqual(settings.crossfade, 0.2)
        self.assertEqual(settings.crossfade_shape, 'equal_power')
        self.assertTrue(settings.export_stems)
        self.assertTrue(settings.normalize)
        self.assertEqual(settings.normalize_target_db, -1.0)

        # 2. Modify UI controls in dialog
        dlg.choice_sr.SetStringSelection("48000")
        dlg.choice_nchnls.SetStringSelection("4")
        dlg.choice_buf.SetStringSelection("1024")
        dlg.choice_threads.SetStringSelection("4")
        dlg.choice_format.SetStringSelection("wav")
        dlg.choice_bitdepth.SetSelection(1)  # 24-bit int
        dlg.spin_preroll.SetValue(0.4)
        dlg.spin_xfade.SetValue(0.08)
        dlg.chk_export_stems.SetValue(False)
        dlg.chk_master_output.SetValue(True)
        dlg.chk_normalize.SetValue(False)
        dlg.txt_normalize_db.SetValue("-3.0")

        dlg._persist_current_settings()
        vars.writeCeciliaPrefsToFile()

        # Check that CeciliaVar got updated
        self.assertEqual(CeciliaLib.getVar('offlineSr'), 48000)
        self.assertEqual(CeciliaLib.getVar('offlineNchnls'), 4)
        self.assertEqual(CeciliaLib.getVar('offlineBufferSize'), '1024')
        self.assertEqual(CeciliaLib.getVar('offlineThreads'), 4)
        self.assertEqual(CeciliaLib.getVar('offlineAudioFileType'), 'wav')
        self.assertEqual(CeciliaLib.getVar('offlineSampSize'), 1)
        self.assertEqual(CeciliaLib.getVar('offlinePreroll'), 0.4)
        self.assertEqual(CeciliaLib.getVar('offlineCrossfade'), 0.08)
        self.assertEqual(CeciliaLib.getVar('offlineExportStems'), 0)
        self.assertEqual(CeciliaLib.getVar('offlineMasterOutput'), 1)
        self.assertEqual(CeciliaLib.getVar('offlineNormalize'), 0)
        self.assertEqual(CeciliaLib.getVar('offlineNormalizeTargetDb'), -3.0)

        # 3. Test sync_from_session retains offline settings and does NOT revert to DAC settings
        CeciliaLib.setVar('sr', 44100)
        CeciliaLib.setVar('nchnls', 2)
        CeciliaLib.setVar('bufferSize', '512')
        CeciliaLib.setVar('audioFileType', 'aif')
        CeciliaLib.setVar('sampSize', 0)

        # Call sync_from_session
        dlg.sync_from_session()

        self.assertEqual(dlg.choice_sr.GetStringSelection(), "48000")
        self.assertEqual(dlg.choice_nchnls.GetStringSelection(), "4")
        self.assertEqual(dlg.choice_buf.GetStringSelection(), "1024")
        self.assertEqual(dlg.choice_format.GetStringSelection(), "wav")
        self.assertEqual(dlg.choice_bitdepth.GetSelection(), 1)
        self.assertFalse(dlg.chk_export_stems.GetValue())
        self.assertTrue(dlg.chk_master_output.GetValue())
        self.assertFalse(dlg.chk_normalize.GetValue())
        self.assertEqual(dlg.txt_normalize_db.GetValue(), "-3.0")

    def test_offline_naming_scheme(self):
        """Test the Final_Master.wav and Final_Delay.wav naming convention for master and stems."""
        from Resources.OfflineRenderDialog import OfflineRenderDialog
        import types

        # 1. Test _split_base_and_root helper
        class DummyDialog:
            _split_base_and_root = OfflineRenderDialog._split_base_and_root
            _get_selected_module_stems = OfflineRenderDialog._get_selected_module_stems
            _get_master_output_path = OfflineRenderDialog._get_master_output_path

        dlg_helper = DummyDialog()

        d, root, master_p, ext = dlg_helper._split_base_and_root("/test/path/Final.wav", "wav")
        self.assertEqual(root, "Final")
        self.assertEqual(os.path.basename(master_p), "Final_Master.wav")
        self.assertEqual(ext, "wav")

        d, root, master_p, ext = dlg_helper._split_base_and_root("/test/path/Final_Master.wav", "wav")
        self.assertEqual(root, "Final")
        self.assertEqual(os.path.basename(master_p), "Final_Master.wav")
        self.assertEqual(ext, "wav")

        d, root, master_p, ext = dlg_helper._split_base_and_root("/test/path/Final_master.aif", "aif")
        self.assertEqual(root, "Final")
        self.assertEqual(os.path.basename(master_p), "Final_Master.aif")
        self.assertEqual(ext, "aif")

        d, root, master_p, ext = dlg_helper._split_base_and_root("/test/path/Final", "flac")
        self.assertEqual(root, "Final")
        self.assertEqual(os.path.basename(master_p), "Final_Master.flac")
        self.assertEqual(ext, "flac")

        # 2. Test _get_selected_module_stems with mock modules
        class MockCheckList:
            def __init__(self, checked_mask):
                self._mask = checked_mask
            def GetCount(self): return len(self._mask)
            def IsChecked(self, i): return self._mask[i]

        class MockSession:
            def __init__(self, modules):
                self.modules = modules
            def get_module(self, mid):
                return next((m for m in self.modules if m.id == mid), None)

        mod1 = types.SimpleNamespace(id="m1", path="/path/Delay.c5", name="Delay")
        mod2 = types.SimpleNamespace(id="m2", path="/path/Filter.c5", name="Filter")
        orig_session = getattr(CeciliaLib, "session", None)
        CeciliaLib.session = MockSession([mod1, mod2])

        try:
            class DummyDialog:
                _split_base_and_root = OfflineRenderDialog._split_base_and_root
                _get_selected_module_stems = OfflineRenderDialog._get_selected_module_stems
                _get_master_output_path = OfflineRenderDialog._get_master_output_path
                _module_checklist_ids = ["m1", "m2"]
                module_checklist = MockCheckList([True, True])

            dlg = DummyDialog()

            # Pass 'Final.wav'
            stems = dlg._get_selected_module_stems("/music/Final.wav", "wav")
            self.assertEqual(os.path.basename(stems["m1"]), "Final_Delay.wav")
            self.assertEqual(os.path.basename(stems["m2"]), "Final_Filter.wav")

            # Pass 'Final_Master.wav' - stems must still be Final_Delay.wav (not Final_Master_Delay.wav)
            stems_m = dlg._get_selected_module_stems("/music/Final_Master.wav", "wav")
            self.assertEqual(os.path.basename(stems_m["m1"]), "Final_Delay.wav")
            self.assertEqual(os.path.basename(stems_m["m2"]), "Final_Filter.wav")

            # Test duplicate module names disambiguation
            mod3 = types.SimpleNamespace(id="m3", path="/path/Delay.c5", name="Delay")
            CeciliaLib.session = MockSession([mod1, mod3])
            dlg._module_checklist_ids = ["m1", "m3"]
            dup_stems = dlg._get_selected_module_stems("/music/Final.wav", "wav")
            self.assertEqual(os.path.basename(dup_stems["m1"]), "Final_Delay_1.wav")
            self.assertEqual(os.path.basename(dup_stems["m3"]), "Final_Delay_2.wav")

        finally:
            CeciliaLib.session = orig_session

    def test_normalize_audio_file(self):
        """Test normalize_audio_file on audio files with various target dB levels."""
        from Resources.OfflineRender import (
            normalize_audio_file,
            _write_wav_float32,
            _read_wav_float64,
        )
        import numpy as np

        # 1. Stereo file with peak 0.25 (-12.04 dB)
        stereo_wav = os.path.join(self.tmp_dir, "stereo_test.wav")
        data = np.array([[0.1, -0.25, 0.2, -0.15], [-0.05, 0.25, -0.1, 0.05]], dtype=np.float64)
        _write_wav_float32(data, stereo_wav, 44100)

        # Normalize to -0.1 dB
        peak_res = normalize_audio_file(stereo_wav, target_db=-0.1, sr=44100, fileformat=0, sampletype=3)
        self.assertEqual(peak_res, -0.1)

        read_back = _read_wav_float64(stereo_wav)
        expected_amp = 10.0 ** (-0.1 / 20.0)
        self.assertAlmostEqual(float(np.max(np.abs(read_back))), expected_amp, places=5)

        # Normalize to -3.0 dB
        peak_res_3 = normalize_audio_file(stereo_wav, target_db=-3.0, sr=44100, fileformat=0, sampletype=3)
        self.assertEqual(peak_res_3, -3.0)
        read_back_3 = _read_wav_float64(stereo_wav)
        expected_amp_3 = 10.0 ** (-3.0 / 20.0)
        self.assertAlmostEqual(float(np.max(np.abs(read_back_3))), expected_amp_3, places=5)

        # 2. Mono file with peak 0.5
        mono_wav = os.path.join(self.tmp_dir, "mono_test.wav")
        mdata = np.array([[0.1, -0.5, 0.3, -0.2]], dtype=np.float64)
        _write_wav_float32(mdata, mono_wav, 48000)

        normalize_audio_file(mono_wav, target_db=0.0, sr=48000, fileformat=0, sampletype=3)
        m_read = _read_wav_float64(mono_wav)
        self.assertAlmostEqual(float(np.max(np.abs(m_read))), 1.0, places=5)

        # 3. Silent file
        silent_wav = os.path.join(self.tmp_dir, "silent_test.wav")
        sdata = np.zeros((2, 100), dtype=np.float64)
        _write_wav_float32(sdata, silent_wav, 44100)
        s_res = normalize_audio_file(silent_wav, target_db=-0.1, sr=44100, fileformat=0, sampletype=3)
        self.assertEqual(s_res, -90.0)


if __name__ == "__main__":
    unittest.main()
