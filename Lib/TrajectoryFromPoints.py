\
# -*- coding: utf-8 -*-
import math, vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

class TrajectoryFromPoints(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Trajectory From Points"
        self.parent.categories = ["IGT", "Utilities"]
        self.parent.contributors = ["Your Name (Your Org)"]
        self.parent.helpText = ("Fibra (cilindro) e necrosi (ellissoide) visibili in 3D e nelle MPR (Intersection, opacity 1.0, line width 5 px).")

class TrajectoryFromPointsWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = TrajectoryFromPointsLogic()
        self.layout.addWidget(qt.QLabel("Crea fibra e necrosi da due Markups. MPR intersection on."))
        box = ctk.ctkCollapsibleButton(); box.text="Parametri"; self.layout.addWidget(box); form=qt.QFormLayout(box)
        self.entryEdit=qt.QLineEdit(); self.entryEdit.placeholderText="Entry label (es. A)"
        self.targetEdit=qt.QLineEdit(); self.targetEdit.placeholderText="Target label (es. A_1)"
        form.addRow("Entry:", self.entryEdit); form.addRow("Target:", self.targetEdit)
        self.onlyVisibleCheck=qt.QCheckBox("Cerca solo Markups visibili"); self.onlyVisibleCheck.checked=False; form.addRow(self.onlyVisibleCheck)
        self.showLineCheck=qt.QCheckBox("Mostra anche la linea Markups"); self.showLineCheck.checked=False; form.addRow(self.showLineCheck)
        self.fiberDiameter=ctk.ctkDoubleSpinBox(); self.fiberDiameter.decimals=2; self.fiberDiameter.minimum=0.2; self.fiberDiameter.maximum=50.0; self.fiberDiameter.value=4.0; form.addRow("Diametro fibra (mm):", self.fiberDiameter)
        self.fiberColor=ctk.ctkColorPickerButton(); self.fiberColor.setColor(qt.QColor(255,85,0)); form.addRow("Colore fibra:", self.fiberColor)
        self.necStartOffset=ctk.ctkDoubleSpinBox(); self.necStartOffset.decimals=2; self.necStartOffset.minimum=0.0; self.necStartOffset.maximum=100.0; self.necStartOffset.value=3.0; form.addRow("Inizio necrosi da A_1 (mm):", self.necStartOffset)
        # (Opzionale) più offset di inizio necrosi, separati da virgole (mm)
        self.multiOffsetsEdit = qt.QLineEdit()
        self.multiOffsetsEdit.setPlaceholderText("es: 0, 5, 12.5")
        form.addRow("Offset multipli (mm):", self.multiOffsetsEdit)
        self.necDiameter=ctk.ctkDoubleSpinBox(); self.necDiameter.decimals=2; self.necDiameter.minimum=1.0; self.necDiameter.maximum=200.0; self.necDiameter.value=10.0; form.addRow("Diametro necrosi (mm):", self.necDiameter)
        self.necLength=ctk.ctkDoubleSpinBox(); self.necLength.decimals=2; self.necLength.minimum=1.0; self.necLength.maximum=200.0; self.necLength.value=15.0; form.addRow("Lunghezza necrosi (mm):", self.necLength)
        self.necColor=ctk.ctkColorPickerButton(); self.necColor.setColor(qt.QColor(50,180,255)); form.addRow("Colore necrosi:", self.necColor)
        self.baseName=qt.QLineEdit(); self.baseName.placeholderText="Se vuoto: Trajectory <entry>→<target>"; form.addRow("Nome base:", self.baseName)
        self.overwriteCheck=qt.QCheckBox("Sovrascrivi output con stesso nome"); self.overwriteCheck.checked=True; form.addRow(self.overwriteCheck)
        self.btn=qt.QPushButton("Genera"); self.layout.addWidget(self.btn); self.status=qt.QLabel(); self.layout.addWidget(self.status); self.layout.addStretch(1)
        self.btn.clicked.connect(self.onGenerate)
        self.updateBtn = qt.QPushButton("Aggiorna traiettoria/necrosi")
        self.layout.addWidget(self.updateBtn)
        self.updateBtn.clicked.connect(self.onUpdate)
    def onGenerate(self):
        entry=self.entryEdit.text.strip(); target=self.targetEdit.text.strip()
        if not entry or not target: slicer.util.errorDisplay("Inserisci le etichette di entry e target."); return
        try:
            offsets_txt=self.multiOffsetsEdit.text.strip()
            if offsets_txt:
                ln, fn, nn = self.logic.runMultipleNecrosis(entry, target, float(self.fiberDiameter.value), offsets_txt,
                                                            float(self.necDiameter.value), float(self.necLength.value),
                                                            self.fiberColor.color, self.necColor.color,
                                                            self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                                                            self.onlyVisibleCheck.checked, self.overwriteCheck.checked, self.showLineCheck.checked)
            else:
                ln, fn, nn = self.logic.run(entry, target, float(self.fiberDiameter.value),
                                        float(self.necStartOffset.value), float(self.necDiameter.value), float(self.necLength.value),
                                        self.fiberColor.color, self.necColor.color,
                                        self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                                        self.onlyVisibleCheck.checked, self.overwriteCheck.checked, self.showLineCheck.checked)
            try: slicer.util.resetThreeDViews()
            except: pass
            self.status.setText(f"Creati: {ln.GetName()}, {fn.GetName()}, {nn.GetName()}")
        except Exception as e:
            slicer.util.errorDisplay(str(e))
    def onUpdate(self):
        # Rigenera forzando la sovrascrittura
        entry=self.entryEdit.text.strip(); target=self.targetEdit.text.strip()
        if not entry or not target: slicer.util.errorDisplay("Inserisci le etichette di entry e target."); return
        try:
            offsets_txt = self.multiOffsetsEdit.text.strip()
            if offsets_txt:
                ln, fn, nn = self.logic.runMultipleNecrosis(entry, target, float(self.fiberDiameter.value),
                                                            offsets_txt,
                                                            float(self.necDiameter.value), float(self.necLength.value),
                                                            self.fiberColor.color, self.necColor.color,
                                                            self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                                                            self.onlyVisibleCheck.checked, True,  # overwrite
                                                            self.showLineCheck.checked)
            else:
                ln, fn, nn = self.logic.run(entry, target, float(self.fiberDiameter.value),
                                            float(self.necStartOffset.value), float(self.necDiameter.value), float(self.necLength.value),
                                            self.fiberColor.color, self.necColor.color,
                                            self.baseName.text.strip() or f"Trajectory {entry}\u2192{target}",
                                            self.onlyVisibleCheck.checked, True, self.showLineCheck.checked)
            try: slicer.util.resetThreeDViews()
            except: pass
            self.status.setText(f"Aggiornati: {ln.GetName()}, {fn.GetName()}, {nn.GetName()}")
        except Exception as e:
            slicer.util.errorDisplay(str(e))

class TrajectoryFromPointsLogic(ScriptedLoadableModuleLogic):
    def _findPointByLabel(self, label, onlyVisible=False):
        for n in slicer.util.getNodesByClass("vtkMRMLMarkupsFiducialNode"):
            if onlyVisible:
                d=n.GetDisplayNode()
                if d and not d.GetVisibility(): continue
            for i in range(n.GetNumberOfControlPoints()):
                if n.GetNthControlPointLabel(i)==label:
                    pos=[0.0,0.0,0.0]; n.GetNthControlPointPositionWorld(i,pos); return pos,n,i
        raise ValueError(f"Punto '{label}' non trovato.")
    def _ensureUniqueNode(self, className, name, overwrite):
        existing=slicer.util.getFirstNodeByClassByName(className, name)
        if existing:
            if overwrite: slicer.mrmlScene.RemoveNode(existing)
            else:
                base=name; idx=1; cand=f"{base} ({idx})"
                while slicer.util.getFirstNodeByClassByName(className, cand): idx+=1; cand=f"{base} ({idx})"
                name=cand
        return name
    def _rgbf(self, qc): return [qc.redF(), qc.greenF(), qc.blueF()]
    def _unit(self, v):
        mag=(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])**0.5
        return [0.0,0.0,1.0] if mag==0 else [v[0]/mag, v[1]/mag, v[2]/mag]
    def _rot_z_to_vec(self, vec):
        z=[0.0,0.0,1.0]; v=self._unit(vec)
        axis=[z[1]*v[2]-z[2]*v[1], z[2]*v[0]-z[0]*v[2], z[0]*v[1]-z[1]*v[0]]
        am=(axis[0]**2+axis[1]**2+axis[2]**2)**0.5
        dot=max(-1.0,min(1.0, z[0]*v[0]+z[1]*v[1]+z[2]*v[2]))
        import math; ang=math.degrees(math.acos(dot))
        return (ang, [1.0,0.0,0.0] if am==0 else [axis[0]/am,axis[1]/am,axis[2]/am])
    def _applySliceIntersectionDisplay(self, displayNode, colorRGBF, thicknessPx=5, opacity=1.0):
        displayNode.SetSliceIntersectionVisibility(1)
        try: displayNode.SetSliceDisplayModeToIntersection()
        except AttributeError:
            try: displayNode.SetSliceDisplayMode(1)
            except Exception: pass
        try: displayNode.SetSliceIntersectionOpacity(opacity)
        except AttributeError: pass
        try: displayNode.SetSliceIntersectionThickness(int(thicknessPx))
        except AttributeError: pass
        displayNode.SetColor(*colorRGBF); displayNode.SetVisibility(1)
    def run(self, entryLabel, targetLabel, fiberDiameterMm, necrosisStartOffsetMm, necrosisDiameterMm, necrosisLengthMm,
            fiberColor, necrosisColor, outputBaseName, searchOnlyVisible, overwrite, showLine):
        pEntry,_,_ = self._findPointByLabel(entryLabel, searchOnlyVisible)
        pTarget,_,_ = self._findPointByLabel(targetLabel, searchOnlyVisible)
        d=[pTarget[0]-pEntry[0], pTarget[1]-pEntry[1], pTarget[2]-pEntry[2]]; u=self._unit(d)
        lineName=self._ensureUniqueNode("vtkMRMLMarkupsLineNode", outputBaseName, overwrite)
        lineNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", lineName)
        lineNode.AddControlPointWorld(pEntry); lineNode.AddControlPointWorld(pTarget)
        ld=lineNode.GetDisplayNode()
        if ld:
            fr,fg,fb=self._rgbf(fiberColor); ld.SetColor(fr,fg,fb); ld.SetSelectedColor(fr,fg,fb); ld.SetLineThickness(1.0); ld.SetPointLabelsVisibility(False); ld.SetVisibility(1 if showLine else 0)
        # Fiber cylinder
        r=max(fiberDiameterMm*0.5, 0.01)
        ls=vtk.vtkLineSource(); ls.SetPoint1(pEntry); ls.SetPoint2(pTarget); ls.Update()
        tf=vtk.vtkTubeFilter(); tf.SetInputConnection(ls.GetOutputPort()); tf.SetRadius(r); tf.SetNumberOfSides(64); tf.CappingOn(); tf.Update()
        fiberPoly=vtk.vtkPolyData(); fiberPoly.DeepCopy(tf.GetOutput())
        fiberName=self._ensureUniqueNode("vtkMRMLModelNode", f"{lineName} (fiber Ø{fiberDiameterMm:.2f}mm)", overwrite)
        fiberNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", fiberName); fiberNode.SetAndObservePolyData(fiberPoly)
        fd=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); fiberNode.SetAndObserveDisplayNodeID(fd.GetID())
        fr,fg,fb=self._rgbf(fiberColor); fd.SetColor(fr,fg,fb); fd.SetOpacity(0.85); fd.SetBackfaceCulling(0); fd.SetScalarVisibility(0); fd.SetVisibility(1)
        self._applySliceIntersectionDisplay(fd, [fr,fg,fb], thicknessPx=5, opacity=1.0)
        # Necrosis ellipsoid
        r_minor=max(necrosisDiameterMm*0.5, 0.01); r_major=max(necrosisLengthMm*0.5, 0.01)
        offset=max(0.0, necrosisStartOffsetMm) + r_major
        center=[pTarget[0]-u[0]*offset, pTarget[1]-u[1]*offset, pTarget[2]-u[2]*offset]
        ell=vtk.vtkParametricEllipsoid(); ell.SetXRadius(r_minor); ell.SetYRadius(r_minor); ell.SetZRadius(r_major)
        src=vtk.vtkParametricFunctionSource(); src.SetParametricFunction(ell); src.SetUResolution(64); src.SetVResolution(64); src.Update()
        ang, axis = self._rot_z_to_vec(u); T=vtk.vtkTransform(); T.PostMultiply(); T.RotateWXYZ(ang, axis); T.Translate(center)
        tpf=vtk.vtkTransformPolyDataFilter(); tpf.SetInputConnection(src.GetOutputPort()); tpf.SetTransform(T); tpf.Update()
        necPoly=vtk.vtkPolyData(); necPoly.DeepCopy(tpf.GetOutput())
        necName=self._ensureUniqueNode("vtkMRMLModelNode", f"{lineName} (necrosi)", overwrite)
        necNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", necName); necNode.SetAndObservePolyData(necPoly)
        nd=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); necNode.SetAndObserveDisplayNodeID(nd.GetID())
        nr,ng,nb=self._rgbf(necrosisColor); nd.SetColor(nr,ng,nb); nd.SetOpacity(0.6); nd.SetBackfaceCulling(0); nd.SetScalarVisibility(0); nd.SetVisibility(1)
        self._applySliceIntersectionDisplay(nd, [nr,ng,nb], thicknessPx=5, opacity=1.0)
        return lineNode, fiberNode, necNode
    def runMultipleNecrosis(self, entryLabel, targetLabel, fiberDiameterMm, offsets_txt,
                            necrosisDiameterMm, necrosisLengthMm,
                            fiberColor, necrosisColor, outputBaseName, searchOnlyVisible, overwrite, showLine):
        # Trova entry/target
        pEntry,_,_ = self._findPointByLabel(entryLabel, searchOnlyVisible)
        pTarget,_,_ = self._findPointByLabel(targetLabel, searchOnlyVisible)
        d=[pTarget[0]-pEntry[0], pTarget[1]-pEntry[1], pTarget[2]-pEntry[2]]; u=self._unit(d)

        # Linea come nell'originale
        lineName=self._ensureUniqueNode("vtkMRMLMarkupsLineNode", outputBaseName, overwrite)
        lineNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", lineName)
        lineNode.AddControlPointWorld(pEntry); lineNode.AddControlPointWorld(pTarget)
        ld=lineNode.GetDisplayNode()
        if ld:
            fr,fg,fb=self._rgbf(fiberColor); ld.SetColor(fr,fg,fb); ld.SetLineThickness(1.0); ld.SetPointLabelsVisibility(False); ld.SetVisibility(1 if showLine else 0)

        # Fibra come nell'originale (tube da linea)
        r=max(fiberDiameterMm*0.5, 0.01)
        ls=vtk.vtkLineSource(); ls.SetPoint1(pEntry); ls.SetPoint2(pTarget); ls.Update()
        tf=vtk.vtkTubeFilter(); tf.SetInputConnection(ls.GetOutputPort()); tf.SetRadius(r); tf.SetNumberOfSides(64); tf.CappingOn(); tf.Update()
        fiberPoly=vtk.vtkPolyData(); fiberPoly.DeepCopy(tf.GetOutput())
        fiberName=self._ensureUniqueNode("vtkMRMLModelNode", f"{lineName} (fiber Ø{fiberDiameterMm:.2f}mm)", overwrite)
        fiberNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", fiberName); fiberNode.SetAndObservePolyData(fiberPoly)
        fd=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); fiberNode.SetAndObserveDisplayNodeID(fd.GetID())
        fr,fg,fb=self._rgbf(fiberColor); fd.SetColor(fr,fg,fb); fd.SetOpacity(0.6); fd.SetBackfaceCulling(0); fd.SetScalarVisibility(0); fd.SetVisibility(1)
        self._applySliceIntersectionDisplay(fd, [fr,fg,fb], thicknessPx=3, opacity=0.7)

        # Parse offsets multipli
        values=[]
        if offsets_txt:
            txt = offsets_txt.replace(';', ',')
            for part in txt.split(','):
                s = part.strip().replace(',', '.')
                if s:
                    try: values.append(float(s))
                    except: pass
        if not values: values=[0.0]

        # Funzione per creare una necrosi come nell'originale, variando l'offset
        def _necrosis_node(idx, offsetFromTargetMm):
            r_minor=max(necrosisDiameterMm*0.5, 0.01); r_major=max(necrosisLengthMm*0.5, 0.01)
            offset=max(0.0, offsetFromTargetMm) + r_major
            center=[pTarget[0]-u[0]*offset, pTarget[1]-u[1]*offset, pTarget[2]-u[2]*offset]
            ell=vtk.vtkParametricEllipsoid(); ell.SetXRadius(r_minor); ell.SetYRadius(r_minor); ell.SetZRadius(r_major)
            src=vtk.vtkParametricFunctionSource(); src.SetParametricFunction(ell); src.SetUResolution(64); src.SetVResolution(64); src.Update()
            ang, axis = self._rot_z_to_vec(u); T=vtk.vtkTransform(); T.PostMultiply(); T.RotateWXYZ(ang, axis); T.Translate(center)
            tpf=vtk.vtkTransformPolyDataFilter(); tpf.SetInputConnection(src.GetOutputPort()); tpf.SetTransform(T); tpf.Update()
            necPoly=vtk.vtkPolyData(); necPoly.DeepCopy(tpf.GetOutput())
            necName=self._ensureUniqueNode("vtkMRMLModelNode", f"{lineName} (necrosi {idx})", overwrite)
            necNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", necName); necNode.SetAndObservePolyData(necPoly)
            nd=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode"); necNode.SetAndObserveDisplayNodeID(nd.GetID())
            nr,ng,nb=self._rgbf(necrosisColor); nd.SetColor(nr,ng,nb); nd.SetOpacity(0.4); nd.SetBackfaceCulling(0); nd.SetScalarVisibility(0); nd.SetVisibility(1)
            self._applySliceIntersectionDisplay(nd, [nr,ng,nb], thicknessPx=5, opacity=1.0)
            return necNode

        last=None
        for idx, off in enumerate(values, 1):
            last = _necrosis_node(idx, off)

        return lineNode, fiberNode, last
