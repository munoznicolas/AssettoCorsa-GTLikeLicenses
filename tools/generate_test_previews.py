#!/usr/bin/env python3
"""
generate_test_previews.py
Zoomed 1024x576 PNG per test (Content Manager career event preview size),
framed on the orange start->finish stretch with surrounding track as context.
Output: assets/previews/tests/<TEST_ID>.png  (picked up by tools/content/generator.py)
"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from tools.spline.parser import SplineParser, find_spline_file  # noqa: E402
from tools.generate_test_maps import sector_indices  # noqa: E402

OUT_DIR = os.path.join(REPO_ROOT, "assets", "previews", "tests")
W, H, SS = 1024, 576, 2          # output size, supersampling factor
MARGIN = 0.12                    # empty border around the stretch (fraction)
MIN_SPAN_M = 120.0               # never zoom closer than this (metres)


def render(test, wps):
    pts = [(w.x, w.z) for w in wps]
    idx, _ = sector_indices(test, pts)
    sec = [pts[i] for i in idx]
    xs = [p[0] for p in sec]; zs = [p[1] for p in sec]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    spanx = max(max(xs) - min(xs), MIN_SPAN_M)
    spanz = max(max(zs) - min(zs), MIN_SPAN_M * H / W)
    scale = min(W * (1 - 2 * MARGIN) / spanx, H * (1 - 2 * MARGIN) / spanz) * SS

    def tp(p):  # world (x,z) -> pixel, +Z up
        return ((p[0] - cx) * scale + W * SS / 2, -(p[1] - cz) * scale + H * SS / 2)

    img = Image.new("RGB", (W * SS, H * SS), (27, 27, 27))
    d = ImageDraw.Draw(img)

    def stroke(points, width, color):
        px = [tp(p) for p in points]
        d.line(px, fill=color, width=int(width), joint="curve")
        r = width / 2
        for x, y in px:  # round joins/caps at every vertex (avoids PIL joint artefacts)
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    road = 22 * SS
    stroke(pts, road * 1.3, (119, 119, 119))
    stroke(pts, road, (42, 42, 42))
    stroke(sec, road * 0.8, (255, 159, 26))
    for is_start, col in ((True, (46, 204, 113)), (False, (255, 59, 48))):
        target_idx = idx[0] if is_start else idx[-1]
        wp = pts[target_idx]
        w = wps[target_idx]
        nx, nz = w.normal[0], w.normal[2]
        nl = (nx * nx + nz * nz) ** 0.5 or 1.0
        nx, nz = nx / nl, nz / nl
        target_len_m = (road * 1.5) / scale
        half = target_len_m / 2.0
        gp1 = tp((wp[0] - nx * half, wp[1] - nz * half))
        gp2 = tp((wp[0] + nx * half, wp[1] + nz * half))
        d.line([gp1, gp2], fill=col, width=int(5 * SS))
    sp = test.get("spawn", {}).get("position")
    if sp:
        x, y = tp((sp[0], sp[2])); r = 9 * SS
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 212, 0), outline=(0, 0, 0), width=2 * SS)
    return img.resize((W, H), Image.LANCZOS)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cache = {}
    for f in sorted(glob.glob(os.path.join(REPO_ROOT, "content", "tests", "*", "test_*.json"))):
        t = json.load(open(f, encoding="utf-8"))
        key = (t["track_id"], t.get("track_layout", ""))
        if key not in cache:
            p = find_spline_file(*key)
            cache[key] = SplineParser(p).waypoints if p else None
        if not cache[key]:
            print("SKIP", t["test_id"], key); continue
        render(t, cache[key]).save(os.path.join(OUT_DIR, t["test_id"] + ".png"))
        print("OK", t["test_id"])


if __name__ == "__main__":
    main()
