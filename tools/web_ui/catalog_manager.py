"""
catalog_manager.py
Backend bridge between the License Test Designer Web UI and the Python catalog files.
Provides reading, modifying, persisting of tests, track/car discovery, spline queries,
and triggering content generation / validation / AC live sync.
"""

import glob
import importlib
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import SERIES_METADATA, TIER_FOLDER_MAP
from tools.extract_spline_coords import DEFAULT_AC_ROOT, SplineParser, find_spline_file

TIER_NATIONAL_B = "National B"
TIER_NATIONAL_A = "National A"
TIER_INTERNATIONAL_B = "International B"
TIER_INTERNATIONAL_A = "International A"
TIER_SUPER_LICENSE = "Super License"

TIER_VAR_MAP = {
    TIER_NATIONAL_B: "NATIONAL_B_TESTS",
    TIER_NATIONAL_A: "NATIONAL_A_TESTS",
    TIER_INTERNATIONAL_B: "INTERNATIONAL_B_TESTS",
    TIER_INTERNATIONAL_A: "INTERNATIONAL_A_TESTS",
    TIER_SUPER_LICENSE: "SUPER_LICENSE_TESTS",
}

TIER_FILE_MAP = {
    TIER_NATIONAL_B: "national_b.py",
    TIER_NATIONAL_A: "national_a.py",
    TIER_INTERNATIONAL_B: "international_b.py",
    TIER_INTERNATIONAL_A: "international_a.py",
    TIER_SUPER_LICENSE: "super_license.py",
}

TIER_DOCS = {
    TIER_NATIONAL_B: "National B License Test Catalog.\nFundamentals of vehicle dynamics: longitudinal threshold braking, out-in-out trajectory, weight transfer.",
    TIER_NATIONAL_A: "National A License Test Catalog.\nIntermediate sports car dynamics: high-speed chicanes, blind off-camber drops, mid-engine balance.",
    TIER_INTERNATIONAL_B: "International B License Test Catalog.\nHigh-speed commitment, modern downforce, active diffs, and blind braking.",
    TIER_INTERNATIONAL_A: "International A License Test Catalog.\nMotorsport racecraft: full slick racecars, high-downforce GT3/GT4/DTM, and curb discipline.",
    TIER_SUPER_LICENSE: "Super License Test Catalog.\nThe ultimate test of speed and discipline: full timed laps with zero margin for error.",
}


def get_catalog_module_path(tier_name: str) -> str:
    filename = TIER_FILE_MAP[tier_name]
    return os.path.join(REPO_ROOT, "tools", "content", "catalog", filename)


def _enrich_test_from_saved_cfg(td: Dict[str, Any], folder: str) -> None:
    """Enriches test data with pre-generated 3D spatial parameters if test file exists."""
    t_id = td.get("test_id", "")
    if "-" not in t_id:
        return
    try:
        prefix, num_str = t_id.split("-", 1)
        test_fn = f"test_{prefix.lower()}{int(num_str):02d}.json"
        test_fp = os.path.join(REPO_ROOT, "content", "tests", folder, test_fn)
        if not os.path.isfile(test_fp):
            return
        with open(test_fp, "r", encoding="utf-8") as tf:
            saved_cfg = json.load(tf)
        if isinstance(saved_cfg.get("spawn"), dict):
            td["spawn"] = saved_cfg["spawn"]
        if "timing" in saved_cfg:
            td["timing"] = saved_cfg["timing"]
        if "fail_rules" in saved_cfg:
            td["fail_rules"] = saved_cfg["fail_rules"]
    except Exception:
        pass


def _load_series_tests(s_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    folder = TIER_FOLDER_MAP[s_meta["tier_name"]]
    var_name = TIER_VAR_MAP[s_meta["tier_name"]]
    mod = importlib.import_module(f"tools.content.catalog.{folder}")
    importlib.reload(mod)
    tests = getattr(mod, var_name, [])

    tests_data = []
    for idx, t in enumerate(tests, start=1):
        td = dict(t)
        td["preview_image"] = f"/content/career/{s_meta['folder']}/event{idx}/preview.png"
        _enrich_test_from_saved_cfg(td, folder)
        tests_data.append(td)
    return tests_data


def load_curriculum() -> List[Dict[str, Any]]:
    """Loads all series metadata and their current tests from catalog modules."""
    import tools.content.catalog as cat_pkg
    importlib.reload(cat_pkg)

    curriculum = []
    for s_meta in SERIES_METADATA:
        curriculum.append({
            "code": s_meta["code"],
            "tier_name": s_meta["tier_name"],
            "folder": s_meta["folder"],
            "name": s_meta["name"],
            "description": s_meta["description"],
            "badge_asset": s_meta["badge_asset"],
            "test_prefix": s_meta["test_prefix"],
            "tests": _load_series_tests(s_meta),
        })
    return curriculum


def format_test_dict(t: Dict[str, Any]) -> str:
    lines = [
        "    {",
        f'        "test_id": {repr(str(t.get("test_id", "")).strip())},',
        '        "tier": TIER_NAME,',
        f'        "title": {repr(str(t.get("title", "")).strip())},',
        f'        "description": {repr(str(t.get("description", "")).strip())},',
        f'        "lesson_objective": {repr(str(t.get("lesson_objective", "")).strip())},',
        f'        "car_id": {repr(str(t.get("car_id", "")).strip())},',
        f'        "track_id": {repr(str(t.get("track_id", "")).strip())},',
        f'        "track_layout": {repr(str(t.get("track_layout", "")).strip())},',
        f'        "start_mode": {repr(str(t.get("start_mode", "STANDING")).strip())},',
        f'        "start_s": {round(float(t.get("start_s", 0.0)), 4)},',
        f'        "finish_s": {round(float(t.get("finish_s", 1.0)), 4)},',
        f'        "spawn_offset": {round(float(t.get("spawn_offset", 0.0)), 1)},',
        f'        "speed": {round(float(t.get("speed", 0.0)), 1)},',
    ]

    gear = t.get("gear")
    if gear is not None and str(gear).strip() != "":
        try:
            lines.append(f'        "gear": {int(gear)},')
        except (ValueError, TypeError):
            pass

    rpm = t.get("rpm")
    if rpm is not None and str(rpm).strip() != "":
        try:
            lines.append(f'        "rpm": {int(rpm)},')
        except (ValueError, TypeError):
            pass

    lines.append(f'        "with_stop_box": {repr(bool(t.get("with_stop_box", False)))},')

    targets = t.get("targets", {})
    gold = float(targets.get("gold_seconds", 10.0))
    silver = float(targets.get("silver_seconds", 12.0))
    bronze = float(targets.get("bronze_seconds", 15.0))
    lines.extend([
        f'        "targets": {{"gold_seconds": {gold:.3f}, "silver_seconds": {silver:.3f}, "bronze_seconds": {bronze:.3f}}},',
        "    },",
    ])
    return "\n".join(lines)


def _normalize_standing_test(t: Dict[str, Any]) -> None:
    t["speed"] = 0.0
    t["spawn_offset"] = 0.0
    t.pop("gear", None)
    t.pop("rpm", None)
    if isinstance(t.get("spawn"), dict):
        t["spawn"]["initial_speed_kmh"] = 0.0
        t["spawn"]["spawn_offset_m"] = 0.0
        t["spawn"].pop("initial_gear", None)
        t["spawn"].pop("initial_rpm", None)


def _resolve_rolling_physics(t: Dict[str, Any]) -> None:
    speed = float(t.get("speed") or 0.0)
    if speed > 0.0 and t.get("gear"):
        return
    try:
        from tools.telemetry.recorder import get_or_calculate_initial_physics
        phys = get_or_calculate_initial_physics(
            track_id=t.get("track_id", ""),
            track_layout=t.get("track_layout", ""),
            car_id=t.get("car_id", ""),
            start_s=float(t.get("start_s", 0.0)),
            countdown_sec=3.0,
            allow_live_engine=False,
        )
        if not phys:
            return
        if speed <= 0.0:
            t["speed"] = round(float(phys.get("speed_kmh", 75.0)), 1)
            t["spawn_offset"] = round(float(phys.get("spawn_offset_m", 62.5)), 1)
        if not t.get("gear") and phys.get("gear"):
            t["gear"] = int(phys["gear"])
        if not t.get("rpm") and phys.get("rpm"):
            t["rpm"] = int(phys["rpm"])
    except Exception:
        pass


def _normalize_rolling_test(t: Dict[str, Any], start_mode: str) -> None:
    _resolve_rolling_physics(t)
    if float(t.get("speed") or 0.0) <= 0.0:
        t["speed"] = 140.0 if start_mode == "FLYING_LAP" else 75.0

    spd = float(t.get("speed", 75.0))
    if not t.get("spawn_offset") or float(t.get("spawn_offset", 0.0)) <= 0.0:
        t["spawn_offset"] = round((spd / 3.6) * 3.0, 1)

    if isinstance(t.get("spawn"), dict):
        t["spawn"]["initial_speed_kmh"] = t["speed"]
        t["spawn"]["spawn_offset_m"] = t["spawn_offset"]
        if t.get("gear"):
            t["spawn"]["initial_gear"] = t["gear"]
        if t.get("rpm"):
            t["spawn"]["initial_rpm"] = t["rpm"]


def _normalize_test_definition(t: Dict[str, Any], prefix: str, idx: int) -> None:
    t["test_id"] = f"{prefix}{idx}"
    start_mode = str(t.get("start_mode", "STANDING")).upper()
    if start_mode == "STANDING":
        _normalize_standing_test(t)
    else:
        _normalize_rolling_test(t, start_mode)


def save_tier_catalog(tier_name: str, tests: List[Dict[str, Any]]) -> str:
    """Saves updated test definitions for a specific tier back to its python file."""
    if tier_name not in TIER_FILE_MAP:
        raise ValueError(f"Unknown tier: {tier_name}")

    meta = next((s for s in SERIES_METADATA if s["tier_name"] == tier_name), None)
    prefix = meta["test_prefix"] if meta else "T-"

    # Automatically ensure sequential test_id numbering matching curriculum structure
    for idx, t in enumerate(tests, start=1):
        _normalize_test_definition(t, prefix, idx)

    file_path = get_catalog_module_path(tier_name)
    var_name = TIER_VAR_MAP[tier_name]
    doc = TIER_DOCS.get(tier_name, f"{tier_name} Test Catalog")

    test_blocks = [format_test_dict(t) for t in tests]
    tests_str = "\n".join(test_blocks)

    content = f'''"""
{TIER_FILE_MAP[tier_name]}
{doc} ({len(tests)} Tests)
"""

TIER_NAME = "{tier_name}"

{var_name} = [
{tests_str}
]
'''
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path


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


def _clean_stale_json_files(test_catalog: List[Dict[str, Any]]) -> None:
    valid_files = set()
    for tdef in test_catalog:
        tier_dir = os.path.join(REPO_ROOT, "content", "tests", TIER_FOLDER_MAP[tdef["tier"]])
        prefix, num_str = tdef["test_id"].split("-")
        num = int(num_str)
        valid_files.add(os.path.normpath(os.path.join(tier_dir, f"test_{prefix.lower()}{num:02d}.json")))
        valid_files.add(os.path.normpath(os.path.join(tier_dir, f"ghost_test_{prefix.lower()}{num:02d}.json")))

    tests_root = os.path.join(REPO_ROOT, "content", "tests")
    for t_folder in TIER_FOLDER_MAP.values():
        dir_path = os.path.join(tests_root, t_folder)
        if not os.path.isdir(dir_path):
            continue
        for f in glob.glob(os.path.join(dir_path, "*.json")):
            if os.path.normpath(f) not in valid_files:
                try:
                    os.remove(f)
                except OSError:
                    pass


def _clean_stale_career_events(test_catalog: List[Dict[str, Any]]) -> None:
    import shutil
    career_root = os.path.join(REPO_ROOT, "content", "career")
    for s_meta in SERIES_METADATA:
        series_dir = os.path.join(career_root, s_meta["folder"])
        if not os.path.isdir(series_dir):
            continue
        tier_tests = [t for t in test_catalog if t["tier"] == s_meta["tier_name"]]
        max_events = len(tier_tests)
        for event_dir in glob.glob(os.path.join(series_dir, "event*")):
            m = re.match(r"event(\d+)$", os.path.basename(event_dir))
            if m and int(m.group(1)) > max_events:
                try:
                    shutil.rmtree(event_dir)
                except OSError:
                    pass


def _clean_stale_svg_maps(valid_test_ids: set) -> None:
    maps_dir = os.path.join(REPO_ROOT, "docs", "test_maps")
    if not os.path.isdir(maps_dir):
        return
    for svg_file in glob.glob(os.path.join(maps_dir, "*.svg")):
        tid = os.path.splitext(os.path.basename(svg_file))[0]
        if tid not in valid_test_ids:
            try:
                os.remove(svg_file)
            except OSError:
                pass


def clean_stale_tests() -> None:
    """Removes any generated test JSONs that are no longer in the catalog."""
    from tools.content.catalog import TEST_CATALOG

    _clean_stale_json_files(TEST_CATALOG)
    _clean_stale_career_events(TEST_CATALOG)
    _clean_stale_svg_maps({tdef["test_id"] for tdef in TEST_CATALOG})


def generate_and_validate(ac_root: str = DEFAULT_AC_ROOT) -> Dict[str, Any]:
    """Runs generation and validation, returning status and reports."""
    from tools.content.generator import generate_career, generate_miniatures, generate_tests
    from tools.content.validator import (
        CurriculumValidator,
        DEFAULT_CAREER_DIR,
        DEFAULT_SCHEMA_PATH,
        DEFAULT_TESTS_DIR,
        ValidationReport,
        discover_test_files,
    )

    # 1. Clean stale files
    clean_stale_tests()

    # 2. Generate tests
    generate_tests(ac_root)

    # 3. Generate career structures
    generate_career()

    # 4. Generate track miniatures directly into career event folders and docs/test_maps
    miniatures_count = generate_miniatures(ac_root)

    # 5. Validate
    validator = CurriculumValidator(
        schema_path=DEFAULT_SCHEMA_PATH,
        ac_root=ac_root,
        strict=False,
        skip_ac_check=False,
    )
    test_files = discover_test_files(DEFAULT_TESTS_DIR)
    report = ValidationReport()
    report.total_files_checked = len(test_files)

    for fpath in test_files:
        issues = validator.validate_test_file(fpath)
        has_error = any(i.severity == "ERROR" for i in issues)
        if has_error:
            report.failed_files += 1
        else:
            report.passed_files += 1
        report.issues.extend(issues)

    career_issues = validator.validate_career_series(DEFAULT_CAREER_DIR)
    report.issues.extend(career_issues)

    return {
        "success": not report.has_errors,
        "total_files": report.total_files_checked,
        "miniatures_updated": miniatures_count,
        "passed": report.passed_files,
        "failed": report.failed_files,
        "errors": [
            {
                "severity": iss.severity,
                "category": iss.category,
                "message": iss.message,
                "test_id": iss.test_id,
            }
            for iss in report.issues if iss.severity == "ERROR"
        ],
        "warnings": [
            {
                "severity": iss.severity,
                "category": iss.category,
                "message": iss.message,
                "test_id": iss.test_id,
            }
            for iss in report.issues if iss.severity == "WARNING"
        ],
    }


CAR_SPECS_CACHE: Dict[str, Tuple[int, int, float, str]] = {
    "ferrari_laferrari": (963, 1255, 1.30, "MR"),
    "ks_ferrari_f2004": (865, 605, 0.70, "MR"),
    "ks_toyota_ts040": (1000, 870, 0.87, "MAWD"),
}


def _format_time_str(s: Optional[float]) -> str:
    """Formats seconds into human-readable gold/silver/bronze target display."""
    if s is None:
        return "N/A"
    if s < 60:
        return f"{s:.3f}s"
    m = int(s // 60)
    sec_part = s % 60
    return f"{m}:{sec_part:06.3f}"


def _resolve_car_specs(
    car_id: str,
    default_name: str,
    ac_cars_dir: str,
) -> Tuple[str, int, Optional[int], Optional[float]]:
    """Resolves car display name, horsepower, weight, and power-to-weight ratio."""
    hp: Optional[int] = None
    wt: Optional[int] = None
    pw: Optional[float] = None
    car_display_name = default_name

    if car_id in CAR_SPECS_CACHE:
        hp, wt, pw, _ = CAR_SPECS_CACHE[car_id]
    else:
        ui_path = os.path.join(ac_cars_dir, car_id, "ui", "ui_car.json")
        if os.path.isfile(ui_path):
            try:
                with open(ui_path, "r", encoding="utf-8", errors="ignore") as f:
                    d = json.loads(f.read(), strict=False)
                    car_display_name = d.get("name", default_name)
                    specs = d.get("specs", {})
                    bhp_m = re.search(r"(\d+)", specs.get("bhp", ""))
                    if bhp_m:
                        hp = int(bhp_m.group(1))
                    wt_m = re.search(r"(\d+)", specs.get("weight", ""))
                    if wt_m:
                        wt = int(wt_m.group(1))
                    pw_m = re.search(r"([\d.]+)", specs.get("pwratio", ""))
                    if pw_m:
                        pw = float(pw_m.group(1))
            except Exception:
                pass

    if hp and wt and not pw:
        pw = round(wt / hp, 2)
    if hp and pw and not wt:
        wt = round(hp * pw)

    return car_display_name, hp or 200, wt, pw


def _build_reference_entry(
    test: Dict[str, Any],
    tier_name: str,
    progression: int,
    track_map: Dict[str, str],
    car_name_map: Dict[str, str],
    ac_cars_dir: str,
) -> Dict[str, Any]:
    """Constructs a single reference test entry."""
    car_id = test.get("car_id", "")
    default_name = car_name_map.get(car_id, car_id)
    car_display_name, hp, wt, pw = _resolve_car_specs(car_id, default_name, ac_cars_dir)

    layout = CAR_LAYOUT_MAP.get(car_id, "FR")
    track_id = test.get("track_id", "")
    track_name = track_map.get(track_id, track_id)
    layout_id = test.get("track_layout", "")
    if layout_id:
        track_name += f" ({layout_id})"

    targets = test.get("targets", {})
    gold_sec = targets.get("gold_seconds")
    silver_sec = targets.get("silver_seconds")
    bronze_sec = targets.get("bronze_seconds")
    t_code = test.get("test_id", f"T-{progression}")

    return {
        "id": f"AC_{test.get('test_id', progression)}",
        "game": "AC Mod",
        "license": tier_name,
        "section": f"AC Mod {tier_name}",
        "code": t_code,
        "title": test.get("title", ""),
        "test": f"{test.get('test_id', '')} - {test.get('title', '')}",
        "car": car_display_name,
        "car_id": car_id,
        "hp": hp,
        "weight_kg": wt,
        "pw_kg_hp": pw,
        "drivetrain_layout": layout,
        "track": track_name,
        "gold": _format_time_str(gold_sec),
        "silver": _format_time_str(silver_sec),
        "bronze": _format_time_str(bronze_sec),
        "gold_seconds": gold_sec,
        "silver_seconds": silver_sec,
        "bronze_seconds": bronze_sec,
        "target_type": "time",
        "test_progression": progression,
    }


def get_ac_curriculum_reference_tests() -> List[Dict[str, Any]]:
    """Converts the active 58 AC Mod career license tests into the standard reference format."""
    ac_cars_dir = os.path.join(DEFAULT_AC_ROOT, "content", "cars")
    tracks = get_available_tracks(kunos_only=False)
    track_map = {t["track_id"]: t["name"] for t in tracks}
    cars = get_available_cars(kunos_only=False)
    car_name_map = {c["car_id"]: c["name"] for c in cars}

    curriculum = load_curriculum()
    ac_tests: List[Dict[str, Any]] = []
    progression = 1

    for tier in curriculum:
        tier_name = tier["tier_name"]
        for test in tier["tests"]:
            entry = _build_reference_entry(
                test,
                tier_name,
                progression,
                track_map,
                car_name_map,
                ac_cars_dir,
            )
            ac_tests.append(entry)
            progression += 1

    return ac_tests


def calculate_test_targets_and_physics(
    track_id: str,
    track_layout: str = "",
    car_id: str = "ks_mazda_miata",
    start_s: float = 0.0,
    finish_s: float = 1.0,
    start_mode: str = "ROLLING",
    with_stop_box: bool = False,
    countdown_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    Instantly computes authentic target times (Gold, Silver, Bronze) and launch/countdown physics
    from cached telemetry profiles or synthesized track spline.
    """
    from tools.telemetry.recorder import get_or_calculate_targets
    try:
        res = get_or_calculate_targets(
            track_id=track_id,
            layout=track_layout,
            car_id=car_id,
            start_s=start_s,
            finish_s=finish_s,
            start_mode=start_mode,
            with_stop_box=with_stop_box,
            countdown_sec=countdown_sec,
            allow_live_engine=False,
        )
        return res
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "targets": {"gold_seconds": 15.0, "silver_seconds": 18.0, "bronze_seconds": 22.0},
        }


def _calculate_standing_speed(
    track_id: str,
    track_layout: str,
    car_id: str,
    start_s: float,
    finish_s: float,
    start_mode: str,
    with_stop_box: bool,
) -> Dict[str, Any]:
    """Calculates target parameters for standing start tests."""
    from tools.telemetry.recorder import get_or_calculate_targets
    try:
        tg = get_or_calculate_targets(
            track_id=track_id, layout=track_layout, car_id=car_id,
            start_s=start_s, finish_s=finish_s, start_mode=start_mode, with_stop_box=with_stop_box,
        )
        return {
            "success": True,
            "status": "cached",
            "speed_kmh": 0.0,
            "spawn_offset_m": 0.0,
            "gear": 1,
            "rpm": 1000,
            "source": tg.get("source", "standing_start"),
            "targets": tg.get("targets", {}),
            "sector_time_s": tg.get("sector_time_s", 0.0),
            "sector_length_m": tg.get("sector_length_m", 0.0),
        }
    except Exception:
        return {
            "success": True,
            "status": "cached",
            "speed_kmh": 0.0,
            "spawn_offset_m": 0.0,
            "gear": 1,
            "rpm": 1000,
            "source": "standing_start",
        }


def _find_existing_recording_job(
    queue_status: Dict[str, Any], track_id: str, car_id: str
) -> Optional[Dict[str, Any]]:
    """Checks whether a telemetry recording job for this track and car is already active or in queue."""
    active_job = queue_status.get("active_job")
    if active_job and active_job.get("type") == "record_telemetry":
        p = active_job.get("params", {})
        if p.get("track_id") == track_id and p.get("car_id") == car_id:
            return {
                "success": True,
                "status": "queued",
                "job_id": active_job["id"],
                "message": f"Assetto Corsa is currently recording 100% AI telemetry for {car_id} at {track_id}...",
            }

    for qj in queue_status.get("queue", []):
        if qj.get("type") == "record_telemetry":
            p = qj.get("params", {})
            if p.get("track_id") == track_id and p.get("car_id") == car_id:
                return {
                    "success": True,
                    "status": "queued",
                    "job_id": qj["id"],
                    "message": f"100% AI Telemetry recording for {car_id} at {track_id} is already in queue...",
                }
    return None


def calculate_test_initial_speed(
    track_id: str,
    track_layout: str = "",
    car_id: str = "ks_mazda_miata",
    start_s: float = 0.0,
    finish_s: float = 1.0,
    start_mode: str = "ROLLING",
    with_stop_box: bool = False,
    countdown_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    Calculates initial speed, spawn offset, gear, RPM, and target times for a test.
    If cached telemetry profile exists, returns authentic physics immediately.
    If not cached, enqueues an authentic full-lap recording in Assetto Corsa into the job runner.
    """
    if start_mode == "STANDING":
        return _calculate_standing_speed(
            track_id=track_id,
            track_layout=track_layout,
            car_id=car_id,
            start_s=start_s,
            finish_s=finish_s,
            start_mode=start_mode,
            with_stop_box=with_stop_box,
        )

    from tools.telemetry.recorder import load_telemetry_profile
    from tools.web_ui.runner import queue_mgr

    # 1. Check if an authentic telemetry profile is already cached
    cached_profile = load_telemetry_profile(track_id, track_layout, car_id, ai_level=100)
    if cached_profile:
        physics = cached_profile.calculate_gate_physics(start_s, countdown_sec)
        targets_info = cached_profile.calculate_sector_targets(start_s, finish_s, start_mode, with_stop_box)
        physics["targets"] = targets_info
        physics["sector_time_s"] = targets_info["sector_time_s"]
        physics["sector_length_m"] = targets_info["sector_length_m"]
        physics["success"] = True
        physics["status"] = "cached"
        return physics

    # 2. Check if a recording job for this track and car is already active or queued
    queue_status = queue_mgr.get_status()
    existing_job = _find_existing_recording_job(queue_status, track_id, car_id)
    if existing_job:
        return existing_job

    # 3. Automatically queue a full lap recording in Assetto Corsa
    job = queue_mgr.enqueue_job(
        job_type="record_telemetry",
        test_id="TELEMETRY_REC",
        title=f"Record 100% AI Telemetry: {car_id} @ {track_id}",
        params={
            "track_id": track_id,
            "track_layout": track_layout,
            "car_id": car_id,
            "start_s": start_s,
            "finish_s": finish_s,
            "start_mode": start_mode,
            "with_stop_box": with_stop_box,
            "countdown_sec": countdown_sec,
            "ai_level": 100,
        },
    )

    return {
        "success": True,
        "status": "queued",
        "job_id": job.id,
        "message": f"No pre-recorded profile found for {car_id} at {track_id}. Enqueued authentic Assetto Corsa recording...",
    }


RUN_MODE_LABELS = {
    "ai": "AI Demo",
    "eval": "Audit Eval",
}


def run_live_test(
    test_id: str,
    mode: str = "play",
    sync_first: bool = True,
    test_data: Optional[Dict[str, Any]] = None,
    timeout: int = 8,
) -> Dict[str, Any]:
    """
    Enqueues a license test for execution in Assetto Corsa via the FIFO queue manager.
    Modes:
      - 'play': Interactive session with timing gates and driver control.
      - 'ai': Simulation session with 95% AI autopilot.
      - 'eval': Headless in-engine evaluation loop (8s audit).
    """
    from tools.web_ui.runner import queue_mgr

    mode_label = RUN_MODE_LABELS.get(mode, "Driver Play")
    job = queue_mgr.enqueue_job(
        job_type=mode,
        test_id=test_id,
        title=f"Test [{test_id}] ({mode_label})",
        params={
            "mode": mode,
            "sync_first": sync_first,
            "test_data": test_data,
            "timeout": timeout,
        },
    )

    return {
        "success": True,
        "status": "queued",
        "job_id": job.id,
        "mode": mode,
        "test_id": test_id,
        "message": f"Test [{test_id}] ({mode_label}) enqueued for execution in Assetto Corsa.",
    }


def get_missing_telemetry_summary(
    tier: Optional[str] = None,
    include_flying: bool = True,
) -> Dict[str, Any]:
    """
    Scans curriculum for rolling start tests that lack a recorded 100% AI telemetry profile
    for their (track_id, track_layout, car_id) combination.
    Groups results by unique combination to avoid duplicate Assetto Corsa recording sessions.
    """
    from tools.telemetry.recorder import load_telemetry_profile
    from tools.web_ui.runner import queue_mgr

    curriculum = load_curriculum()
    valid_modes = {"ROLLING", "FLYING_LAP"} if include_flying else {"ROLLING"}

    # Query currently active / queued jobs in runner to detect in-progress recordings
    queue_status = queue_mgr.get_status()
    queued_combos = set()
    active_job = queue_status.get("active_job")
    if active_job and active_job.get("type") == "record_telemetry":
        p = active_job.get("params", {})
        queued_combos.add((p.get("track_id", ""), p.get("track_layout", ""), p.get("car_id", "")))
    for qj in queue_status.get("queue", []):
        if qj.get("type") == "record_telemetry":
            p = qj.get("params", {})
            queued_combos.add((p.get("track_id", ""), p.get("track_layout", ""), p.get("car_id", "")))

    combos_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    missing_tests = []
    total_rolling_tests = 0

    for s in curriculum:
        tier_name = s.get("tier_name", "")
        if tier and tier != "ALL" and tier_name.lower() != tier.lower():
            continue

        for t in s.get("tests", []):
            start_mode = t.get("start_mode", "STANDING")
            if start_mode not in valid_modes:
                continue

            track_id = t.get("track_id", "")
            layout = t.get("track_layout", "")
            car_id = t.get("car_id", "")
            if not track_id or not car_id:
                continue

            total_rolling_tests += 1
            combo_key = (track_id, layout, car_id)

            profile = load_telemetry_profile(track_id, layout, car_id, ai_level=100)
            is_cached = profile is not None
            is_queued = combo_key in queued_combos

            if not is_cached:
                missing_tests.append({
                    "test_id": t.get("test_id", ""),
                    "tier": tier_name,
                    "title": t.get("title", ""),
                    "track_id": track_id,
                    "track_layout": layout,
                    "car_id": car_id,
                    "start_mode": start_mode,
                })

            if combo_key not in combos_map:
                combos_map[combo_key] = {
                    "track_id": track_id,
                    "track_layout": layout,
                    "car_id": car_id,
                    "test_ids": [t.get("test_id", "")],
                    "tiers": [tier_name],
                    "sample_test": t,
                    "is_cached": is_cached,
                    "is_queued": is_queued,
                    "status": "cached" if is_cached else ("queued" if is_queued else "missing"),
                }
            else:
                if t.get("test_id", "") not in combos_map[combo_key]["test_ids"]:
                    combos_map[combo_key]["test_ids"].append(t.get("test_id", ""))
                if tier_name not in combos_map[combo_key]["tiers"]:
                    combos_map[combo_key]["tiers"].append(tier_name)

    unique_missing_combos = [c for c in combos_map.values() if not c["is_cached"]]

    return {
        "success": True,
        "tier": tier or "ALL",
        "include_flying": include_flying,
        "total_rolling_tests": total_rolling_tests,
        "missing_tests_count": len(missing_tests),
        "unique_combos_count": len(unique_missing_combos),
        "unique_missing_combos": unique_missing_combos,
        "all_combos": list(combos_map.values()),
    }


def enqueue_missing_telemetry_jobs(
    tier: Optional[str] = None,
    include_flying: bool = True,
) -> Dict[str, Any]:
    """
    Enqueues live in-engine telemetry recording sessions into queue_mgr
    for all unique track+car combinations currently missing telemetry.
    """
    from tools.web_ui.runner import queue_mgr

    summary = get_missing_telemetry_summary(tier=tier, include_flying=include_flying)
    missing_combos = [c for c in summary["unique_missing_combos"] if not c["is_queued"]]

    enqueued_jobs = []
    for c in missing_combos:
        st = c.get("sample_test", {})
        track_id = c["track_id"]
        layout = c["track_layout"]
        car_id = c["car_id"]
        test_ids_str = ", ".join(c["test_ids"])

        job = queue_mgr.enqueue_job(
            job_type="record_telemetry",
            test_id=c["test_ids"][0],
            title=f"Record 100% AI Telemetry: {car_id} @ {track_id} ({test_ids_str})",
            params={
                "track_id": track_id,
                "track_layout": layout,
                "car_id": car_id,
                "start_s": float(st.get("start_s", 0.0)),
                "finish_s": float(st.get("finish_s", 1.0)),
                "start_mode": st.get("start_mode", "ROLLING"),
                "with_stop_box": bool(st.get("with_stop_box", False)),
                "countdown_sec": 3.0,
                "ai_level": 100,
            },
        )
        enqueued_jobs.append({
            "job_id": job.id,
            "track_id": track_id,
            "track_layout": layout,
            "car_id": car_id,
            "test_ids": c["test_ids"],
        })

    return {
        "success": True,
        "enqueued_count": len(enqueued_jobs),
        "already_queued_count": len(summary["unique_missing_combos"]) - len(missing_combos),
        "total_missing_combos": len(summary["unique_missing_combos"]),
        "jobs": enqueued_jobs,
        "message": f"Successfully enqueued {len(enqueued_jobs)} AI telemetry recording session(s) in Assetto Corsa queue runner.",
    }

