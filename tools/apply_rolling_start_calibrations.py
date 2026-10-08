"""
Automated Calibration & Application Engine for Rolling Start Curriculum
Grounds all 40 rolling start tests in the Assetto Corsa GT-Like Licenses mod
using authentic 95% AI telemetry, calibrated countdown run-ups, and verified straight approach segments.
"""

import os
import sys
import re
import json
import math
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from generate_all_content import TEST_CATALOG
from extract_spline_coords import SplineParser, find_spline_file
from track_straight_analyzer import TrackStraightAnalyzer
from tools.spline.straight_analyzer import RollingStartCandidate

CONFIG_40 = {
    # TIER 1: NATIONAL B (7 rolling tests - Beginner Driving School: 65 - 90 km/h, with B-6 high-speed threshold braking)
    "B-3":  {"straight_s": 0.72, "finish_s": 0.92, "custom_speed": 70.0, "post_go": 1.0, "desc": "Vallelunga Infield Straight into Curva Roma Hairpin"},
    "B-4":  {"straight_s": 0.65, "finish_s": 0.77, "custom_speed": 80.0, "post_go": 1.0, "desc": "Magione Back Straight into Curva del Muro"},
    "B-5":  {"straight_s": 0.58, "finish_s": 0.84, "custom_speed": 80.0, "post_go": 1.0, "desc": "Silverstone Nat Wellington Straight into Brooklands & Luffield"},
    "B-6":  {"straight_s": 0.14, "finish_s": 0.23, "custom_speed": 185.0, "post_go": 1.5, "desc": "Monza Rettifilo into Variante del Rettifilo Chicane"},
    "B-8":  {"straight_s": 0.99, "finish_s": 0.14, "custom_speed": 90.0, "post_go": 0.8, "desc": "Brands Hatch Indy Brabham Straight into Paddock Hill Bend"},
    "B-10": {"straight_s": 0.88, "finish_s": 0.12, "custom_speed": 65.0, "desc": "Nurburgring Sprint Pit Straight into Mercedes Arena"},
    "B-11": {"straight_s": 0.98, "finish_s": 0.16, "custom_speed": 80.0, "desc": "Zandvoort Pit Straight into Tarzan & Gerlachbocht"},

    # TIER 2: NATIONAL A (10 rolling tests - Intermediate Sports Cars: 55 - 115 km/h)
    "A-2":  {"straight_s": 0.50, "finish_s": 0.61, "custom_speed": 55.0, "desc": "Laguna Seca Rahal Straight into The Corkscrew"},
    "A-3":  {"straight_s": 0.26, "finish_s": 0.38, "custom_speed": 80.0, "desc": "Magione Straight into Monte Sperello Hairpin"},
    "A-4":  {"straight_s": 0.25, "finish_s": 0.44, "custom_speed": 90.0, "desc": "Brands Hatch Cooper Straight into Graham Hill Bend & Surtees Run"},
    "A-5":  {"straight_s": 0.65, "finish_s": 0.77, "custom_speed": 45.0, "desc": "Imola Piratella Straight into Variante Alta"},
    "A-6":  {"straight_s": 0.18, "finish_s": 0.38, "custom_speed": 70.0, "desc": "Highlands Short Straight into Turns 1 & 2"},
    "A-7":  {"straight_s": 0.18, "finish_s": 0.28, "custom_speed": 75.0, "desc": "Red Bull Ring Uphill Straight into Remus Turn 3"},
    "A-8":  {"straight_s": 0.24, "finish_s": 0.43, "custom_speed": 75.0, "post_go": 0.7, "desc": "Zandvoort Hunserug into Scheivlak"},
    "A-9":  {"straight_s": 0.26, "finish_s": 0.38, "custom_speed": 85.0, "desc": "Silverstone GP Farm Straight into Maggotts & Becketts"},
    "A-10": {"straight_s": 0.44, "finish_s": 0.68, "custom_speed": 115.0, "desc": "Vallelunga Classic Back Straight into Curva Cimini 1 & 2"},
    "A-11": {"straight_s": 0.54, "finish_s": 0.84, "custom_speed": 105.0, "desc": "Brands Hatch Colin Chapman Straight into Surtees & Clearways"},

    # TIER 3: INTERNATIONAL B (11 rolling tests)
    "IB-1": {"straight_s": 0.99, "finish_s": 0.11, "desc": "Imola Pit Straight into Tamburello Chicane"},
    "IB-2": {"straight_s": 0.44, "finish_s": 0.56, "desc": "Vallelunga Extended Back Straight into Campagnano"},
    "IB-3": {"straight_s": 0.41, "finish_s": 0.52, "desc": "Spa Approach Straight into Pouhon Double-Apex"},
    "IB-4": {"straight_s": 0.98, "finish_s": 0.14, "desc": "Laguna Seca Pit Straight into Andretti Hairpin"},
    "IB-5": {"straight_s": 0.16, "finish_s": 0.26, "desc": "Barcelona Elf Straight into Curvone Renault"},
    "IB-6": {"straight_s": 0.56, "finish_s": 0.69, "desc": "Monza Serraglio Straight into Variante Ascari"},
    "IB-7": {"straight_s": 0.75, "finish_s": 0.88, "desc": "Nurburgring GP Kurve Straight into NGK Chicane"},
    "IB-8": {"straight_s": 0.26, "finish_s": 0.39, "desc": "Mugello Luco Straight into Casanova-Savelli"},
    "IB-9": {"straight_s": 0.04, "finish_s": 0.22, "desc": "Red Bull Ring Pit Straight into Remus Slipstream Overtake"},
    "IB-10":{"straight_s": 0.86, "finish_s": 0.97, "desc": "Monza Back Straight into Curva Parabolica"},
    "IB-11":{"straight_s": 0.50, "finish_s": 0.65, "desc": "Silverstone 1967 Hangar Straight into Stowe & Club"},

    # TIER 4: INTERNATIONAL A (12 rolling tests)
    "IA-1": {"straight_s": 0.03, "finish_s": 0.15, "desc": "Spa Pit Straight into Eau Rouge & Raidillon"},
    "IA-2": {"straight_s": 0.46, "finish_s": 0.62, "desc": "Brands Hatch GP Pilgrim's Drop into Hawthorns & Westfield"},
    "IA-3": {"straight_s": 0.35, "finish_s": 0.49, "desc": "Mugello Casanova Straight into Arrabbiata 1 & 2"},
    "IA-4": {"straight_s": 0.24, "finish_s": 0.35, "desc": "Imola Approach Straight into Acque Minerali"},
    "IA-5": {"straight_s": 0.16, "finish_s": 0.25, "desc": "Barcelona Pit Straight into Elf Chicane & Renault"},
    "IA-6": {"straight_s": 0.93, "finish_s": 0.986, "desc": "Spa Blanchimont Straight into Bus Stop Chicane"},
    "IA-7": {"straight_s": 0.02, "finish_s": 0.18, "desc": "Nurburgring GP Pit Straight into Castrol S & Ford Kurve"},
    "IA-8": {"straight_s": 0.47, "finish_s": 0.58, "desc": "Silverstone GP National Straight into Copse"},
    "IA-9": {"straight_s": 0.18, "finish_s": 0.43, "desc": "Monza 66 Rettifilo into Curva Grande & Lesmo"},
    "IA-10":{"straight_s": 0.38, "finish_s": 0.65, "desc": "Nurburgring Sprint Middle Sector GT3 Traffic Overtake"},
    "IA-11":{"straight_s": 0.44, "finish_s": 0.59, "desc": "Vallelunga Extended Semaforo into Tornantino"},
    "IA-12":{"straight_s": 0.32, "finish_s": 0.62, "desc": "Spa Kemmel through Pouhon (Sector 2 Graduation Trial)"},
}


def _calc_cyclic_distance(dist_a: float, dist_b: float, total_len: float) -> float:
    """Calculates the shortest distance between two points along a closed track spline."""
    delta = abs((dist_a - dist_b + total_len) % total_len)
    return total_len - delta if delta > total_len / 2.0 else delta


def _find_best_candidate(
    analyzer: TrackStraightAnalyzer,
    target_d: float,
    tot: float,
    post_go: float,
    custom_speed: Optional[float] = None,
) -> Optional[RollingStartCandidate]:
    """Finds the best straight approach candidate closest to target_d across steer tolerances."""
    best_cand = None
    min_dist = float("inf")

    for tol in [2.5, 3.5, 4.5, 5.5]:
        straights = analyzer.find_straight_segments(max_steer_deg=tol, min_length_m=20.0)
        cands = analyzer.evaluate_rolling_candidates(
            straights,
            countdown_sec=3.0,
            post_go_sec=post_go,
            target_speed_kmh=custom_speed,
        )
        for c in cands:
            d = _calc_cyclic_distance(c.start_gate_distance_m, target_d, tot)
            if d < min_dist:
                min_dist = d
                best_cand = c
        if best_cand and min_dist < 250.0:
            break

    return best_cand


def _calculate_sector_time(
    analyzer: TrackStraightAnalyzer,
    gate_d: float,
    sec_len: float,
    tot: float,
    step: float = 1.0,
) -> float:
    """Integrates sector traversal time using 95% AI speed telemetry."""
    t_accum = 0.0
    curr_d = gate_d
    dist_traveled = 0.0
    while dist_traveled < sec_len:
        spd_kmh, _, _ = analyzer.telemetry.query_sample(curr_d)
        v_ms = max(5.0, spd_kmh / 3.6)
        t_accum += step / v_ms
        dist_traveled += step
        curr_d = (curr_d + step) % tot
    return t_accum


def calibrate_single_test(test_info: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Computes calibrated rolling start parameters and medal targets for a single test."""
    t_id = test_info["test_id"]
    track = test_info["track_id"]
    layout = test_info["track_layout"]
    car = test_info["car_id"]

    sf = find_spline_file(track, layout)
    p = SplineParser(sf)
    a = TrackStraightAnalyzer(p, track_id=track, layout=layout, car_id=car)
    tot = p.total_length

    target_d = cfg["straight_s"] * tot
    post_go = cfg.get("post_go", 1.0)
    c_spd = cfg.get("custom_speed")

    best_cand = _find_best_candidate(a, target_d, tot, post_go, c_spd)
    if not best_cand:
        raise RuntimeError(f"No candidate straight found for test {t_id}")

    gate_d = best_cand.start_gate_distance_m
    gate_s = best_cand.start_gate_progress
    fin_d = cfg["finish_s"] * tot
    sec_len = (fin_d - gate_d + tot) % tot

    if sec_len < 100.0:
        sec_len = 250.0
        fin_d = (gate_d + sec_len) % tot
    fin_s = round(fin_d / tot, 4)

    t_accum = _calculate_sector_time(a, gate_d, sec_len, tot)

    gold = math.ceil(round(t_accum * 0.98, 4) * 10.0) / 10.0
    silver = math.ceil(round(t_accum * 1.05, 4) * 10.0) / 10.0
    bronze = math.ceil(round(t_accum * 1.15, 4) * 10.0) / 10.0

    return {
        "start_s": gate_s,
        "finish_s": fin_s,
        "spawn_offset": best_cand.spawn_offset_m,
        "speed": best_cand.target_speed_kmh,
        "gear": best_cand.engaged_gear,
        "rpm": best_cand.engine_rpm,
        "max_steer": best_cand.max_countdown_steer_deg,
        "sec_len": round(sec_len, 1),
        "targets": {
            "gold_seconds": gold,
            "silver_seconds": silver,
            "bronze_seconds": bronze,
        },
    }


def compute_calibrations() -> Dict[str, Dict[str, Any]]:
    """Calculates all 40 calibrated configurations."""
    calibrations = {}
    rolling_tests = [t for t in TEST_CATALOG if t.get("start_mode") == "ROLLING"]
    for t in rolling_tests:
        t_id = t["test_id"]
        cfg = CONFIG_40[t_id]
        calibrations[t_id] = calibrate_single_test(t, cfg)

    return calibrations


def get_tier_file_for_test(test_id: str) -> str:
    """Returns the file path for the tier catalog file containing test_id."""
    prefix = test_id.split("-")[0]
    mapping = {
        "B": "national_b.py",
        "A": "national_a.py",
        "IB": "international_b.py",
        "IA": "international_a.py",
        "S": "super_license.py",
    }
    filename = mapping.get(prefix, "national_b.py")
    return os.path.join(REPO_ROOT, "tools", "content", "catalog", filename)


def update_catalog_in_file(calibrations):
    """Updates TEST_CATALOG in modular tier catalog files."""
    files_to_update = {}
    for t_id in calibrations:
        fpath = get_tier_file_for_test(t_id)
        if fpath not in files_to_update:
            with open(fpath, "r", encoding="utf-8") as f:
                files_to_update[fpath] = f.read()

    updated_count = 0

    for t_id, cal in calibrations.items():
        fpath = get_tier_file_for_test(t_id)
        content = files_to_update[fpath]

        # Match test dictionary block for this test_id
        pattern = rf'({{\s*"test_id":\s*"{re.escape(t_id)}",.*?}})'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            print(f"[!] Warning: Could not match test block for {t_id} in {os.path.basename(fpath)}")
            continue

        block = match.group(1)

        # Update start_s
        block = re.sub(r'"start_s":\s*[\d\.]+', f'"start_s": {cal["start_s"]}', block)
        # Update finish_s
        block = re.sub(r'"finish_s":\s*[\d\.]+', f'"finish_s": {cal["finish_s"]}', block)
        # Update spawn_offset
        block = re.sub(r'"spawn_offset":\s*[\d\.]+', f'"spawn_offset": {cal["spawn_offset"]}', block)
        # Update speed
        block = re.sub(r'"speed":\s*[\d\.]+', f'"speed": {cal["speed"]}', block)

        # Insert or update gear and rpm
        if '"gear":' in block:
            block = re.sub(r'"gear":\s*\d+', f'"gear": {cal["gear"]}', block)
        else:
            block = re.sub(r'("speed":\s*[\d\.]+),', rf'\1,\n        "gear": {cal["gear"]},', block)

        if '"rpm":' in block:
            block = re.sub(r'"rpm":\s*\d+', f'"rpm": {cal["rpm"]}', block)
        else:
            block = re.sub(r'("gear":\s*\d+),', rf'\1,\n        "rpm": {cal["rpm"]},', block)

        # Update targets
        tg = cal["targets"]
        tg_str = f'"targets": {{"gold_seconds": {tg["gold_seconds"]:.3f}, "silver_seconds": {tg["silver_seconds"]:.3f}, "bronze_seconds": {tg["bronze_seconds"]:.3f}}}'
        block = re.sub(r'"targets":\s*\{[^}]+\}', tg_str, block)

        files_to_update[fpath] = content[:match.start(1)] + block + content[match.end(1):]
        updated_count += 1

    for fpath, content in files_to_update.items():
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"Updated {updated_count} / {len(calibrations)} rolling test entries across {len(files_to_update)} tier catalog files.")


def main():
    print("=" * 80)
    print("ASSETTO CORSA GT-LIKE LICENSES - ROLLING START CURRICULUM CALIBRATOR")
    print("=" * 80)

    print("\n[Step 1] Computing authoritative calibrations for all 40 rolling tests...")
    calibrations = compute_calibrations()
    print(f"  + Calibrated {len(calibrations)} tests successfully.")

    print("\n[Step 2] Updating modular catalog files in tools/content/catalog/...")
    update_catalog_in_file(calibrations)

    print("\nCalibration application complete!")


if __name__ == "__main__":
    main()

