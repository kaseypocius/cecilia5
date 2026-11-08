# encoding: utf-8
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
"""

import os, time, random
import wx
from .constants import *
import Resources.CeciliaLib as CeciliaLib
import Resources.PreferencePanel as PreferencePanel
import Resources.CeciliaInterface as CeciliaInterface
from .menubar import InterfaceMenuBar
from .Widgets import *
from .DocFrame import ManualFrame

class CeciliaMainFrame(wx.Frame):
    def __init__(self, parent, ID):
        wx.Frame.__init__(self, parent, ID)
        self.menubar = InterfaceMenuBar(self, self)
        self.SetMenuBar(self.menubar)
        self.prefs = None
        self.time = 0
        self.api_doc_frame = ManualFrame(kind="api")
        self.mod_doc_frame = ManualFrame(kind="modules")

    def setTime(self, curTime=0):
        self.time = curTime

    def updateTitle(self):
        if CeciliaLib.getVar('interface'):
            from .ChainUI import update_title
            update_title(CeciliaLib.getVar('interface'))

    def onShortPlayStop(self, event):
        self.onPlayStop(not CeciliaLib.getVar("audioServer").isAudioServerRunning())

    def onPlayStop(self, value):
        if value:
            if not CeciliaLib.session.modules:
                CeciliaLib.startCeciliaSound()
                return
            CeciliaLib.getControlPanel().nonZeroTime = 0
            CeciliaLib.setVar("toDac", True)
            CeciliaLib.getVar("grapher").toolbar.loadingMsg.SetForegroundColour("#FFFFFF")
            CeciliaLib.getVar("grapher").toolbar.loadingMsg.Refresh()
            CeciliaLib.getControlPanel().transportButtons.setPlay(True)
            wx.CallLater(50, CeciliaLib.startCeciliaSound, True)
        else:
            CeciliaLib.stopCeciliaSound()

    def onOfflineRender(self, event):
        CeciliaLib.openOfflineRenderDialog(mode="single")

    def onBounceToDisk(self, event):
        if not CeciliaLib.session.modules:
            return
        CeciliaLib.getControlPanel().onBounceToDisk()

    def applyBatchProcessingFolder(self, value=""):
        if not CeciliaLib.session.modules:
            return
        CeciliaLib.openOfflineRenderDialog(mode="folder")

    def applyBatchProcessingPreset(self, value=""):
        if not CeciliaLib.session.modules:
            return
        CeciliaLib.openOfflineRenderDialog(mode="presets")

    def onBatchProcessing(self, event):
        if not CeciliaLib.session.modules:
            CeciliaLib.showErrorDialog('No active module', 'Open a module or chain session before running batch processing.')
            return
        if event.GetId() == ID_BATCH_FOLDER:
            CeciliaLib.openOfflineRenderDialog(mode="folder")
        else:
            CeciliaLib.openOfflineRenderDialog(mode="presets")

    def onUseSoundDuration(self, evt):
        CeciliaLib.setVar("useSoundDur", evt.GetInt())

    def onSelectOutputFilename(self):
        file = CeciliaLib.saveFileDialog(self, AUDIO_FILE_WILDCARD, type='Save audio')
        if file is not None:
            CeciliaLib.setVar("saveAudioFilePath", os.path.split(file)[0])
        return file

    def closeInterface(self):
        if CeciliaLib.getVar("interface") is not None:
            CeciliaLib.getVar("interface").destroySessionWindow()
            CeciliaLib.setVar("interface", None)

    def newRecent(self, file, remove=False):
        file = CeciliaLib.ensureNFD(os.path.abspath(file))
        try:
            with open(RECENT_FILE_PATH, encoding='utf-8') as stream:
                lines = [line.strip() for line in stream if line.strip()]
        except OSError:
            lines = []
        lines = [path for path in lines if path != file]
        if not remove:
            lines.insert(0, file)
        with open(RECENT_FILE_PATH, 'w', encoding='utf-8') as stream:
            stream.writelines(path + '\n' for path in lines[:10])
        for frame in (self, CeciliaLib.getVar('interface')):
            if frame is not None:
                frame.menubar.refreshRecentMenu()

    def openModuleFromMenu(self, path, builtin=False):
        return CeciliaLib.openCeciliaFile(
            self, path, builtin,
            new_session=not getattr(self, 'addingChainModule', False))

    def onOpen(self, event, builtin=False):
        if isinstance(event, wx.CommandEvent):
            CeciliaLib.openCeciliaFile(self)
        elif os.path.isfile(event):
            if event.lower().endswith('.c5chain'):
                CeciliaLib.openChainSession(self, event)
            else:
                self.openModuleFromMenu(event, builtin)

    def onOpenRandom(self, event):
        categories = [folder for folder in os.listdir(MODULES_PATH) if not folder.startswith(".")]
        category = random.choice(categories)
        files = [f for f in os.listdir(os.path.join(MODULES_PATH, category)) if f.endswith(FILE_EXTENSION)]
        file = random.choice(files)
        self.onOpen(os.path.join(MODULES_PATH, category, file), True)

    def openRecent(self, event):
        menu = self.GetMenuBar()
        id = event.GetId()
        file = menu.FindItemById(id).GetItemLabelText().replace("\n", "").strip()
        if os.path.isfile(file):
            self.openModuleFromMenu(file)
        else:
            CeciliaLib.showErrorDialog("Error while trying to open a file!", "No such file : %s" % file[:-1])
            self.newRecent(file, remove=True)

    def onOpenBuiltin(self, event):
        menu = self.GetMenuBar()
        id = event.GetId()
        file = menu.FindItemById(id)
        filename = file.GetItemLabelText()
        filedict = self.GetMenuBar().files
        for key in filedict.keys():
            if filename in filedict[key]:
                dirname = key
                break
        name = os.path.join(CeciliaLib.ensureNFD(MODULES_PATH), dirname, filename)
        self.openModuleFromMenu(name, True)

    def onOpenPrefModule(self, event):
        menu = self.GetMenuBar()
        id = event.GetId()
        file = menu.FindItemById(id)
        filename = file.GetItemLabelText()
        filedir = file.GetMenu().GetTitle()
        prefPath = CeciliaLib.getVar("prefferedPath")
        prefPaths = prefPath.split(';')
        prefBaseNames = [os.path.basename(path) for path in prefPaths]
        dirname = prefPaths[prefBaseNames.index(filedir)]
        if dirname:
            name = os.path.join(dirname, filename)
            self.openModuleFromMenu(name)

    def openModuleAsText(self, event):
        if CeciliaLib.session.selected is None:
            return
        CeciliaLib.openCurrentFileAsText(CeciliaLib.getVar("currentCeciliaFile"))

    def reloadCurrentModule(self, event):
        if CeciliaLib.session.selected is None:
            return
        CeciliaLib.openCeciliaFile(self, CeciliaLib.getVar("currentCeciliaFile"), replace=True)

    def onSaveAs(self, event):
        if CeciliaLib.session.selected is None:
            return
        CeciliaLib.saveCeciliaFile(self)
        self.updateTitle()

    def onPreferences(self, event):
        self.prefs = PreferencePanel.PreferenceFrame(self)
        self.prefs.Show()
        self.prefs.Center()

    def onRememberInputSound(self, event):
        CeciliaLib.getVar("interface").menubar.editMenu.FindItemById(ID_REMEMBER).Check(event.GetInt())
        CeciliaLib.setVar("rememberedSound", event.GetInt())
        return

    def onUpdateInterface(self, event):
        if CeciliaLib.session.selected is not None:
            self.reloadCurrentModule(event)

    def onShowSpectrum(self, event):
        CeciliaLib.setVar('showSpectrum', event.GetInt())

    def openSpectrumWindow(self):
        if CeciliaLib.getVar('spectrumFrame') is None:
            f = SpectrumFrame(CeciliaLib.getVar("interface"))
            f.setAnalyzer(CeciliaLib.getVar("audioServer").spectrum)
            f.Center()
            f.Show()
            CeciliaLib.setVar('spectrumFrame', f)

    def onQuit(self, event):
        if not CeciliaLib.confirmSessionDiscard(CeciliaLib.getVar('interface') or self):
            return

        try:
            self.prefs.onClose(event)
        except:
            pass

        if CeciliaLib.getVar("audioServer").isAudioServerRunning():
            CeciliaLib.getVar("audioServer").stop()
            time.sleep(.2)

        if CeciliaLib.getVar('spectrumFrame') is not None:
            try:
                CeciliaLib.getVar('spectrumFrame')._destroy(None)
            except:
                pass
            finally:
                CeciliaLib.setVar('spectrumFrame', None)

        self.api_doc_frame.Destroy()
        self.mod_doc_frame.Destroy()
        CeciliaLib.closeCeciliaFile(self)
        CeciliaLib.writeVarToDisk()
        self.Destroy()

    def onUseMidi(self, event):
        CeciliaLib.setVar("useMidi", event.GetInt())

    def onHelpAbout(self, evt):
        Y = CeciliaLib.getVar("displaySize")[0][1]
        about = AboutPopupFrame(self, Y // 5)
        about.Show()

    def onModuleAbout(self, evt):
        if CeciliaLib.session.selected is None:
            return
        file = os.path.split(CeciliaLib.getVar("currentCeciliaFile"))[1]
        self.mod_doc_frame.Center()
        self.mod_doc_frame.openPage(file)

    def onDocFrame(self, evt):
        self.api_doc_frame.Center()
        self.api_doc_frame.Show()

    def onGraphFrame(self, evt):
        self.graph_doc_frame = wx.MessageDialog(self, TT_GRAPHER)
        self.graph_doc_frame.ShowModal()
        self.graph_doc_frame.Destroy()
