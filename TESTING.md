# PLATiN automated tests

This folder contains minimal automated correctness checks intended to satisfy
the JOSS criterion: "procedures (such as automated tests) for checking correctness".

## Requirements
- 3D Slicer (run tests inside Slicer; the tests rely on the Slicer Python environment)

## How to run
Ensure the PLATiN modules are available via "Additional module paths" in Slicer,
then run:

- Linux/macOS:
  Slicer --no-splash --python-script Tests/run_tests.py

- Windows (PowerShell):
  .\Slicer.exe --no-splash --python-script Tests\run_tests.py

The process exits with code 0 on success and 1 on failure.

## What is tested
- SEEG: generation of a trajectory line and electrode model from entry/target fiducials
- LiTT: generation of multiple necrosis models from a list of offsets
- Basic polydata existence and minimal geometric sanity checks

## What is NOT tested
- Clinical validation, collision checking, safety margins, or trajectory optimization
- DICOM interoperability with specific vendors/robotic systems
