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
from typing import Dict, Optional

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
        return ('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s"/>'
                % (wp[0], -wp[1], road / 2.0, color))
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


def generate_maps(
    ac_root: str = None,
    out_dir: str = OUT_DIR,
    tests_dir: str = None,
) -> int:
    """Generates vector SVG track maps with highlighted test sector for all tests."""
    from tools.spline.parser import DEFAULT_AC_ROOT
    if ac_root is None:
        ac_root = DEFAULT_AC_ROOT
    if tests_dir is None:
        tests_dir = os.path.join(REPO_ROOT, "content", "tests")

    os.makedirs(out_dir, exist_ok=True)
    cache = {}
    count = 0
    test_files = sorted(glob.glob(os.path.join(tests_dir, "*", "test_*.json")))
    for f in test_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                t = json.load(fh)
        except Exception:
            continue
        key = (t["track_id"], t.get("track_layout", ""))
        if key not in cache:
            p = find_spline_file(key[0], key[1], ac_root=ac_root)
            cache[key] = SplineParser(p).waypoints if p else None
        if not cache[key]:
            print("SKIP", t.get("test_id"), key)
            continue
        dest_file = os.path.join(out_dir, t["test_id"] + ".svg")
        with open(dest_file, "w", encoding="utf-8") as fh:
            fh.write(build(t, cache[key]))
        count += 1
    return count


def generate_single_map(
    test_id: str,
    test_data: Optional[Dict] = None,
    ac_root: str = None,
    out_dir: str = OUT_DIR,
) -> Optional[str]:
    """
    Generates a vector SVG track map with highlighted test sector for a single test.
    Saves to docs/test_maps/<test_id>.svg and returns destination path.
    """
    from tools.spline.parser import DEFAULT_AC_ROOT
    if ac_root is None:
        ac_root = DEFAULT_AC_ROOT

    t = dict(test_data) if test_data else None
    if not t:
        from tools.testing.eval_loop import find_test_file_by_id
        repo_file = find_test_file_by_id(test_id, REPO_ROOT)
        if repo_file and os.path.isfile(repo_file):
            try:
                with open(repo_file, "r", encoding="utf-8") as fh:
                    t = json.load(fh)
            except Exception:
                pass

    if not t:
        from tools.content.catalog import TESTS_BY_ID
        t = TESTS_BY_ID.get(test_id)
        if t:
            t = dict(t)

    if not t:
        return None

    track_id = t.get("track_id")
    layout = t.get("track_layout", "")
    if not track_id:
        return None

    spline_file = find_spline_file(track_id, layout, ac_root=ac_root)
    if not spline_file or not os.path.isfile(spline_file):
        return None

    parser = SplineParser(spline_file)
    wps = parser.waypoints
    if not wps:
        return None

    has_timing = (
        isinstance(t.get("timing"), dict)
        and "start_gate" in t["timing"]
        and "finish_gate" in t["timing"]
    )
    if not has_timing or "start_s" in t:
        from tools.spline.parser import generate_test_parameters
        geom = generate_test_parameters(
            parser=parser,
            start_progress=float(t.get("start_s", 0.0)),
            finish_progress=float(t.get("finish_s", 1.0)),
            spawn_offset_m=float(t.get("spawn_offset", 0.0)),
            initial_speed_kmh=float(t.get("speed", 0.0)),
            with_stop_box=bool(t.get("with_stop_box", False)),
            gear=int(t["gear"]) if t.get("gear") is not None else None,
            rpm=int(t["rpm"]) if t.get("rpm") is not None else None,
            gate_width=t.get("gate_width"),
            track_id=t.get("track_id"),
        )
        t["spawn"] = geom["spawn"]
        t["timing"] = geom["timing"]

    os.makedirs(out_dir, exist_ok=True)
    dest_file = os.path.join(out_dir, f"{test_id}.svg")
    with open(dest_file, "w", encoding="utf-8") as fh:
        fh.write(build(t, wps))

    return dest_file


def main():
    count = generate_maps()
    print(f"Generated {count} test track map SVGs in {OUT_DIR}")


if __name__ == "__main__":
    main()

