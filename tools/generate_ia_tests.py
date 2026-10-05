#!/usr/bin/env python3
"""
generate_ia_tests.py
Authors all 12 International A license test definitions into content/tests/international_a/
"""

import json
import os
import sys

from extract_spline_coords import DEFAULT_AC_ROOT
from test_calibration_tool import build_test_definition
from validate_curriculum import CurriculumValidator

IA_TESTS = [
    {
        "test_id": "IA-1",
        "tier": "International A",
        "title": "The Benchmark: Eau Rouge & Raidillon Flat-Out",
        "description": "Navigate motorsport's most famous elevation climb: Eau Rouge and Raidillon at full throttle.",
        "lesson_objective": "Compressing at the bottom of Eau Rouge, flicking right up the blind 18% hill, clipping the left curb of Raidillon, and cresting onto Kemmel Straight at 240+ km/h without lifting or lifting only a fraction.",
        "car_id": "ks_ferrari_488_gt3",
        "track_id": "spa",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.105,
        "finish_s": 0.225,
        "spawn_offset": 45.0,
        "speed": 180.0,
        "gold": 14.200,
        "silver": 14.900,
        "bronze": 16.000,
        "filename": "test_ia01.json",
    },
    {
        "test_id": "IA-2",
        "tier": "International A",
        "title": "GT4 Trail-Braking & Weight Conservation",
        "description": "Master high-speed trail-braking and momentum conservation in the GT4 Porsche through Brands Hatch.",
        "lesson_objective": "Fast woodland section of Brands GP. Hard trail braking into Westfield, carrying momentum through the dip, and clipping the blind apex of Dingle Dell with race slicks.",
        "car_id": "ks_porsche_cayman_gt4_clubsport",
        "track_id": "ks_brands_hatch",
        "track_layout": "gp",
        "start_mode": "ROLLING",
        "start_s": 0.550,
        "finish_s": 0.740,
        "spawn_offset": 35.0,
        "speed": 140.0,
        "gold": 18.400,
        "silver": 19.300,
        "bronze": 20.800,
        "filename": "test_ia02.json",
    },
    {
        "test_id": "IA-3",
        "tier": "International A",
        "title": "Extreme Downforce Cornering: Arrabbiata 1 & 2",
        "description": "Harness high-aerodynamic downforce across Mugello's iconic double-apex Arrabbiata sweepers.",
        "lesson_objective": "Back-to-back uphill right-hand sweepers pulling over 2.5G. Squeezing full downforce out of the GT3 rear wing; holding a tight line through Arrabbiata 1 and maintaining flat throttle through the crest of Arrabbiata 2.",
        "car_id": "ks_audi_r8_lms_2016",
        "track_id": "mugello",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.420,
        "finish_s": 0.598,
        "spawn_offset": 40.0,
        "speed": 170.0,
        "gold": 17.500,
        "silver": 18.300,
        "bronze": 19.600,
        "filename": "test_ia03.json",
    },
    {
        "test_id": "IA-4",
        "tier": "International A",
        "title": "Classic DTM Aggressive Curb Hopping",
        "description": "Attack high yellow sausage curbs aggressively with the high-revving AWD Alfa Romeo 155 DTM touring car.",
        "lesson_objective": "12,000 RPM high-downforce AWD touring car. Aggressively launching over the high yellow curb stones; keeping the throttle pinned to let the AWD pull the car straight upon landing.",
        "car_id": "ks_alfa_romeo_155_v6",
        "track_id": "imola",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.215,
        "finish_s": 0.342,
        "spawn_offset": 45.0,
        "speed": 180.0,
        "gold": 13.900,
        "silver": 14.600,
        "bronze": 15.800,
        "filename": "test_ia04.json",
    },
    {
        "test_id": "IA-5",
        "tier": "International A",
        "title": "Front-Mid GT3 Platform Stability",
        "description": "Balance front-mid engine stability and high aero grip through Barcelona's demanding opening complex.",
        "lesson_objective": "Heavy braking from 240 km/h into a tight uphill flick (Turn 1/2) followed immediately by the long Turn 3 sweeper. Managing front-tire heat and maintaining aero balance.",
        "car_id": "ks_mercedes_amg_gt3",
        "track_id": "ks_barcelona",
        "track_layout": "layout_gp",
        "start_mode": "ROLLING",
        "start_s": 0.135,
        "finish_s": 0.355,
        "spawn_offset": 55.0,
        "speed": 220.0,
        "gold": 22.000,
        "silver": 23.000,
        "bronze": 24.800,
        "filename": "test_ia05.json",
    },
    {
        "test_id": "IA-6",
        "tier": "International A",
        "title": "Bus Stop Chicane: Braking from 270 km/h",
        "description": "Execute extreme threshold deceleration from maximum speed down to a crawl into Spa's Bus Stop chicane.",
        "lesson_objective": "Braking from Blanchimont into the tightest chicane on the circuit. Setting racing brake bias, stopping from 260 km/h down to 65 km/h, and squaring off the right-left exit onto the start straight.",
        "car_id": "ks_mclaren_650_gt3",
        "track_id": "spa",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.890,
        "finish_s": 0.995,
        "spawn_offset": 65.0,
        "speed": 250.0,
        "gold": 16.800,
        "silver": 17.600,
        "bronze": 19.000,
        "filename": "test_ia06.json",
    },
    {
        "test_id": "IA-7",
        "tier": "International A",
        "title": "Rear-Engine GT3 Pivot & Curb Launch",
        "description": "Rotate the rear-engine Porsche 911 GT3 chassis under trail-braking and power over the curbs at Nürburgring GP.",
        "lesson_objective": "Downhill braking into tight chicane. Trail-braking to rotate the rear-engine chassis quickly, bouncing over the left curb, and hammering the throttle over the right exit curb.",
        "car_id": "ks_porsche_911_gt3_r_2016",
        "track_id": "ks_nurburgring",
        "track_layout": "layout_gp_a",
        "start_mode": "ROLLING",
        "start_s": 0.080,
        "finish_s": 0.197,
        "spawn_offset": 40.0,
        "speed": 170.0,
        "gold": 15.200,
        "silver": 16.000,
        "bronze": 17.400,
        "filename": "test_ia07.json",
    },
    {
        "test_id": "IA-8",
        "tier": "International A",
        "title": "GTE Aerodynamic Diffuser Suction",
        "description": "Commit to full-throttle aerodynamic commitment at Silverstone's terrifyingly fast Copse corner.",
        "lesson_objective": "230+ km/h blind right-hander. Mid-engine inverted GTE diffuser suction allows carrying staggering apex speed; dab brake, turn in decisively, and ride the exit rumble strip.",
        "car_id": "ks_porsche_911_rsr_2017",
        "track_id": "ks_silverstone",
        "track_layout": "gp",
        "start_mode": "ROLLING",
        "start_s": 0.445,
        "finish_s": 0.562,
        "spawn_offset": 55.0,
        "speed": 220.0,
        "gold": 10.900,
        "silver": 11.500,
        "bronze": 12.600,
        "filename": "test_ia08.json",
    },
    {
        "test_id": "IA-9",
        "tier": "International A",
        "title": "Analog 1960s Prototype Mastery",
        "description": "Tame 1960s mechanical grip and high speeds through Curva Grande and Lesmo with zero driver aids.",
        "lesson_objective": "Vintage cross-ply racing slicks, heavy clutch, zero assists. Navigating high-speed sweeping curves with precise steering angles and countersteering micro-corrections.",
        "car_id": "ks_ford_gt40",
        "track_id": "ks_monza66",
        "track_layout": "road",
        "start_mode": "ROLLING",
        "start_s": 0.140,
        "finish_s": 0.465,
        "spawn_offset": 50.0,
        "speed": 200.0,
        "gold": 28.500,
        "silver": 30.000,
        "bronze": 32.500,
        "filename": "test_ia09.json",
    },
    {
        "test_id": "IA-10",
        "tier": "International A",
        "title": "Multi-Car GT3 Traffic Overtake",
        "description": "Execute clean multi-class overtakes through Nürburgring Sprint sector without contact or penalties.",
        "lesson_objective": "Clean multi-class passing challenge. Overtake three slower GT4 cars cleanly without any body contact or off-track excursions before crossing the sector line.",
        "car_id": "ks_ferrari_488_gt3",
        "track_id": "ks_nurburgring",
        "track_layout": "layout_sprint_a",
        "start_mode": "ROLLING",
        "start_s": 0.050,
        "finish_s": 0.546,
        "spawn_offset": 35.0,
        "speed": 140.0,
        "gold": 42.500,
        "silver": 44.800,
        "bronze": 48.000,
        "filename": "test_ia10.json",
    },
    {
        "test_id": "IA-11",
        "tier": "International A",
        "title": "Classic DTM Heel-and-Toe Dogfight",
        "description": "Rev-match analog downshifts and conquer Vallelunga's demanding Trincea and Semaforo sequence.",
        "lesson_objective": "Fast narrow sequence of sweeping turns. Rev-matching downshifts into Semaforo hairpin; maximizing mechanical grip from an unassisted analog race chassis.",
        "car_id": "ks_mercedes_190_evo2",
        "track_id": "ks_vallelunga",
        "track_layout": "extended_circuit",
        "start_mode": "ROLLING",
        "start_s": 0.565,
        "finish_s": 0.785,
        "spawn_offset": 40.0,
        "speed": 150.0,
        "gold": 22.800,
        "silver": 24.000,
        "bronze": 26.000,
        "filename": "test_ia11.json",
    },
    {
        "test_id": "IA-12",
        "tier": "International A",
        "title": "Graduation: Circuit de Spa-Francorchamps Sector Trial",
        "description": "The ultimate International A test: navigate Spa's full Sector 2 without exceeding track limits.",
        "lesson_objective": "Comprehensive International A graduation sector. Navigates Les Combes chicane, Bruxelles downhill carousel, the left flick, flat Pouhon, and the fast right sweep into Stavelot without a single tire exceeding track limits.",
        "car_id": "ks_ferrari_488_gt3",
        "track_id": "spa",
        "track_layout": "",
        "start_mode": "ROLLING",
        "start_s": 0.315,
        "finish_s": 0.785,
        "spawn_offset": 50.0,
        "speed": 190.0,
        "gold": 64.500,
        "silver": 67.500,
        "bronze": 72.000,
        "filename": "test_ia12.json",
    },
]


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(repo_root, "content", "tests", "international_a")
    os.makedirs(target_dir, exist_ok=True)

    validator = CurriculumValidator(ac_root=DEFAULT_AC_ROOT, strict=True)
    all_passed = True

    for t in IA_TESTS:
        print(f"Generating {t['test_id']} ({t['filename']})...")
        test_dict = build_test_definition(
            test_id=t["test_id"],
            tier=t["tier"],
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
            with_stop_box=False,
            ac_root=DEFAULT_AC_ROOT,
        )

        out_path = os.path.join(target_dir, t["filename"])
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test_dict, f, indent=2)
            f.write("\n")

        issues = validator.validate_test_file(out_path)
        if issues:
            print(f"  [ISSUES in {t['filename']}]:")
            for iss in issues:
                print(f"    [{iss.severity}] {iss.category}: {iss.message}")
                if iss.severity == "ERROR":
                    all_passed = False
        else:
            print(f"  [OK] Passed validation with 0 issues.")

    if not all_passed:
        print("\n[FAILED] Some tests had errors during generation!")
        return 1

    print("\n[SUCCESS] All 12 International A tests generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
