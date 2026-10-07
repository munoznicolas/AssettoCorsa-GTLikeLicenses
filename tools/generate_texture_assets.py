#!/usr/bin/env python3
"""
generate_texture_assets.py
Procedural RGBA Texture Asset Generator for Assetto Corsa GT Licenses.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.assets.texture_generator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.assets.texture_generator import (
    draw_finish_ribbon,
    draw_medal,
    draw_start_ribbon,
    main,
)

__all__ = [
    "draw_medal",
    "draw_start_ribbon",
    "draw_finish_ribbon",
    "main",
]

if __name__ == "__main__":
    main()
