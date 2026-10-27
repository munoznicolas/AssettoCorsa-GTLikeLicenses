#!/usr/bin/env python3
"""
build_static_site.py
Static Site & GitHub Pages Artifact Generator for Assetto Corsa GT Licenses.

Pre-renders all curriculum datasets, catalog endpoints, test maps, and preview
assets into a standalone static distribution directory (dist_site/) ready for
immediate deployment to GitHub Pages.

Usage:
    python tools/build_static_site.py [--out-dir dist_site] [--clean]
"""

import argparse
import json
import os
import shutil
import sys
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import TEST_CATALOG
from tools.web_ui.catalog_manager import (
    CAR_LAYOUT_MAP,
    CAR_SPECS_CACHE,
    get_ac_curriculum_reference_tests,
    get_available_cars,
    get_available_tracks,
    get_missing_telemetry_summary,
    load_curriculum,
)


def _build_fallback_tracks(curriculum: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Synthesizes track metadata directly from curriculum definitions when AC root is absent."""
    tracks_map: Dict[str, Dict[str, Any]] = {}
    for tier in curriculum:
        for t in tier.get("tests", []):
            tid = t.get("track_id", "")
            layout = t.get("track_layout", "")
            if not tid:
                continue
            if tid not in tracks_map:
                name = tid.replace("ks_", "").replace("_", " ").title()
                tracks_map[tid] = {
                    "track_id": tid,
                    "name": name,
                    "layouts": [],
                }
            if layout not in tracks_map[tid]["layouts"]:
                tracks_map[tid]["layouts"].append(layout)

    return sorted(tracks_map.values(), key=lambda x: x["name"])


def _build_fallback_cars(curriculum: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Synthesizes car metadata directly from curriculum definitions when AC root is absent."""
    cars_map: Dict[str, Dict[str, Any]] = {}
    for tier in curriculum:
        for t in tier.get("tests", []):
            cid = t.get("car_id", "")
            if not cid or cid in cars_map:
                continue

            name = cid.replace("ks_", "").replace("_", " ").title()
            cached_specs = CAR_SPECS_CACHE.get(cid)
            if cached_specs:
                hp, wt, pw, dt = cached_specs
                specs = {"bhp": hp, "weight_kg": wt, "pw_ratio": pw, "drivetrain": dt}
            else:
                specs = {"bhp": 200, "weight_kg": 1200, "pw_ratio": 6.0, "drivetrain": CAR_LAYOUT_MAP.get(cid, "FR")}

            brand = cid.split("_")[0].replace("ks", "").title() or "Assetto Corsa"
            cars_map[cid] = {
                "car_id": cid,
                "name": name,
                "brand": brand,
                "tags": [specs.get("drivetrain", CAR_LAYOUT_MAP.get(cid, "FR"))],
                "specs": specs,
            }

    return sorted(cars_map.values(), key=lambda x: x["name"])


def build_static_site(out_dir: str = "dist_site", clean: bool = True) -> str:
    """Builds the complete static site distribution for GitHub Pages."""
    dist_path = os.path.abspath(out_dir)
    print(f"Building static GitHub Pages bundle in: {dist_path}")

    if clean and os.path.exists(dist_path):
        shutil.rmtree(dist_path)
    os.makedirs(dist_path, exist_ok=True)

    # 1. Copy Frontend Static Assets
    static_src = os.path.join(REPO_ROOT, "tools", "web_ui", "static")
    if os.path.isdir(static_src):
        for item in os.listdir(static_src):
            s_item = os.path.join(static_src, item)
            d_item = os.path.join(dist_path, item)
            if os.path.isdir(s_item):
                shutil.copytree(s_item, d_item, dirs_exist_ok=True)
            else:
                shutil.copy2(s_item, d_item)
        print("  [OK] Copied web UI frontend assets (HTML, CSS, JS)")

    # 2. Pre-render Static JSON API Payloads
    api_dir = os.path.join(dist_path, "api")
    os.makedirs(api_dir, exist_ok=True)

    print("  [*] Pre-rendering static API endpoints...")
    # /api/curriculum
    curriculum = load_curriculum()
    with open(os.path.join(api_dir, "curriculum.json"), "w", encoding="utf-8") as f:
        json.dump({"success": True, "curriculum": curriculum}, f, indent=2)

    # /api/tracks
    tracks = get_available_tracks()
    if not tracks:
        tracks = _build_fallback_tracks(curriculum)
    with open(os.path.join(api_dir, "tracks.json"), "w", encoding="utf-8") as f:
        json.dump({"success": True, "tracks": tracks, "kunos_only": True}, f, indent=2)

    # /api/cars
    cars = get_available_cars()
    if not cars:
        cars = _build_fallback_cars(curriculum)
    with open(os.path.join(api_dir, "cars.json"), "w", encoding="utf-8") as f:
        json.dump({"success": True, "cars": cars, "kunos_only": True}, f, indent=2)

    # /api/reference_tests
    ref_gt_path = os.path.join(REPO_ROOT, "docs", "Gran_Turismo_License_Tests.json")
    ref_gt = []
    if os.path.isfile(ref_gt_path):
        with open(ref_gt_path, "r", encoding="utf-8") as f:
            ref_gt = json.load(f)
    ref_ac = get_ac_curriculum_reference_tests()
    combined_refs = ref_gt + ref_ac
    with open(os.path.join(api_dir, "reference_tests.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "success": True,
                "tests": combined_refs,
                "count": len(combined_refs),
                "gt_count": len(ref_gt),
                "ac_count": len(ref_ac),
            },
            f,
            indent=2,
        )

    # /api/missing_telemetry
    missing_summary = get_missing_telemetry_summary()
    with open(os.path.join(api_dir, "missing_telemetry.json"), "w", encoding="utf-8") as f:
        json.dump(missing_summary, f, indent=2)

    print("  [OK] Pre-rendered curriculum, tracks, cars, reference tests, and missing telemetry APIs")

    # 3. Copy Career Previews and Vector Maps
    career_src = os.path.join(REPO_ROOT, "content", "career")
    career_dst = os.path.join(dist_path, "content", "career")
    if os.path.isdir(career_src):
        os.makedirs(career_dst, exist_ok=True)
        for root, _, files in os.walk(career_src):
            for file in files:
                if file.endswith((".png", ".ini")):
                    s_file = os.path.join(root, file)
                    rel = os.path.relpath(s_file, career_src)
                    d_file = os.path.join(career_dst, rel)
                    os.makedirs(os.path.dirname(d_file), exist_ok=True)
                    shutil.copy2(s_file, d_file)
        print("  [OK] Copied career preview badges and event miniatures")

    # 3b. Copy UI Badges and Textures from assets/
    assets_src = os.path.join(REPO_ROOT, "assets")
    assets_dst = os.path.join(dist_path, "assets")
    if os.path.isdir(assets_src):
        for sub in ["career_ui", "textures"]:
            s_sub = os.path.join(assets_src, sub)
            d_sub = os.path.join(assets_dst, sub)
            if os.path.isdir(s_sub):
                os.makedirs(d_sub, exist_ok=True)
                for f in os.listdir(s_sub):
                    if f.endswith((".png", ".jpg", ".svg")):
                        shutil.copy2(os.path.join(s_sub, f), os.path.join(d_sub, f))
        print("  [OK] Copied career UI badges and textures to assets/")

    # 4. Copy Vector SVG Maps
    docs_maps = [("test_maps", os.path.join(REPO_ROOT, "docs", "test_maps")),
                 ("track_maps", os.path.join(REPO_ROOT, "docs", "track_maps"))]
    for name, src in docs_maps:
        if os.path.isdir(src):
            dst = os.path.join(dist_path, "docs", name)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src):
                if f.endswith(".svg"):
                    shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            print(f"  [OK] Copied SVG vector diagrams from docs/{name}")

    # 5. Copy Output HTML Visualizers
    output_src = os.path.join(REPO_ROOT, "output")
    reports_dst = os.path.join(dist_path, "reports")
    if os.path.isdir(output_src):
        os.makedirs(reports_dst, exist_ok=True)
        for f in os.listdir(output_src):
            if f.endswith(".html"):
                shutil.copy2(os.path.join(output_src, f), os.path.join(reports_dst, f))
        print("  [OK] Copied standalone spline & rolling start HTML analyzers")

    # 6. Prevent GitHub Pages from using Jekyll processing
    with open(os.path.join(dist_path, ".nojekyll"), "w") as f:
        f.write("")

    print(f"\n[DONE] Static site build complete! Artifacts staged in: {dist_path}")
    return dist_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assetto Corsa GT Licenses Static Site Builder")
    parser.add_argument("--out-dir", default="dist_site", help="Destination directory for static site")
    parser.add_argument("--no-clean", action="store_true", help="Do not clear destination folder before building")
    args = parser.parse_args()

    build_static_site(out_dir=args.out_dir, clean=not args.no_clean)
