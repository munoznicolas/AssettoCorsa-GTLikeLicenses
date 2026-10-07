#!/usr/bin/env python3
"""
simulate_all_tests.py
Headless Kinematic Simulation & Adjudication Harness for Assetto Corsa GT Licenses.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.content.simulator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.simulator import (
    HeadlessAdjudicator,
    evaluate_medal,
    main,
    point_in_stop_box,
    segments_intersect_2d,
    simulate_single_test,
)

__all__ = [
    "HeadlessAdjudicator",
    "evaluate_medal",
    "point_in_stop_box",
    "segments_intersect_2d",
    "simulate_single_test",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
