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
from typing import Dict, Optional

from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
from tools.spline.parser import SplineParser, find_spline_file  # noqa: E402
from tools.assets.test_map_generator import sector_indices  # noqa: E402

CAREER_ROOT = os.path.join(REPO_ROOT, "content", "career")
W, H, SS = 1024, 576, 2          # output size, supersampling factor
MARGIN = 0.12                    # empty border around the stretch (fraction)
MIN_SPAN_M = 120.0               # never zoom closer than this (metres)


def build_test_to_event_path_map() -> Dict[str, str]:
    """
    Builds a map from test_id (e.g. 'A-2', 'B-1') to its direct career event preview path:
    e.g. content/career/series_gt_license_a/event2/preview.png
    """
    from tools.content.catalog import SERIES_METADATA, TEST_CATALOG
    mapping = {}
    for s_meta in SERIES_METADATA:
        tier_tests = [t for t in TEST_CATALOG if t["tier"] == s_meta["tier_name"]]
        for idx, tdef in enumerate(tier_tests, start=1):
            event_preview = os.path.join(CAREER_ROOT, s_meta["folder"], f"event{idx}", "preview.png")
            mapping[tdef["test_id"]] = event_preview
    return mapping


def get_preview_path_for_test(test_id: str, tier: Optional[str] = None) -> Optional[str]:
    """
    Resolves destination career preview.png path for a given test_id.
    e.g. 'B-3' -> 'content/career/series_gt_license_b/event3/preview.png'
    """
    mapping = build_test_to_event_path_map()
    if test_id in mapping:
        return mapping[test_id]
    if "-" in test_id:
        prefix, num_str = test_id.split("-", 1)
        try:
            num = int(num_str)
            from tools.content.catalog import SERIES_METADATA
            s_meta = next(
                (
                    s
                    for s in SERIES_METADATA
                    if s["code"].upper() == prefix.upper()
                    or s["test_prefix"].rstrip("-").upper() == prefix.upper()
                ),
                None,
            )
            if not s_meta and tier:
                s_meta = next(
                    (s for s in SERIES_METADATA if s["tier_name"].lower() == tier.lower()),
                    None,
                )
            if s_meta:
                return os.path.join(CAREER_ROOT, s_meta["folder"], f"event{num}", "preview.png")
        except ValueError:
            pass
    return None


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
    dot_r = road / 2.0
    for is_start, col in ((True, (46, 204, 113)), (False, (255, 59, 48))):
        target_idx = idx[0] if is_start else idx[-1]
        x, y = tp(pts[target_idx])
        d.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=col)
    sp = test.get("spawn", {}).get("position")
    if sp:
        x, y = tp((sp[0], sp[2]))
        sr = 9 * SS
        d.ellipse((x - sr, y - sr, x + sr, y + sr), fill=(255, 212, 0), outline=(0, 0, 0), width=2 * SS)
    return img.resize((W, H), Image.LANCZOS)


def generate_previews(
    ac_root: str = None,
    tests_dir: str = None,
) -> int:
    """Generates 1024x576 zoomed track miniature previews directly in career event folders."""
    from tools.spline.parser import DEFAULT_AC_ROOT
    if ac_root is None:
        ac_root = DEFAULT_AC_ROOT
    if tests_dir is None:
        tests_dir = os.path.join(REPO_ROOT, "content", "tests")

    test_to_event = build_test_to_event_path_map()
    cache = {}
    count = 0
    test_files = sorted(glob.glob(os.path.join(tests_dir, "*", "test_*.json")))
    for f in test_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                t = json.load(fh)
        except Exception:
            continue
        test_id = t.get("test_id")
        dest_file = test_to_event.get(test_id)
        if not dest_file:
            print("SKIP (no career event mapping)", test_id)
            continue

        key = (t["track_id"], t.get("track_layout", ""))
        if key not in cache:
            p = find_spline_file(key[0], key[1], ac_root=ac_root)
            cache[key] = SplineParser(p).waypoints if p else None
        if not cache[key]:
            print("SKIP", test_id, key)
            continue
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        render(t, cache[key]).save(dest_file)
        count += 1
        print(f"OK {test_id} -> {os.path.relpath(dest_file, REPO_ROOT)}")
    return count


def generate_single_preview(
    test_id: str,
    test_data: Optional[Dict] = None,
    ac_root: str = None,
) -> Optional[str]:
    """
    Generates a 1024x576 zoomed track miniature preview PNG for a single test.
    Saves to content/career/<series>/event<idx>/preview.png and returns destination path.
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
        print(f"[!] Warning: Test {test_id} not found for preview generation", file=sys.stderr)
        return None

    track_id = t.get("track_id")
    layout = t.get("track_layout", "")
    if not track_id:
        return None

    spline_file = find_spline_file(track_id, layout, ac_root=ac_root)
    if not spline_file or not os.path.isfile(spline_file):
        print(f"[!] Warning: Spline file not found for track {track_id} ({layout})", file=sys.stderr)
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

    import re
    safe_test_id = re.sub(r"[^A-Za-z0-9_\-]", "", str(test_id))
    if not safe_test_id:
        return None

    dest_file = get_preview_path_for_test(safe_test_id, tier=t.get("tier"))
    if not dest_file:
        return None

    real_career_root = os.path.realpath(CAREER_ROOT)
    real_dest_file = os.path.realpath(dest_file)
    if os.path.commonpath([real_career_root, real_dest_file]) != real_career_root:
        return None

    os.makedirs(os.path.dirname(real_dest_file), exist_ok=True)
    img = render(t, wps)
    img.save(real_dest_file)

    # Mirror to assets/previews/tests/<TEST_ID>.png if directory exists
    alt_dir = os.path.realpath(os.path.join(REPO_ROOT, "assets", "previews", "tests"))
    if os.path.isdir(alt_dir):
        alt_target = os.path.realpath(os.path.join(alt_dir, f"{safe_test_id}.png"))
        if os.path.commonpath([alt_dir, alt_target]) == alt_dir:
            img.save(alt_target)

    # Mirror directly to local Assetto Corsa install directory if it exists
    if ac_root and os.path.isdir(ac_root):
        rel_to_repo = os.path.relpath(real_dest_file, REPO_ROOT)
        ac_dest = os.path.realpath(os.path.join(ac_root, rel_to_repo))
        real_ac_root = os.path.realpath(ac_root)
        if os.path.commonpath([real_ac_root, ac_dest]) == real_ac_root and os.path.isdir(os.path.dirname(ac_dest)):
            try:
                import shutil
                shutil.copyfile(real_dest_file, ac_dest)
            except Exception:
                pass

    return real_dest_file


def main():
    count = generate_previews()
    print(f"Generated {count} test track preview miniatures in career event folders")


if __name__ == "__main__":
    main()
