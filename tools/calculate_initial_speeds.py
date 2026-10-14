#!/usr/bin/env python3
"""
calculate_initial_speeds.py
Calculates and calibrates the authentic initial speed, countdown run-up spawn offset,
engaged gear, and initial RPM for Assetto Corsa GT-Like License tests
(Rolling Starts and Flying Laps) using Assetto Corsa Game Engine AI telemetry.

Usage:
  # Query calculation for a single test
  python tools/calculate_initial_speeds.py --test B-3

  # Calculate and apply to catalog files for a single test
  python tools/calculate_initial_speeds.py --test B-3 --apply

  # Calculate and apply for an entire tier
  python tools/calculate_initial_speeds.py --tier super_license --apply

  # Calculate and apply for all curriculum tests + regenerate content
  python tools/calculate_initial_speeds.py --all --apply --rebuild

  # Force live in-engine launch of acs.exe to record telemetry
  python tools/calculate_initial_speeds.py --test B-3 --live-engine
"""

import argparse
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import (
    INTERNATIONAL_A_TESTS,
    INTERNATIONAL_B_TESTS,
    NATIONAL_A_TESTS,
    NATIONAL_B_TESTS,
    SUPER_LICENSE_TESTS,
    TEST_CATALOG,
    TESTS_BY_ID,
    TESTS_BY_TIER,
    TIER_FOLDER_MAP,
)
from tools.telemetry.recorder import (
    DEFAULT_AC_ROOT,
    get_or_calculate_initial_physics,
    load_telemetry_profile,
    profile_filename,
    save_telemetry_profile,
)

CATALOG_FILE_MAP = {
    "National B": os.path.join(REPO_ROOT, "tools", "content", "catalog", "national_b.py"),
    "National A": os.path.join(REPO_ROOT, "tools", "content", "catalog", "national_a.py"),
    "International B": os.path.join(REPO_ROOT, "tools", "content", "catalog", "international_b.py"),
    "International A": os.path.join(REPO_ROOT, "tools", "content", "catalog", "international_a.py"),
    "Super License": os.path.join(REPO_ROOT, "tools", "content", "catalog", "super_license.py"),
}


def calculate_for_test(
    test_data: Dict[str, Any],
    countdown_sec: float = 3.0,
    allow_live_engine: bool = False,
    ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    """Calculates ground-truth AI physics for a single test definition."""
    start_mode = test_data.get("start_mode", "STANDING")
    if start_mode == "STANDING":
        return {
            "test_id": test_data.get("test_id", ""),
            "start_mode": start_mode,
            "speed_kmh": 0.0,
            "spawn_offset_m": 0.0,
            "gear": 1,
            "rpm": 1000,
            "source": "standing_start",
        }

    track_id = test_data["track_id"]
    layout = test_data.get("track_layout", "")
    car_id = test_data["car_id"]
    start_s = float(test_data.get("start_s", 0.0))

    physics = get_or_calculate_initial_physics(
        track_id=track_id,
        layout=layout,
        car_id=car_id,
        start_s=start_s,
        countdown_sec=countdown_sec,
        ai_level=100,
        allow_live_engine=allow_live_engine,
        ac_root=ac_root,
    )

    return {
        "test_id": test_data.get("test_id", ""),
        "title": test_data.get("title", ""),
        "tier": test_data.get("tier", ""),
        "track_id": track_id,
        "track_layout": layout,
        "car_id": car_id,
        "start_mode": start_mode,
        "start_s": start_s,
        "speed_kmh": physics["speed_kmh"],
        "spawn_offset_m": physics["spawn_offset_m"],
        "gear": physics["gear"],
        "rpm": physics["rpm"],
        "spawn_speed_kmh": physics.get("spawn_speed_kmh", physics["speed_kmh"]),
        "spawn_gear": physics.get("spawn_gear", physics["gear"]),
        "spawn_rpm": physics.get("spawn_rpm", physics["rpm"]),
        "countdown_sec": countdown_sec,
        "source": physics["source"],
    }


def update_catalog_file(tier_name: str, test_updates: Dict[str, Dict[str, Any]]) -> bool:
    """Updates initial speed, spawn offset, gear, and RPM in catalog python files."""
    filepath = CATALOG_FILE_MAP.get(tier_name)
    if not filepath or not os.path.isfile(filepath):
        print(f"[!] Catalog file not found for tier: {tier_name}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False
    for t_id, data in test_updates.items():
        if data.get("start_mode") == "STANDING":
            continue

        spd = data["speed_kmh"]
        offset = data["spawn_offset_m"]
        gear = data["gear"]
        rpm = data["rpm"]

        # Regex to locate the test dictionary by test_id
        pattern = re.compile(
            rf'(["\']test_id["\']\s*:\s*["\']{re.escape(t_id)}["\'].*?)(}}\s*,?)',
            re.DOTALL,
        )

        match = pattern.search(content)
        if not match:
            continue

        block = match.group(1)

        # Replace or insert speed
        if re.search(r'["\']speed["\']\s*:\s*[\d\.]+', block):
            block = re.sub(r'(["\']speed["\']\s*:\s*)[\d\.]+', rf'\g<1>{spd:.1f}', block)
        else:
            block += f'\n        "speed": {spd:.1f},'

        # Replace or insert spawn_offset
        if re.search(r'["\']spawn_offset["\']\s*:\s*[\d\.]+', block):
            block = re.sub(r'(["\']spawn_offset["\']\s*:\s*)[\d\.]+', rf'\g<1>{offset:.1f}', block)
        else:
            block += f'\n        "spawn_offset": {offset:.1f},'

        # Replace or insert gear
        if re.search(r'["\']gear["\']\s*:\s*\d+', block):
            block = re.sub(r'(["\']gear["\']\s*:\s*)\d+', rf'\g<1>{gear}', block)
        else:
            block += f'\n        "gear": {gear},'

        # Replace or insert rpm
        if re.search(r'["\']rpm["\']\s*:\s*\d+', block):
            block = re.sub(r'(["\']rpm["\']\s*:\s*)\d+', rf'\g<1>{rpm}', block)
        else:
            block += f'\n        "rpm": {rpm},'

        new_segment = block + match.group(2)
        content = content[: match.start()] + new_segment + content[match.end() :]
        modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Updated catalog file: {os.path.relpath(filepath, REPO_ROOT)}")

    return modified


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assetto Corsa GT-Like Licenses Initial Speed & AI Telemetry Calculator"
    )
    parser.add_argument("--test", type=str, help="Specific test ID to calculate (e.g. B-3, S-1)")
    parser.add_argument(
        "--tier",
        type=str,
        help="Tier name or code (national_b, national_a, international_b, international_a, super_license)",
    )
    parser.add_argument("--all", action="store_true", help="Calculate for all Rolling & Flying Lap tests")
    parser.add_argument(
        "--live-engine",
        action="store_true",
        help="Launch acs.exe to record ground-truth 95% AI telemetry if not cached",
    )
    parser.add_argument("--apply", action="store_true", help="Write calculated parameters back into catalog files")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild curriculum JSONs (generate_all_content) and sync to AC after apply",
    )
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa installation directory")

    args = parser.parse_args()

    targets: List[Dict[str, Any]] = []

    if args.test:
        test_id_clean = args.test.strip().upper()
        t = TESTS_BY_ID.get(test_id_clean)
        if not t:
            print(f"[!] Test ID not found: {args.test}")
            return 1
        targets.append(t)
    elif args.tier:
        tier_key = args.tier.strip().lower()
        tier_name = None
        for name, folder in TIER_FOLDER_MAP.items():
            if folder == tier_key or name.lower() == tier_key:
                tier_name = name
                break
        if not tier_name or tier_name not in TESTS_BY_TIER:
            print(f"[!] Invalid tier: {args.tier}. Choose from: {list(TIER_FOLDER_MAP.values())}")
            return 1
        targets = [t for t in TESTS_BY_TIER[tier_name] if t.get("start_mode") in ("ROLLING", "FLYING_LAP")]
    elif args.all:
        targets = [t for t in TEST_CATALOG if t.get("start_mode") in ("ROLLING", "FLYING_LAP")]
    else:
        parser.print_help()
        return 0

    print(f"[*] Processing {len(targets)} test(s) for Initial Speed calculation...")
    print(f"{'TEST':<7} | {'MODE':<10} | {'START_S':<8} | {'SPEED':<10} | {'OFFSET':<9} | {'GEAR':<5} | {'RPM':<6} | {'SOURCE'}")
    print("-" * 88)

    updates_by_tier: Dict[str, Dict[str, Any]] = {}

    for t in targets:
        res = calculate_for_test(t, countdown_sec=3.0, allow_live_engine=args.live_engine, ac_root=args.ac_root)
        t_id = res["test_id"]
        tier = t.get("tier", "National B")

        if tier not in updates_by_tier:
            updates_by_tier[tier] = {}
        updates_by_tier[tier][t_id] = res

        print(
            f"{t_id:<7} | {res['start_mode']:<10} | {res.get('start_s', 0.0):<8.4f} | "
            f"{res['speed_kmh']:>6.1f} km/h | {res['spawn_offset_m']:>6.1f}m | "
            f"G{res['gear']:<4} | {res['rpm']:<6} | {res['source']}"
        )

    if args.apply:
        print("\n[*] Applying calculated values to catalog files...")
        for tier_name, test_map in updates_by_tier.items():
            update_catalog_file(tier_name, test_map)

        if args.rebuild:
            print("\n[*] Rebuilding content and syncing to Assetto Corsa...")
            import subprocess
            subprocess.run([sys.executable, os.path.join(REPO_ROOT, "tools", "generate_all_content.py")], check=True)
            subprocess.run([sys.executable, os.path.join(REPO_ROOT, "tools", "sync_to_ac.py")], check=True)
            print("[+] Rebuild & sync complete!")

    print("\n[+] Calculation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

