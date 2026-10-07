#!/usr/bin/env python3
"""
track_straight_analyzer.py
Assetto Corsa Spline Kinematics & Straight Segment Detection Engine.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.spline.straight_analyzer`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.straight_analyzer import (
    RollingStartCandidate,
    StraightSegment,
    TrackStraightAnalyzer,
    angle_diff_deg,
    compass_heading_to_label,
)

__all__ = [
    "StraightSegment",
    "RollingStartCandidate",
    "TrackStraightAnalyzer",
    "compass_heading_to_label",
    "angle_diff_deg",
]

if __name__ == "__main__":
    sys.exit(main())
