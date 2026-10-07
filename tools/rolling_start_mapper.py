#!/usr/bin/env python3
"""
rolling_start_mapper.py
Assetto Corsa Rolling Start Straight Line Analyzer & Interactive Circuit Mapper.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.spline.circuit_mapper` and `tools.spline.templates`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.circuit_mapper import (
    CURRICULUM_TRACKS,
    OFFICIAL_KUNOS_TRACKS,
    discover_kunos_tracks,
    generate_interactive_html,
    main,
    print_cli_summary,
    serialize_spline_data,
)

__all__ = [
    "OFFICIAL_KUNOS_TRACKS",
    "CURRICULUM_TRACKS",
    "discover_kunos_tracks",
    "serialize_spline_data",
    "print_cli_summary",
    "generate_interactive_html",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
