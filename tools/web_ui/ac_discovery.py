"""
ac_discovery.py
Track, layout, car, and AI spline discovery utilities for the License Test Designer Web UI.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.parser import DEFAULT_AC_ROOT, SplineParser, find_spline_file

KUNOS_BASE_TRACKS = {
    "drift",
    "imola",
    "magione",
    "monza",
    "mugello",
    "spa",
    "trento-bondone",
    "vallelunga",
}
KUNOS_TRACK_IDS = KUNOS_BASE_TRACKS

KUNOS_BASE_CARS = {
    "abarth500",
    "abarth500_s1",
    "alfa_romeo_giulietta_qv",
    "alfa_romeo_giulietta_qv_le",
    "bmw_1m",
    "bmw_1m_s3",
    "bmw_m3_e30",
    "bmw_m3_e30_drift",
    "bmw_m3_e30_dtm",
    "bmw_m3_e30_gra",
    "bmw_m3_e30_s1",
    "bmw_m3_e92",
    "bmw_m3_e92_drift",
    "bmw_m3_e92_s1",
    "bmw_m3_gt2",
    "bmw_z4",
    "bmw_z4_drift",
    "bmw_z4_gt3",
    "bmw_z4_s1",
    "ferrari_312t",
    "ferrari_458",
    "ferrari_458_gt2",
    "ferrari_458_s3",
    "ferrari_f40",
    "ferrari_f40_s3",
    "ferrari_laferrari",
    "ktm_x_bow_r",
    "lotus_2_eleven",
    "lotus_2_eleven_gt4",
    "lotus_98t",
    "lotus_elise_sc",
    "lotus_elise_sc_s1",
    "lotus_elise_sc_s2",
    "lotus_evora_gtc",
    "lotus_evora_gte",
    "lotus_evora_gte_carbon",
    "lotus_evora_gx",
    "lotus_evora_s",
    "lotus_evora_s_s2",
    "lotus_exige_240",
    "lotus_exige_240_s3",
    "lotus_exige_s",
    "lotus_exige_s_roadster",
    "lotus_exige_scura",
    "lotus_exige_v6_cup",
    "lotus_exos_125",
    "lotus_exos_125_s1",
    "mclaren_mp412c",
    "mclaren_mp412c_gt3",
    "mercedes_sls",
    "mercedes_sls_gt3",
    "pagani_huayra",
    "pagani_zonda_r",
    "ruf_yellowbird",
    "scuderia_glickenhaus_scg003",
    "shelby_cobra_427sc",
    "tatuusfa01",
}
KUNOS_CAR_IDS = KUNOS_BASE_CARS

CAR_LAYOUT_MAP: Dict[str, str] = {
    "abarth500": "FF", "alfa_romeo_giulietta_qv": "FF", "ks_alfa_mito_qv": "FF",
    "ks_audi_a1s1": "FAWD", "ks_audi_sport_quattro": "FAWD", "ks_toyota_celica_st185": "FAWD",
    "ks_nissan_gtr": "FAWD", "ks_alfa_romeo_155_v6": "FAWD",
    "ks_lamborghini_huracan_performante": "MAWD", "ks_porsche_919_hybrid_2016": "MAWD", "ks_toyota_ts040": "MAWD",
    "ks_porsche_911_gt3_r_2016": "RR", "ks_porsche_911_gt3_rs": "RR", "ks_porsche_911_rsr_2017": "RR",
    "ferrari_458": "MR", "ferrari_laferrari": "MR", "ks_alfa_romeo_4c": "MR", "ks_audi_r8_lms_2016": "MR",
    "ks_ferrari_488_gt3": "MR", "ks_ferrari_488_gtb": "MR", "ks_ferrari_f2004": "MR", "ks_ford_gt40": "MR",
    "ks_mazda_787b": "MR", "ks_mclaren_650_gt3": "MR", "ks_mclaren_p1": "MR", "ks_mercedes_c9": "MR",
    "ks_porsche_718_cayman_s": "MR", "ks_porsche_962c_shorttail": "MR", "ks_porsche_cayman_gt4_clubsport": "MR",
    "lotus_2_eleven": "MR", "lotus_elise_sc": "MR", "lotus_exige_240": "MR", "pagani_zonda_r": "MR",
}


def is_kunos_track(track_id: str) -> bool:
    """Checks whether a track was created by Kunos Simulazioni."""
    return track_id.startswith("ks_") or track_id in KUNOS_BASE_TRACKS


def is_kunos_car(car_id: str) -> bool:
    """Checks whether a car was created by Kunos Simulazioni."""
    return car_id.startswith("ks_") or car_id in KUNOS_BASE_CARS


def _read_ui_name(json_path: str, default: str) -> str:
    """Safely reads the display name from a ui_track.json file."""
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                u = json.loads(f.read(), strict=False)
                return u.get("name", default)
        except Exception:
            pass
    return default


def _discover_track_layouts(t_path: str, t_id: str, ac_root: str) -> List[Dict[str, Any]]:
    """Discovers default and sub-folder layouts for a track directory."""
    layouts = []
    def_spline = find_spline_file(t_id, "", ac_root)
    if def_spline:
        layouts.append({
            "layout_id": "",
            "name": "Default Layout",
            "spline_file": def_spline,
        })

    for sub in sorted(os.listdir(t_path)):
        sub_path = os.path.join(t_path, sub)
        if not os.path.isdir(sub_path):
            continue
        sub_spline = find_spline_file(t_id, sub, ac_root)
        if sub_spline and sub_spline != def_spline:
            sub_ui = os.path.join(t_path, "ui", sub, "ui_track.json")
            layouts.append({
                "layout_id": sub,
                "name": _read_ui_name(sub_ui, sub),
                "spline_file": sub_spline,
            })
    return layouts


def get_available_tracks(ac_root: str = DEFAULT_AC_ROOT, kunos_only: bool = True) -> List[Dict[str, Any]]:
    """Discovers all tracks and layouts that have valid AI splines, filtered to Kunos content."""
    tracks_dir = os.path.join(ac_root, "content", "tracks")
    if not os.path.isdir(tracks_dir):
        return []

    tracks_list = []
    for t_id in sorted(os.listdir(tracks_dir)):
        t_path = os.path.join(tracks_dir, t_id)
        if not os.path.isdir(t_path):
            continue

        if kunos_only and not is_kunos_track(t_id):
            continue

        track_name = _read_ui_name(os.path.join(t_path, "ui", "ui_track.json"), t_id)
        layouts = _discover_track_layouts(t_path, t_id, ac_root)
        if layouts:
            tracks_list.append({
                "track_id": t_id,
                "name": track_name,
                "layouts": layouts,
            })

    return tracks_list


def _read_car_ui_data(c_path: str, c_id: str) -> Tuple[str, str, List[str]]:
    """Safely extracts name, brand, and tags from ui_car.json."""
    ui_file = os.path.join(c_path, "ui", "ui_car.json")
    if not os.path.isfile(ui_file):
        return c_id, "", []
    try:
        with open(ui_file, "r", encoding="utf-8", errors="ignore") as f:
            u = json.loads(f.read(), strict=False)
            car_name = u.get("name", c_id)
            brand = u.get("brand", "")
            raw_tags = u.get("tags", [])
            tags = [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
            return car_name, brand, tags
    except Exception:
        return c_id, "", []


def _determine_drivetrain(c_id: str, tags: List[str]) -> str:
    """Determines authoritative drivetrain (FWD, RWD, AWD) from tags or layout mapping."""
    lower_tags = {t.lower() for t in tags}
    if any(t in lower_tags for t in ("awd", "4wd", "mawd", "fawd")):
        return "AWD"
    if "fwd" in lower_tags or "ff" in lower_tags:
        return "FWD"
    if "rwd" in lower_tags or any(t in lower_tags for t in ("fr", "mr", "rr")):
        return "RWD"

    layout = CAR_LAYOUT_MAP.get(c_id, "FR")
    if layout in ("FAWD", "MAWD", "AWD"):
        return "AWD"
    if layout in ("FF", "FWD"):
        return "FWD"
    return "RWD"


def get_available_cars(ac_root: str = DEFAULT_AC_ROOT, kunos_only: bool = True) -> List[Dict[str, Any]]:
    """Discovers all cars in AC with their display names, tags, and drivetrain, filtered to Kunos content."""
    cars_dir = os.path.join(ac_root, "content", "cars")
    if not os.path.isdir(cars_dir):
        return []

    cars_list = []
    for c_id in sorted(os.listdir(cars_dir)):
        c_path = os.path.join(cars_dir, c_id)
        if not os.path.isdir(c_path):
            continue

        if kunos_only and not is_kunos_car(c_id):
            continue

        car_name, brand, tags = _read_car_ui_data(c_path, c_id)
        drivetrain = _determine_drivetrain(c_id, tags)

        cars_list.append({
            "car_id": c_id,
            "name": car_name,
            "brand": brand,
            "tags": tags,
            "drivetrain": drivetrain,
        })
    return cars_list


def get_track_spline_data(track_id: str, layout: str = "", ac_root: str = DEFAULT_AC_ROOT) -> Optional[Dict[str, Any]]:
    """Extracts downsampled centerline points for 2D map preview."""
    spline_file = find_spline_file(track_id, layout, ac_root)
    if not spline_file:
        return None

    try:
        parser = SplineParser(spline_file)
    except Exception as e:
        return {"error": str(e)}

    total_len = parser.total_length
    count = len(parser.waypoints)
    if count == 0:
        return None

    # Downsample to ~250 points for smooth, lightweight canvas/svg rendering
    step = max(1, count // 250)
    samples = []
    xs = []
    zs = []

    for wp in parser.waypoints[::step]:
        # Top-down coordinates: x = wp.x, y = -wp.z
        xs.append(wp.x)
        zs.append(-wp.z)
        samples.append({
            "x": round(wp.x, 2),
            "y": round(-wp.z, 2),
            "s": round(wp.distance / total_len if total_len > 0 else 0.0, 4),
            "dist": round(wp.distance, 1),
        })

    # Close loop if circuit
    if count > 2 and (
        (parser.waypoints[0].x - parser.waypoints[-1].x)**2 +
        (parser.waypoints[0].z - parser.waypoints[-1].z)**2
    )**0.5 < 50.0:
        samples.append(samples[0])

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(zs), max(zs)

    return {
        "track_id": track_id,
        "track_layout": layout,
        "total_length_m": round(total_len, 2),
        "point_count": len(samples),
        "bounds": {
            "min_x": round(min_x, 2),
            "max_x": round(max_x, 2),
            "min_y": round(min_y, 2),
            "max_y": round(max_y, 2),
            "width": round(max_x - min_x, 2),
            "height": round(max_y - min_y, 2),
        },
        "points": samples,
    }
