<p align="center">
  <img src="./Resources/Icons/SEEG_LiTT_Planner_LOGO.png" width="380" alt="PLATiN logo">
</p>

# PLATiN

**PLATiN** is a package of **3D Slicer scripted modules** for stereotactic trajectory planning in **SEEG** and **LiTT** workflows.

**Version:** v3  
**Distribution:** self-contained

This package is fully self-contained and **does not require any older or external copies** of the modules.

---

## Overview

PLATiN provides tools to:
- plan straight stereotactic trajectories from user-defined entry and target points,
- model LiTT fibers and necrosis volumes,
- model SEEG electrodes and contacts,
- visualize trajectories using trajectory-based MPR views,
- export fused trajectory volumes in NIfTI and DICOM formats.

All planning operations are **purely geometry-based** and rely exclusively on fiducial points defined by the user.

---

## Included Modules

The package includes the following Python files:

- **SEEG_LiTT_Planner.py**  
  Visible module (Category: `PLATiN`)  
  Main interface for SEEG and LiTT trajectory planning.

- **TrajectoryFusion.py**  
  Visible module (Category: `PLATiN`)  
  Batch generation of fused NIfTI volumes and optional RAS/DICOM export.

- **PLATiN_Launcher.py**  
  Hidden module  
  Adds a top menu bar entry named **“PLATiN”**.

- **TrajectoryFromPoints.py**  
  Backend logic used internally by `SEEG_LiTT_Planner.py`.  
  Loaded directly from the same folder and not exposed as a standalone module.

---

## Installation

1. Open **3D Slicer**
2. Go to **Edit → Application Settings → Modules**
3. Add the folder containing the PLATiN `.py` files to  
   **Additional module paths**
4. Restart **3D Slicer**

After restarting, the modules will be available under the **PLATiN** category.

---

## Documentation

Detailed usage instructions are available in the **GitHub Wiki**, including:

- Naming and Markups Conventions  
- LiTT Trajectory Planning and Necrosis Modeling  
- SEEG Trajectory Planning  
- Trajectory-Based MPR Views  
- Trajectory Fusion and Export to NIfTI / DICOM  

---

## Notes and Limitations

- Only straight trajectories are supported.
- No anatomical constraints or collision checking are performed.
- No image-based optimization or tissue simulation is included.
- All outputs are derived exclusively from user-defined fiducial points.

---

## License

License information can be added here.

---

## Citation

If you use PLATiN in academic work, please cite appropriately.  

Tortora D, Couto R, Panzeri S, Parodi C, Resaz M, Ramaglia A, Pacetti M, Nobile G, Francione S, Consales A, Severino M, Rossi A. Advanced neuroimaging in pediatric epilepsy surgery: state of the art and future perspectives. Neuroradiology. 2025 Nov 29. doi: 10.1007/s00234-025-03859-9. Epub ahead of print. PMID: 41317206.
