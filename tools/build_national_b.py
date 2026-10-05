#!/usr/bin/env python3
"""
build_national_b.py
Generates all 12 National B license test JSON files using extract_spline_coords.
"""

import json
import os
import sys

from extract_spline_coords import find_spline_file, SplineParser, generate_test_parameters
from validate_curriculum import CurriculumValidator

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(REPO_ROOT, "content", "tests", "national_b")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TESTS = [
    {
        "filename": "test_b01.json",
        "test_id": "B-1",
        "tier": "National B",
        "title": "200m Acceleration & Braking",
        "description": "Launch cleanly with minimal front wheelspin. Reach peak speed in 3rd gear, anchor eyes on the 150m braking marker, and execute threshold braking to bring the car to a full stop inside the marked grid box without locking the tires or overshooting.",
        "lesson_objective": "Master standing launch traction and threshold braking down to complete standstill within target stop box.",
        "car_id": "abarth500",
        "track_id": "ks_drag",
        "track_layout": "drag200",
        "spline_track": "ks_drag",
        "spline_layout": "drag200",
        "start_mode": "STANDING",
        "start_dist": 10.0,
        "finish_dist": 210.0,
        "spawn_offset": 3.0,
        "speed": 0.0,
        "with_stop_box": True,
        "stop_box_offset": 5.0,
        "gold": 11.200,
        "silver": 11.800,
        "bronze": 12.800,
    },
    {
        "filename": "test_b02.json",
        "test_id": "B-2",
        "tier": "National B",
        "title": "500m Acceleration & High-Speed Stop",
        "description": "High-speed braking from 170+ km/h. Managing the heavier 1,390 kg curb weight; braking early enough to avoid triggering ABS wheel hop while stopping fully within the designated box.",
        "lesson_objective": "Threshold braking from high speed with high-inertia chassis into a controlled stop.",
        "car_id": "alfa_romeo_giulietta_qv",
        "track_id": "ks_drag",
        "track_layout": "drag500",
        "spline_track": "ks_drag",
        "spline_layout": "drag500",
        "start_mode": "STANDING",
        "start_dist": 10.0,
        "finish_dist": 510.0,
        "spawn_offset": 3.0,
        "speed": 0.0,
        "with_stop_box": True,
        "stop_box_offset": 5.0,
        "gold": 18.400,
        "silver": 19.100,
        "bronze": 20.500,
    },
    {
        "filename": "test_b03.json",
        "test_id": "B-3",
        "tier": "National B",
        "title": "Out-In-Out Hairpin Trajectory",
        "description": "Approach from the far track edge. Brake in a straight line, clip the rumble strip late at the apex, and open the steering wheel progressively onto the exit straight to preserve rolling momentum in a low-horsepower roadster.",
        "lesson_objective": "Learn the classic out-in-out racing line through a tight 180-degree hairpin.",
        "car_id": "ks_mazda_miata",
        "track_id": "ks_vallelunga",
        "track_layout": "club_circuit",
        "spline_track": "ks_vallelunga",
        "spline_layout": "club_circuit",
        "start_mode": "ROLLING",
        "start_dist": 690.0,
        "finish_dist": 840.0,
        "spawn_offset": 35.0,
        "speed": 70.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 13.800,
        "silver": 14.500,
        "bronze": 15.800,
    },
    {
        "filename": "test_b04.json",
        "test_id": "B-4",
        "tier": "National B",
        "title": "Front-Wheel Drive Understeer Management",
        "description": "Understanding that aggressive throttle in FWD pushes the nose wide. Modulate throttle at 40–50% mid-corner until the front tires regain grip, then squeeze full throttle once the wheels are straightened.",
        "lesson_objective": "Mitigate front tire scrub and understeer by feathering throttle mid-corner.",
        "car_id": "ks_alfa_mito_qv",
        "track_id": "magione",
        "track_layout": "",
        "spline_track": "magione",
        "spline_layout": "",
        "start_mode": "ROLLING",
        "start_dist": 1650.0,
        "finish_dist": 1850.0,
        "spawn_offset": 40.0,
        "speed": 90.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 12.900,
        "silver": 13.500,
        "bronze": 14.600,
    },
    {
        "filename": "test_b05.json",
        "test_id": "B-5",
        "tier": "National B",
        "title": "Low-Speed Weight Transfer & Transition",
        "description": "Managing a classic live-axle rear-wheel drive chassis. Trail-braking into Brooklands, settling the suspension, and smoothly transferring lateral load across into the long looping Luffield radius.",
        "lesson_objective": "Coordinate longitudinal braking and lateral weight transfer through linked corners.",
        "car_id": "ks_toyota_ae86",
        "track_id": "ks_silverstone",
        "track_layout": "national",
        "spline_track": "ks_silverstone",
        "spline_layout": "national",
        "start_mode": "ROLLING",
        "start_dist": 1680.0,
        "finish_dist": 2080.0,
        "spawn_offset": 50.0,
        "speed": 100.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 19.400,
        "silver": 20.200,
        "bronze": 21.800,
    },
    {
        "filename": "test_b06.json",
        "test_id": "B-6",
        "tier": "National B",
        "title": "Threshold Braking from 190 km/h into Chicane",
        "description": "Heavy braking at the 150m board down to 60 km/h. Downshifting with rev-matching, hopping the first right curb cleanly without unsettling the rear, and accelerating tight off the left exit.",
        "lesson_objective": "Execute high-speed straight-line deceleration into a tight multi-apex chicane.",
        "car_id": "bmw_m3_e30",
        "track_id": "monza",
        "track_layout": "",
        "spline_track": "monza",
        "spline_layout": "",
        "start_mode": "ROLLING",
        "start_dist": 780.0,
        "finish_dist": 1050.0,
        "spawn_offset": 70.0,
        "speed": 180.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 14.800,
        "silver": 15.500,
        "bronze": 16.800,
    },
    {
        "filename": "test_b07.json",
        "test_id": "B-7",
        "tier": "National B",
        "title": "Slalom Rhythm & Transient Agility",
        "description": "Steering cadence through 6 staggered cones. Throttle feathering in 2nd gear; using weight transfer to rotate the mid-engine chassis around each cone without scrubbing front tire grip or touching cones.",
        "lesson_objective": "Develop precise steering rhythm and rapid transient weight shifting.",
        "car_id": "lotus_elise_sc",
        "track_id": "drift",
        "track_layout": "karting",
        "spline_track": "drift",
        "spline_layout": "karting",
        "start_mode": "STANDING",
        "start_dist": 180.0,
        "finish_dist": 360.0,
        "spawn_offset": 3.0,
        "speed": 0.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 17.200,
        "silver": 18.000,
        "bronze": 19.600,
    },
    {
        "filename": "test_b08.json",
        "test_id": "B-8",
        "tier": "National B",
        "title": "Blind Compression Corner Entry",
        "description": "Downhill compression dynamics. Committing to turn-in at the blind crest, soaking the vertical compression at the bottom, and staying off the outside gravel trap.",
        "lesson_objective": "Maintain steering commitment over a crest through vertical suspension compression.",
        "car_id": "ks_mazda_mx5_nd",
        "track_id": "ks_brands_hatch",
        "track_layout": "indy",
        "spline_track": "ks_brands_hatch",
        "spline_layout": "indy",
        "start_mode": "ROLLING",
        "start_dist": 120.0,
        "finish_dist": 400.0,
        "spawn_offset": 50.0,
        "speed": 120.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 11.900,
        "silver": 12.500,
        "bronze": 13.600,
    },
    {
        "filename": "test_b09.json",
        "test_id": "B-9",
        "tier": "National B",
        "title": "All-Wheel Drive Launch & Traction Cornering",
        "description": "Aggressive standing AWD launch. Braking uphill deep into Turn 1, clipping the tall curb, and leveraging quattro all-wheel pull early out of the apex without inducing understeer push.",
        "lesson_objective": "Exploit all-wheel drive traction on standing launch and corner exit acceleration.",
        "car_id": "ks_audi_a1s1",
        "track_id": "ks_red_bull_ring",
        "track_layout": "layout_national",
        "spline_track": "ks_red_bull_ring",
        "spline_layout": "layout_national",
        "start_mode": "STANDING",
        "start_dist": 120.0,
        "finish_dist": 420.0,
        "spawn_offset": 3.0,
        "speed": 0.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 14.200,
        "silver": 14.900,
        "bronze": 16.100,
    },
    {
        "filename": "test_b10.json",
        "test_id": "B-10",
        "tier": "National B",
        "title": "High-Speed Carousel Feathering",
        "description": "Long tightening carousel turn. Balancing the car on the edge of oversteer on low-grip factory tires; avoiding violent steering corrections that scrub time.",
        "lesson_objective": "Feather throttle around a long sustained radius corner near lateral limits.",
        "car_id": "ks_toyota_gt86",
        "track_id": "ks_nurburgring",
        "track_layout": "layout_sprint_a",
        "spline_track": "ks_nurburgring",
        "spline_layout": "layout_sprint_a",
        "start_mode": "ROLLING",
        "start_dist": 700.0,
        "finish_dist": 1150.0,
        "spawn_offset": 40.0,
        "speed": 90.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 22.500,
        "silver": 23.600,
        "bronze": 25.400,
    },
    {
        "filename": "test_b11.json",
        "test_id": "B-11",
        "tier": "National B",
        "title": "S-Bend Line Straightening",
        "description": "Classic lightweight live-axle rear-wheel drive. Sacrificing entry speed in Turn 2 to straighten the line and maximize rolling exit speed up the banked Hugenholtz corner.",
        "lesson_objective": "Sacrifice entry velocity to straighten the geometry and maximize exit momentum.",
        "car_id": "ks_ford_escort_mk1",
        "track_id": "ks_zandvoort",
        "track_layout": "",
        "spline_track": "ks_zandvoort",
        "spline_layout": "",
        "start_mode": "ROLLING",
        "start_dist": 580.0,
        "finish_dist": 960.0,
        "spawn_offset": 50.0,
        "speed": 100.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 16.800,
        "silver": 17.600,
        "bronze": 19.000,
    },
    {
        "filename": "test_b12.json",
        "test_id": "B-12",
        "tier": "National B",
        "title": "Graduation: Vallelunga Club Full Lap",
        "description": "Comprehensive National B graduation trial. Connect Curva Grande, Campagnano, Tornantino, and the final sweeping bends cleanly without exceeding track boundaries or touching barriers.",
        "lesson_objective": "Demonstrate mastery of all National B vehicle dynamics across a full flying lap.",
        "car_id": "ks_toyota_gt86",
        "track_id": "ks_vallelunga",
        "track_layout": "club_circuit",
        "spline_track": "ks_vallelunga",
        "spline_layout": "club_circuit",
        "start_mode": "FLYING_LAP",
        "start_dist": 5.0,
        "finish_dist": 1715.0,
        "spawn_offset": 60.0,
        "speed": 110.0,
        "with_stop_box": False,
        "stop_box_offset": 0.0,
        "gold": 57.900,
        "silver": 60.200,
        "bronze": 64.500,
    },
]

def main():
    print("[INFO] Building all 12 National B test definitions...")
    validator = CurriculumValidator()

    for item in TESTS:
        spline_file = find_spline_file(item["spline_track"], item["spline_layout"])
        if not spline_file or not os.path.isfile(spline_file):
            print(f"[ERROR] Spline not found for {item['test_id']}: {item['spline_track']} / {item['spline_layout']}")
            return 1

        parser = SplineParser(spline_file)
        start_progress = item["start_dist"] / parser.total_length
        finish_progress = item["finish_dist"] / parser.total_length

        params = generate_test_parameters(
            parser=parser,
            start_progress=start_progress,
            finish_progress=finish_progress,
            spawn_offset_m=item["spawn_offset"],
            initial_speed_kmh=item["speed"],
            with_stop_box=item["with_stop_box"],
            stop_box_offset_m=item["stop_box_offset"],
        )

        # For standing start tests on drag strip, make sure forward vector is normalized [1.0, 0.0, 0.0]
        # In case waypoint 0 had flipped sign in header
        fwd = params["spawn"]["forward_vector"]
        if item["test_id"] in ("B-1", "B-2"):
            if fwd[0] < 0:
                params["spawn"]["forward_vector"] = [1.0, 0.0, 0.0]

        test_data = {
            "test_id": item["test_id"],
            "tier": item["tier"],
            "title": item["title"],
            "description": item["description"],
            "lesson_objective": item["lesson_objective"],
            "car_id": item["car_id"],
            "track_id": item["track_id"],
            "track_layout": item["track_layout"],
            "start_mode": item["start_mode"],
            "spawn": params["spawn"],
            "timing": params["timing"],
            "fail_rules": {
                "max_wheels_off": 2,
                "wall_collision_threshold_n": 1500,
                "max_yaw_angle_deg": 90,
                "stop_box_overshoot_fail": item["with_stop_box"],
            },
            "targets": {
                "gold_seconds": round(item["gold"], 3),
                "silver_seconds": round(item["silver"], 3),
                "bronze_seconds": round(item["bronze"], 3),
            },
        }

        out_path = os.path.join(OUTPUT_DIR, item["filename"])
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2)
            f.write("\n")

        print(f"[OK] Generated {item['test_id']}: {out_path}")

    print("\n[INFO] Validating generated National B curriculum...")
    issues = validator.validate_tier("National B")
    error_count = sum(1 for i in issues if i.severity == "ERROR")
    warning_count = sum(1 for i in issues if i.severity == "WARNING")

    for i in issues:
        print(f"[{i.severity}] ({i.category}) {i.test_id}: {i.message}")

    print(f"\n[REPORT] Errors: {error_count}, Warnings: {warning_count}")
    if error_count == 0 and warning_count == 0:
        print("[SUCCESS] All 12 National B tests validated with 0 errors and 0 warnings!")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
