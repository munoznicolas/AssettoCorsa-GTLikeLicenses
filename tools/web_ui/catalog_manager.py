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

TIER_VAR_MAP = {
    "National B": "NATIONAL_B_TESTS",
    "National A": "NATIONAL_A_TESTS",
    "International B": "INTERNATIONAL_B_TESTS",
    "International A": "INTERNATIONAL_A_TESTS",
    "Super License": "SUPER_LICENSE_TESTS",
}

TIER_FILE_MAP = {
    "National B": "national_b.py",
    "National A": "national_a.py",
    "International B": "international_b.py",
    "International A": "international_a.py",
    "Super License": "super_license.py",
}

TIER_DOCS = {
    "National B": "National B License Test Catalog.\nFundamentals of vehicle dynamics: longitudinal threshold braking, out-in-out trajectory, weight transfer.",
    "National A": "National A License Test Catalog.\nIntermediate sports car dynamics: high-speed chicanes, blind off-camber drops, mid-engine balance.",
    "International B": "International B License Test Catalog.\nHigh-speed commitment, modern downforce, active diffs, and blind braking.",
    "International A": "International A License Test Catalog.\nMotorsport racecraft: full slick racecars, high-downforce GT3/GT4/DTM, and curb discipline.",
    "Super License": "Super License Test Catalog.\nThe ultimate test of speed and discipline: full timed laps with zero margin for error.",
}


def get_catalog_module_path(tier_name: str) -> str:
    filename = TIER_FILE_MAP[tier_name]
    return os.path.join(REPO_ROOT, "tools", "content", "catalog", filename)


def load_curriculum() -> List[Dict[str, Any]]:
    """Loads all series metadata and their current tests from catalog modules."""
    import tools.content.catalog as cat_pkg
    importlib.reload(cat_pkg)

    curriculum = []
    for s_meta in SERIES_METADATA:
        tier_name = s_meta["tier_name"]
        folder = TIER_FOLDER_MAP[tier_name]
        var_name = TIER_VAR_MAP[tier_name]

        mod = importlib.import_module(f"tools.content.catalog.{folder}")
        importlib.reload(mod)
        tests = getattr(mod, var_name, [])

        tests_data = []
        for idx, t in enumerate(tests, start=1):
            td = dict(t)
            td["preview_image"] = f"/content/career/{s_meta['folder']}/event{idx}/preview.png"
            tests_data.append(td)

        # Copy tests to avoid mutating loaded modules directly
        curriculum.append({
            "code": s_meta["code"],
            "tier_name": tier_name,
            "folder": s_meta["folder"],
            "name": s_meta["name"],
            "description": s_meta["description"],
            "badge_asset": s_meta["badge_asset"],
            "test_prefix": s_meta["test_prefix"],
            "tests": tests_data,
        })
    return curriculum


def format_test_dict(t: Dict[str, Any]) -> str:
    lines = ["    {"]
    lines.append(f'        "test_id": {repr(str(t.get("test_id", "")).strip())},')
    lines.append('        "tier": TIER_NAME,')
    lines.append(f'        "title": {repr(str(t.get("title", "")).strip())},')
    lines.append(f'        "description": {repr(str(t.get("description", "")).strip())},')
    lines.append(f'        "lesson_objective": {repr(str(t.get("lesson_objective", "")).strip())},')
    lines.append(f'        "car_id": {repr(str(t.get("car_id", "")).strip())},')
    lines.append(f'        "track_id": {repr(str(t.get("track_id", "")).strip())},')
    lines.append(f'        "track_layout": {repr(str(t.get("track_layout", "")).strip())},')
    lines.append(f'        "start_mode": {repr(str(t.get("start_mode", "STANDING")).strip())},')
    lines.append(f'        "start_s": {round(float(t.get("start_s", 0.0)), 4)},')
    lines.append(f'        "finish_s": {round(float(t.get("finish_s", 1.0)), 4)},')
    lines.append(f'        "spawn_offset": {round(float(t.get("spawn_offset", 0.0)), 1)},')
    lines.append(f'        "speed": {round(float(t.get("speed", 0.0)), 1)},')

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
    lines.append(
        f'        "targets": {{"gold_seconds": {gold:.3f}, "silver_seconds": {silver:.3f}, "bronze_seconds": {bronze:.3f}}},'
    )
    lines.append("    },")
    return "\n".join(lines)


def save_tier_catalog(tier_name: str, tests: List[Dict[str, Any]]) -> str:
    """Saves updated test definitions for a specific tier back to its python file."""
    if tier_name not in TIER_FILE_MAP:
        raise ValueError(f"Unknown tier: {tier_name}")

    meta = next((s for s in SERIES_METADATA if s["tier_name"] == tier_name), None)
    prefix = meta["test_prefix"] if meta else "T-"

    # Automatically ensure sequential test_id numbering matching curriculum structure
    for idx, t in enumerate(tests, start=1):
        t["test_id"] = f"{prefix}{idx}"

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

        ui_track_file = os.path.join(t_path, "ui", "ui_track.json")
        track_name = t_id
        if os.path.isfile(ui_track_file):
            try:
                with open(ui_track_file, "r", encoding="utf-8", errors="ignore") as f:
                    u = json.loads(f.read(), strict=False)
                    track_name = u.get("name", t_id)
            except Exception:
                pass

        layouts = []

        # Check default layout
        def_spline = find_spline_file(t_id, "", ac_root)
        if def_spline:
            layouts.append({
                "layout_id": "",
                "name": "Default Layout",
                "spline_file": def_spline,
            })

        # Check subdirectories
        for sub in sorted(os.listdir(t_path)):
            sub_path = os.path.join(t_path, sub)
            if not os.path.isdir(sub_path):
                continue
            sub_spline = find_spline_file(t_id, sub, ac_root)
            if sub_spline and sub_spline != def_spline:
                sub_name = sub
                sub_ui = os.path.join(t_path, "ui", sub, "ui_track.json")
                if os.path.isfile(sub_ui):
                    try:
                        with open(sub_ui, "r", encoding="utf-8", errors="ignore") as f:
                            su = json.loads(f.read(), strict=False)
                            sub_name = su.get("name", sub)
                    except Exception:
                        pass
                layouts.append({
                    "layout_id": sub,
                    "name": sub_name,
                    "spline_file": sub_spline,
                })

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

        ui_file = os.path.join(c_path, "ui", "ui_car.json")
        car_name = c_id
        brand = ""
        tags: List[str] = []
        if os.path.isfile(ui_file):
            try:
                with open(ui_file, "r", encoding="utf-8", errors="ignore") as f:
                    u = json.loads(f.read(), strict=False)
                    car_name = u.get("name", c_id)
                    brand = u.get("brand", "")
                    raw_tags = u.get("tags", [])
                    if isinstance(raw_tags, list):
                        tags = [str(t).strip() for t in raw_tags if str(t).strip()]
            except Exception:
                pass

        # Determine authoritative drivetrain (FWD, RWD, AWD)
        lower_tags = {t.lower() for t in tags}
        if any(t in lower_tags for t in ("awd", "4wd", "mawd", "fawd")):
            drivetrain = "AWD"
        elif "fwd" in lower_tags or "ff" in lower_tags:
            drivetrain = "FWD"
        elif "rwd" in lower_tags or any(t in lower_tags for t in ("fr", "mr", "rr")):
            drivetrain = "RWD"
        else:
            layout = CAR_LAYOUT_MAP.get(c_id, "FR")
            if layout in ("FAWD", "MAWD", "AWD"):
                drivetrain = "AWD"
            elif layout in ("FF", "FWD"):
                drivetrain = "FWD"
            else:
                drivetrain = "RWD"

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


def clean_stale_tests() -> None:
    """Removes any generated test JSONs that are no longer in the catalog."""
    from tools.content.catalog import TEST_CATALOG, TIER_FOLDER_MAP

    valid_files = set()
    for tdef in TEST_CATALOG:
        t_id = tdef["test_id"]
        tier = tdef["tier"]
        tier_dir = os.path.join(REPO_ROOT, "content", "tests", TIER_FOLDER_MAP[tier])
        prefix, num_str = t_id.split("-")
        filename = f"test_{prefix.lower()}{int(num_str):02d}.json"
        valid_files.add(os.path.normpath(os.path.join(tier_dir, filename)))
        ghost_filename = f"ghost_test_{prefix.lower()}{int(num_str):02d}.json"
        valid_files.add(os.path.normpath(os.path.join(tier_dir, ghost_filename)))

    tests_root = os.path.join(REPO_ROOT, "content", "tests")
    for t_folder in TIER_FOLDER_MAP.values():
        dir_path = os.path.join(tests_root, t_folder)
        if os.path.isdir(dir_path):
            for f in glob.glob(os.path.join(dir_path, "*.json")):
                if os.path.normpath(f) not in valid_files:
                    try:
                        os.remove(f)
                    except OSError:
                        pass

    # Clean stale career event folders if test counts shrunk
    import shutil
    career_root = os.path.join(REPO_ROOT, "content", "career")
    for s_meta in SERIES_METADATA:
        series_dir = os.path.join(career_root, s_meta["folder"])
        if os.path.isdir(series_dir):
            tier_tests = [t for t in TEST_CATALOG if t["tier"] == s_meta["tier_name"]]
            max_events = len(tier_tests)
            for event_dir in glob.glob(os.path.join(series_dir, "event*")):
                m = re.match(r"event(\d+)$", os.path.basename(event_dir))
                if m and int(m.group(1)) > max_events:
                    try:
                        shutil.rmtree(event_dir)
                    except OSError:
                        pass

    # Clean stale SVG maps
    valid_test_ids = {tdef["test_id"] for tdef in TEST_CATALOG}
    maps_dir = os.path.join(REPO_ROOT, "docs", "test_maps")
    if os.path.isdir(maps_dir):
        for svg_file in glob.glob(os.path.join(maps_dir, "*.svg")):
            tid = os.path.splitext(os.path.basename(svg_file))[0]
            if tid not in valid_test_ids:
                try:
                    os.remove(svg_file)
                except OSError:
                    pass


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


def get_ac_curriculum_reference_tests() -> List[Dict[str, Any]]:
    """Converts the active 58 AC Mod career license tests into the standard reference format."""
    ac_cars_dir = os.path.join(DEFAULT_AC_ROOT, "content", "cars")
    tracks = get_available_tracks(kunos_only=False)
    track_map = {t["track_id"]: t["name"] for t in tracks}
    cars = get_available_cars(kunos_only=False)
    car_name_map = {c["car_id"]: c["name"] for c in cars}

    car_specs_cache: Dict[str, Tuple[int, int, float, str]] = {
        "ferrari_laferrari": (963, 1255, 1.30, "MR"),
        "ks_ferrari_f2004": (865, 605, 0.70, "MR"),
        "ks_toyota_ts040": (1000, 870, 0.87, "MAWD"),
    }

    layout_map = CAR_LAYOUT_MAP

    curriculum = load_curriculum()
    ac_tests: List[Dict[str, Any]] = []
    progression = 1

    for tier in curriculum:
        tier_name = tier["tier_name"]
        for test in tier["tests"]:
            car_id = test.get("car_id", "")
            car_display_name = car_name_map.get(car_id, car_id)
            hp: Optional[int] = None
            wt: Optional[int] = None
            pw: Optional[float] = None

            # Check cache/fallback first
            if car_id in car_specs_cache:
                hp, wt, pw, _ = car_specs_cache[car_id]
            else:
                ui_path = os.path.join(ac_cars_dir, car_id, "ui", "ui_car.json")
                if os.path.isfile(ui_path):
                    try:
                        with open(ui_path, "r", encoding="utf-8", errors="ignore") as f:
                            d = json.loads(f.read(), strict=False)
                            car_display_name = d.get("name", car_display_name)
                            specs = d.get("specs", {})
                            bhp_m = re.search(r"(\d+)", specs.get("bhp", ""))
                            if bhp_m: hp = int(bhp_m.group(1))
                            wt_m = re.search(r"(\d+)", specs.get("weight", ""))
                            if wt_m: wt = int(wt_m.group(1))
                            pw_m = re.search(r"([\d.]+)", specs.get("pwratio", ""))
                            if pw_m: pw = float(pw_m.group(1))
                    except Exception:
                        pass

            if hp and wt and not pw:
                pw = round(wt / hp, 2)
            if hp and pw and not wt:
                wt = round(hp * pw)

            layout = layout_map.get(car_id, "FR")
            track_id = test.get("track_id", "")
            track_name = track_map.get(track_id, track_id)
            layout_id = test.get("track_layout", "")
            if layout_id:
                track_name += f" ({layout_id})"

            targets = test.get("targets", {})
            gold_sec = targets.get("gold_seconds")
            silver_sec = targets.get("silver_seconds")
            bronze_sec = targets.get("bronze_seconds")

            def format_time_str(s: Optional[float]) -> str:
                if s is None: return "N/A"
                if s < 60: return f"{s:.3f}s"
                m = int(s // 60)
                sec_part = s % 60
                return f"{m}:{sec_part:06.3f}"

            entry = {
                "id": f"AC_{test.get('test_id', progression)}",
                "game": "AC Mod",
                "license": tier_name,
                "section": f"AC Mod {tier_name}",
                "code": test.get("test_id", f"T-{progression}"),
                "title": test.get("title", ""),
                "test": f"{test.get('test_id', '')} - {test.get('title', '')}",
                "car": car_display_name,
                "car_id": car_id,
                "hp": hp or 200,
                "weight_kg": wt,
                "pw_kg_hp": pw,
                "drivetrain_layout": layout,
                "track": track_name,
                "gold": format_time_str(gold_sec),
                "silver": format_time_str(silver_sec),
                "bronze": format_time_str(bronze_sec),
                "gold_seconds": gold_sec,
                "silver_seconds": silver_sec,
                "bronze_seconds": bronze_sec,
                "target_type": "time",
                "test_progression": progression,
            }
            ac_tests.append(entry)
            progression += 1

    return ac_tests
