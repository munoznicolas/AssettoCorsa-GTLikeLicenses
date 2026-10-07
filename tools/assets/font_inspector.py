#!/usr/bin/env python3
"""
font_inspector.py
TrueType Font (TTF) Metadata and PostScript Name Inspector for Assetto Corsa CSP DWrite.
"""

import os
from pathlib import Path
from fontTools.ttLib import TTFont

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def inspect_fonts(font_dir: Path = None):
    if font_dir is None:
        font_dir = REPO_ROOT / "assets" / "fonts"

    if not font_dir.is_dir():
        print(f"Font directory not found: {font_dir}")
        return

    for fn in sorted(os.listdir(font_dir)):
        if fn.endswith(".ttf"):
            f = TTFont(os.path.join(font_dir, fn))
            name_record = f["name"]
            family = name_record.getDebugName(1)
            subfamily = name_record.getDebugName(2)
            full = name_record.getDebugName(4)
            postscript = name_record.getDebugName(6)
            weight = f["OS/2"].usWeightClass if "OS/2" in f else "N/A"
            print(f"{fn:28s} | Weight: {weight:<4} | Family: '{family}' | Subfamily: '{subfamily}' | PostScript: '{postscript}'")


def main():
    inspect_fonts()


if __name__ == "__main__":
    main()

