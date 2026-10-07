#!/usr/bin/env python3
"""
create_app_icons.py
Generates clean 128x128 RGBA icons for the GT License AC Lua App windows:
- icons/settings.png
- icons/timer.png
- icons/banner.png
- icons/ghost.png
- icons/speedo.png
- icon.png (Main App Icon)
"""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_ICONS_DIR = REPO_ROOT / "apps" / "lua" / "gt_license" / "icons"
APP_ROOT_DIR = REPO_ROOT / "apps" / "lua" / "gt_license"


def create_timer_icon(path: Path):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Circle stopwatch body
    d.ellipse([24, 28, 104, 108], outline=(255, 255, 255, 240), width=6)
    # Top knob
    d.rectangle([58, 12, 70, 26], fill=(255, 255, 255, 240))
    d.rectangle([52, 10, 76, 16], fill=(255, 255, 255, 240))
    # Clock hands
    d.line([64, 68, 64, 40], fill=(255, 215, 0, 255), width=5) # Gold minute hand
    d.line([64, 68, 86, 68], fill=(255, 255, 255, 255), width=4) # Second hand
    # Center pin
    d.ellipse([60, 64, 68, 72], fill=(255, 215, 0, 255))
    im.save(path)


def create_banner_icon(path: Path):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Flag pole
    d.rectangle([20, 16, 26, 112], fill=(200, 200, 200, 240))
    d.ellipse([17, 10, 29, 22], fill=(255, 215, 0, 255))
    # Checkered / License banner flag
    points = [(26, 20), (108, 20), (96, 54), (108, 88), (26, 88)]
    d.polygon(points, fill=(30, 30, 30, 220), outline=(255, 255, 255, 240))
    # Accent stripes
    d.line([(26, 42), (102, 42)], fill=(255, 215, 0, 255), width=4) # Gold
    d.line([(26, 66), (102, 66)], fill=(220, 50, 50, 255), width=4) # Red
    im.save(path)


def create_ghost_icon(path: Path):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Stylized ghost car silhouette / Pacman ghost shape
    # Ghost dome head
    d.pieslice([24, 20, 104, 100], 180, 360, fill=(100, 200, 255, 220), outline=(255, 255, 255, 240))
    # Body
    d.rectangle([24, 60, 104, 96], fill=(100, 200, 255, 220))
    d.line([(24, 60), (24, 96)], fill=(255, 255, 255, 240), width=3)
    d.line([(104, 60), (104, 96)], fill=(255, 255, 255, 240), width=3)
    # Bottom wavy ruffles
    d.polygon([(24, 96), (37, 86), (51, 96), (64, 86), (77, 96), (91, 86), (104, 96)], fill=(100, 200, 255, 220), outline=(255, 255, 255, 240))
    # Eyes
    d.ellipse([42, 48, 56, 64], fill=(255, 255, 255, 255))
    d.ellipse([72, 48, 86, 64], fill=(255, 255, 255, 255))
    d.ellipse([48, 54, 56, 64], fill=(0, 100, 220, 255))
    d.ellipse([78, 54, 86, 64], fill=(0, 100, 220, 255))
    im.save(path)


def create_speedo_icon(path: Path):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Speedometer gauge arc (135 to 405 deg)
    d.arc([20, 20, 108, 108], start=135, end=405, fill=(255, 255, 255, 240), width=6)
    # Redline zone arc
    d.arc([20, 20, 108, 108], start=345, end=405, fill=(240, 50, 50, 255), width=7)
    # Needle pointing towards 280 degrees (~70% max)
    cx, cy = 64, 64
    d.ellipse([58, 58, 70, 70], fill=(255, 215, 0, 255))
    angle = math.radians(240)
    nx = cx + 38 * math.cos(angle)
    ny = cy + 38 * math.sin(angle)
    d.line([cx, cy, nx, ny], fill=(255, 50, 50, 255), width=5)
    im.save(path)


def create_settings_icon(path: Path):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = 64, 64
    outer_r = 44
    inner_r = 32
    num_teeth = 8
    points = []
    for i in range(num_teeth * 2):
        angle = i * (2 * math.pi / (num_teeth * 2))
        r = outer_r if (i % 2 == 0) else inner_r
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        points.append((px, py))
    d.polygon(points, fill=(220, 220, 220, 240))
    # Inner hole
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(0, 0, 0, 0))
    im.save(path)


def main():
    APP_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    APP_ROOT_DIR.mkdir(parents=True, exist_ok=True)

    create_timer_icon(APP_ICONS_DIR / "timer.png")
    create_banner_icon(APP_ICONS_DIR / "banner.png")
    create_ghost_icon(APP_ICONS_DIR / "ghost.png")
    create_settings_icon(APP_ICONS_DIR / "settings.png")

    # Main App icon
    create_timer_icon(APP_ROOT_DIR / "icon.png")
    print("Created all 128x128 icons successfully.")


if __name__ == "__main__":
    main()

