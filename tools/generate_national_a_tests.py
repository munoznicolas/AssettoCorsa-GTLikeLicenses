#!/usr/bin/env python3
"""
generate_national_a_tests.py
Authoring script for National A License tests (A-1 through A-12).
Generates test JSON definitions conforming to schema/test_definition.schema.json
and validated by tools/validate_curriculum.py.
"""

import json
import math
import os
import sys

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.extract_spline_coords import SplineParser, find_spline_file

OUTPUT_DIR = os.path.join(REPO_ROOT, "content", "tests", "national_a")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_DEFINITIONS = [
    {
        "num": 1,
        "test_id": "A-1",
        "title": "1000m Maximum Acceleration & High-Speed Stop",
        "description": "Accelerate to maximum velocity along the 1000m drag strip and execute threshold braking to bring the BMW M3 E92 to a complete stop inside the designated stop box.",
        "lesson_objective": "High-velocity braking from 225+ km/h. Managing the high inertia of a 1.6-tonne V8 coupe; brake smoothly to the threshold to stop cleanly inside the box without front-lock lockup.",
        "car_id": "bmw_m3_e92",
        "track_id": "ks_drag",
        "track_layout": "drag1000",
        "start_mode": "STANDING",
        "initial_speed_kmh": 0.0,
        "start_d": 0.5,
        "finish_d": 1000.0,
        "spawn_d": 0.0,
        "with_stop_box": True,
        "stop_box_d": 1025.0,
        "targets": {
            "gold_seconds": 26.500,
            "silver_seconds": 27.400,
            "bronze_seconds": 29.000,
        },
    },
    {
        "num": 2,
        "test_id": "A-2",
        "title": "The Corkscrew: Severe Elevation Drop",
        "description": "Brake blind uphill over the crest of Turn 8 at Laguna Seca, plunging five stories downward through Turn 8A into the compression while keeping the Porsche 718 Cayman S balanced.",
        "lesson_objective": "Braking uphill into a completely blind crest. Sighting the oak tree marker, braking in a straight line, clipping the left curb as the track falls 5 stories, and immediately transitioning right into the bottom compression.",
        "car_id": "ks_porsche_718_cayman_s",
        "track_id": "ks_laguna_seca",
        "track_layout": "",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 130.0,
        "start_d": 2250.0,
        "finish_d": 2700.0,
        "spawn_d": 2200.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 15.800,
            "silver_seconds": 16.500,
            "bronze_seconds": 17.800,
        },
    },
    {
        "num": 3,
        "test_id": "A-3",
        "title": "Turbo Torque Modulation on Corner Exit",
        "description": "Negotiate the tight double hairpins of Magione, squeezing the throttle progressively to manage the 2JZ twin-turbo boost onset without breaking rear traction.",
        "lesson_objective": "Managing sequential twin-turbo boost onset. Squeezing throttle progressively on corner exit; preventing sudden boost spikes from breaking rear traction into snap oversteer.",
        "car_id": "ks_toyota_supra_mkiv",
        "track_id": "magione",
        "track_layout": "",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 80.0,
        "start_d": 720.0,
        "finish_d": 1050.0,
        "spawn_d": 670.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 16.200,
            "silver_seconds": 17.000,
            "bronze_seconds": 18.500,
        },
    },
    {
        "num": 4,
        "test_id": "A-4",
        "title": "Mid-Engine Snap Oversteer Control",
        "description": "Tackle the fast downhill left at Graham Hill Bend in the carbon-monocoque Alfa Romeo 4C, balancing maintenance throttle through turn-in and mid-corner.",
        "lesson_objective": "Off-camber downhill left turn. Avoiding abrupt throttle lift mid-corner which triggers instantaneous snap oversteer in a light, carbon-tub mid-engine car.",
        "car_id": "ks_alfa_romeo_4c",
        "track_id": "ks_brands_hatch",
        "track_layout": "indy",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 110.0,
        "start_d": 720.0,
        "finish_d": 1100.0,
        "spawn_d": 660.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 13.100,
            "silver_seconds": 13.800,
            "bronze_seconds": 14.900,
        },
    },
    {
        "num": 5,
        "test_id": "A-5",
        "title": "High-Speed Curb Bouncing Chicane",
        "description": "Attack the high kerbs of Variante Alta at Imola in the BMW 1M, squaring up the steering to absorb the curb strikes without unsettling the short-wheelbase chassis.",
        "lesson_objective": "Attacking high kerbs. Straightening the steering wheel just before mounting the high curbs so the wheels absorb the shock without kicking the rear bumper sideways.",
        "car_id": "bmw_1m",
        "track_id": "imola",
        "track_layout": "",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 140.0,
        "start_d": 3100.0,
        "finish_d": 3550.0,
        "spawn_d": 3020.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 14.500,
            "silver_seconds": 15.200,
            "bronze_seconds": 16.400,
        },
    },
    {
        "num": 6,
        "test_id": "A-6",
        "title": "Group B Rally Homologation AWD Handling",
        "description": "Thread the Audi Sport quattro through the narrow stone walls and bridges of Highlands Short, initiating early turn-in to overcome understeer before powering out.",
        "lesson_objective": "Taming a short-wheelbase front-heavy turbo AWD rally legend. Initiating turn-in early to overcome initial understeer, then powering through narrow stone-wall lined roads.",
        "car_id": "ks_audi_sport_quattro",
        "track_id": "ks_highlands",
        "track_layout": "layout_short",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 100.0,
        "start_d": 300.0,
        "finish_d": 800.0,
        "spawn_d": 240.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 17.800,
            "silver_seconds": 18.600,
            "bronze_seconds": 20.000,
        },
    },
    {
        "num": 7,
        "test_id": "A-7",
        "title": "Downhill Hairpin Trail-Braking",
        "description": "Brake hard up the steep incline of the Red Bull Ring into the Remus hairpin, trailing off the brakes smoothly to rotate the Nissan 370Z NISMO down toward the exit.",
        "lesson_objective": "Steep uphill braking followed by a sharp downhill drop. Trailing brake pressure smoothly past turn-in to keep weight on the front tires and tuck the nose into the apex.",
        "car_id": "ks_nissan_370z",
        "track_id": "ks_red_bull_ring",
        "track_layout": "layout_gp",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 170.0,
        "start_d": 1000.0,
        "finish_d": 1500.0,
        "spawn_d": 900.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 16.900,
            "silver_seconds": 17.700,
            "bronze_seconds": 19.000,
        },
    },
    {
        "num": 8,
        "test_id": "A-8",
        "title": "High-Speed Blind Crest Commitment",
        "description": "Commit flat out over the blind downhill crest of Scheivlak at Circuit Zandvoort in the Lotus Exige 240R, relying on mechanical downforce and committed steering.",
        "lesson_objective": "Fast blind right-hander falling downhill. Trusting the mechanical grip of an aggressive track setup; carrying 160+ km/h through the crest without backing off.",
        "car_id": "lotus_exige_240",
        "track_id": "ks_zandvoort",
        "track_layout": "",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 150.0,
        "start_d": 1550.0,
        "finish_d": 2000.0,
        "spawn_d": 1470.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 12.400,
            "silver_seconds": 13.000,
            "bronze_seconds": 14.200,
        },
    },
    {
        "num": 9,
        "test_id": "A-9",
        "title": "High-Speed Esses Precision",
        "description": "Thread the BMW M3 E30 S1 through the high-speed Maggotts-Becketts-Chapel esses at Silverstone GP with precision rhythm, minimal brake taps, and flowing momentum.",
        "lesson_objective": "One of the fastest corner combinations in motorsport. Precision rhythm: lift slightly for Maggotts, dab brakes into Becketts, and set up a wide line into Chapel for the Hangar Straight.",
        "car_id": "bmw_m3_e30_s1",
        "track_id": "ks_silverstone",
        "track_layout": "gp",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 160.0,
        "start_d": 3400.0,
        "finish_d": 4250.0,
        "spawn_d": 3300.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 21.000,
            "silver_seconds": 22.000,
            "bronze_seconds": 23.800,
        },
    },
    {
        "num": 10,
        "test_id": "A-10",
        "title": "Rotary Engine High-RPM Throttle Feathering",
        "description": "Keep the twin-rotor Mazda RX-7 singing in its high-RPM powerband around the sweeping Curva Campagnano at Vallelunga, balancing throttle feathering with tire slip angle.",
        "lesson_objective": "Long 180° sweeping turn. Keeping the twin-rotary engine singing in its high-power powerband while feathering throttle to avoid burning the rear tires.",
        "car_id": "ks_mazda_rx7_spirit_r",
        "track_id": "ks_vallelunga",
        "track_layout": "classic_circuit",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 130.0,
        "start_d": 850.0,
        "finish_d": 1300.0,
        "spawn_d": 770.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 15.500,
            "silver_seconds": 16.300,
            "bronze_seconds": 17.500,
        },
    },
    {
        "num": 11,
        "test_id": "A-11",
        "title": "Classic Rally 4WD Slide & Exit",
        "description": "Utilize the full traction of the Celica GT-Four ST185 through the linked Surtees-to-Clearways sweep at Brands Hatch Indy, stabilizing turn exit onto Brabham Straight.",
        "lesson_objective": "Connecting off-camber linked corners. Using the 4WD system to stabilize the car across the long looping Clearways sweep and accelerating onto Brabham Straight.",
        "car_id": "ks_toyota_celica_st185",
        "track_id": "ks_brands_hatch",
        "track_layout": "indy",
        "start_mode": "ROLLING",
        "initial_speed_kmh": 110.0,
        "start_d": 1150.0,
        "finish_d": 1750.0,
        "spawn_d": 1080.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 18.200,
            "silver_seconds": 19.000,
            "bronze_seconds": 20.500,
        },
    },
    {
        "num": 12,
        "test_id": "A-12",
        "title": "Graduation: Brands Hatch Indy Full Lap",
        "description": "Complete a full flying lap around Brands Hatch Indy in the mid-engine Porsche 718 Cayman S, synthesizing elevation drops, blind apexes, and throttle modulation.",
        "lesson_objective": "Comprehensive National A graduation lap. Synthesizes blind drops, hairpin patience, off-camber trail-braking, and exit momentum across a complete sub-minute lap.",
        "car_id": "ks_porsche_718_cayman_s",
        "track_id": "ks_brands_hatch",
        "track_layout": "indy",
        "start_mode": "FLYING_LAP",
        "initial_speed_kmh": 130.0,
        "start_d": 15.0,
        "finish_d": 1900.0,
        "spawn_d": 1908.0,
        "with_stop_box": False,
        "targets": {
            "gold_seconds": 52.800,
            "silver_seconds": 55.200,
            "bronze_seconds": 59.000,
        },
    },
]

def normalize_vector(vec):
    length = math.sqrt(sum(v * v for v in vec))
    if length > 1e-6:
        return [round(v / length, 4) for v in vec]
    return [0.0, 0.0, 1.0]

def main():
    print(f"Generating 12 National A tests in {OUTPUT_DIR}...")
    created_files = []

    for spec in TEST_DEFINITIONS:
        track_id = spec["track_id"]
        layout = spec["track_layout"]
        sf = find_spline_file(track_id, layout)
        if not sf:
            raise FileNotFoundError(f"Spline file not found for track {track_id} [{layout}]")

        parser = SplineParser(sf)

        # Gates
        start_gate = parser.compute_gate(spec["start_d"])
        finish_gate = parser.compute_gate(spec["finish_d"])

        # Enforce gate width limits (8.0m <= width <= 25.0m)
        assert 8.0 <= start_gate.width <= 25.0, f"Start gate width {start_gate.width} out of bounds"
        assert 8.0 <= finish_gate.width <= 25.0, f"Finish gate width {finish_gate.width} out of bounds"

        # Spawn
        spawn_pos, spawn_fwd, _, _ = parser.query_distance(spec["spawn_d"])
        if track_id == "ks_drag":
            # For drag strip, vehicle drives along +X
            spawn_fwd = (1.0, 0.0, 0.0)

        fwd_norm = normalize_vector(spawn_fwd)

        timing_dict = {
            "start_gate": {
                "p1": start_gate.p1,
                "p2": start_gate.p2,
            },
            "finish_gate": {
                "p1": finish_gate.p1,
                "p2": finish_gate.p2,
            },
        }

        if spec["with_stop_box"]:
            box_pos, box_fwd, _, _ = parser.query_distance(spec["stop_box_d"])
            if track_id == "ks_drag":
                yaw_deg = 90.0
            else:
                yaw_deg = round(math.degrees(math.atan2(box_fwd[0], box_fwd[2])), 2)

            timing_dict["stop_box"] = {
                "center": [round(box_pos[0], 3), round(box_pos[1] + 2.0, 3), round(box_pos[2], 3)],
                "size": [15.0, 4.0, 50.0],
                "rotation_deg": yaw_deg,
            }

        fail_rules = {
            "max_wheels_off": 2,
            "wall_collision_threshold_n": 1500,
            "max_yaw_angle_deg": 90,
            "stop_box_overshoot_fail": spec["with_stop_box"],
        }

        test_data = {
            "test_id": spec["test_id"],
            "tier": "National A",
            "title": spec["title"],
            "description": spec["description"],
            "lesson_objective": spec["lesson_objective"],
            "car_id": spec["car_id"],
            "track_id": spec["track_id"],
            "track_layout": spec["track_layout"],
            "start_mode": spec["start_mode"],
            "spawn": {
                "position": spawn_pos,
                "forward_vector": fwd_norm,
                "initial_speed_kmh": spec["initial_speed_kmh"],
            },
            "timing": timing_dict,
            "fail_rules": fail_rules,
            "targets": spec["targets"],
        }

        filename = f"test_a{spec['num']:02d}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2)

        print(f"Created {filename} for {spec['test_id']}: {spec['title']}")
        created_files.append(filepath)

    print(f"Successfully generated {len(created_files)} test definition files.")

if __name__ == "__main__":
    main()
