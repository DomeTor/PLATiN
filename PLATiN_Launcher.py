# -*- coding: utf-8 -*-
import slicer
from slicer.ScriptedLoadableModule import *

class PLATiN(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "PLATiN"
        parent.categories = ["PLATiN"]
        parent.dependencies = []
        parent.contributors = []
        parent.helpText = "Launcher for PLATiN tools."
        parent.acknowledgementText = ""

class PLATiNWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        import qt
        layout = self.layout
        layout.addWidget(qt.QLabel("<h2>PLATiN</h2><p>Apri uno dei tool:</p>"))
        b1 = qt.QPushButton("SEEG/LiTT Planner")
        b1.clicked.connect(lambda: slicer.util.selectModule("SEEG_LiTT_Planner"))
        layout.addWidget(b1)
        b2 = qt.QPushButton("Trajectory Fusion")
        b2.clicked.connect(lambda: slicer.util.selectModule("TrajectoryFusion"))
        layout.addWidget(b2)
        layout.addStretch(1)
