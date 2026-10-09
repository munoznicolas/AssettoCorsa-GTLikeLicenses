#!/usr/bin/env python3
"""
generator.py
Autonomous Content Generator for Assetto Corsa Gran Turismo Licenses Mod.

Generates:
  1. All 58 test JSON definition files in content/tests/<tier>/test_<code_num>.json
     calibrated directly from official AC AI splines (fast_lane.ai / ideal_line.ai).
  2. All 5 Content Manager career series in content/career/series_gt_license_<tier>/
     with series.ini, preview.png badges, and eventX/event.ini configs.
"""

import configparser
import json
import os
import shutil
import sys
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import (
    SERIES_METADATA,
    TEST_CATALOG,
    TIER_FOLDER_MAP,
)
from tools.extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
    generate_test_parameters,
)


def generate_tests(ac_root: str = DEFAULT_AC_ROOT) -> None:
    """Generates all 58 test JSON definition files calibrated from track AI splines."""
    print(f"[1/3] Generating all 58 License Test definitions from track splines...")
    spline_parsers = {}

    for tdef in TEST_CATALOG:
        t_id = tdef["test_id"]
        tier = tdef["tier"]
        tier_dir = os.path.join(REPO_ROOT, "content", "tests", TIER_FOLDER_MAP[tier])
        os.makedirs(tier_dir, exist_ok=True)

        prefix, num_str = t_id.split("-")
        filename = f"test_{prefix.lower()}{int(num_str):02d}.json"
        target_path = os.path.join(tier_dir, filename)

        track_id = tdef["track_id"]
        layout = tdef["track_layout"]
        cache_key = f"{track_id}::{layout}"

        if cache_key not in spline_parsers:
            spline_file = find_spline_file(track_id, layout, ac_root)
            if not spline_file:
                raise FileNotFoundError(f"Missing AI spline for track {track_id} (layout: '{layout}')")
            spline_parsers[cache_key] = SplineParser(spline_file)

        parser = spline_parsers[cache_key]

        # Generate spatial parameters
        geom = generate_test_parameters(
            parser=parser,
            start_progress=tdef["start_s"],
            finish_progress=tdef["finish_s"],
            spawn_offset_m=tdef["spawn_offset"],
            initial_speed_kmh=tdef["speed"],
            with_stop_box=tdef["with_stop_box"],
            gear=tdef.get("gear"),
            rpm=tdef.get("rpm"),
        )

        test_json = {
            "test_id": tdef["test_id"],
            "tier": tdef["tier"],
            "title": tdef["title"],
            "description": tdef["description"],
            "lesson_objective": tdef["lesson_objective"],
            "car_id": tdef["car_id"],
            "track_id": tdef["track_id"],
            "track_layout": tdef["track_layout"],
            "start_mode": tdef["start_mode"],
            "spawn": geom["spawn"],
            "timing": geom["timing"],
            "fail_rules": {
                "max_wheels_off": 2,
                "wall_collision_threshold_n": 1500,
                "max_yaw_angle_deg": 90,
                "stop_box_overshoot_fail": tdef["with_stop_box"],
            },
            "targets": tdef["targets"],
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(test_json, f, indent=2)

        print(f"  + Generated {t_id.ljust(5)} -> {os.path.relpath(target_path, REPO_ROOT)}")


def generate_career() -> None:
    """Generates all 5 Content Manager career series directories and INI configurations."""
    print(f"\n[2/3] Generating Content Manager Career Series structures...")
    career_root = os.path.join(REPO_ROOT, "content", "career")
    os.makedirs(career_root, exist_ok=True)

    for s_meta in SERIES_METADATA:
        s_folder = os.path.join(career_root, s_meta["folder"])
        os.makedirs(s_folder, exist_ok=True)

        # 1. series.ini
        series_ini_path = os.path.join(s_folder, "series.ini")
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        cp["SERIES"] = {
            "CODE": s_meta["code"],
            "NAME": s_meta["name"],
            "DESCRIPTION": s_meta["description"],
            "REQUIRES": s_meta["requires"] or "",
            "POINTS": "0",
        }
        cp["GOALS"] = {
            "POINTS": "0",
            "RANKING": "0",
            "TIER1": "1",
            "TIER2": "0",
            "TIER3": "0",
        }
        with open(series_ini_path, "w", encoding="utf-8") as f:
            cp.write(f, space_around_delimiters=False)

        # 2. preview.png badge
        badge_src = os.path.join(REPO_ROOT, "assets", "career_ui", s_meta["badge_asset"])
        preview_dest = os.path.join(s_folder, "preview.png")
        if os.path.isfile(badge_src):
            shutil.copyfile(badge_src, preview_dest)
        elif not os.path.isfile(preview_dest):
            # Create a simple 1x1 placeholder PNG if badge is missing
            with open(preview_dest, "wb") as f:
                f.write(
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                )

        # 3. Events
        tier_tests = [t for t in TEST_CATALOG if t["tier"] == s_meta["tier_name"]]
        for idx, tdef in enumerate(tier_tests, start=1):
            event_dir = os.path.join(s_folder, f"event{idx}")
            os.makedirs(event_dir, exist_ok=True)
            event_ini_path = os.path.join(event_dir, "event.ini")

            ecp = configparser.ConfigParser(interpolation=None)
            ecp.optionxform = str
            ecp["EVENT"] = {
                "NAME": f"{tdef['test_id']}: {tdef['title']}",
                "DESCRIPTION": f"{tdef['description']}\n\nObjective: {tdef['lesson_objective']}",
            }
            ecp["RACE"] = {
                "TRACK": tdef["track_id"],
                "CONFIG_TRACK": tdef["track_layout"],
                "MODEL": tdef["car_id"],
                "MODEL_CONFIG": "",
                "CARS": "1",
                "AI_LEVEL": "98",
                "DRIFT_MODE": "0",
                "FIXED_SETUP": "1",
                "PENALTIES": "1",
                "__CM_CUSTOM_MODE": "gt-license",
            }
            ecp["CAR_0"] = {
                "MODEL": tdef["car_id"],
                "MODEL_CONFIG": "",
                "SETUP": "",
                "SKIN": "",
                "BALLAST": "0",
                "RESTRICTOR": "0",
            }
            ecp["LIGHTING"] = {
                "SUN_ANGLE": "48",
                "TIME_MULT": "1",
                "CLOUD_SPEED": "0.2",
            }
            ecp["SESSION_0"] = {
                "NAME": "License Test",
                "TYPE": "1",
                "DURATION": "0",
                "SPAWN_SET": "PIT",
            }
            # Target times in milliseconds
            targets = tdef["targets"]
            ecp["CONDITION_0"] = {
                "TYPE": "TIME",
                "OBJECTIVE": str(int(targets["bronze_seconds"] * 1000)),
            }
            ecp["CONDITION_1"] = {
                "TYPE": "TIME",
                "OBJECTIVE": str(int(targets["silver_seconds"] * 1000)),
            }
            ecp["CONDITION_2"] = {
                "TYPE": "TIME",
                "OBJECTIVE": str(int(targets["gold_seconds"] * 1000)),
            }

            with open(event_ini_path, "w", encoding="utf-8") as f:
                ecp.write(f, space_around_delimiters=False)

            # Copy event preview image
            preview_src = os.path.join(REPO_ROOT, "assets", "previews", "numbers", f"{idx}.png")
            preview_dest = os.path.join(event_dir, "preview.png")
            if os.path.isfile(preview_src):
                shutil.copyfile(preview_src, preview_dest)

        print(f"  + Generated Series: {s_meta['folder']} ({len(tier_tests)} events)")


def main() -> int:
    try:
        generate_tests()
        generate_career()
        print("\n[3/3] Content generation complete!")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

