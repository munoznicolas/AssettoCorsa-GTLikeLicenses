#!/usr/bin/env python3
"""
inspect_fonts.py
TrueType Font (TTF) Inspector for Assetto Corsa CSP DWrite.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.assets.font_inspector`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.assets.font_inspector import inspect_fonts, main

__all__ = ["inspect_fonts", "main"]

if __name__ == "__main__":
    main()
