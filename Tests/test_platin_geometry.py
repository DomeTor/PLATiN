# -*- coding: utf-8 -*-
"""Minimal automated correctness checks for PLATiN.

Notes
-----
These tests are designed to run inside 3D Slicer (Python environment with VTK/Qt/Slicer API).
They focus on geometric consistency of:
  - trajectory definition from entry/target points
  - SEEG electrode contact/shaft model generation
  - LiTT necrosis model generation for multiple offsets

They do NOT attempt to validate clinical safety or optimize trajectories.
"""

import math
import unittest

import slicer

# Import PLATiN modules (they must be available in Slicer additional module paths)
import SEEG_LiTT_Planner
import TrajectoryFromPoints


class TestPLATiNGeometry(unittest.TestCase):

    def setUp(self):
        # Start with a clean scene for each test
        slicer.mrmlScene.Clear(0)

        # Create a fiducial node with two control points: Entry and Target
        self.fids = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "F")
        self.fids.AddControlPointWorld([0.0, 0.0, 0.0], "E")
        self.fids.AddControlPointWorld([0.0, 0.0, 100.0], "T")

    def _distance(self, a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

    def test_seeg_run_creates_line_and_model(self):
        logic = SEEG_LiTT_Planner.SEEG_LiTT_PlannerLogic()

        # Parameters kept simple and deterministic
        lineNode, elecNode = logic.runSEEG(
            entryLabel="E",
            targetLabel="T",
            nContacts=4,
            contactLenMm=2.0,
            gapLenMm=1.5,
            contactRadiusMm=0.4,
            shaftRadiusMm=0.7,
            shaftColor=slicer.util.getNode("vtkMRMLColorTableNodeFileGenericAnatomyColors") if False else slicer.app.palette().windowText(),  # placeholder, color not tested
            contactColor=slicer.app.palette().text(),
            outputBaseName="SEEG_E_T",
            searchOnlyVisible=False,
            overwrite=True,
            showLine=True,
            electrodeName="",
        )

        self.assertIsNotNone(lineNode)
        self.assertIsNotNone(elecNode)
        self.assertEqual(lineNode.GetNumberOfControlPoints(), 2)

        p0 = [0.0, 0.0, 0.0]
        p1 = [0.0, 0.0, 0.0]
        lineNode.GetNthControlPointPositionWorld(0, p0)
        lineNode.GetNthControlPointPositionWorld(1, p1)

        self.assertAlmostEqual(self._distance(p0, p1), 100.0, places=3)

        poly = elecNode.GetPolyData()
        self.assertIsNotNone(poly)
        self.assertGreater(poly.GetNumberOfPoints(), 0)

    def test_litt_multiple_necrosis_creates_expected_nodes(self):
        logic = TrajectoryFromPoints.TrajectoryFromPointsLogic()

        # Use multiple offsets; parsing supports commas and semicolons in the module
        offsets_txt = "0, 10; 20"
        lineNode, fiberNode, lastNecNode = logic.runMultipleNecrosis(
            entryLabel="E",
            targetLabel="T",
            fiberDiameterMm=1.65,
            offsets_txt=offsets_txt,
            necrosisDiameterMm=12.0,
            necrosisLengthMm=30.0,
            fiberColor=slicer.app.palette().windowText(),
            necrosisColor=slicer.app.palette().text(),
            outputBaseName="LiTT_E_T",
            searchOnlyVisible=False,
            overwrite=True,
            showLine=True,
        )

        self.assertIsNotNone(lineNode)
        self.assertIsNotNone(fiberNode)
        self.assertIsNotNone(lastNecNode)

        # Count generated necrosis model nodes
        model_nodes = slicer.util.getNodesByClass("vtkMRMLModelNode")
        nec_nodes = [n for n in model_nodes if "(necrosi" in n.GetName()]
        self.assertEqual(len(nec_nodes), 3)

        # Fiber polydata should exist
        self.assertIsNotNone(fiberNode.GetPolyData())
        self.assertGreater(fiberNode.GetPolyData().GetNumberOfPoints(), 0)


if __name__ == "__main__":
    unittest.main()
