#!/usr/bin/env python3
"""
generate_test_maps.py
One SVG per license test: the full track map with the section between the test's
start gate and finish gate highlighted (plus gate / spawn markers).
Output: docs/test_maps/<TEST_ID>.svg
"""
import glob
import html
import json
import math
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from tools.spline.parser import SplineParser, find_spline_file  # noqa: E402
from tools.generate_track_svgs import pts_str  # noqa: E402

OUT_DIR = os.path.join(REPO_ROOT, "docs", "test_maps")


def mid(g):
    return ((g["p1"][0] + g["p2"][0]) / 2, (g["p1"][2] + g["p2"][2]) / 2)


def nearest(center, x, z):
    return min(range(len(center)), key=lambda i: (center[i][0] - x) ** 2 + (center[i][1] - z) ** 2)


def sector_indices(test, pts):
    """Return (indices of the spline stretch between start/finish gates, is_closed_circuit)."""
    n = len(pts)
    sg, fg = test["timing"]["start_gate"], test["timing"]["finish_gate"]
    s = nearest(pts, *mid(sg)); f = nearest(pts, *mid(fg))
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    extent = max(max(xs) - min(xs), max(zs) - min(zs))
    gap = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    closed = gap < 0.05 * extent
    if closed:
        span = (f - s) % n
        idx = [(s + k) % n for k in range(span + 1)]
        if span < 3:  # start == finish: full lap
            idx = [(s + k) % n for k in range(n + 1)]
    else:
        a, b = sorted((s, f)); idx = list(range(a, b + 1))
    return idx, closed


def build(test, wps):
    pts = [(w.x, w.z) for w in wps]  # world x, z
    sg, fg = test["timing"]["start_gate"], test["timing"]["finish_gate"]
    idx, closed = sector_indices(test, pts)
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    extent = max(max(xs) - min(xs), max(zs) - min(zs))
    flip = lambda p: (p[0], -p[1])
    base = [flip(p) for p in pts] + ([flip(pts[0])] if closed else [])
    hi = [flip(pts[i]) for i in idx]
    road = extent / 90.0
    pad = 0.04 * extent + road
    vb = (min(xs) - pad, -max(zs) - pad, max(xs) - min(xs) + 2 * pad, max(zs) - min(zs) + 2 * pad)
    r = road * 1.2

    def gate(is_start, color):
        target_idx = idx[0] if is_start else idx[-1]
        wp = pts[target_idx]
        w = wps[target_idx]
        nx, nz = w.normal[0], w.normal[2]
        nl = math.hypot(nx, nz) or 1.0
        nx, nz = nx / nl, nz / nl
        half = (road * 1.6) / 2.0
        x1, z1 = wp[0] - nx * half, wp[1] - nz * half
        x2, z2 = wp[0] + nx * half, wp[1] + nz * half
        return ('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%.2f"/>'
                % (x1, -z1, x2, -z2, color, road * 0.5))
    sp = test.get("spawn", {}).get("position")
    spawn = ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#ffd400" stroke="#000" stroke-width="%.2f"/>'
             % (sp[0], -sp[2], r * 0.7, road * 0.15)) if sp else ""
    title = html.escape("%s: %s (%s / %s)" % (test["test_id"], test["title"], test["track_id"], test.get("track_layout", "")))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.2f %.2f %.2f %.2f">\n'
        '  <title>%s</title>\n'
        '  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#1b1b1b"/>\n'
        '  <g fill="none" stroke-linejoin="round" stroke-linecap="round">\n'
        '    <polyline stroke="#777" stroke-width="%.2f" points="%s"/>\n'
        '    <polyline stroke="#2a2a2a" stroke-width="%.2f" points="%s"/>\n'
        '    <polyline id="test-sector" stroke="#ff9f1a" stroke-width="%.2f" points="%s"/>\n'
        '  </g>\n'
        '  %s\n  %s\n  %s\n'
        '</svg>\n'
    ) % (vb + (title,) + vb + (road * 1.35, pts_str(base), road, pts_str(base),
                              road * 1.5, pts_str(hi),
                              gate(True, "#2ecc71"), gate(False, "#ff3b30"), spawn))


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
        with open(os.path.join(OUT_DIR, t["test_id"] + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(build(t, cache[key]))
        print("OK", t["test_id"])


if __name__ == "__main__":
    main()

