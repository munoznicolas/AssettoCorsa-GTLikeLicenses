#!/usr/bin/env python3
"""
test_calibration_tool.py
Interactive & Programmatic Test Calibration & Generator Tool

Bridges extract_spline_coords.py and validate_curriculum.py to quickly generate,
calibrate, and format license test JSON files conforming to schema/test_definition.schema.json.

Usage:
  python tools/test_calibration_tool.py \
    --id B-3 \
    --tier "National B" \
    --title "Tornantino Hairpin" \
    --desc "Late apex deceleration and corner exit acceleration." \
    --obj "Brake in a straight line before turning in." \
    --car ks_alfa_romeo_mito_qv \
    --track ks_vallelunga \
    --layout club_circuit \
    --start-s 0.28 \
    --finish-s 0.42 \
    --spawn-offset 35 \
    --speed 70 \
    --gold 14.8 \
    --silver 16.0 \
    --bronze 18.0 \
    --out content/tests/national_b/test_b03.json
"""

import argparse
import json
import os
import sys

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
    generate_test_parameters,
)
from validate_curriculum import CurriculumValidator


def build_test_definition(
    test_id: str,
    tier: str,
    title: str,
    description: str,
    lesson_objective: str,
    car_id: str,
    track_id: str,
    track_layout: str,
    start_mode: str,
    start_s: float,
    finish_s: float,
    spawn_offset: float,
    speed: float,
    gold: float,
    silver: float,
    bronze: float,
    with_stop_box: bool = False,
    ac_root: str = DEFAULT_AC_ROOT,
    gate_width: float = None,
) -> dict:
    spline_file = find_spline_file(track_id, track_layout, ac_root)
    if not spline_file:
        raise FileNotFoundError(
            f"Could not find AI spline for track '{track_id}' layout '{track_layout}' in {ac_root}"
        )

    spline = SplineParser(spline_file)
    timing_spawn = generate_test_parameters(
        parser=spline,
        start_progress=start_s,
        finish_progress=finish_s,
        spawn_offset_m=spawn_offset,
        initial_speed_kmh=speed,
        gate_width=gate_width,
        with_stop_box=with_stop_box,
    )

    test_dict = {
        "test_id": test_id,
        "tier": tier,
        "title": title,
        "description": description,
        "lesson_objective": lesson_objective,
        "car_id": car_id,
        "track_id": track_id,
        "track_layout": track_layout,
        "start_mode": start_mode,
        "spawn": timing_spawn["spawn"],
        "timing": timing_spawn["timing"],
        "fail_rules": {
            "max_wheels_off": 2,
            "wall_collision_threshold_n": 1500,
            "max_yaw_angle_deg": 90,
            "stop_box_overshoot_fail": with_stop_box,
        },
        "targets": {
            "gold_seconds": round(gold, 3),
            "silver_seconds": round(silver, 3),
            "bronze_seconds": round(bronze, 3),
        },
    }

    return test_dict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assetto Corsa GT Licenses - Test Definition Calibration Tool"
    )
    parser.add_argument("--id", required=True, help="Test ID (e.g. B-1, A-5)")
    parser.add_argument("--tier", required=True, help="Tier display name (e.g. National B)")
    parser.add_argument("--title", required=True, help="Test title")
    parser.add_argument("--desc", default="Complete the sector within target time.", help="Description")
    parser.add_argument("--obj", default="Master throttle and braking control.", help="Lesson objective")
    parser.add_argument("--car", required=True, help="Car folder ID")
    parser.add_argument("--track", required=True, help="Track folder ID")
    parser.add_argument("--layout", default="", help="Track layout folder")
    parser.add_argument("--start-mode", default="ROLLING", choices=["STANDING", "ROLLING", "FLYING_LAP"])
    parser.add_argument("--start-s", type=float, required=True, help="Start gate progress (0.0 - 1.0)")
    parser.add_argument("--finish-s", type=float, required=True, help="Finish gate progress (0.0 - 1.0)")
    parser.add_argument("--spawn-offset", type=float, default=30.0, help="Meters behind start gate")
    parser.add_argument("--speed", type=float, default=60.0, help="Initial speed km/h")
    parser.add_argument("--gold", type=float, required=True, help="Gold target time (seconds)")
    parser.add_argument("--silver", type=float, required=True, help="Silver target time (seconds)")
    parser.add_argument("--bronze", type=float, required=True, help="Bronze target time (seconds)")
    parser.add_argument("--stop-box", action="store_true", help="Include stop box")
    parser.add_argument("--ac-root", default=DEFAULT_AC_ROOT, help="Assetto Corsa root folder")
    parser.add_argument("--out", "-o", help="Target output JSON path")

    args = parser.parse_args()

    try:
        test_data = build_test_definition(
            test_id=args.id,
            tier=args.tier,
            title=args.title,
            description=args.desc,
            lesson_objective=args.obj,
            car_id=args.car,
            track_id=args.track,
            track_layout=args.layout,
            start_mode=args.start_mode,
            start_s=args.start_s,
            finish_s=args.finish_s,
            spawn_offset=args.spawn_offset,
            speed=args.speed,
            gold=args.gold,
            silver=args.silver,
            bronze=args.bronze,
            with_stop_box=args.stop_box,
            ac_root=args.ac_root,
        )
    except Exception as e:
        print(f"[ERROR] Calibration failed: {e}", file=sys.stderr)
        return 1

    formatted = json.dumps(test_data, indent=2)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(formatted + "\n")
        print(f"[SUCCESS] Test written to {args.out}")

        # Immediately validate
        validator = CurriculumValidator(ac_root=args.ac_root)
        issues = validator.validate_test_file(args.out)
        if any(i.severity == "ERROR" for i in issues):
            print("[WARN] Generated test has validation errors:", file=sys.stderr)
            for i in issues:
                print(f"  {i.severity}: {i.message}", file=sys.stderr)
            return 1
        print("[SUCCESS] Test passed immediate schema and geometry validation!")
    else:
        print(formatted)

    return 0


if __name__ == "__main__":
    sys.exit(main())
