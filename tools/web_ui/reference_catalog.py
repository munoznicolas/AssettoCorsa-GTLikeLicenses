"""
reference_catalog.py
Reference test matrix builder and car specification parser for the License Test Designer Web UI.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.parser import DEFAULT_AC_ROOT
from tools.web_ui.ac_discovery import CAR_LAYOUT_MAP, get_available_cars, get_available_tracks

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


def _parse_ui_car_specs(
    ui_path: str,
    default_name: str,
) -> Tuple[str, Optional[int], Optional[int], Optional[float]]:
    """Extracts car display name, hp, weight, and pwratio from ui_car.json."""
    if not os.path.isfile(ui_path):
        return default_name, None, None, None

    try:
        with open(ui_path, "r", encoding="utf-8", errors="ignore") as f:
            d = json.loads(f.read(), strict=False)
            name = d.get("name", default_name)
            specs = d.get("specs", {})

            bhp_m = re.search(r"(\d+)", specs.get("bhp", ""))
            hp = int(bhp_m.group(1)) if bhp_m else None

            wt_m = re.search(r"(\d+)", specs.get("weight", ""))
            wt = int(wt_m.group(1)) if wt_m else None

            pw_m = re.search(r"([\d.]+)", specs.get("pwratio", ""))
            pw = float(pw_m.group(1)) if pw_m else None

            return name, hp, wt, pw
    except Exception:
        return default_name, None, None, None


def _derive_missing_specs(
    hp: Optional[int],
    wt: Optional[int],
    pw: Optional[float],
) -> Tuple[Optional[int], Optional[float]]:
    """Derives weight or power-to-weight ratio if one is missing and the other is available."""
    if hp:
        if wt and not pw:
            pw = round(wt / hp, 2)
        elif pw and not wt:
            wt = round(hp * pw)
    return wt, pw


def _resolve_car_specs(
    car_id: str,
    default_name: str,
    ac_cars_dir: str,
) -> Tuple[str, int, Optional[int], Optional[float]]:
    """Resolves car display name, horsepower, weight, and power-to-weight ratio."""
    if car_id in CAR_SPECS_CACHE:
        hp, wt, pw, _ = CAR_SPECS_CACHE[car_id]
        car_display_name = default_name
    else:
        ui_path = os.path.join(ac_cars_dir, car_id, "ui", "ui_car.json")
        car_display_name, hp, wt, pw = _parse_ui_car_specs(ui_path, default_name)

    wt, pw = _derive_missing_specs(hp, wt, pw)
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
    from tools.web_ui.catalog_manager import load_curriculum

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
