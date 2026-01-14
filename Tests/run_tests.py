# -*- coding: utf-8 -*-
"""Run PLATiN automated tests inside 3D Slicer.

Linux/macOS:
  Slicer --no-splash --python-script /path/to/PLATiN/Tests/run_tests.py
"""

import sys
import pathlib
import unittest

try:
    import slicer  # noqa: F401
except Exception as e:
    print("ERROR: This test runner must be executed inside 3D Slicer.")
    print(e)
    sys.exit(1)

def main():
    # Directory layout expected:
    #   PLATiN_Package_v3/
    #     SEEG_LiTT_Planner.py
    #     TrajectoryFromPoints.py
    #     ...
    #     Tests/
    #       run_tests.py
    #       test_platin_geometry.py
    this_file = pathlib.Path(__file__).resolve()
    tests_dir = this_file.parent
    root_dir = tests_dir.parent

    # Make sure PLATiN root is importable (so tests can "import SEEG_LiTT_Planner", etc.)
    sys.path.insert(0, str(root_dir))

    # Sanity check
    if not tests_dir.exists():
        print(f"ERROR: Tests directory not found: {tests_dir}")
        sys.exit(1)

    print(f"[PLATiN tests] root_dir = {root_dir}")
    print(f"[PLATiN tests] tests_dir = {tests_dir}")

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(tests_dir),
        pattern="test_*.py",
        top_level_dir=str(tests_dir),
    )

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
