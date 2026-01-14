# PLATiN automated tests

PLATiN includes automated unit tests that can be executed inside 3D Slicer using its embedded Python interpreter.

# Requirements

3D Slicer (tested with recent stable versions)
macOS / Linux
PLATiN source code cloned locally

#Running the tests

From a terminal, run:
/Applications/Slicer.app/Contents/MacOS/Slicer --no-splash \
  --python-script "/absolute/path/to/PLATiN_Package_v3/Tests/run_tests.py"

#Note

Tests must be executed using Slicer’s Python environment.
Running them with a system Python interpreter is not supported.

#Expected output

A successful test run produces output similar to the following:
[PLATiN tests] root_dir = /path/to/PLATiN_Package_v3
[PLATiN tests] tests_dir = /path/to/PLATiN_Package_v3/Tests

test_litt_multiple_necrosis_creates_expected_nodes
    (test_platin_geometry.TestPLATiNGeometry) ... ok
test_seeg_run_creates_line_and_model
    (test_platin_geometry.TestPLATiNGeometry) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.2s

OK
Warnings related to VTK deprecations or Slicer settings may be printed but do not indicate test failures.
The process exits with code 0 when all tests pass.
