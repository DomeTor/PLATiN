
import os
import numpy as np
import vtk
import slicer
import qt
from slicer.ScriptedLoadableModule import *
import random

class TrajectoryFusion(ScriptedLoadableModule):
    def __init__(self, parent):
        parent.title = "Trajectory Fusion"
        parent.categories = ["PLATiN"]
        parent.dependencies = []
        parent.contributors = ["DomeTor"]
        parent.helpText = "Create and fuse trajectory models between markup points using vtkLineSource."
        parent.acknowledgementText = "Thanks to OpenAI."
        self.parent = parent
    
        import os
        iconPath = os.path.join(
            os.path.dirname(__file__),
            'Resources', 'Icons', 'SEEG_LiTT_Planner.png'
        )
        if os.path.exists(iconPath):
            self.parent.icon = qt.QIcon(iconPath)

class TrajectoryFusionWidget(ScriptedLoadableModuleWidget):
    def _tf_log(self, message: str) -> None:
        """Minimal logger used by the added optional features.

        Does not affect existing PLATiN logic.
        """
        try:
            print(f"[TrajectoryFusion] {message}")
        except Exception:
            pass
        try:
            import slicer
            slicer.util.showStatusMessage(message, 3000)
        except Exception:
            pass

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.markupSelector = slicer.qMRMLNodeComboBox()
        self.markupSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.markupSelector.selectNodeUponCreation = True
        self.markupSelector.setMRMLScene(slicer.mrmlScene)
        self.markupSelector.setToolTip("Select markup with entry and target points.")
        self.layout.addWidget(self.markupSelector)

        self.refSelector = slicer.qMRMLNodeComboBox()
        self.refSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.refSelector.selectNodeUponCreation = True
        self.refSelector.setMRMLScene(slicer.mrmlScene)
        self.refSelector.setToolTip("Select the reference T1 volume.")
        self.layout.addWidget(self.refSelector)

        self.intensitySlider = qt.QSlider(qt.Qt.Horizontal)
        self.intensitySlider.setMinimum(0)
        self.intensitySlider.setMaximum(50000)
        self.intensitySlider.setValue(500)
        self.layout.addWidget(qt.QLabel("Intensità Fusione"))
        self.layout.addWidget(self.intensitySlider)

        self.directoryButton = qt.QPushButton("Seleziona Cartella Output")
        self.directoryButton.toolTip = "Seleziona dove salvare i file r-*.nii.gz"
        self.directoryButton.connect('clicked()', self.selectOutputDirectory)
        self.layout.addWidget(self.directoryButton)
        self.outputDirectory = slicer.app.temporaryPath


        # ============================================================
        # ADD-ON (OPTIONAL): Reorient generated NIfTI to RAS and export to DICOM
        # - Does NOT change existing behavior unless enabled
        # ============================================================
        self.exportDicomCheck = qt.QCheckBox("Reorient in RAS + Export NIfTI to DICOM")
        self.exportDicomCheck.toolTip = "Se abilitato: crea anche r-*-RAS.nii.gz e una serie DICOM per ogni volume generato"
        self.layout.addWidget(self.exportDicomCheck)

        formLayout = qt.QFormLayout()
        self.patientNameLineEdit = qt.QLineEdit()
        self.patientNameLineEdit.setPlaceholderText("Es. Rossi Mario / SUBJ001")
        formLayout.addRow("Nome soggetto (Patient Name):", self.patientNameLineEdit)

        self.modalityLineEdit = qt.QLineEdit()
        self.modalityLineEdit.setText("MR")
        formLayout.addRow("Modalità (DICOM 0008,0060):", self.modalityLineEdit)

        self.seriesDescLineEdit = qt.QLineEdit()
        self.seriesDescLineEdit.setPlaceholderText("Es. TrajectoryFusion / T1+Traiettorie")
        formLayout.addRow("Nome serie (Series Description):", self.seriesDescLineEdit)

        self.layout.addLayout(formLayout)

        # Disable metadata fields unless export is enabled
        def _onExportToggled(state):
            enabled = bool(state)
            self.patientNameLineEdit.enabled = enabled
            self.modalityLineEdit.enabled = enabled
            self.seriesDescLineEdit.enabled = enabled
        self.exportDicomCheck.connect("toggled(bool)", _onExportToggled)
        _onExportToggled(False)

        # ------------------------------
        # Manual selection: choose which NIfTI to reorient/export to DICOM
        # (non-invasive: does not change existing behavior; optional extra button)
        # ------------------------------
        self.manualGroupBox = qt.QGroupBox("Manual RAS + DICOM export (select NIfTI)")
        self.manualGroupBox.setToolTip("Optional: reorient selected NIfTI to RAS and export to DICOM. Does not affect trajectory generation.")
        manualLayout = qt.QVBoxLayout(self.manualGroupBox)

        self.refreshNiftiListButton = qt.QPushButton("Refresh NIfTI list from output folder")
        self.refreshNiftiListButton.toolTip = "Scan the selected output folder for .nii/.nii.gz files"
        manualLayout.addWidget(self.refreshNiftiListButton)
        self.refreshNiftiListButton.connect('clicked(bool)', self._tf_refreshNiftiList)

        self.niftiListWidget = qt.QListWidget()
        self.niftiListWidget.setToolTip("Select which NIfTI files you want to convert. Use the checkboxes.")
        self.niftiListWidget.setSelectionMode(qt.QAbstractItemView.NoSelection)
        manualLayout.addWidget(self.niftiListWidget)

        self.convertSelectedButton = qt.QPushButton("Reorient selected to RAS + Export selected to DICOM")
        self.convertSelectedButton.toolTip = "For each checked NIfTI: load volume, reorient to RAS, export to DICOM"
        manualLayout.addWidget(self.convertSelectedButton)
        self.convertSelectedButton.connect('clicked(bool)', self._tf_convertSelectedNifti)

        self.layout.addWidget(self.manualGroupBox)


        self.applyButton = qt.QPushButton("Generate Trajectories")
        self.applyButton.toolTip = "Run script"
        self.layout.addWidget(self.applyButton)
        self.applyButton.connect('clicked(bool)', self.runScript)

        self.layout.addStretch(1)

    def selectOutputDirectory(self):
        dir = qt.QFileDialog.getExistingDirectory()
        if dir:
            self.outputDirectory = dir
            print(f"[Cartella Selezionata] {self.outputDirectory}")


    # ------------------------------
    # Manual selection helpers (optional)
    # ------------------------------
    def _tf_refreshNiftiList(self):
        """Populate the list widget with .nii/.nii.gz files found in the output directory."""
        if not hasattr(self, "niftiListWidget"):
            return

        self.niftiListWidget.clear()

        outDir = getattr(self, "outputDirectory", None)
        if not outDir or not os.path.isdir(outDir):
            slicer.util.errorDisplay("Please select a valid output directory first.")
            return

        niftiFiles = []
        for fn in os.listdir(outDir):
            low = fn.lower()
            if low.endswith(".nii") or low.endswith(".nii.gz"):
                niftiFiles.append(os.path.join(outDir, fn))

        niftiFiles.sort(key=lambda p: os.path.basename(p).lower())

        if not niftiFiles:
            item = qt.QListWidgetItem("(No NIfTI files found in output folder)")
            item.setFlags(item.flags() & ~qt.Qt.ItemIsEnabled)
            self.niftiListWidget.addItem(item)
            return

        for p in niftiFiles:
            label = os.path.basename(p)
            item = qt.QListWidgetItem(label)
            item.setToolTip(p)
            item.setFlags(item.flags() | qt.Qt.ItemIsUserCheckable)
            item.setCheckState(qt.Qt.Unchecked)
            # store full path
            item.setData(qt.Qt.UserRole, p)
            self.niftiListWidget.addItem(item)

    def _tf_convertSelectedNifti(self):
        """For each checked NIfTI in the list: reorient to RAS (file->file) and export to DICOM."""
        outDir = getattr(self, "outputDirectory", None)
        if not outDir or not os.path.isdir(outDir):
            slicer.util.errorDisplay("Please select a valid output directory first.")
            return

        if not hasattr(self, "niftiListWidget"):
            slicer.util.errorDisplay("NIfTI selection list is not available.")
            return

        selectedPaths = []
        for i in range(self.niftiListWidget.count):
            item = self.niftiListWidget.item(i)
            if item is None or not item.flags() & qt.Qt.ItemIsUserCheckable:
                continue
            if item.checkState() == qt.Qt.Checked:
                p = item.data(qt.Qt.UserRole)
                if p:
                    selectedPaths.append(p)

        if not selectedPaths:
            slicer.util.infoDisplay("No NIfTI selected.")
            return

        patientName = self.patientNameLineEdit.text.strip() if hasattr(self, "patientNameLineEdit") else ""
        modality = self.modalityLineEdit.text.strip() if hasattr(self, "modalityLineEdit") else "MR"
        seriesDesc = self.seriesDescLineEdit.text.strip() if hasattr(self, "seriesDescLineEdit") else ""

        if not patientName:
            slicer.util.errorDisplay("Please enter Patient Name.")
            return
        if not modality:
            modality = "MR"
        if not seriesDesc:
            seriesDesc = "TrajectoryFusion"

        failures = []
        for niftiPath in selectedPaths:
            try:
                if not os.path.exists(niftiPath):
                    raise RuntimeError(f"Input image file does not exist: {niftiPath}")

                # 1) Reorient on disk to RAS (do not overwrite original)
                rasPath = _tf_make_ras_nifti_path(niftiPath)

                # If rasPath equals input and we still want a RAS copy, create a sibling file
                if os.path.abspath(rasPath) == os.path.abspath(niftiPath):
                    rasPath = _tf_make_ras_nifti_path(niftiPath + "_copy")

                _tf_orient_nifti_file_to_ras(niftiPath, rasPath)
                self._tf_log(f"[RAS Save] ✓ {rasPath}")

                # 2) Export that RAS NIfTI to DICOM (file->DICOM)
                dicomOut = os.path.join(outDir, "DICOM", os.path.splitext(os.path.basename(rasPath))[0])
                _tf_export_volume_to_dicom(
                    rasPath,
                    dicomDir=dicomOut,
                    patientName=patientName,
                    modality=modality,
                    seriesDescription=seriesDesc,
                    studyDescription=seriesDesc,
                )
                self._tf_log(f"[DICOM Export] ✓ {dicomOut}")

            except Exception as e:
                failures.append(f"{os.path.basename(niftiPath)}: {e}")

        if failures:
            slicer.util.errorDisplay("Some exports failed:\n" + "\n".join(failures))
        else:
            slicer.util.infoDisplay("Selected NIfTI exported to DICOM successfully.")

    def _tf_getPatientName(self):
        if hasattr(self, "patientNameLineEdit"):
            name = self.patientNameLineEdit.text.strip()
        else:
            name = ""
        if name:
            return name
        # Ask only when export is enabled
        name, ok = qt.QInputDialog.getText(slicer.util.mainWindow(), "DICOM Export", "Nome soggetto (Patient Name):")
        return name.strip() if ok else ""

    def _tf_getModality(self):
        if hasattr(self, "modalityLineEdit"):
            mod = self.modalityLineEdit.text.strip()
        else:
            mod = "MR"
        if mod:
            return mod
        mod, ok = qt.QInputDialog.getText(slicer.util.mainWindow(), "DICOM Export", "Modalità (es. MR, CT):")
        mod = mod.strip() if ok else ""
        return mod if mod else "MR"

    def _tf_getSeriesDescription(self):
        if hasattr(self, "seriesDescLineEdit"):
            sd = self.seriesDescLineEdit.text.strip()
        else:
            sd = ""
        if sd:
            return sd
        sd, ok = qt.QInputDialog.getText(slicer.util.mainWindow(), "DICOM Export", "Nome della serie (Series Description):")
        return sd.strip() if ok else ""

    def runScript(self):
        markupNode = self.markupSelector.currentNode()
        refVolume = self.refSelector.currentNode()
        intensityValue = self.intensitySlider.value
        if not markupNode or not refVolume:
            slicer.util.errorDisplay("Please select both a markup and a reference volume.")
            return

        fiducials = {}
        for i in range(markupNode.GetNumberOfControlPoints()):
            label = markupNode.GetNthControlPointLabel(i)
            pos = [0, 0, 0]
            markupNode.GetNthControlPointPositionWorld(i, pos)
            if "_" in label:
                base = label.split("_")[0]
                fiducials.setdefault(base, {})["target"] = pos
            else:
                fiducials.setdefault(label, {})["entry"] = pos

        for key, pts in fiducials.items():
            if "entry" not in pts or "target" not in pts:
                continue
            p1 = pts["entry"]
            p2 = pts["target"]
            print(f"[LineSource] Traiettoria {key} → P1: {p1}, P2: {p2}")
            polydata = createTubeBetweenPoints(p1, p2, radius=2.0)

            modelNode = slicer.modules.models.logic().AddModel(polydata)
            modelNode.SetName(f"Model_{key}")
            modelNode.CreateDefaultDisplayNodes()
            r, g, b = [random.uniform(0.2, 1.0) for _ in range(3)]
            modelNode.GetDisplayNode().SetColor(r, g, b)

            segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", f"Seg_{key}")
            segNode.SetReferenceImageGeometryParameterFromVolumeNode(refVolume)
            slicer.modules.segmentations.logic().ImportModelToSegmentationNode(modelNode, segNode)

            segmentIds = vtk.vtkStringArray()
            segNode.GetSegmentation().GetSegmentIDs(segmentIds)
            if segmentIds.GetNumberOfValues() > 0:
                segId = segmentIds.GetValue(segmentIds.GetNumberOfValues() - 1)
                segNode.GetSegmentation().GetSegment(segId).SetName(key)

            labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", f"Label_{key}")
            slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(segNode, labelNode, refVolume)

            labelArray = slicer.util.arrayFromVolume(labelNode)
            unique = np.unique(labelArray)
            print(f"→ Valori unici nella labelmap {key}: {unique}")
            if len(unique) <= 1 and unique[0] == 0:
                print(f"[Python] Labelmap {key} vuota: verifica traiettoria o geometria")

            fusedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", f"Fused_{key}")
            refArray = slicer.util.arrayFromVolume(refVolume).copy()
            refArray += labelArray * intensityValue
            slicer.util.updateVolumeFromArray(fusedNode, refArray)

            fusedNode.SetSpacing(refVolume.GetSpacing())
            fusedNode.SetOrigin(refVolume.GetOrigin())
            mat = vtk.vtkMatrix4x4()
            refVolume.GetIJKToRASMatrix(mat)
            fusedNode.SetIJKToRASMatrix(mat)

            outputPath = os.path.join(self.outputDirectory, f"r-{key}.nii.gz")
            success = slicer.util.saveNode(fusedNode, outputPath)
            print(f"[Save] {'✓' if success else '✗'} Salvataggio: {outputPath}")

            # Optional add-on: create RAS-oriented NIfTI and export to DICOM
            if hasattr(self, "exportDicomCheck") and self.exportDicomCheck.checked and success:
                try:
                    _tf_export_nifti_as_ras_and_dicom(
                        inputVolumeNode=fusedNode,
                        originalNiftiPath=outputPath,
                        outputDirectory=self.outputDirectory,
                        patientName=self._tf_getPatientName(),
                        modality=self._tf_getModality(),
                        seriesDescription=self._tf_getSeriesDescription(),
                    )
                except Exception as e:
                    slicer.util.errorDisplay(f"RAS/DICOM export failed for {key}: {e}")


def createTubeBetweenPoints(p1, p2, radius=2.0, resolution=20):
    line = vtk.vtkLineSource()
    line.SetPoint1(p1)
    line.SetPoint2(p2)
    line.Update()

    tube = vtk.vtkTubeFilter()
    tube.SetInputConnection(line.GetOutputPort())
    tube.SetRadius(radius)
    tube.SetNumberOfSides(resolution)
    tube.CappingOn()
    tube.Update()

    return tube.GetOutput()


# === Auto NRRD export add-on (non-invasive) ===
# This block does NOT modify any existing functions. It simply watches for newly saved
# fused volumes ("Fused_*") and automatically saves an additional .nrrd copy next to
# the .nii/.nii.gz file exported by the original script.
try:
    _tf_export_timer  # avoid creating multiple timers on reload
except NameError:
    import os
    _tf_export_timer = qt.QTimer()
    _tf_export_timer.setInterval(1000)  # check once per second

    def _tf_on_timeout():
        # Look for Fused_* scalar volumes that have been saved as NIfTI
        nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for node in nodes:
            name = node.GetName() or ""
            if not name.startswith("Fused_"):
                continue

            # Skip if we've already exported NRRD for this node
            if node.GetAttribute("AutoNRRDExportDone") == "1":
                continue

            storage = node.GetStorageNode()
            if not storage:
                continue

            fname = storage.GetFileName()
            if not fname:
                continue

            low = fname.lower()
            # Only proceed after the original script has saved NIfTI
            if low.endswith(".nii.gz"):
                outpath = fname[:-7] + ".nrrd"
            elif low.endswith(".nii"):
                outpath = fname[:-4] + ".nrrd"
            else:
                # Not yet saved as NIfTI by the original script
                continue

            ok = slicer.util.saveNode(node, outpath)
            print(f"[Auto-NRRD] {'✓' if ok else '✗'} Saved: {outpath}")
            if ok:
                node.SetAttribute("AutoNRRDExportDone", "1")

    _tf_export_timer.timeout.connect(_tf_on_timeout)
    _tf_export_timer.start()
    
# ============================================================
# ADD-ON (ROBUST): Burn trajectories + TEXT labels into T1
# - No changes to existing functions
# - Uses VTK PolyData -> ImageStencil -> Labelmap (no Segmentation)
# ============================================================

import os
import vtk
import slicer
import qt
from vtk.util.numpy_support import vtk_to_numpy


# ---------- Core: PolyData (in RAS) -> Labelmap aligned to reference volume ----------
def _tf_polydata_ras_to_labelmap(refVolumeNode, polydataRAS, labelValue=1, nodeName="LabelTmp"):
    import vtk
    import slicer
    from vtk.util.numpy_support import vtk_to_numpy

    if refVolumeNode is None or refVolumeNode.GetImageData() is None:
        raise ValueError("Reference volume is invalid")

    dims = refVolumeNode.GetImageData().GetDimensions()  # (x,y,z)

    rasToIjk = vtk.vtkMatrix4x4()
    refVolumeNode.GetRASToIJKMatrix(rasToIjk)

    t = vtk.vtkTransform()
    t.Identity()
    t.Concatenate(rasToIjk)

    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetTransform(t)
    tf.SetInputData(polydataRAS)
    tf.Update()

    polyIJK = tf.GetOutput()

    img = vtk.vtkImageData()
    img.SetDimensions(dims[0], dims[1], dims[2])
    img.SetSpacing(1.0, 1.0, 1.0)
    img.SetOrigin(0.0, 0.0, 0.0)
    img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    img.GetPointData().GetScalars().Fill(int(labelValue))

    p2s = vtk.vtkPolyDataToImageStencil()
    p2s.SetInputData(polyIJK)
    p2s.SetOutputSpacing(1.0, 1.0, 1.0)
    p2s.SetOutputOrigin(0.0, 0.0, 0.0)
    p2s.SetOutputWholeExtent(img.GetExtent())
    p2s.Update()

    st = vtk.vtkImageStencil()
    st.SetInputData(img)
    st.SetStencilConnection(p2s.GetOutputPort())
    st.ReverseStencilOff()
    st.SetBackgroundValue(0)
    st.Update()

    outImg = st.GetOutput()
    scalars = outImg.GetPointData().GetScalars()
    arr = vtk_to_numpy(scalars).reshape(dims[2], dims[1], dims[0])  # (k,j,i)

    labelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", nodeName)
    slicer.util.updateVolumeFromArray(labelNode, arr)

    # copy geometry from reference
    labelNode.SetSpacing(refVolumeNode.GetSpacing())
    labelNode.SetOrigin(refVolumeNode.GetOrigin())
    ijkToRas = vtk.vtkMatrix4x4()
    refVolumeNode.GetIJKToRASMatrix(ijkToRas)
    labelNode.SetIJKToRASMatrix(ijkToRas)

    return labelNode



# ---------- Text: label -> PolyData in RAS ----------
def _tf_text_to_polydata_ras(text, rasXYZ, scaleMm=8.0, thicknessMm=2.0, offsetRAS=(1.0, 1.0, 1.0)):
    # 1) testo vettoriale
    vtxt = vtk.vtkVectorText()
    vtxt.SetText(str(text))
    vtxt.Update()

    tri0 = vtk.vtkTriangleFilter()
    tri0.SetInputData(vtxt.GetOutput())
    tri0.Update()

    # 2) normals (aiuta extrusion/manifold)
    n0 = vtk.vtkPolyDataNormals()
    n0.SetInputData(tri0.GetOutput())
    n0.ConsistencyOn()
    n0.AutoOrientNormalsOn()
    n0.SplittingOff()
    n0.Update()

    # 3) estrusione con capping (superficie “chiusa” per lo stencil)
    extr = vtk.vtkLinearExtrusionFilter()
    extr.SetInputData(n0.GetOutput())
    extr.SetExtrusionTypeToNormalExtrusion()
    extr.SetScaleFactor(thicknessMm)
    extr.CappingOn()
    extr.Update()

    tri1 = vtk.vtkTriangleFilter()
    tri1.SetInputData(extr.GetOutput())
    tri1.Update()

    fill = vtk.vtkFillHolesFilter()
    fill.SetInputData(tri1.GetOutput())
    fill.SetHoleSize(1000.0)
    fill.Update()

    clean = vtk.vtkCleanPolyData()
    clean.SetInputData(fill.GetOutput())
    clean.Update()

    # 4) TRANSFORM CORRETTA:
    # PostMultiply + Translate poi Scale  ->  M = T * S  (scala poi trasla, senza traslazione scalata)
    tx = rasXYZ[0] + offsetRAS[0]
    ty = rasXYZ[1] + offsetRAS[1]
    tz = rasXYZ[2] + offsetRAS[2]

    t = vtk.vtkTransform()
    t.Identity()
    t.PostMultiply()
    t.Translate(tx, ty, tz)
    t.Scale(scaleMm, scaleMm, scaleMm)

    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetTransform(t)
    tf.SetInputData(clean.GetOutput())
    tf.Update()

    return tf.GetOutput()

# ---------- Markups parsing (same rule you already use) ----------
def _tf_collect_trajectories_from_markup(markupNode):
    traj = {}
    for i in range(markupNode.GetNumberOfControlPoints()):
        label = markupNode.GetNthControlPointLabel(i)
        pos = [0.0, 0.0, 0.0]
        markupNode.GetNthControlPointPositionWorld(i, pos)

        if "_" in label:
            base = label.split("_")[0]
            traj.setdefault(base, {})["target"] = list(pos)
            traj.setdefault(base, {})["targetLabel"] = label
        else:
            traj.setdefault(label, {})["entry"] = list(pos)
            traj.setdefault(label, {})["entryLabel"] = label
    return traj


# ---------- Fuse masks into scalar array ----------
import numpy as np

def _tf_add_mask(refArray, maskArray, intensityValue):
    out = refArray.copy()
    on = (maskArray > 0)
    # forza almeno intensityValue dove c’è la maschera (non dipende dal contrasto della T1)
    out[on] = np.maximum(out[on], intensityValue)
    return out

def _tf_copy_geometry_from_ref(outVolumeNode, refVolumeNode):
    outVolumeNode.SetSpacing(refVolumeNode.GetSpacing())
    outVolumeNode.SetOrigin(refVolumeNode.GetOrigin())
    m = vtk.vtkMatrix4x4()
    refVolumeNode.GetIJKToRASMatrix(m)
    outVolumeNode.SetIJKToRASMatrix(m)


# ---------- NEW MODE 1: per-trajectory (one file each) ----------
def _tf_run_per_trajectory_with_labels(widgetSelf):
    markupNode = widgetSelf.markupSelector.currentNode()
    refVolume = widgetSelf.refSelector.currentNode()
    intensityValue = widgetSelf.intensitySlider.value
    outDir = getattr(widgetSelf, "outputDirectory", slicer.app.temporaryPath)

    if not markupNode or not refVolume:
        slicer.util.errorDisplay("Please select both a markup and a reference volume.")
        return

    traj = _tf_collect_trajectories_from_markup(markupNode)

    # 👇 legge la modalità selezionata in UI
    mode = _tf_get_label_mode(widgetSelf)  # "Entry only" / "Target only" / "Entry + Target"

    for key, pts in traj.items():
        if "entry" not in pts or "target" not in pts:
            continue

        p1 = pts["entry"]
        p2 = pts["target"]
        entryLabel = pts.get("entryLabel", key)
        targetLabel = pts.get("targetLabel", f"{key}_1")

        # Parto dalla T1
        fused = slicer.util.arrayFromVolume(refVolume).copy()

        # Traiettoria
        tubePoly = createTubeBetweenPoints(p1, p2, radius=2.0)
        tubeLabel = _tf_polydata_ras_to_labelmap(refVolume, tubePoly, labelValue=1, nodeName=f"Label_Tube_{key}")
        tubeMask = slicer.util.arrayFromVolume(tubeLabel)
        fused = _tf_add_mask(fused, tubeMask, intensityValue)

        # Label (stampate) in base alla modalità
        if mode in ("Entry only", "Entry + Target"):
            _tf_stamp_text(
                fused, refVolume, entryLabel, p1, value=intensityValue,
                pixelSize=2, thickness=2, spacing=1, offsetIJK=(2, 2, 0)
            )

        if mode in ("Target only", "Entry + Target"):
            _tf_stamp_text(
                fused, refVolume, targetLabel, p2, value=intensityValue,
                pixelSize=2, thickness=2, spacing=1, offsetIJK=(2, 2, 0)
            )

        # Salva volume per traiettoria
        fusedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", f"FusedLabel_{key}")
        slicer.util.updateVolumeFromArray(fusedNode, fused)
        _tf_copy_geometry_from_ref(fusedNode, refVolume)

        outPath = os.path.join(outDir, f"r-{key}-labels.nii.gz")
        ok = slicer.util.saveNode(fusedNode, outPath)
        print(f"[Save per-trajectory +Labels] {'✓' if ok else '✗'} {outPath}")

# ---------- NEW MODE 2: combined (single file with all trajectories + labels) ----------
def _tf_run_combined_with_labels(widgetSelf):
    markupNode = widgetSelf.markupSelector.currentNode()
    refVolume = widgetSelf.refSelector.currentNode()
    intensityValue = widgetSelf.intensitySlider.value
    outDir = getattr(widgetSelf, "outputDirectory", slicer.app.temporaryPath)

    if not markupNode or not refVolume:
        slicer.util.errorDisplay("Please select both a markup and a reference volume.")
        return

    traj = _tf_collect_trajectories_from_markup(markupNode)
    fused = slicer.util.arrayFromVolume(refVolume).copy()

    # 👇 legge la modalità selezionata in UI
    mode = _tf_get_label_mode(widgetSelf)  # "Entry only" / "Target only" / "Entry + Target"

    for key, pts in traj.items():
        if "entry" not in pts or "target" not in pts:
            continue

        p1 = pts["entry"]
        p2 = pts["target"]
        entryLabel = pts.get("entryLabel", key)
        targetLabel = pts.get("targetLabel", f"{key}_1")

        # Traiettoria
        tubePoly = createTubeBetweenPoints(p1, p2, radius=2.0)
        tubeLabel = _tf_polydata_ras_to_labelmap(refVolume, tubePoly, labelValue=1, nodeName=f"Label_Tube_{key}")
        tubeMask = slicer.util.arrayFromVolume(tubeLabel)
        fused = _tf_add_mask(fused, tubeMask, intensityValue)

        # Label (stampate) in base alla modalità
        if mode in ("Entry only", "Entry + Target"):
            _tf_stamp_text(
                fused, refVolume, entryLabel, p1, value=intensityValue,
                pixelSize=2, thickness=2, spacing=1, offsetIJK=(2, 2, 0)
            )

        if mode in ("Target only", "Entry + Target"):
            _tf_stamp_text(
                fused, refVolume, targetLabel, p2, value=intensityValue,
                pixelSize=2, thickness=2, spacing=1, offsetIJK=(2, 2, 0)
            )

    fusedNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "FusedLabel_ALL")
    slicer.util.updateVolumeFromArray(fusedNode, fused)
    _tf_copy_geometry_from_ref(fusedNode, refVolume)

    outPath = os.path.join(outDir, "r-ALL-labels.nii.gz")
    ok = slicer.util.saveNode(fusedNode, outPath)
    print(f"[Save ALL +Labels] {'✓' if ok else '✗'} {outPath}")


# ---------- UI injection: add 2 buttons without touching your setup() ----------
try:
    _tf_ui_injection_timer_robust
except NameError:
    _tf_ui_injection_timer_robust = qt.QTimer()
    _tf_ui_injection_timer_robust.setInterval(400)

    def _tf_try_inject_buttons_robust():
        try:
            w = slicer.modules.trajectoryfusion.widgetRepresentation()
            if not w:
                return
            pyw = w.self()
            if not pyw:
                return

            if getattr(pyw, "_tfButtonsInjectedRobust", False):
                _tf_ui_injection_timer_robust.stop()
                return

            b1 = qt.QPushButton("Generate Trajectories + Labels (per file) [ROBUST]")
            b1.toolTip = "1 NIfTI/NRRD per traiettoria, con label entry/target bruciate nel volume"
            b1.connect('clicked()', lambda: _tf_run_per_trajectory_with_labels(pyw))

            b2 = qt.QPushButton("Generate ALL Trajectories + Labels (single file) [ROBUST]")
            b2.toolTip = "1 NIfTI/NRRD con tutte le traiettorie + label sovraimpresse"
            b2.connect('clicked()', lambda: _tf_run_combined_with_labels(pyw))

            pyw.layout.addWidget(b1)
            pyw.layout.addWidget(b2)

            pyw._tfButtonsInjectedRobust = True
            print("[TrajectoryFusion] ROBUST add-on injected (stencil rasterization).")
            _tf_ui_injection_timer_robust.stop()

        except Exception:
            pass

    _tf_ui_injection_timer_robust.timeout.connect(_tf_try_inject_buttons_robust)
    _tf_ui_injection_timer_robust.start()

# ==========================
# FORCE UI BUTTON INJECTION
# ==========================
import slicer, qt

def _tf_force_add_buttons():
    try:
        w = slicer.modules.trajectoryfusion.widgetRepresentation()
        if not w:
            print("[TrajectoryFusion] widgetRepresentation() not ready")
            return False

        pyw = w.self()
        if not pyw:
            print("[TrajectoryFusion] widget self() not ready")
            return False

        if getattr(pyw, "_tfButtonsForced", False):
            # già aggiunti
            return True

        # Safety: check that target functions exist
        if "_tf_run_per_trajectory_with_labels" not in globals() or "_tf_run_combined_with_labels" not in globals():
            print("[TrajectoryFusion] Missing functions _tf_run_per_trajectory_with_labels / _tf_run_combined_with_labels")
            return False

        # --- Label mode selector (Entry / Target / Both) ---
        labelModeBox = qt.QComboBox()
        labelModeBox.addItems(["Entry only", "Target only", "Entry + Target"])
        labelModeBox.toolTip = "Scegli quali label stampare nel volume"
        pyw.layout.addWidget(labelModeBox)

        # store on widget so logic can read it
        pyw._tfLabelModeBox = labelModeBox

        # --- Buttons ---
        b1 = qt.QPushButton("Create labels (per trajectory)")
        b1.toolTip = "Crea un NIfTI/NRRD per traiettoria con traiettoria + lettere bruciate"
        b1.connect("clicked()", lambda: _tf_run_per_trajectory_with_labels(pyw))

        b2 = qt.QPushButton("Create labels (ALL in one file)")
        b2.toolTip = "Crea un solo NIfTI/NRRD con tutte le traiettorie + lettere bruciate"
        b2.connect("clicked()", lambda: _tf_run_combined_with_labels(pyw))

        pyw.layout.addWidget(b1)
        pyw.layout.addWidget(b2)

        pyw._tfButtonsForced = True
        print("[TrajectoryFusion] Buttons + label mode added OK")
        return True

    except Exception as e:
        print("[TrajectoryFusion] Button injection error:", e)
        return False


def _tf_get_label_mode(widgetSelf):
    box = getattr(widgetSelf, "_tfLabelModeBox", None)
    if box is None:
        return "Entry + Target"
    return box.currentText


# Try a few times (module UI might not be ready immediately)
def _tf_force_inject_with_retries(maxTries=15, intervalMs=300):
    tries = {"n": 0}
    t = qt.QTimer()
    t.setInterval(intervalMs)

    def _tick():
        tries["n"] += 1
        ok = _tf_force_add_buttons()
        if ok or tries["n"] >= maxTries:
            t.stop()

    t.timeout.connect(_tick)
    t.start()

qt.QTimer.singleShot(0, lambda: _tf_force_inject_with_retries())

# ---------- TEXT STAMP (no VTK stencil): draw 5x7 letters directly into volume array ----------

def _tf_ras_to_ijk(refVolumeNode, rasXYZ):
    m = vtk.vtkMatrix4x4()
    refVolumeNode.GetRASToIJKMatrix(m)
    x, y, z = rasXYZ
    ijk_h = [0.0, 0.0, 0.0, 1.0]
    m.MultiplyPoint([x, y, z, 1.0], ijk_h)
    return int(round(ijk_h[0])), int(round(ijk_h[1])), int(round(ijk_h[2]))


# 5x7 font (solo le lettere che ti servono: A..Z, _ e numeri 0..9)
# Ogni glyph è 7 righe da 5 bit: '1' = pixel acceso.
_TF_FONT_5x7 = {
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "C": ["01110","10001","10000","10000","10000","10001","01110"],
    "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "F": ["11111","10000","10000","11110","10000","10000","10000"],
    "G": ["01110","10001","10000","10111","10001","10001","01110"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "I": ["11111","00100","00100","00100","00100","00100","11111"],
    "J": ["00111","00010","00010","00010","10010","10010","01100"],
    "K": ["10001","10010","10100","11000","10100","10010","10001"],
    "L": ["10000","10000","10000","10000","10000","10000","11111"],
    "M": ["10001","11011","10101","10101","10001","10001","10001"],
    "N": ["10001","11001","10101","10011","10001","10001","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "P": ["11110","10001","10001","11110","10000","10000","10000"],
    "Q": ["01110","10001","10001","10001","10101","10010","01101"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "S": ["01111","10000","10000","01110","00001","00001","11110"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "U": ["10001","10001","10001","10001","10001","10001","01110"],
    "V": ["10001","10001","10001","10001","10001","01010","00100"],
    "W": ["10001","10001","10001","10101","10101","11011","10001"],
    "X": ["10001","10001","01010","00100","01010","10001","10001"],
    "Y": ["10001","10001","01010","00100","00100","00100","00100"],
    "Z": ["11111","00001","00010","00100","01000","10000","11111"],
    "_": ["00000","00000","00000","00000","00000","00000","11111"],
    "0": ["01110","10001","10011","10101","11001","10001","01110"],
    "1": ["00100","01100","00100","00100","00100","00100","01110"],
    "2": ["01110","10001","00001","00010","00100","01000","11111"],
    "3": ["11110","00001","00001","01110","00001","00001","11110"],
    "4": ["00010","00110","01010","10010","11111","00010","00010"],
    "5": ["11111","10000","10000","11110","00001","00001","11110"],
    "6": ["01110","10000","10000","11110","10001","10001","01110"],
    "7": ["11111","00001","00010","00100","01000","01000","01000"],
    "8": ["01110","10001","10001","01110","10001","10001","01110"],
    "9": ["01110","10001","10001","01111","00001","00001","01110"],
}


def _tf_stamp_text(fusedArray, refVolumeNode, text, rasXYZ,
                   value, pixelSize=2, thickness=2, spacing=1, offsetIJK=(2,2,0)):
    """
    Disegna testo 5x7 nel volume (array in KJI).
    - pixelSize: quanto "grosso" è ogni pixel della font (in voxel)
    - thickness: spessore in K (numero slice)
    - spacing: spazio tra caratteri (in pixel font)
    - offsetIJK: offset (i,j,k) per non sovrapporre al punto
    """
    if text is None:
        return

    text = str(text).upper()

    i0, j0, k0 = _tf_ras_to_ijk(refVolumeNode, rasXYZ)
    i0 += int(offsetIJK[0])
    j0 += int(offsetIJK[1])
    k0 += int(offsetIJK[2])

    # fusedArray è KJI
    K, J, I = fusedArray.shape

    cursor_i = i0

    for ch in text:
        glyph = _TF_FONT_5x7.get(ch)
        if glyph is None:
            cursor_i += (5 + spacing) * pixelSize
            continue

        for row in range(7):
            bits = glyph[6 - row]
            for col in range(5):
                if bits[col] != "1":
                    continue

                # area in I,J
                ii_start = cursor_i + col * pixelSize
                jj_start = j0 + row * pixelSize
                ii_end = ii_start + pixelSize
                jj_end = jj_start + pixelSize

                # clamp
                if ii_end <= 0 or jj_end <= 0 or ii_start >= I or jj_start >= J:
                    continue

                ii_start = max(0, ii_start); ii_end = min(I, ii_end)
                jj_start = max(0, jj_start); jj_end = min(J, jj_end)

                # thickness in K
                for dk in range(thickness):
                    kk = k0 + dk
                    if 0 <= kk < K:
                        fusedArray[kk, jj_start:jj_end, ii_start:ii_end] = value

        cursor_i += (5 + spacing) * pixelSize


# ============================================================
# ADD-ON (OPTIONAL): Reorient generated volumes to RAS and export to DICOM
# - Does NOT change existing behavior unless the checkbox is enabled
# - Creates an additional RAS-oriented NIfTI file: r-*-RAS.nii.gz
# - Exports a DICOM series using "Create a DICOM Series" module
# ============================================================

def _tf_make_ras_nifti_path(originalNiftiPath: str) -> str:
    """Return path for an additional RAS-oriented NIfTI.

    - Never overwrites the original.
    - Prevents stacking '-RAS' repeatedly (e.g. '-RAS-RAS-RAS').
    """
    import os
    import re

    p = originalNiftiPath
    low = p.lower()

    # Split extension (.nii or .nii.gz)
    ext = ""
    if low.endswith(".nii.gz"):
        ext = ".nii.gz"
        stem = p[:-7]
    elif low.endswith(".nii"):
        ext = ".nii"
        stem = p[:-4]
    else:
        # Unknown extension; keep whole as stem and append default
        stem = p
        ext = ".nii.gz"

    # Collapse any trailing '-RAS' repetitions before the extension
    # e.g. 'file-RAS-RAS' -> 'file-RAS'
    stem = re.sub(r"(-ras)+$", "-RAS", stem, flags=re.IGNORECASE)

    # If already ends with single -RAS, keep it (no further changes)
    if stem.lower().endswith("-ras"):
        return stem + ext

    return stem + "-RAS" + ext





def _tf_run_console_process(args, keep_ui_responsive=True):
    """Run a console process in Slicer and return (exitCode, stdout, stderr).

    Works across Slicer builds where slicer.util.launchConsoleProcess may return
    a qt.QProcess (common) or a subprocess.Popen (some packaged environments).
    """
    import slicer
    import qt

    p = slicer.util.launchConsoleProcess(args)

    # qt.QProcess path
    if hasattr(p, "waitForFinished") and hasattr(p, "readAllStandardOutput"):
        # Keep UI responsive while waiting
        while hasattr(p, "state") and p.state() != qt.QProcess.NotRunning:
            if keep_ui_responsive:
                slicer.app.processEvents()
            p.waitForFinished(50)

        exitCode = p.exitCode() if hasattr(p, "exitCode") else 0
        try:
            stdout = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
        except Exception:
            stdout = ""
        try:
            stderr = bytes(p.readAllStandardError()).decode("utf-8", errors="replace")
        except Exception:
            stderr = ""
        return exitCode, stdout, stderr

    # subprocess.Popen path
    if hasattr(p, "communicate"):
        out, err = p.communicate()
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", errors="replace")
        exitCode = getattr(p, "returncode", 0) or 0
        return exitCode, out or "", err or ""

    # Fallback
    if hasattr(p, "wait"):
        p.wait()
    exitCode = getattr(p, "returncode", 0) or 0
    return exitCode, "", ""



def _tf_get_cli_executable(moduleName: str, exeBaseName: str) -> str:
    """Return full path to a Slicer CLI executable.

    Prefers `slicer.modules.<moduleName>.path` when available.
    Falls back to searching under slicer.app.slicerHome for 'cli-modules/<exeBaseName>'.
    """
    import os
    import glob
    import slicer

    mod = getattr(slicer.modules, moduleName.lower(), None)
    if mod is not None and hasattr(mod, "path") and mod.path:
        return mod.path

    # Fallback: search in Slicer installation
    slicerHome = getattr(slicer.app, "slicerHome", None) or getattr(slicer.app, "applicationDirPath", None)
    if not slicerHome:
        raise RuntimeError(f"Cannot locate Slicer home to find {exeBaseName}")

    # Typical: <Slicer>/Contents/lib/Slicer-*/cli-modules/<exeBaseName> (macOS)
    patterns = [
        os.path.join(slicerHome, "**", "cli-modules", exeBaseName),
        os.path.join(slicerHome, "**", "cli-modules", exeBaseName + ".exe"),
    ]
    for pat in patterns:
        hits = glob.glob(pat, recursive=True)
        if hits:
            return hits[0]

    raise RuntimeError(f"CLI executable not found: {exeBaseName}")


def _tf_orient_nifti_file_to_ras(inputPath: str, outputPath: str) -> None:
    """Run OrientScalarVolume on disk (file->file), producing a RAS-oriented NIfTI."""
    import os
    import slicer

    exe = _tf_get_cli_executable("orientscalarvolume", "OrientScalarVolume")
    args = [exe, inputPath, "-o", "RAS", outputPath]

    exitCode, stdout, stderr = _tf_run_console_process(args)
    if stdout.strip():
        print("[OrientScalarVolume stdout]\n" + stdout)
    if stderr.strip():
        print("[OrientScalarVolume stderr]\n" + stderr)

    if exitCode != 0:
        raise RuntimeError(f"OrientScalarVolume failed (exitCode={exitCode}).")

    if not os.path.exists(outputPath):
        raise RuntimeError(f"RAS output was not created: {outputPath}")


def _tf_reorient_volume_to_ras(inputVolumeNode):
    """Reorient a scalar volume to RAS using Slicer's OrientScalarVolume CLI.

    In Slicer (5.x), OrientScalarVolume accepts an orientation string such as 'RAS'.
    This implementation tries a couple of known parameter-name variants to stay compatible
    across Slicer builds, without changing any other module behavior.
    """
    import slicer

    if not hasattr(slicer.modules, "orientscalarvolume"):
        raise RuntimeError("OrientScalarVolume module is not available in this Slicer installation")

    rasNode = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLScalarVolumeNode", inputVolumeNode.GetName() + "_RAS"
    )

    # Try common CLI parameter-name variants for maximum compatibility.
    param_variants = [
        {  # Most common in Slicer 5.x
            "inputVolume": inputVolumeNode,
            "outputVolume": rasNode,
            "orientation": "RAS",
        },
        {  # Seen in some wrappers / older scripts
            "inputVolume1": inputVolumeNode,
            "outputVolume": rasNode,
            "orientation": "RAS",
        },
        {  # Some builds may use outputOrientation naming
            "inputVolume": inputVolumeNode,
            "outputVolume": rasNode,
            "outputOrientation": "RAS",
        },
        {
            "inputVolume1": inputVolumeNode,
            "outputVolume": rasNode,
            "outputOrientation": "RAS",
        },
    ]

    last_error = None
    for params in param_variants:
        try:
            slicer.cli.run(slicer.modules.orientscalarvolume, None, params, wait_for_completion=True)
            return rasNode
        except Exception as e:
            last_error = e

    # If all variants failed, clean up and raise the last error for visibility.
    try:
        slicer.mrmlScene.RemoveNode(rasNode)
    except Exception:
        pass
    raise last_error

def _tf_export_volume_to_dicom(volumeNode, dicomDir: str, patientName: str, modality: str, seriesDescription: str, dicomPrefix: str=None, studyDescription: str=None, **_ignored_kwargs):
    """Export a NIfTI (or other readable image) to a DICOM series using Slicer's CLI executable.

    IMPORTANT: We intentionally call the *CLI executable* directly (same as your working shell script),
    instead of using `slicer.cli.run()`. In some packaged environments (e.g., PLATiN), the MRML-node
    to temporary-file handoff used by `slicer.cli.run()` can fail, producing logs like:
      - "No input data assigned to Input Volume"
      - missing /T/Slicer-*/...vtkMRMLScalarVolumeNode*.nrrd

    This direct call avoids the temp-NRRD mechanism entirely.
    """
    import os
    import slicer
    import qt

    # We require a file path, because we call the CLI like:
    #   CreateDICOMSeries <inputImage> --dicomDirectory <dir> ...
    if not isinstance(volumeNode, str):
        raise RuntimeError("DICOM export expects an input *file path* (string).")
    inputPath = volumeNode
    if not os.path.exists(inputPath):
        raise RuntimeError(f"Input image file does not exist: {inputPath}")

    os.makedirs(dicomDir, exist_ok=True)

    # Resolve CLI executable path (most reliable: module path)
    cliExe = None
    if hasattr(slicer.modules, "createdicomseries") and hasattr(slicer.modules.createdicomseries, "path"):
        cliExe = slicer.modules.createdicomseries.path

    # Fallback (best-effort) for unusual builds
    if (not cliExe) or (not os.path.exists(cliExe)):
        # Typical macOS layout: <Slicer.app>/Contents/lib/Slicer-5.6/cli-modules/CreateDICOMSeries
        slicerHome = getattr(slicer.app, "slicerHome", None) or getattr(slicer.app, "slicerHomeDir", None) or ""
        if slicerHome:
            # Try to find a Slicer-* directory
            libDir = os.path.join(slicerHome, "lib")
            if os.path.isdir(libDir):
                for d in os.listdir(libDir):
                    if d.lower().startswith("slicer-"):
                        candidate = os.path.join(libDir, d, "cli-modules", "CreateDICOMSeries")
                        if os.path.exists(candidate):
                            cliExe = candidate
                            break

    if (not cliExe) or (not os.path.exists(cliExe)):
        raise RuntimeError("Cannot locate CreateDICOMSeries CLI executable (module not available or path not found).")

    # Match your working script's arguments
    # NOTE: we keep studyDescription = studyDescription if studyDescription else seriesDescription unless caller wants something else.
    patientName = patientName if patientName else "Unknown"
    modality = modality if modality else "MR"
    seriesDescription = seriesDescription if seriesDescription else "TrajectoryFusion"
    studyDescription = seriesDescription

    args = [
        cliExe,
        inputPath,
        "--dicomDirectory", dicomDir,
        "--patientName", patientName,
        "--modality", modality,
        "--seriesDescription", seriesDescription,
        "--studyDescription", studyDescription,
    ]

    # Launch and wait (robust across QProcess/Popen)
    exitCode, stdout, stderr = _tf_run_console_process(args)

    if stdout.strip():
        print("[CreateDICOMSeries stdout]\n" + stdout)
    if stderr.strip():
        print("[CreateDICOMSeries stderr]\n" + stderr)

    if exitCode != 0:
        raise RuntimeError(f"CreateDICOMSeries failed with exit code {exitCode}")


def _tf_export_nifti_as_ras_and_dicom(inputVolumeNode, originalNiftiPath: str, outputDirectory: str,
                                     patientName: str, modality: str, seriesDescription: str):
    """
    1) Reorient generated volume to RAS (creates a temporary RAS node)
    2) Save additional RAS-oriented NIfTI next to the original output
    3) Export the RAS volume as a DICOM series (one series per output volume)
    """
    import os
    import slicer

    # 1) Reorient
    rasNode = _tf_reorient_volume_to_ras(inputVolumeNode)

    try:
        # 2) Save RAS NIfTI (do NOT overwrite the original file)
        rasNiftiPath = _tf_make_ras_nifti_path(originalNiftiPath)
        ok = slicer.util.saveNode(rasNode, rasNiftiPath)
        print(f"[RAS Save] {'✓' if ok else '✗'} {rasNiftiPath}")

        # 3) Export DICOM
        dicomRoot = os.path.join(outputDirectory, "DICOM")
        seriesKey = os.path.basename(originalNiftiPath).replace(".nii.gz", "").replace(".nii", "")
        dicomDir = os.path.join(dicomRoot, seriesKey)
        # Make series description unique but keep user-provided base name
        seriesDescFull = seriesDescription if seriesDescription else "TrajectoryFusion"
        seriesDescFull = f"{seriesDescFull} ({seriesKey})"
        _tf_export_volume_to_dicom(
            volumeNode=rasNiftiPath,
            dicomDir=dicomDir,
            patientName=patientName,
            modality=modality,
            seriesDescription=seriesDescFull,
            dicomPrefix=seriesKey,
        )
        print(f"[DICOM Export] ✓ {dicomDir}")

    finally:
        # cleanup temp node
        try:
            slicer.mrmlScene.RemoveNode(rasNode)
        except Exception:
            pass
