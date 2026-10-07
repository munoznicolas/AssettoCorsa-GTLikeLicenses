#!/usr/bin/env python3
"""
extract_spline_coords.py
Assetto Corsa AI Spline (fast_lane.ai / ideal_line.ai) Parser & Coordinate Extractor.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.spline.parser`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.parser import (
    DEFAULT_AC_ROOT,
    GateDefinition,
    SpawnDefinition,
    SplineParser,
    SplineWaypoint,
    StopBoxDefinition,
    find_spline_file,
    generate_test_parameters,
    main,
)

__all__ = [
    "DEFAULT_AC_ROOT",
    "SplineWaypoint",
    "GateDefinition",
    "StopBoxDefinition",
    "SpawnDefinition",
    "SplineParser",
    "find_spline_file",
    "generate_test_parameters",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
