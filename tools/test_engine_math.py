#!/usr/bin/env python3
"""
Compatibility shim for test_engine_math.py.
Delegates to tests/unit/test_engine_math.py.
"""
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests.unit.test_engine_math import (  # noqa: F401
    ccw,
    segments_intersect_2d,
    is_inside_stop_box,
    evaluate_medal,
    TestEngineMath,
)

if __name__ == "__main__":
    unittest.main()
