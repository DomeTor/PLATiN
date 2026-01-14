# -*- coding: utf-8 -*-
"""Run PLATiN automated tests inside 3D Slicer.

Usage (examples):
  - Linux/macOS:
      Slicer --no-splash --python-script Tests/run_tests.py
  - Windows (PowerShell):
      .\Slicer.exe --no-splash --python-script Tests\run_tests.py

The script exits with code 0 on success and 1 on failure.
"""

import sys
import unittest

# Ensure Slicer is fully initialized
try:
    import slicer  # noqa: F401
except Exception as e:
    print("ERROR: This test runner must be executed inside 3D Slicer.")
    print(e)
    sys.exit(1)

def main():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="Tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
