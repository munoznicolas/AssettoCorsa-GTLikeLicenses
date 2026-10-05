#!/usr/bin/env python3
"""
generate_super_license.py
Generates the 10 Super License test JSON definitions (test_s01.json to test_s10.json)
in content/tests/super_license/ conforming to schema/test_definition.schema.json.
"""

import json
import os
import sys

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)
from validate_curriculum import CurriculumValidator

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUPER_LICENSE_TESTS = [
    {
        "num": 1,
        "title": "Supercar Hot Lap: Laguna Seca",
        "desc": "Full unassisted hot lap in a 963 bhp hybrid hypercar across WeatherTech Raceway Laguna Seca.",
        "obj": "Managing explosive electric torque out of the Andretti hairpin, high-g commitment through Turn 6, and navigating the Corkscrew drop cleanly.",
        "car": "ferrari_laferrari",
        "track": "ks_laguna_seca",
        "layout": "",
        "speed": 140.0,
        "gold": 80.500,
        "silver": 84.000,
        "bronze": 90.000,
    },
    {
        "num": 2,
        "title": "British Heritage Time Attack: Brands Hatch GP",
        "desc": "Full lap around the narrow, barrier-lined Brands Hatch Grand Prix circuit in a hybrid hypercar.",
        "obj": "Active aero and DRS deployment; high concentration through fast off-camber woodland curves.",
        "car": "ks_mclaren_p1",
        "track": "ks_brands_hatch",
        "layout": "gp",
        "speed": 150.0,
        "gold": 84.200,
        "silver": 88.000,
        "bronze": 94.000,
    },
    {
        "num": 3,
        "title": "High-Downforce Aerodynamic Flow: Mugello",
        "desc": "Full lap in a naturally aspirated V12 track special around Autodromo del Mugello.",
        "obj": "Zero driving assists; connecting Casanova-Savelli, Arrabbiata 1 & 2, and Correntaio into one seamless high-g rhythm.",
        "car": "pagani_zonda_r",
        "track": "mugello",
        "layout": "",
        "speed": 160.0,
        "gold": 99.800,
        "silver": 104.000,
        "bronze": 111.000,
    },
    {
        "num": 4,
        "title": "High-Velocity Temple of Speed: Monza GP",
        "desc": "Full hot lap in the 1989 Group C Le Mans winner around the temple of speed, Monza.",
        "obj": "Exceeding 340 km/h on the straights, managing heavy turbo spool, and executing precise heavy braking into Prima Variante and Ascari.",
        "car": "ks_mercedes_c9",
        "track": "monza",
        "layout": "",
        "speed": 180.0,
        "gold": 94.500,
        "silver": 99.000,
        "bronze": 106.000,
    },
    {
        "num": 5,
        "title": "The 4-Rotor Symphony: Silverstone GP",
        "desc": "Full lap in the 1991 Le Mans-winning rotary prototype around Silverstone Grand Prix circuit.",
        "obj": "Heel-toe downshifting without synchros; pinning the throttle through Copse and Maggotts-Becketts-Chapel.",
        "car": "ks_mazda_787b",
        "track": "ks_silverstone",
        "layout": "gp",
        "speed": 160.0,
        "gold": 107.800,
        "silver": 112.500,
        "bronze": 120.000,
    },
    {
        "num": 6,
        "title": "Undulating Perfection: Imola GP",
        "desc": "Full lap utilizing ground-effect underbody tunnels around Autodromo Enzo e Dino Ferrari.",
        "obj": "High aerodynamic suction keeps the car glued to the track through Piratella and Acque Minerali; zero curb slamming.",
        "car": "ks_porsche_962c_shorttail",
        "track": "imola",
        "layout": "",
        "speed": 160.0,
        "gold": 95.200,
        "silver": 99.500,
        "bronze": 106.000,
    },
    {
        "num": 7,
        "title": "Modern Hybrid Prototype Mastery: Spa-Francorchamps",
        "desc": "Full hot lap in an 8-Megajoule LMP1 hybrid endurance monster around Circuit de Spa-Francorchamps.",
        "obj": "Electric front-wheel drive launch out of La Source, flat-out through Eau Rouge, and energy regeneration under braking into the Bus Stop.",
        "car": "ks_porsche_919_hybrid_2016",
        "track": "spa",
        "layout": "",
        "speed": 150.0,
        "gold": 114.000,
        "silver": 119.000,
        "bronze": 127.000,
    },
    {
        "num": 8,
        "title": "1,000 Horsepower Hybrid Attack: Red Bull Ring",
        "desc": "Complete hot lap in Toyota's WEC World Championship prototype around Red Bull Ring Grand Prix.",
        "obj": "Utilizing instant capacitor boost down the uphill straights and carrying massive speed through the final two sweepers.",
        "car": "ks_toyota_ts040",
        "track": "ks_red_bull_ring",
        "layout": "layout_gp",
        "speed": 170.0,
        "gold": 78.500,
        "silver": 82.000,
        "bronze": 88.000,
    },
    {
        "num": 9,
        "title": "Formula 1 V10 Apex Velocity: Barcelona GP",
        "desc": "Full lap in the benchmark Formula 1 V10 around Circuit de Barcelona-Catalunya Grand Prix.",
        "obj": "Generating over 4.5G in lateral cornering and pulling 100 m braking distances from 310 km/h. Zero room for hesitation.",
        "car": "ks_ferrari_f2004",
        "track": "ks_barcelona",
        "layout": "layout_gp",
        "speed": 190.0,
        "gold": 74.200,
        "silver": 77.500,
        "bronze": 83.000,
    },
    {
        "num": 10,
        "title": "The Ultimate Trial: Nürburgring Nordschleife Hot Lap",
        "desc": "Direct homage to Gran Turismo 4's legendary S-16 test: complete unassisted hot lap of the Green Hell (20.8 km) in an authentic DTM touring car.",
        "obj": "A single barrier touch, spin, or 4-wheels-off infraction triggers an instant disqualification across 154 turns.",
        "car": "ks_mercedes_190_evo2",
        "track": "ks_nordschleife",
        "layout": "nordschleife",
        "speed": 130.0,
        "gold": 428.500,
        "silver": 445.000,
        "bronze": 475.000,
    },
]


def generate_all(ac_root: str = DEFAULT_AC_ROOT):
    out_dir = os.path.join(REPO_ROOT, "content", "tests", "super_license")
    os.makedirs(out_dir, exist_ok=True)

    created_files = []

    for t in SUPER_LICENSE_TESTS:
        spline_file = find_spline_file(t["track"], t["layout"], ac_root)
        if not spline_file:
            raise FileNotFoundError(
                f"Spline file not found for track {t['track']} layout {t['layout']} in {ac_root}"
            )

        parser = SplineParser(spline_file)
        L = parser.total_length

        # For a full lap flying start:
        # Spawn at d = 0.0 (the start/finish line) heading forward along track
        # Start gate at d = 12.0m (12m ahead of spawn)
        # Finish gate at d = L - 12.0m (12m before the start/finish line)
        pos_spawn, fwd_spawn, _, _ = parser.query_distance(0.0)
        g_start = parser.compute_gate(12.0)
        g_finish = parser.compute_gate(L - 12.0)

        test_def = {
            "test_id": f"S-{t['num']}",
            "tier": "Super License",
            "title": t["title"],
            "description": t["desc"],
            "lesson_objective": t["obj"],
            "car_id": t["car"],
            "track_id": t["track"],
            "track_layout": t["layout"],
            "start_mode": "FLYING_LAP",
            "spawn": {
                "position": pos_spawn,
                "forward_vector": list(fwd_spawn),
                "initial_speed_kmh": round(t["speed"], 1),
            },
            "timing": {
                "start_gate": {
                    "p1": g_start.p1,
                    "p2": g_start.p2,
                },
                "finish_gate": {
                    "p1": g_finish.p1,
                    "p2": g_finish.p2,
                },
            },
            "fail_rules": {
                "max_wheels_off": 2,
                "wall_collision_threshold_n": 1500,
                "max_yaw_angle_deg": 90,
                "stop_box_overshoot_fail": False,
            },
            "targets": {
                "gold_seconds": round(t["gold"], 3),
                "silver_seconds": round(t["silver"], 3),
                "bronze_seconds": round(t["bronze"], 3),
            },
        }

        filename = f"test_s{t['num']:02d}.json"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_def, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"[OK] Generated {filename} (Track: {t['track']}, Lap Length: {L:.1f}m)")
        created_files.append(filepath)

    return created_files


if __name__ == "__main__":
    files = generate_all()
    print(f"\nAll {len(files)} Super License definitions written successfully.")

    # Validate generated files
    print("\nRunning curriculum validator...")
    validator = CurriculumValidator(strict=True)
    total_issues = 0
    for f in files:
        issues = validator.validate_test_file(f)
        if issues:
            total_issues += len(issues)
            for iss in issues:
                print(f"[{iss.severity}] {os.path.basename(f)}: {iss.message}")

    if total_issues == 0:
        print("[SUCCESS] All 10 Super License tests passed validation with 0 errors and 0 warnings!")
        sys.exit(0)
    else:
        print(f"[FAILED] Found {total_issues} issues.")
        sys.exit(1)
