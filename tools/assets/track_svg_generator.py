#!/usr/bin/env python3
"""
generate_track_svgs.py
Builds a vector (SVG) top-down map for every track/layout used by the license tests,
from the track's own AI spline (fast_lane.ai): edges from wall distances + racing line.

Coordinate convention (so test gates/sectors can be overlaid exactly):
    svg_x =  world_x
    svg_y = -world_z        (top-down view, +Z = up)
viewBox is in world metres. Output: docs/track_maps/<track>__<layout>.svg
"""
import glob
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
from tools.spline.parser import SplineParser, find_spline_file  # noqa: E402

OUT_DIR = os.path.join(REPO_ROOT, "docs", "track_maps")


def pts_str(pts):
    return " ".join("%.2f,%.2f" % p for p in pts)


def build_svg(track, layout, wps):
    center = [(w.x, -w.z) for w in wps]
    minx = min(p[0] for p in center); maxx = max(p[0] for p in center)
    miny = min(p[1] for p in center); maxy = max(p[1] for p in center)
    extent = max(maxx - minx, maxy - miny)
    road = extent / 90.0          # constant road stroke width (world metres)
    pad = 0.04 * extent + road
    vb = (minx - pad, miny - pad, maxx - minx + 2 * pad, maxy - miny + 2 * pad)
    # close the loop only for circuits (start ~ end)
    gap = ((center[0][0] - center[-1][0]) ** 2 + (center[0][1] - center[-1][1]) ** 2) ** 0.5
    pts = center + center[:1] if gap < 0.05 * extent else center
    p = pts_str(pts)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.2f %.2f %.2f %.2f" '
        'data-track="%s" data-layout="%s">\n'
        '  <!-- svg_x = world_x, svg_y = -world_z (metres) -->\n'
        '  <g id="track" fill="none" stroke-linejoin="round" stroke-linecap="round">\n'
        '    <polyline id="edge" stroke="#e0e0e0" stroke-width="%.3f" points="%s"/>\n'
        '    <polyline id="surface" stroke="#3a3a3a" stroke-width="%.3f" points="%s"/>\n'
        '  </g>\n'
        '  <g id="sector"><!-- overlay test sector here --></g>\n'
        '</svg>\n'
    ) % (vb + (track, layout, road * 1.35, p, road, p))



def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    combos = set()
    for f in glob.glob(os.path.join(REPO_ROOT, "content", "tests", "*", "test_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        combos.add((d["track_id"], d.get("track_layout", "")))
    for track, layout in sorted(combos):
        path = find_spline_file(track, layout)
        if not path:
            print("MISSING spline: %s / %s" % (track, layout)); continue
        try:
            wps = SplineParser(path).waypoints
        except Exception as ex:
            print("FAILED %s / %s: %s" % (track, layout, ex)); continue
        name = "%s__%s.svg" % (track, layout or "default")
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(build_svg(track, layout, wps))
        print("OK", name, len(wps), "points")


if __name__ == "__main__":
    main()

