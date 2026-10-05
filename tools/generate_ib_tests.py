#!/usr/bin/env python3
"""
generate_ib_tests.py
Generates the 12 International B license tests according to docs/04_kunos_licenses_proposal.md
and validates them against schema/test_definition.schema.json.
"""

import json
import os
import sys

# Ensure tools directory is on path
tools_dir = os.path.dirname(os.path.abspath(__file__))
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)

from test_calibration_tool import build_test_definition
from validate_curriculum import CurriculumValidator

REPO_ROOT = os.path.dirname(tools_dir)
OUT_DIR = os.path.join(REPO_ROOT, "content", "tests", "international_b")

TESTS = [
    {
        "num": 1,
        "test_id": "IB-1",
        "title": "High-Speed Heavy Braking into Tamburello",
        "description": "High-speed deceleration from 250 km/h in a 9,000 RPM supercar. Hard initial brake hit, bleed off pressure, and flick left-right across high curbs without unsettling the rear diffuser.",
        "lesson_objective": "Master high-speed heavy straight-line braking, threshold pressure release, and curb absorption.",
        "car_id": "ferrari_458",
        "track_id": "imola",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.0864,
        "finish_s": 0.2015,
        "spawn_offset": 50.0,
        "speed": 240.0,
        "gold": 15.9,
        "silver": 16.7,
        "bronze": 18.0,
    },
    {
        "num": 2,
        "test_id": "IB-2",
        "title": "Rear-Engine Pendulum Dynamics & Traction",
        "description": "Mastering the rear-engine layout. Deep trail-braking to pin the front tires into Cimini 1, followed by utilizing huge rear traction over the rear axle to launch through Cimini 2.",
        "lesson_objective": "Master rear-engine weight transfer, trail-braking front loading, and aggressive exit traction.",
        "car_id": "ks_porsche_911_gt3_rs",
        "track_id": "ks_vallelunga",
        "track_layout": "extended_circuit",
        "start_mode": "ROLLING",
        "start_s": 0.1861,
        "finish_s": 0.3177,
        "spawn_offset": 40.0,
        "speed": 160.0,
        "gold": 17.8,
        "silver": 18.7,
        "bronze": 20.1,
    },
    {
        "num": 3,
        "test_id": "IB-3",
        "title": "Downforce Commitment: Pouhon Double-Apex",
        "description": "Legendary high-speed downhill double-left. In a lightweight aero car, tap the brake lightly, tuck into the first apex at 170 km/h, let the car float to mid-track, and pull tight for the second apex.",
        "lesson_objective": "Commit to aerodynamic downforce, maintain high apex speed, and execute a geometric double-apex line.",
        "car_id": "lotus_2_eleven",
        "track_id": "spa",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.5040,
        "finish_s": 0.6264,
        "spawn_offset": 40.0,
        "speed": 170.0,
        "gold": 19.4,
        "silver": 20.3,
        "bronze": 22.0,
    },
    {
        "num": 4,
        "test_id": "IB-4",
        "title": "Big Displacement V8 Torque Modulation",
        "description": "Tight double-apex hairpin. Managing 630 Nm of torque in 2nd gear; waiting until the car is pointed straight before pinning the throttle to prevent power oversteer.",
        "lesson_objective": "Modulate high-torque delivery out of low-speed hairpins to prevent power oversteer.",
        "car_id": "ks_corvette_c7_stingray",
        "track_id": "ks_laguna_seca",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.0422,
        "finish_s": 0.1827,
        "spawn_offset": 35.0,
        "speed": 150.0,
        "gold": 16.8,
        "silver": 17.6,
        "bronze": 19.0,
    },
    {
        "num": 5,
        "test_id": "IB-5",
        "title": "Active Aerodynamics at 230 km/h",
        "description": "Long uphill high-speed sweeper. Trusting the Aerodinamica Lamborghini Attiva (ALA) vectoring downforce; pinning the throttle at 220+ km/h without backing off.",
        "lesson_objective": "Trust active aerodynamic downforce and hold flat throttle through high-g sweepers.",
        "car_id": "ks_lamborghini_huracan_performante",
        "track_id": "ks_barcelona",
        "track_layout": "layout_gp",
        "start_mode": "ROLLING",
        "start_s": 0.2135,
        "finish_s": 0.3660,
        "spawn_offset": 40.0,
        "speed": 180.0,
        "gold": 14.2,
        "silver": 14.9,
        "bronze": 16.0,
    },
    {
        "num": 6,
        "test_id": "IB-6",
        "title": "High-Speed Chicane Precision: Ascari",
        "description": "High-speed entrance into left-right-left transition. Hard braking into Turn 8, clipping the right curb at Turn 9, and carrying full acceleration flat-out through Turn 10 towards the back straight.",
        "lesson_objective": "Execute rapid directional transitions and maintain curb stability at high speeds.",
        "car_id": "bmw_m3_e92_s1",
        "track_id": "monza",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.6340,
        "finish_s": 0.7730,
        "spawn_offset": 50.0,
        "speed": 220.0,
        "gold": 18.5,
        "silver": 19.4,
        "bronze": 20.8,
    },
    {
        "num": 7,
        "test_id": "IB-7",
        "title": "Heavyweight Digital AWD Traction",
        "description": "Managing 1.7 tonnes at race pace. Braking in a straight line, letting the electronic ATTESA differential sort traction, and rocketing out of the final chicane.",
        "lesson_objective": "Harness all-wheel-drive traction systems under heavy braking and corner-exit rotation.",
        "car_id": "ks_nissan_gtr",
        "track_id": "ks_nurburgring",
        "track_layout": "layout_gp_a",
        "start_mode": "ROLLING",
        "start_s": 0.7880,
        "finish_s": 0.9259,
        "spawn_offset": 40.0,
        "speed": 160.0,
        "gold": 19.1,
        "silver": 20.0,
        "bronze": 21.5,
    },
    {
        "num": 8,
        "test_id": "IB-8",
        "title": "Blind Crest Downhill Esses: Casanova-Savelli",
        "description": "Severe downhill S-curve. Unloading the suspension over the Casanova crest, quick dab of brakes, and pitching the car left into Savelli as the road drops away.",
        "lesson_objective": "Navigate blind downhill elevation drops and manage transient lateral balance.",
        "car_id": "ks_alfa_giulia_qv",
        "track_id": "mugello",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.3176,
        "finish_s": 0.4427,
        "spawn_offset": 40.0,
        "speed": 170.0,
        "gold": 15.6,
        "silver": 16.4,
        "bronze": 17.8,
    },
    {
        "num": 9,
        "test_id": "IB-9",
        "title": "Slipstream Drafting & Clean Overtake",
        "description": "Drafting behind two spec race cars. Tucking into the slipstream to gain 15 km/h, pulling out to make a clean, non-contact pass into the heavy braking zone of Turn 3 before crossing the finish.",
        "lesson_objective": "Use aerodynamic slipstream drafting to maximize terminal velocity and execute clean overtaking.",
        "car_id": "ks_mazda_mx5_cup",
        "track_id": "ks_red_bull_ring",
        "track_layout": "layout_gp",
        "start_mode": "ROLLING",
        "start_s": 0.1284,
        "finish_s": 0.4084,
        "spawn_offset": 35.0,
        "speed": 120.0,
        "gold": 24.0,
        "silver": 25.2,
        "bronze": 27.0,
    },
    {
        "num": 10,
        "test_id": "IB-10",
        "title": "High-Speed Parabolica Exit Momentum",
        "description": "Decreasing-radius high-speed sweeper opening onto the main straight. Trail-braking deep, hugging the inside line, and opening the steering wheel early to reach 260+ km/h across the finish.",
        "lesson_objective": "Maximize corner exit speed onto a long straight through progressive throttle and unwinding steering.",
        "car_id": "ks_ferrari_488_gtb",
        "track_id": "monza",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.8424,
        "finish_s": 0.9814,
        "spawn_offset": 40.0,
        "speed": 180.0,
        "gold": 17.2,
        "silver": 18.0,
        "bronze": 19.4,
    },
    {
        "num": 11,
        "test_id": "IB-11",
        "title": "Historic High-Speed Drifting: Stowe & Club",
        "description": "1960s cross-ply tires and monstrous V8 power. Controlling sustained 4-wheel slip angle through high-speed bends without barriers; feathering throttle to avoid spinning into open fields.",
        "lesson_objective": "Balance high power and bias-ply vintage tire slip angles through high-speed sweeping corners.",
        "car_id": "shelby_cobra_427sc",
        "track_id": "ks_silverstone1967",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.5164,
        "finish_s": 0.7377,
        "spawn_offset": 40.0,
        "speed": 150.0,
        "gold": 23.5,
        "silver": 24.6,
        "bronze": 26.5,
    },
    {
        "num": 12,
        "test_id": "IB-12",
        "title": "Graduation: Red Bull Ring GP Full Lap",
        "description": "Complete International B graduation test. Full 4.3 km lap linking uphill heavy braking, off-camber drops, and fast aerodynamic 4th gear sweeps with zero track limit infringements.",
        "lesson_objective": "Demonstrate mastery of advanced car control, elevation changes, and high-speed commitment across a full lap.",
        "car_id": "ks_porsche_911_gt3_rs",
        "track_id": "ks_red_bull_ring",
        "track_layout": "layout_gp",
        "start_mode": "FLYING_LAP",
        "start_s": 0.001,
        "finish_s": 0.999,
        "spawn_offset": 100.0,
        "speed": 160.0,
        "gold": 96.5,
        "silver": 100.0,
        "bronze": 106.0,
    },
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    validator = CurriculumValidator(strict=True)

    print("Generating and validating International B license tests...")
    all_clean = True

    for t in TESTS:
        filename = f"test_ib{t['num']:02d}.json"
        out_path = os.path.join(OUT_DIR, filename)

        test_data = build_test_definition(
            test_id=t["test_id"],
            tier="International B",
            title=t["title"],
            description=t["description"],
            lesson_objective=t["lesson_objective"],
            car_id=t["car_id"],
            track_id=t["track_id"],
            track_layout=t["track_layout"],
            start_mode=t["start_mode"],
            start_s=t["start_s"],
            finish_s=t["finish_s"],
            spawn_offset=t["spawn_offset"],
            speed=t["speed"],
            gold=t["gold"],
            silver=t["silver"],
            bronze=t["bronze"],
        )

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2)

        issues = validator.validate_test_file(out_path)
        if issues:
            print(f"[FAIL] {t['test_id']} ({filename}):")
            for iss in issues:
                print(f"  {iss.severity} ({iss.category}): {iss.message}")
            all_clean = False
        else:
            print(f"[PASS] {t['test_id']} ({filename})")

    if all_clean:
        print("\nAll 12 International B tests generated and validated cleanly with 0 errors!")
    else:
        print("\nSome tests had issues. Please review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
