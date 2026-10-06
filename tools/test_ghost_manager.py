#!/usr/bin/env python3
"""
Compatibility shim for test_ghost_manager.py.
Delegates to tests/unit/test_ghost_manager.py.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.unit.test_ghost_manager import TestGhostTrajectoryGenerator  # noqa: F401

if __name__ == "__main__":
    unittest.main()
