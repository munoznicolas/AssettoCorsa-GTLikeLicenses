"""
catalog_manager.py
Backend bridge between the License Test Designer Web UI and the Python catalog files.
Provides reading, modifying, persisting of tests, track/car discovery, spline queries,
and triggering content generation / validation / AC live sync.
"""

import importlib
import json
import os
import sys
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import SERIES_METADATA, TIER_FOLDER_MAP
from tools.extract_spline_coords import DEFAULT_AC_ROOT
from tools.web_ui.ac_discovery import (
    CAR_LAYOUT_MAP,
    KUNOS_BASE_CARS,
    KUNOS_BASE_TRACKS,
    KUNOS_CAR_IDS,
    KUNOS_TRACK_IDS,
    _determine_drivetrain,
    _discover_track_layouts,
    _read_car_ui_data,
    _read_ui_name,
    get_available_cars,
    get_available_tracks,
    get_track_spline_data,
    is_kunos_car,
    is_kunos_track,
)
from tools.web_ui.asset_relocator import (
    _clean_stale_career_events,
    _clean_stale_json_files,
    _clean_stale_svg_maps,
    _mirror_file_to_ac_if_present,
    _parse_test_number,
    _read_binary_if_exists,
    _read_test_asset_bundle,
    _relocate_tier_test_assets,
    _remove_slot_assets,
    _resolve_previous_test_ids,
    _test_identity_signature,
    _write_relocated_test_assets,
    clean_stale_tests,
)
from tools.web_ui.physics_calculator import (
    RUN_MODE_LABELS,
    _calculate_standing_speed,
    _collect_rolling_tests,
    _extract_telemetry_combo,
    _find_existing_recording_job,
    _get_queued_telemetry_combos,
    _is_tier_matching,
    _resolve_combo_status,
    _update_combo_entry,
    build_test_miniature,
    calculate_test_initial_speed,
    calculate_test_targets_and_physics,
    enqueue_missing_telemetry_jobs,
    get_missing_telemetry_summary,
    run_live_test,
)
from tools.web_ui.reference_catalog import (
    CAR_SPECS_CACHE,
    _build_reference_entry,
    _derive_missing_specs,
    _format_time_str,
    _parse_ui_car_specs,
    _resolve_car_specs,
    get_ac_curriculum_reference_tests,
)

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
        if (
            saved_cfg.get("track_id") != td.get("track_id")
            or saved_cfg.get("track_layout", "") != td.get("track_layout", "")
        ):
            return
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
    importlib.reload(cat_pkg)
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
    t.pop("previous_test_id", None)
    t["test_id"] = f"{prefix}{idx}"
    start_mode = str(t.get("start_mode", "STANDING")).upper()
    if start_mode == "STANDING":
        _normalize_standing_test(t)
    else:
        _normalize_rolling_test(t, start_mode)


def _reload_tier_catalog_modules(tier_name: str) -> None:
    folder = TIER_FOLDER_MAP.get(tier_name)
    if folder:
        mod = importlib.import_module(f"tools.content.catalog.{folder}")
        importlib.reload(mod)
    import tools.content.catalog as cat_pkg
    importlib.reload(cat_pkg)


def save_tier_catalog(tier_name: str, tests: List[Dict[str, Any]]) -> str:
    """Saves updated test definitions for a specific tier back to its python file."""
    if tier_name not in TIER_FILE_MAP:
        raise ValueError(f"Unknown tier: {tier_name}")

    meta = next((s for s in SERIES_METADATA if s["tier_name"] == tier_name), None)
    prefix = meta["test_prefix"] if meta else "T-"

    tier_folder = TIER_FOLDER_MAP[tier_name]
    var_name = TIER_VAR_MAP[tier_name]
    mod = importlib.import_module(f"tools.content.catalog.{tier_folder}")
    importlib.reload(mod)
    old_tests = [dict(x) for x in getattr(mod, var_name, [])]
    old_test_ids = _resolve_previous_test_ids(tests, old_tests, prefix)

    # Automatically ensure sequential test_id numbering matching curriculum structure
    for idx, t in enumerate(tests, start=1):
        _normalize_test_definition(t, prefix, idx)

    file_path = get_catalog_module_path(tier_name)
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

    _reload_tier_catalog_modules(tier_name)
    _relocate_tier_test_assets(tier_name, tests, old_test_ids, len(old_tests))

    return file_path


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


__all__ = [
    "CAR_LAYOUT_MAP",
    "CAR_SPECS_CACHE",
    "KUNOS_BASE_CARS",
    "KUNOS_BASE_TRACKS",
    "KUNOS_CAR_IDS",
    "KUNOS_TRACK_IDS",
    "RUN_MODE_LABELS",
    "TIER_DOCS",
    "TIER_FILE_MAP",
    "TIER_INTERNATIONAL_A",
    "TIER_INTERNATIONAL_B",
    "TIER_NATIONAL_A",
    "TIER_NATIONAL_B",
    "TIER_SUPER_LICENSE",
    "TIER_VAR_MAP",
    "_build_reference_entry",
    "_calculate_standing_speed",
    "_clean_stale_career_events",
    "_clean_stale_json_files",
    "_clean_stale_svg_maps",
    "_collect_rolling_tests",
    "_derive_missing_specs",
    "_determine_drivetrain",
    "_discover_track_layouts",
    "_enrich_test_from_saved_cfg",
    "_extract_telemetry_combo",
    "_find_existing_recording_job",
    "_format_time_str",
    "_get_queued_telemetry_combos",
    "_is_tier_matching",
    "_load_series_tests",
    "_mirror_file_to_ac_if_present",
    "_normalize_rolling_test",
    "_normalize_standing_test",
    "_normalize_test_definition",
    "_parse_test_number",
    "_parse_ui_car_specs",
    "_read_binary_if_exists",
    "_read_car_ui_data",
    "_read_test_asset_bundle",
    "_read_ui_name",
    "_reload_tier_catalog_modules",
    "_relocate_tier_test_assets",
    "_remove_slot_assets",
    "_resolve_car_specs",
    "_resolve_combo_status",
    "_resolve_previous_test_ids",
    "_resolve_rolling_physics",
    "_test_identity_signature",
    "_update_combo_entry",
    "_write_relocated_test_assets",
    "build_test_miniature",
    "calculate_test_initial_speed",
    "calculate_test_targets_and_physics",
    "clean_stale_tests",
    "enqueue_missing_telemetry_jobs",
    "format_test_dict",
    "generate_and_validate",
    "get_ac_curriculum_reference_tests",
    "get_available_cars",
    "get_available_tracks",
    "get_catalog_module_path",
    "get_missing_telemetry_summary",
    "get_track_spline_data",
    "is_kunos_car",
    "is_kunos_track",
    "load_curriculum",
    "run_live_test",
    "save_tier_catalog",
]
