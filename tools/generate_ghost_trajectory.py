#!/usr/bin/env python3
"""
generate_ghost_trajectory.py
Generates physics-calibrated Gold medal ghost trajectories for Assetto Corsa GT License tests.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.telemetry.ghost_generator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.telemetry.ghost_generator import (
    compute_curvature_radius,
    generate_ghost_profile,
    main,
    segments_intersect_2d,
)

__all__ = [
    "compute_curvature_radius",
    "segments_intersect_2d",
    "generate_ghost_profile",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
