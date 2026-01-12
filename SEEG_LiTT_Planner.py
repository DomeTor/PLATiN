# -*- coding: utf-8 -*-
import math, vtk, qt, ctk, slicer
import json
from slicer.ScriptedLoadableModule import *

class SEEG_LiTT_Planner(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SEEG/LiTT Planner"
        self.parent.categories = ["PLATiN"]
        self.parent.contributors = ["Domenico + Assistant"]
        self.parent.helpText = (
            "Planner combinato: SEEG (elettrodi a contatti) e LiTT (fibra + necrosi). "
            "La sezione LiTT richiama la Logic del modulo originale TrajectoryFromPoints."
        )
        import os
        iconPath = os.path.join(
            os.path.dirname(__file__),
            'Resources', 'Icons', 'SEEG_LiTT_Planner.png'
        )
        if os.path.exists(iconPath):
            self.parent.icon = qt.QIcon(iconPath)

class SEEG_LiTT_PlannerWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # --- Selettore modalità ---
        modeRow = qt.QHBoxLayout()
        modeLabel = qt.QLabel("Planning type:")
        self.planningType = qt.QComboBox(); self.planningType.addItems(["LiTT", "SEEG"])
        modeRow.addWidget(modeLabel); modeRow.addWidget(self.planningType); modeRow.addStretch(1)
        self.layout.addLayout(modeRow)

        # ========= LiTT (replica UI originale) =========
        self.littInfo = qt.QLabel("Create fiber and necrosis from two Markups. MPR intersection on.")
        self.layout.addWidget(self.littInfo)

        self.littBox = ctk.ctkCollapsibleButton(); self.littBox.text="Parameters"
        self.layout.addWidget(self.littBox)
        form = qt.QFormLayout(self.littBox)

        self.entryEdit=qt.QLineEdit(); self.entryEdit.placeholderText="Entry label (e.g., A)"
        self.targetEdit=qt.QLineEdit(); self.targetEdit.placeholderText="Target label (e.g., A_1)"
        form.addRow("Entry:", self.entryEdit); form.addRow("Target:", self.targetEdit)

        self.onlyVisibleCheck=qt.QCheckBox("Search visible Markups only"); self.onlyVisibleCheck.checked=False
        form.addRow(self.onlyVisibleCheck)
        self.showLineCheck=qt.QCheckBox("Also show Markups line"); self.showLineCheck.checked=False
        form.addRow(self.showLineCheck)

        self.fiberDiameter=ctk.ctkDoubleSpinBox(); self.fiberDiameter.decimals=2; self.fiberDiameter.minimum=0.1; self.fiberDiameter.maximum=20.0; self.fiberDiameter.value=4.0
        form.addRow("Fiber diameter (mm):", self.fiberDiameter)
        self.fiberColor=ctk.ctkColorPickerButton(); self.fiberColor.color=qt.QColor(255,85,0)
        form.addRow("Fiber color:", self.fiberColor)

        self.necStartOffset=ctk.ctkDoubleSpinBox(); self.necStartOffset.decimals=2; self.necStartOffset.minimum=-200.0; self.necStartOffset.maximum=200.0; self.necStartOffset.value=0.0
        form.addRow("Necrosis start from A_1 (mm):", self.necStartOffset)

        self.multiOffsetsEdit = qt.QLineEdit(); self.multiOffsetsEdit.setPlaceholderText("e.g., 0, 5, 12.5")
        form.addRow("Multiple offsets (mm):", self.multiOffsetsEdit)

        self.necDiameter=ctk.ctkDoubleSpinBox(); self.necDiameter.decimals=2; self.necDiameter.minimum=0.1; self.necDiameter.maximum=100.0; self.necDiameter.value=10.0
        form.addRow("Necrosis diameter (mm):", self.necDiameter)
        self.necLength=ctk.ctkDoubleSpinBox(); self.necLength.decimals=2; self.necLength.minimum=0.1; self.necLength.maximum=200.0; self.necLength.value=15.0
        form.addRow("Necrosis length (mm):", self.necLength)
        self.necColor=ctk.ctkColorPickerButton(); self.necColor.color=qt.QColor(50,180,255)
        form.addRow("Necrosis color:", self.necColor)

        self.baseName=qt.QLineEdit(); self.baseName.placeholderText="Trajectory <entry>→<target>"
        form.addRow("Base name:", self.baseName)

        # --- Saved LiTT trajectories ---
        self.littSavedCombo = qt.QComboBox()
        self.littSavedCombo.toolTip = "Select a previously generated LiTT trajectory to restore its parameters"
        self.littLoadBtn = qt.QPushButton("Load")
        self.littLoadBtn.toolTip = "Load parameters of the selected LiTT trajectory"
        littSavedW = qt.QWidget()
        littSavedL = qt.QHBoxLayout(littSavedW)
        littSavedL.setContentsMargins(0,0,0,0)
        littSavedL.addWidget(self.littSavedCombo)
        littSavedL.addWidget(self.littLoadBtn)
        form.addRow("Saved LiTT:", littSavedW)

        self.overwriteCheck=qt.QCheckBox("Overwrite output with same name"); self.overwriteCheck.checked=True
        form.addRow(self.overwriteCheck)

        self.generateBtn = qt.QPushButton("Generate")
        self.layout.addWidget(self.generateBtn)
        self.updateBtn = qt.QPushButton("Update trajectory/necrosis")
        self.layout.addWidget(self.updateBtn)
        self.littMprBtn = qt.QPushButton("Create MPR (LiTT)")
        self.layout.addWidget(self.littMprBtn)
        # --- MPR rotation sliders (LiTT): one per slice view ---
        self.littMprRotateRed = ctk.ctkSliderWidget()
        self.littMprRotateRed.singleStep = 1.0
        self.littMprRotateRed.minimum = 0.0
        self.littMprRotateRed.maximum = 360.0
        self.littMprRotateRed.value = 0.0
        self.littMprRotateRed.decimals = 0
        self.littMprRotateRed.enabled = False  # active only after Create MPR
        self.littMprRotateRed.toolTip = "Rotate RED MPR in-plane (degrees)"
        self.layout.addWidget(self.littMprRotateRed)

        self.littMprRotateGreen = ctk.ctkSliderWidget()
        self.littMprRotateGreen.singleStep = 1.0
        self.littMprRotateGreen.minimum = 0.0
        self.littMprRotateGreen.maximum = 360.0
        self.littMprRotateGreen.value = 0.0
        self.littMprRotateGreen.decimals = 0
        self.littMprRotateGreen.enabled = False
        self.littMprRotateGreen.toolTip = "Rotate GREEN MPR in-plane (degrees)"
        self.layout.addWidget(self.littMprRotateGreen)

        self.littMprRotateYellow = ctk.ctkSliderWidget()
        self.littMprRotateYellow.singleStep = 1.0
        self.littMprRotateYellow.minimum = 0.0
        self.littMprRotateYellow.maximum = 360.0
        self.littMprRotateYellow.value = 0.0
        self.littMprRotateYellow.decimals = 0
        self.littMprRotateYellow.enabled = False
        self.littMprRotateYellow.toolTip = "Rotate YELLOW MPR in-plane (degrees)"
        self.layout.addWidget(self.littMprRotateYellow)

        self.status = qt.QLabel("Ready")
        self.layout.addWidget(self.status)

        # ========= SEEG =========
        self.seegBox = ctk.ctkCollapsibleButton(); self.seegBox.text = "SEEG parameters"
        self.layout.addWidget(self.seegBox)
        seegForm = qt.QFormLayout(self.seegBox)

        self.seegEntryEdit = qt.QLineEdit(); self.seegEntryEdit.setPlaceholderText("Entry label (e.g., A)")
        self.seegTargetEdit = qt.QLineEdit(); self.seegTargetEdit.setPlaceholderText("Target label (e.g., A_1)")
        seegForm.addRow("Entry (SEEG):", self.seegEntryEdit)
        seegForm.addRow("Target (SEEG):", self.seegTargetEdit)

        # --- Saved SEEG trajectories ---
        self.seegSavedCombo = qt.QComboBox()
        self.seegSavedCombo.toolTip = "Select a previously generated SEEG trajectory to restore its parameters"
        self.seegLoadBtn = qt.QPushButton("Load")
        self.seegLoadBtn.toolTip = "Load parameters of the selected SEEG trajectory"
        seegSavedW = qt.QWidget()
        seegSavedL = qt.QHBoxLayout(seegSavedW)
        seegSavedL.setContentsMargins(0,0,0,0)
        seegSavedL.addWidget(self.seegSavedCombo)
        seegSavedL.addWidget(self.seegLoadBtn)
        seegForm.addRow("Saved SEEG:", seegSavedW)

        self.seegContactsCombo = qt.QComboBox(); self.seegContactsCombo.addItems([str(x) for x in (5,8,10,12,15,18)])
        self.seegContactLen = ctk.ctkDoubleSpinBox(); self.seegContactLen.minimum=0.1; self.seegContactLen.maximum=10.0; self.seegContactLen.value=1.5; self.seegContactLen.suffix=" mm"; self.seegContactLen.decimals=2
        self.seegGapLen = ctk.ctkDoubleSpinBox(); self.seegGapLen.minimum=0.1; self.seegGapLen.maximum=10.0; self.seegGapLen.value=2.0; self.seegGapLen.suffix=" mm"; self.seegGapLen.decimals=2
        self.seegShaftRadius = ctk.ctkDoubleSpinBox(); self.seegShaftRadius.minimum=0.1; self.seegShaftRadius.maximum=5.0; self.seegShaftRadius.value=0.6; self.seegShaftRadius.suffix=" mm"; self.seegShaftRadius.decimals=2
        self.seegContactRadius = ctk.ctkDoubleSpinBox(); self.seegContactRadius.minimum=0.1; self.seegContactRadius.maximum=5.0; self.seegContactRadius.value=0.7; self.seegContactRadius.suffix=" mm"; self.seegContactRadius.decimals=2
        seegForm.addRow("No. contacts:", self.seegContactsCombo)
        seegForm.addRow("Contact length:", self.seegContactLen)
        seegForm.addRow("Interval (gap):", self.seegGapLen)
        seegForm.addRow("Shaft radius:", self.seegShaftRadius)
        seegForm.addRow("Contact radius:", self.seegContactRadius)
        self.seegSuggestion = qt.QLabel("Suggestion: —")
        seegForm.addRow(self.seegSuggestion)
        self.seegElectrodeName = qt.QLineEdit(); self.seegElectrodeName.setPlaceholderText("es: SEEG A-A1 (12C)")
        seegForm.addRow("Electrode name:", self.seegElectrodeName)

        self.seegMprBtn = qt.QPushButton("Create MPR (SEEG)")
        seegForm.addRow(self.seegMprBtn)
        # --- MPR rotation sliders (SEEG): one per slice view ---
        # MPR rotation sliders are shared with LiTT (shown once at the bottom)


        # Pannelli visibilità
        def updatePanels():
            isLiTT = (self.planningType.currentText if hasattr(self.planningType, "currentText") else self.planningType.currentText()) == "LiTT"
            self.littInfo.setVisible(isLiTT); self.littBox.setVisible(isLiTT)
            self.seegBox.setVisible(not isLiTT)
            try:
                self.littMprBtn.setVisible(isLiTT)
                self.seegMprBtn.setVisible(not isLiTT)
            except: pass
        updatePanels()
        self.planningType.currentIndexChanged.connect(updatePanels)

        # Signals
        self.generateBtn.clicked.connect(self.onGeneratete); self.updateBtn.clicked.connect(self.onUpdate)
        try:
            self.littMprBtn.clicked.connect(self.onCreateMPR_LiTT)
            self.seegMprBtn.clicked.connect(self.onCreateMPR_SEEG)
            # Per-slice in-plane MPR rotations (active only after MPR is created)
            self.littMprRotateRed.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Red", v))
            self.littMprRotateGreen.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Green", v))
            self.littMprRotateYellow.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Yellow", v))
            # SEEG uses the same rotation sliders (bottom). Keep compatibility if legacy widgets exist.
            if hasattr(self, "seegMprRotateRed") and self.seegMprRotateRed is not None:
                self.seegMprRotateRed.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Red", v))
            if hasattr(self, "seegMprRotateGreen") and self.seegMprRotateGreen is not None:
                self.seegMprRotateGreen.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Green", v))
            if hasattr(self, "seegMprRotateYellow") and self.seegMprRotateYellow is not None:
                self.seegMprRotateYellow.valueChanged.connect(lambda v: self.onMPRPlaneRotationChanged("Yellow", v))
        except: pass

        # Extra connections (do not modify existing behaviors)
        self.generateBtn.clicked.connect(self._rememberCurrentTrajectoryParams)
        self.updateBtn.clicked.connect(self._rememberCurrentTrajectoryParams)
        self.littLoadBtn.clicked.connect(self.onLoadSavedLiTT)
        self.seegLoadBtn.clicked.connect(self.onLoadSavedSEEG)
        self.littSavedCombo.activated.connect(self.onLoadSavedLiTT)
        self.seegSavedCombo.activated.connect(self.onLoadSavedSEEG)

        # Initialize saved lists
        self._refreshSavedCombos()

        # Logiche
        self.seegLogic = SEEG_LiTT_PlannerLogic()
        try:
            # Robust local import (does not require TrajectoryFromPoints to be installed as a Slicer module)
            import importlib.util, os, sys
            moduleFile = os.path.join(os.path.dirname(__file__), "TrajectoryFromPoints.py")
            if not os.path.exists(moduleFile):
                raise FileNotFoundError(moduleFile)
            spec = importlib.util.spec_from_file_location("PLATiN_TrajectoryFromPoints", moduleFile)
            TFPMOD = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(TFPMOD)
            self.littLogic = TFPMOD.TrajectoryFromPointsLogic()
        except Exception as e:
            self.littLogic = None
            qt.QMessageBox.warning(
                slicer.util.mainWindow(),
                "LiTT backend not found",
                "Could not load TrajectoryFromPoints backend from the PLATiN folder.\n"
                "Make sure 'TrajectoryFromPoints.py' is in the same folder as this module.\n\n"
                f"Details: {e}"
            )
    def _readEntryTarget(self):
        # Lettura campi globali (pannello LiTT)
        entry=self.entryEdit.text.strip(); target=self.targetEdit.text.strip()
        if not entry or not target:
            slicer.util.errorDisplay("Inserisci le etichette di entry e target.")
            return None, None
        return entry, target

    def _readSEEGEntryTarget(self):
        entry = self.seegEntryEdit.text.strip() if hasattr(self, 'seegEntryEdit') else ''
        target = self.seegTargetEdit.text.strip() if hasattr(self, 'seegTargetEdit') else ''
        if not entry or not target:
            slicer.util.errorDisplay("Inserisci le etichette di entry e target (SEEG).")
            return None, None
        return entry, target

    def onGeneratete(self):
        mode = self.planningType.currentText if hasattr(self.planningType, "currentText") else self.planningType.currentText()
        entry, target = (self._readSEEGEntryTarget() if ((self.planningType.currentText if hasattr(self.planningType, 'currentText') else self.planningType.currentText())=='SEEG') else self._readEntryTarget())
        if entry is None: return
        try:
            if mode == "SEEG":
                dist = self.seegLogic.distanceBetween(entry, target, self.onlyVisibleCheck.checked)
                n_sug = self.seegLogic.suggestContacts(dist, [5,8,10,12,15,18], float(self.seegContactLen.value), float(self.seegGapLen.value))
                try: self.seegSuggestion.setText(f"Suggestion: {n_sug} contatti per coprire {dist:.1f} mm")
                except: pass
                try: chosen = int(self.seegContactsCombo.currentText) if hasattr(self.seegContactsCombo, "currentText") else int(self.seegContactsCombo.currentText())
                except: chosen = n_sug
                self.seegLogic.runSEEG(
                    entry, target, chosen,
                    float(self.seegContactLen.value), float(self.seegGapLen.value),
                    float(self.seegContactRadius.value), float(self.seegShaftRadius.value),
                    self.fiberColor.color, self.necColor.color,
                    self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                    self.onlyVisibleCheck.checked, self.overwriteCheck.checked, self.showLineCheck.checked,
                    self.seegElectrodeName.text.strip()
                )
            else:
                if not self.littLogic: raise RuntimeError("Modulo 'TrajectoryFromPoints' non trovato. Impossibile eseguire LiTT originale.")
                offsets_txt=self.multiOffsetsEdit.text.strip()
                if offsets_txt:
                    self.littLogic.runMultipleNecrosis(
                        entry, target, float(self.fiberDiameter.value), offsets_txt,
                        float(self.necDiameter.value), float(self.necLength.value),
                        self.fiberColor.color, self.necColor.color,
                        self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                        self.onlyVisibleCheck.checked, self.overwriteCheck.checked, self.showLineCheck.checked
                    )
                else:
                    self.littLogic.run(
                        entry, target, float(self.fiberDiameter.value),
                        float(self.necStartOffset.value), float(self.necDiameter.value), float(self.necLength.value),
                        self.fiberColor.color, self.necColor.color,
                        self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                        self.onlyVisibleCheck.checked, self.overwriteCheck.checked, self.showLineCheck.checked
                    )
            try: slicer.util.resetThreeDViews()
            except: pass
            self.status.setText("OK")
        except Exception as e:
            slicer.util.errorDisplay(str(e))

    def onUpdate(self):
        mode = self.planningType.currentText if hasattr(self.planningType, "currentText") else self.planningType.currentText()
        entry, target = (self._readSEEGEntryTarget() if ((self.planningType.currentText if hasattr(self.planningType, 'currentText') else self.planningType.currentText())=='SEEG') else self._readEntryTarget())
        if entry is None: return
        try:
            if mode == "SEEG":
                dist = self.seegLogic.distanceBetween(entry, target, self.onlyVisibleCheck.checked)
                n_sug = self.seegLogic.suggestContacts(dist, [5,8,10,12,15,18], float(self.seegContactLen.value), float(self.seegGapLen.value))
                try: self.seegSuggestion.setText(f"Suggestion: {n_sug} contatti per coprire {dist:.1f} mm")
                except: pass
                try: chosen = int(self.seegContactsCombo.currentText) if hasattr(self.seegContactsCombo, "currentText") else int(self.seegContactsCombo.currentText())
                except: chosen = n_sug
                self.seegLogic.runSEEG(
                    entry, target, chosen,
                    float(self.seegContactLen.value), float(self.seegGapLen.value),
                    float(self.seegContactRadius.value), float(self.seegShaftRadius.value),
                    self.fiberColor.color, self.necColor.color,
                    self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                    self.onlyVisibleCheck.checked, True, self.showLineCheck.checked,
                    self.seegElectrodeName.text.strip()
                )
            else:
                if not self.littLogic: raise RuntimeError("Modulo 'TrajectoryFromPoints' non trovato. Impossibile eseguire LiTT originale.")
                offsets_txt=self.multiOffsetsEdit.text.strip()
                if offsets_txt:
                    self.littLogic.runMultipleNecrosis(
                        entry, target, float(self.fiberDiameter.value), offsets_txt,
                        float(self.necDiameter.value), float(self.necLength.value),
                        self.fiberColor.color, self.necColor.color,
                        self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                        self.onlyVisibleCheck.checked, True, self.showLineCheck.checked
                    )
                else:
                    self.littLogic.run(
                        entry, target, float(self.fiberDiameter.value),
                        float(self.necStartOffset.value), float(self.necDiameter.value), float(self.necLength.value),
                        self.fiberColor.color, self.necColor.color,
                        self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                        self.onlyVisibleCheck.checked, True, self.showLineCheck.checked
                    )
            try: slicer.util.resetThreeDViews()
            except: pass
            self.status.setText("OK")
        except Exception as e:
            slicer.util.errorDisplay(str(e))

    def onCreateMPR_LiTT(self):
        entry, target = self._readEntryTarget()
        if entry is None:
            return
        try:
            self.seegLogic.createTrajectoryMPR(entry, target, self.onlyVisibleCheck.checked)
            self._setMPRRotationEnabled(True)
            self._resetMPRRotationSliders()
        except Exception as e:
            slicer.util.errorDisplay(str(e))

    def onCreateMPR_SEEG(self):
        entry, target = self._readSEEGEntryTarget()
        if entry is None:
            return
        try:
            self.seegLogic.createTrajectoryMPR(entry, target, self.onlyVisibleCheck.checked)
            self._setMPRRotationEnabled(True)
            self._resetMPRRotationSliders()
        except Exception as e:
            slicer.util.errorDisplay(str(e))

    # ------------------------------------------------------------------
    # MPR rotation UI helpers (Widget)
    # ------------------------------------------------------------------
    def _allMprRotationSliders(self):
        return [
            getattr(self, "littMprRotateRed", None),
            getattr(self, "littMprRotateGreen", None),
            getattr(self, "littMprRotateYellow", None),
            getattr(self, "seegMprRotateRed", None),
            getattr(self, "seegMprRotateGreen", None),
            getattr(self, "seegMprRotateYellow", None),
        ]

    def _setMPRRotationEnabled(self, enabled: bool):
        """Enable/disable the MPR rotation sliders (all three views)."""
        for w in self._allMprRotationSliders():
            try:
                if w is not None:
                    w.enabled = bool(enabled)
            except Exception:
                pass

    def _resetMPRRotationSliders(self):
        """Reset all sliders to 0° without triggering callbacks."""
        for w in self._allMprRotationSliders():
            if w is None:
                continue
            try:
                w.blockSignals(True)
                w.value = 0.0
            except Exception:
                pass
            finally:
                try:
                    w.blockSignals(False)
                except Exception:
                    pass

    def onMPRPlaneRotationChanged(self, sliceName: str, value):
        """Rotate a single MPR view in-plane (0..360°) after MPR creation."""
        try:
            if hasattr(self, "seegLogic") and self.seegLogic:
                self.seegLogic.rotateTrajectoryMPRInPlane(sliceName, float(value))
        except Exception as e:
            slicer.util.errorDisplay(str(e))




    # --------------------------------------------------------------------------
    # Saved trajectories (non-invasive add-on)
    # --------------------------------------------------------------------------
    def _getStateNode(self):
        """
        Store saved trajectories inside the scene so they persist with the .mrml.
        """
        nodeName = "SEEG_LiTT_Planner_State"
        nodes = slicer.util.getNodesByClass("vtkMRMLScriptedModuleNode")
        for n in nodes.values() if isinstance(nodes, dict) else nodes:
            try:
                if n.GetName() == nodeName:
                    return n
            except Exception:
                continue
        n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode", nodeName)
        return n

    def _readSavedDict(self):
        stateNode = self._getStateNode()
        try:
            txt = stateNode.GetAttribute("savedTrajectoriesJSON") or ""
            if not txt.strip():
                return {"LiTT": {}, "SEEG": {}}
            d = json.loads(txt)
            if "LiTT" not in d: d["LiTT"] = {}
            if "SEEG" not in d: d["SEEG"] = {}
            return d
        except Exception:
            return {"LiTT": {}, "SEEG": {}}

    def _writeSavedDict(self, d):
        stateNode = self._getStateNode()
        try:
            stateNode.SetAttribute("savedTrajectoriesJSON", json.dumps(d))
        except Exception:
            # fallback: do nothing if serialization fails
            pass

    def _refreshSavedCombos(self):
        d = self._readSavedDict()
        try:
            self.littSavedCombo.blockSignals(True)
            self.seegSavedCombo.blockSignals(True)
            self.littSavedCombo.clear(); self.seegSavedCombo.clear()
            self.littSavedCombo.addItem("— select —")
            self.seegSavedCombo.addItem("— select —")
            for name in sorted(d.get("LiTT", {}).keys()):
                self.littSavedCombo.addItem(name)
            for name in sorted(d.get("SEEG", {}).keys()):
                self.seegSavedCombo.addItem(name)
        finally:
            try: self.littSavedCombo.blockSignals(False)
            except: pass
            try: self.seegSavedCombo.blockSignals(False)
            except: pass

    def _currentMode(self):
        """Return planning mode as plain Python str (robust across PythonQt/PyQt bindings)."""
        try:
            ct = self.planningType.currentText if hasattr(self.planningType, "currentText") else self.planningType.currentText()
            # PythonQt may expose currentText as a bound method or as a property
            if callable(ct):
                ct = ct()
            return str(ct)
        except Exception:
            try:
                return str(self.planningType.currentText())
            except Exception:
                return "LiTT"

    def _rememberCurrentTrajectoryParams(self):
        """
        Called on Generate/Update click.
        Non-invasive: just snapshots current UI parameters by trajectory name.
        """
        mode = self._currentMode()
        # Only snapshot if we have an identifiable name or at least entry/target
        if mode == "SEEG":
            entry = self.seegEntryEdit.text.strip()
            target = self.seegTargetEdit.text.strip()
        else:
            entry = self.entryEdit.text.strip()
            target = self.targetEdit.text.strip()
        if not entry or not target:
            return
        name = (self.baseName.text.strip() or f"{mode} {entry}→{target}")

        params = {"mode": mode, "name": name, "entry": entry, "target": target}

        # Shared params (used also by SEEG generation in this module)
        params.update({
            "onlyVisible": bool(self.onlyVisibleCheck.checked),
            "showLine": bool(self.showLineCheck.checked),
            "overwrite": bool(self.overwriteCheck.checked),
            "fiberColor": self.fiberColor.color.name() if hasattr(self.fiberColor, "color") else None,
            "necColor": self.necColor.color.name() if hasattr(self.necColor, "color") else None,
        })

        if mode == "LiTT":
            params.update({
                "fiberDiameter": float(self.fiberDiameter.value),
                "necStartOffset": float(self.necStartOffset.value),
                "necDiameter": float(self.necDiameter.value),
                "necLength": float(self.necLength.value),
                "multiOffsets": self.multiOffsetsEdit.text.strip(),
            })
        else:
            # SEEG-specific
            try:
                contactsTxt = self.seegContactsCombo.currentText if hasattr(self.seegContactsCombo, "currentText") else self.seegContactsCombo.currentText()
            except Exception:
                contactsTxt = ""
            params.update({
                "seegContacts": str(contactsTxt),
                "seegContactLen": float(self.seegContactLen.value),
                "seegGapLen": float(self.seegGapLen.value),
                "seegContactRadius": float(self.seegContactRadius.value),
                "seegShaftRadius": float(self.seegShaftRadius.value),
                "seegElectrodeName": self.seegElectrodeName.text.strip(),
            })

        d = self._readSavedDict()
        d.setdefault(mode, {})[name] = params
        self._writeSavedDict(d)
        self._refreshSavedCombos()

    def _applyParamsToUI(self, params):
        mode = params.get("mode", "LiTT")
        # Ensure correct mode
        try:
            self.planningType.setCurrentText(mode)
        except Exception:
            # older Qt
            idx = 0 if mode == "LiTT" else 1
            self.planningType.setCurrentIndex(idx)

        # Entry/Target
        if mode == "SEEG":
            self.seegEntryEdit.setText(params.get("entry", ""))
            self.seegTargetEdit.setText(params.get("target", ""))
        else:
            self.entryEdit.setText(params.get("entry", ""))
            self.targetEdit.setText(params.get("target", ""))

        # Base name
        self.baseName.setText(params.get("name", ""))

        # Shared
        try: self.onlyVisibleCheck.checked = bool(params.get("onlyVisible", self.onlyVisibleCheck.checked))
        except: pass
        try: self.showLineCheck.checked = bool(params.get("showLine", self.showLineCheck.checked))
        except: pass
        try: self.overwriteCheck.checked = bool(params.get("overwrite", self.overwriteCheck.checked))
        except: pass

        # Colors
        try:
            fc = params.get("fiberColor", None)
            if fc: self.fiberColor.color = qt.QColor(fc)
        except: pass
        try:
            nc = params.get("necColor", None)
            if nc: self.necColor.color = qt.QColor(nc)
        except: pass

        if mode == "LiTT":
            for key, widget in [
                ("fiberDiameter", self.fiberDiameter),
                ("necStartOffset", self.necStartOffset),
                ("necDiameter", self.necDiameter),
                ("necLength", self.necLength),
            ]:
                try:
                    if key in params: widget.value = float(params[key])
                except: pass
            try:
                self.multiOffsetsEdit.setText(params.get("multiOffsets", ""))
            except: pass
        else:
            # SEEG widgets
            try:
                if "seegContacts" in params:
                    idx = self.seegContactsCombo.findText(str(params["seegContacts"]))
                    if idx >= 0: self.seegContactsCombo.setCurrentIndex(idx)
            except: pass
            for key, widget in [
                ("seegContactLen", self.seegContactLen),
                ("seegGapLen", self.seegGapLen),
                ("seegContactRadius", self.seegContactRadius),
                ("seegShaftRadius", self.seegShaftRadius),
            ]:
                try:
                    if key in params: widget.value = float(params[key])
                except: pass
            try:
                self.seegElectrodeName.setText(params.get("seegElectrodeName", ""))
            except: pass

    def onLoadSavedLiTT(self):
        name = None
        try:
            name = self.littSavedCombo.currentText if hasattr(self.littSavedCombo, "currentText") else self.littSavedCombo.currentText()
        except Exception:
            return
        if not name or name.startswith("—"):
            return
        d = self._readSavedDict()
        params = d.get("LiTT", {}).get(name, None)
        if not params:
            return
        self._applyParamsToUI(params)
        try: self.status.setText(f"Loaded LiTT: {name}")
        except: pass

    def onLoadSavedSEEG(self):
        name = None
        try:
            name = self.seegSavedCombo.currentText if hasattr(self.seegSavedCombo, "currentText") else self.seegSavedCombo.currentText()
        except Exception:
            return
        if not name or name.startswith("—"):
            return
        d = self._readSavedDict()
        params = d.get("SEEG", {}).get(name, None)
        if not params:
            return
        self._applyParamsToUI(params)
        try: self.status.setText(f"Loaded SEEG: {name}")
        except: pass
class SEEG_LiTT_PlannerLogic(ScriptedLoadableModuleLogic):
    # -------- Utilities comuni --------


    def _findPointByLabel(self, label, onlyVisible):
        nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsFiducialNode")
        if not nodes:
            raise RuntimeError("Nessun Markups Fiducial in scena.")
        for n in nodes:
            if onlyVisible:
                d=n.GetDisplayNode()
                if d and not d.GetVisibility(): 
                    continue
            for i in range(n.GetNumberOfControlPoints()):
                if n.GetNthControlPointLabel(i) == label:
                    p = [0.0,0.0,0.0]; n.GetNthControlPointPositionWorld(i, p)
                    return p, n, i
        raise RuntimeError(f"Punto '{label}' non trovato.")

    def _unit(self, v):
        l = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
        if l < 1e-9:
            return [0.0,0.0,1.0]
        return [v[0]/l, v[1]/l, v[2]/l]

    def _setSliceNodeToReformat(self, sliceNode):
        """Set slice node orientation to 'Reformat' in a Slicer-version-safe way."""
        if hasattr(sliceNode, 'SetOrientationToReformat'):
            sliceNode.SetOrientationToReformat()
            return
        try:
            sliceNode.SetOrientation('Reformat')
        except Exception:
            # Older/alternative APIs: if this fails, we still proceed by directly setting SliceToRAS
            pass

    def _setSliceToRASMatrix(self, sliceNode, sliceToRASMatrix):
        """Apply a SliceToRAS matrix in a way that works across Slicer versions.

        Newer Slicer builds expose SetSliceToRAS(), while others only allow
        accessing the internal matrix via GetSliceToRAS().
        """
        # Preferred API (if available)
        if hasattr(sliceNode, 'SetSliceToRAS'):
            try:
                sliceNode.SetSliceToRAS(sliceToRASMatrix)
                return
            except Exception:
                pass

        # Alternative convenience API
        if hasattr(sliceNode, 'SetSliceToRASByNTP'):
            # Try a couple of common signatures
            n = [sliceToRASMatrix.GetElement(0,2), sliceToRASMatrix.GetElement(1,2), sliceToRASMatrix.GetElement(2,2)]
            t = [sliceToRASMatrix.GetElement(0,0), sliceToRASMatrix.GetElement(1,0), sliceToRASMatrix.GetElement(2,0)]
            p = [sliceToRASMatrix.GetElement(0,3), sliceToRASMatrix.GetElement(1,3), sliceToRASMatrix.GetElement(2,3)]
            for args in [
                (n[0], n[1], n[2], t[0], t[1], t[2], p[0], p[1], p[2], 0.0),
                (n[0], n[1], n[2], t[0], t[1], t[2], p[0], p[1], p[2]),
            ]:
                try:
                    sliceNode.SetSliceToRASByNTP(*args)
                    return
                except Exception:
                    continue

        # Oldest/most compatible: directly deep-copy into the node's matrix
        if hasattr(sliceNode, 'GetSliceToRAS'):
            try:
                sliceNode.GetSliceToRAS().DeepCopy(sliceToRASMatrix)
                sliceNode.Modified()
                return
            except Exception:
                pass

        raise AttributeError("Cannot set SliceToRAS matrix: unsupported Slicer build.")

    def _applySliceToRASMatrix(self, sliceNode, sliceToRASMatrix):
        """Apply SliceToRAS on sliceNode without relying on version-specific setters.

        Some Slicer builds expose sliceNode.SetSliceToRAS(matrix), others don't.
        GetSliceToRAS() is widely available: we can DeepCopy into it and mark the node modified.
        """
        # Preferred API when available
        if hasattr(sliceNode, 'SetSliceToRAS'):
            sliceNode.SetSliceToRAS(sliceToRASMatrix)
            return

        # Fallback 1: try by normal/transverse/position API (signature differs across versions)
        if hasattr(sliceNode, 'SetSliceToRASByNTP'):
            n = [sliceToRASMatrix.GetElement(0,2), sliceToRASMatrix.GetElement(1,2), sliceToRASMatrix.GetElement(2,2)]
            t = [sliceToRASMatrix.GetElement(0,0), sliceToRASMatrix.GetElement(1,0), sliceToRASMatrix.GetElement(2,0)]
            p = [sliceToRASMatrix.GetElement(0,3), sliceToRASMatrix.GetElement(1,3), sliceToRASMatrix.GetElement(2,3)]
            for args in (
                (n[0], n[1], n[2], t[0], t[1], t[2], p[0], p[1], p[2], 0),
                (n[0], n[1], n[2], t[0], t[1], t[2], p[0], p[1], p[2]),
            ):
                try:
                    sliceNode.SetSliceToRASByNTP(*args)
                    return
                except Exception:
                    pass

        # Fallback 2: direct matrix copy (most compatible)
        if hasattr(sliceNode, 'GetSliceToRAS'):
            try:
                sliceNode.GetSliceToRAS().DeepCopy(sliceToRASMatrix)
                sliceNode.Modified()
                return
            except Exception:
                pass

        raise AttributeError('Cannot set SliceToRAS on this Slicer version (missing SetSliceToRAS/SetSliceToRASByNTP/GetSliceToRAS).')

    def _rgbf(self, qcolor):
        return qcolor.red()/255.0, qcolor.green()/255.0, qcolor.blue()/255.0

    def _ensureUniqueNode(self, className, baseName, overwrite):
        if overwrite:
            existing = slicer.util.getFirstNodeByClassByName(className, baseName)
            if existing:
                slicer.mrmlScene.RemoveNode(existing)
        # guarantee unique name if overwrite False
        name = baseName
        if not overwrite:
            idx = 1
            while slicer.util.getFirstNodeByClassByName(className, name):
                idx += 1
                name = f"{baseName} ({idx})"
        return name

    def _applySliceIntersectionDisplay(self, displayNode, rgb, thicknessPx=4, opacity=1.0):
        displayNode.SetSliceIntersectionVisibility(True)
        displayNode.SetSliceIntersectionThickness(thicknessPx)
        displayNode.SetOpacity(opacity)
        displayNode.SetSelectedColor(*rgb)

    def _rot_z_to_vec(self, u):
        # Calcola rotazione che porta l'asse Z sull'asse u
        import numpy as np
        uz = np.array([0.0,0.0,1.0]); v = np.array(u, dtype=float)
        v = v / (np.linalg.norm(v) + 1e-12)
        axis = np.cross(uz, v); s = np.linalg.norm(axis); c = float(np.dot(uz, v))
        if s < 1e-12:
            return (0.0, [0,0,1])
        axis = list(axis / s)
        angle_deg = math.degrees(math.atan2(s, c))
        return (angle_deg, axis)

    def createTrajectoryMPR(self, entryLabel, targetLabel, searchOnlyVisible=False):
        """Create 3 orthogonal MPR slice orientations based on the trajectory entry->target.

        Red:    plane perpendicular to trajectory (normal = axis)
        Green:  plane parallel to axis (normal = v)
        Yellow: plane parallel to axis and orthogonal to Green (normal = w)

        Slice origin is set at the trajectory midpoint.
        """
        pEntry,_,_ = self._findPointByLabel(entryLabel, searchOnlyVisible)
        pTarget,_,_ = self._findPointByLabel(targetLabel, searchOnlyVisible)

        axis = self._unit([pTarget[0]-pEntry[0], pTarget[1]-pEntry[1], pTarget[2]-pEntry[2]])

        # Choose a reference not collinear with axis
        ref = [0.0, 0.0, 1.0]
        if abs(axis[0]*ref[0] + axis[1]*ref[1] + axis[2]*ref[2]) > 0.95:
            ref = [0.0, 1.0, 0.0]

        def cross(a,b):
            return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

        v = self._unit(cross(axis, ref))
        w = self._unit(cross(axis, v))

        center = [(pEntry[0]+pTarget[0])*0.5, (pEntry[1]+pTarget[1])*0.5, (pEntry[2]+pTarget[2])*0.5]

        # Store baseline MPR frame for subsequent rotation
        self._mprAxis = axis
        self._mprV0 = v
        self._mprW0 = w
        self._mprCenter = center
        self._mprAngleDeg = 0.0
        self._mprBaseSliceToRAS = {}

        def setSlice(sliceName, normal, transverse):
            lm = slicer.app.layoutManager()
            sw = lm.sliceWidget(sliceName) if lm else None
            if not sw:
                raise RuntimeError("Slice views not available (no layout manager).")
            sliceNode = sw.mrmlSliceNode()
            self._setSliceNodeToReformat(sliceNode)

            n = self._unit(normal)
            t = self._unit(transverse)

            # IMPORTANT: Fix only the GREEN and YELLOW slice left-right mirroring.
            # We keep the same reformat plane (changing normal sign does not change the plane),
            # and we do NOT touch RED behavior.
            # Flipping X (transverse) alone would create a left-handed basis; therefore we also
            # flip Z (normal) to preserve a right-handed SliceToRAS while removing the mirror.
            if sliceName in ("Green", "Yellow"):
                t = [-t[0], -t[1], -t[2]]
                n = [-n[0], -n[1], -n[2]]

            y = self._unit(cross(n, t))

            m = vtk.vtkMatrix4x4()
            # Columns: X(transverse), Y, Z(normal), Origin
            m.SetElement(0,0, t[0]); m.SetElement(1,0, t[1]); m.SetElement(2,0, t[2]); m.SetElement(3,0, 0.0)
            m.SetElement(0,1, y[0]); m.SetElement(1,1, y[1]); m.SetElement(2,1, y[2]); m.SetElement(3,1, 0.0)
            m.SetElement(0,2, n[0]); m.SetElement(1,2, n[1]); m.SetElement(2,2, n[2]); m.SetElement(3,2, 0.0)
            m.SetElement(0,3, center[0]); m.SetElement(1,3, center[1]); m.SetElement(2,3, center[2]); m.SetElement(3,3, 1.0)

            # Set SliceToRAS in a Slicer-version-tolerant way
            self._setSliceToRASMatrix(sliceNode, m)
            sliceNode.UpdateMatrices()
            # Keep a copy as baseline for in-plane rotations
            try:
                baseM = vtk.vtkMatrix4x4(); baseM.DeepCopy(sliceNode.GetSliceToRAS())
                self._mprBaseSliceToRAS[sliceName] = baseM
            except Exception:
                pass
            try:
                sw.sliceLogic().FitSliceToAll()
            except Exception:
                pass

            # Center the view on the trajectory immediately (Green/Yellow/Red).
            # This does NOT change the plane/orientation; it only moves the slice offset.
            if sliceName in ("Green", "Yellow", "Red"):
                try:
                    # Prefer slice node API if available
                    if hasattr(sliceNode, "JumpSliceByCentering"):
                        sliceNode.JumpSliceByCentering(center[0], center[1], center[2])
                    elif hasattr(sliceNode, "JumpSlice"):
                        sliceNode.JumpSlice(center[0], center[1], center[2])
                    else:
                        sw.sliceLogic().JumpSliceByCentering(center[0], center[1], center[2])
                except Exception:
                    pass

        setSlice("Red", axis, v)
        setSlice("Green", v, axis)
        setSlice("Yellow", w, axis)

        try:
            slicer.util.resetThreeDViews()
        except Exception:
            pass


    # -------- SEEG --------
    

    def _rotateAroundAxis(self, vec, axis, angleRad):
        # Rodrigues' rotation formula
        ax = self._unit(axis)
        v = vec
        c = math.cos(angleRad)
        s = math.sin(angleRad)
        dot = v[0]*ax[0] + v[1]*ax[1] + v[2]*ax[2]
        cross = [ax[1]*v[2]-ax[2]*v[1], ax[2]*v[0]-ax[0]*v[2], ax[0]*v[1]-ax[1]*v[0]]
        return [
            v[0]*c + cross[0]*s + ax[0]*dot*(1.0-c),
            v[1]*c + cross[1]*s + ax[1]*dot*(1.0-c),
            v[2]*c + cross[2]*s + ax[2]*dot*(1.0-c),
        ]


    def rotateTrajectoryMPRInPlane(self, sliceName: str, angleDeg: float):
        """Rotate a single slice view *within its own plane* (0..360°).

        This rotates the in-plane X/Y axes around the slice normal (Z axis of SliceToRAS),
        keeping the normal and the slice position unchanged.

        Works only after createTrajectoryMPR has been called at least once.
        """
        if not hasattr(self, "_mprBaseSliceToRAS") or sliceName not in self._mprBaseSliceToRAS:
            return

        lm = slicer.app.layoutManager()
        sw = lm.sliceWidget(sliceName) if lm else None
        if not sw:
            return
        sliceNode = sw.mrmlSliceNode()
        self._setSliceNodeToReformat(sliceNode)

        base = self._mprBaseSliceToRAS[sliceName]

        # Extract base X and Y axes (columns 0 and 1), Z axis stays the same
        x0 = [base.GetElement(0,0), base.GetElement(1,0), base.GetElement(2,0)]
        y0 = [base.GetElement(0,1), base.GetElement(1,1), base.GetElement(2,1)]
        z0 = [base.GetElement(0,2), base.GetElement(1,2), base.GetElement(2,2)]
        o0 = [base.GetElement(0,3), base.GetElement(1,3), base.GetElement(2,3)]

        a = math.radians(float(angleDeg))
        c = math.cos(a)
        s = math.sin(a)

        # Post-multiply by Rz(angle) in slice coordinates:
        # newX = X*c + Y*s
        # newY = X*(-s) + Y*c
        x = [x0[0]*c + y0[0]*s, x0[1]*c + y0[1]*s, x0[2]*c + y0[2]*s]
        y = [x0[0]*(-s) + y0[0]*c, x0[1]*(-s) + y0[1]*c, x0[2]*(-s) + y0[2]*c]

        m = vtk.vtkMatrix4x4()
        m.Identity()
        m.SetElement(0,0, x[0]); m.SetElement(1,0, x[1]); m.SetElement(2,0, x[2])
        m.SetElement(0,1, y[0]); m.SetElement(1,1, y[1]); m.SetElement(2,1, y[2])
        m.SetElement(0,2, z0[0]); m.SetElement(1,2, z0[1]); m.SetElement(2,2, z0[2])
        m.SetElement(0,3, o0[0]); m.SetElement(1,3, o0[1]); m.SetElement(2,3, o0[2])
        m.SetElement(3,3, 1.0)

        self._setSliceToRASMatrix(sliceNode, m)
        sliceNode.UpdateMatrices()
        try:
            sw.sliceLogic().FitSliceToAll()
        except Exception:
            pass


    def rotateTrajectoryMPR(self, angleDeg):
        """Rotate the current MPR around the stored trajectory axis.

        This only affects slice orientations; it does not modify any markup/trajectory objects.
        Has effect only after createTrajectoryMPR has been called at least once.
        """
        if not hasattr(self, "_mprAxis") or self._mprAxis is None:
            return

        self._mprAngleDeg = float(angleDeg)
        angleRad = math.radians(self._mprAngleDeg)

        axis = self._mprAxis
        center = getattr(self, "_mprCenter", [0.0, 0.0, 0.0])
        v0 = self._mprV0
        w0 = self._mprW0

        v = self._unit(self._rotateAroundAxis(v0, axis, angleRad))
        w = self._unit(self._rotateAroundAxis(w0, axis, angleRad))

        def cross(a,b):
            return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

        def setSlice(sliceName, normal, transverse):
            lm = slicer.app.layoutManager()
            sw = lm.sliceWidget(sliceName) if lm else None
            if not sw:
                return
            sliceNode = sw.mrmlSliceNode()
            self._setSliceNodeToReformat(sliceNode)

            n = self._unit(normal)
            t = self._unit(transverse)
            y = self._unit(cross(n, t))

            m = vtk.vtkMatrix4x4()
            m.SetElement(0,0, t[0]); m.SetElement(1,0, t[1]); m.SetElement(2,0, t[2]); m.SetElement(3,0, 0.0)
            m.SetElement(0,1, y[0]); m.SetElement(1,1, y[1]); m.SetElement(2,1, y[2]); m.SetElement(3,1, 0.0)
            m.SetElement(0,2, n[0]); m.SetElement(1,2, n[1]); m.SetElement(2,2, n[2]); m.SetElement(3,2, 0.0)
            m.SetElement(0,3, center[0]); m.SetElement(1,3, center[1]); m.SetElement(2,3, center[2]); m.SetElement(3,3, 1.0)

            # Set SliceToRAS in a Slicer-version-tolerant way
            self._setSliceToRASMatrix(sliceNode, m)
            sliceNode.UpdateMatrices()
            try:
                sw.sliceLogic().FitSliceToAll()
            except Exception:
                pass

        setSlice("Red", axis, v)
        setSlice("Green", v, axis)
        setSlice("Yellow", w, axis)

    def distanceBetween(self, entryLabel, targetLabel, searchOnlyVisible=False):
        pEntry,_,_ = self._findPointByLabel(entryLabel, searchOnlyVisible)
        pTarget,_,_ = self._findPointByLabel(targetLabel, searchOnlyVisible)
        return math.dist(pEntry, pTarget)

    def suggestContacts(self, distanceMm, allowed, contactLenMm, gapLenMm):
        def total(n): return n*contactLenMm + max(0, n-1)*gapLenMm
        for n in sorted(allowed):
            if total(n) >= distanceMm - 1e-6:
                return n
        return max(allowed)

    def runSEEG(self, entryLabel, targetLabel, nContacts, contactLenMm, gapLenMm,
                contactRadiusMm, shaftRadiusMm, shaftColor, contactColor,
                outputBaseName, searchOnlyVisible, overwrite, showLine, electrodeName=""):

        # Punti e direzione (u da entry->target; contiamo dal TARGET indietro)
        pEntry,_,_ = self._findPointByLabel(entryLabel, searchOnlyVisible)
        pTarget,_,_ = self._findPointByLabel(targetLabel, searchOnlyVisible)
        d=[pTarget[0]-pEntry[0], pTarget[1]-pEntry[1], pTarget[2]-pEntry[2]]; u=self._unit(d)

        # Linea A→A1
        lineName=self._ensureUniqueNode("vtkMRMLMarkupsLineNode", outputBaseName, overwrite)
        lineNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", lineName)
        lineNode.AddControlPointWorld(pEntry); lineNode.AddControlPointWorld(pTarget)
        ld=lineNode.GetDisplayNode()
        if ld:
            fr,fg,fb=self._rgbf(shaftColor); ld.SetColor(fr,fg,fb); ld.SetLineThickness(4.0); ld.SetSelectedColor(fr,fg,fb)
            ld.SetTextScale(0); ld.SetPointLabelsVisibility(False); ld.SetVisibility(1 if showLine else 0)

        # Fusto lungo la traiettoria
        ls=vtk.vtkLineSource(); ls.SetPoint1(pEntry); ls.SetPoint2(pTarget); ls.Update()
        shaftTube=vtk.vtkTubeFilter(); shaftTube.SetInputConnection(ls.GetOutputPort()); shaftTube.SetRadius(max(shaftRadiusMm, 0.01))
        shaftTube.SetNumberOfSides(64); shaftTube.CappingOn(); shaftTube.Update()

        # Append unico shaft+contatti (modello originale stabile)
        append=vtk.vtkAppendPolyData()
        append.AddInputConnection(shaftTube.GetOutputPort())

        baseCyl = vtk.vtkCylinderSource(); baseCyl.SetRadius(max(contactRadiusMm, 0.01)); baseCyl.SetHeight(max(contactLenMm, 0.01))
        baseCyl.SetResolution(64); baseCyl.CappingOn(); baseCyl.Update()

        ang, axis = self._rot_z_to_vec(u)

        step = contactLenMm + gapLenMm
        for i in range(int(nContacts)):
            center = [pTarget[0] - u[0]*(contactLenMm*0.5 + step*i),
                      pTarget[1] - u[1]*(contactLenMm*0.5 + step*i),
                      pTarget[2] - u[2]*(contactLenMm*0.5 + step*i)]
            T=vtk.vtkTransform(); T.PostMultiply(); T.RotateWXYZ(ang, axis); T.Translate(center)
            tpf=vtk.vtkTransformPolyDataFilter(); tpf.SetInputConnection(baseCyl.GetOutputPort()); tpf.SetTransform(T); tpf.Update()
            append.AddInputConnection(tpf.GetOutputPort())

        append.Update()
        electrodePoly = vtk.vtkPolyData(); electrodePoly.DeepCopy(append.GetOutput())

        # Nome elettrodo
        elecBase = electrodeName.strip() if electrodeName and electrodeName.strip() else f"{lineName} (SEEG {nContacts}C)"
        elecName=self._ensureUniqueNode("vtkMRMLModelNode", elecBase, overwrite)
        elecNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", elecName); elecNode.SetAndObservePolyData(electrodePoly)
        md=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); elecNode.SetAndObserveDisplayNodeID(md.GetID())
        sr,sg,sb=self._rgbf(shaftColor)  # colore unico del modello originale
        md.SetColor(sr,sg,sb); md.SetOpacity(1.0); md.SetBackfaceCulling(0); md.SetScalarVisibility(0); md.SetVisibility(1)
        self._applySliceIntersectionDisplay(md, [sr,sg,sb], thicknessPx=4, opacity=1.0)

        # ---- Overlay contatti con colore indipendente (stessa geometria dei contatti) ----
        try:
            contactsAppend2 = vtk.vtkAppendPolyData()
            baseCyl2 = vtk.vtkCylinderSource(); baseCyl2.SetRadius(max(contactRadiusMm, 0.01)); baseCyl2.SetHeight(max(contactLenMm, 0.01))
            baseCyl2.SetResolution(64); baseCyl2.CappingOn(); baseCyl2.Update()

            step2 = contactLenMm + gapLenMm
            for i in range(int(nContacts)):
                center2 = [pTarget[0] - u[0]*(contactLenMm*0.5 + step2*i),
                           pTarget[1] - u[1]*(contactLenMm*0.5 + step2*i),
                           pTarget[2] - u[2]*(contactLenMm*0.5 + step2*i)]
                T2=vtk.vtkTransform(); T2.PostMultiply(); T2.RotateWXYZ(ang, axis); T2.Translate(center2)
                tpf2=vtk.vtkTransformPolyDataFilter(); tpf2.SetInputConnection(baseCyl2.GetOutputPort()); tpf2.SetTransform(T2); tpf2.Update()
                contactsAppend2.AddInputConnection(tpf2.GetOutputPort())

            contactsAppend2.Update()
            contactsPoly2 = vtk.vtkPolyData(); contactsPoly2.DeepCopy(contactsAppend2.GetOutput())

            contactsBase = (electrodeName.strip() + " (contacts)") if electrodeName and electrodeName.strip() else f"{lineName} (contacts)"
            contactsName = self._ensureUniqueNode("vtkMRMLModelNode", contactsBase, overwrite)
            contactsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", contactsName); contactsNode.SetAndObservePolyData(contactsPoly2)
            contactsDisp = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); contactsNode.SetAndObserveDisplayNodeID(contactsDisp.GetID())
            cr,cg,cb = self._rgbf(contactColor)
            contactsDisp.SetColor(cr,cg,cb); contactsDisp.SetOpacity(1.0); contactsDisp.SetBackfaceCulling(0); contactsDisp.SetScalarVisibility(0); contactsDisp.SetVisibility(1)
            self._applySliceIntersectionDisplay(contactsDisp, [cr,cg,cb], thicknessPx=1, opacity=1.0)
        except Exception:
            pass

        return lineNode, elecNode
