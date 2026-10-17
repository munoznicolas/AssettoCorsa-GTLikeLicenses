"""
physics_calculator.py
Target and initial speed physics calculation, live test launch queueing,
missing telemetry summary/queueing, and miniature generation for the Web UI.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.extract_spline_coords import DEFAULT_AC_ROOT


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


def _extract_telemetry_combo(job_data: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str, str]]:
    """Extracts (track_id, track_layout, car_id) tuple if job is record_telemetry."""
    if not job_data or job_data.get("type") != "record_telemetry":
        return None
    p = job_data.get("params", {})
    return (p.get("track_id", ""), p.get("track_layout", ""), p.get("car_id", ""))


def _get_queued_telemetry_combos(queue_status: Dict[str, Any]) -> Set[Tuple[str, str, str]]:
    """Collects set of active or enqueued telemetry recording combos."""
    queued_combos: Set[Tuple[str, str, str]] = set()
    active_combo = _extract_telemetry_combo(queue_status.get("active_job"))
    if active_combo:
        queued_combos.add(active_combo)

    for qj in queue_status.get("queue", []):
        combo = _extract_telemetry_combo(qj)
        if combo:
            queued_combos.add(combo)
    return queued_combos


def _resolve_combo_status(is_cached: bool, is_queued: bool) -> str:
    """Returns 'cached', 'queued', or 'missing' status for a telemetry combo."""
    if is_cached:
        return "cached"
    if is_queued:
        return "queued"
    return "missing"


def _is_tier_matching(tier_name: str, requested_tier: Optional[str]) -> bool:
    """Checks whether tier matches filter (or filter is ALL/None)."""
    if not requested_tier or requested_tier == "ALL":
        return True
    return tier_name.lower() == requested_tier.lower()


def _collect_rolling_tests(
    curriculum: List[Dict[str, Any]],
    tier: Optional[str],
    valid_modes: Set[str],
) -> List[Tuple[Dict[str, Any], str]]:
    """Gathers all rolling start tests matching tier filter and valid start modes."""
    rolling_tests: List[Tuple[Dict[str, Any], str]] = []
    for s in curriculum:
        tier_name = s.get("tier_name", "")
        if not _is_tier_matching(tier_name, tier):
            continue

        for t in s.get("tests", []):
            if t.get("start_mode", "STANDING") not in valid_modes:
                continue
            if not t.get("track_id") or not t.get("car_id"):
                continue
            rolling_tests.append((t, tier_name))
    return rolling_tests


def _update_combo_entry(
    combos_map: Dict[Tuple[str, str, str], Dict[str, Any]],
    combo_key: Tuple[str, str, str],
    test: Dict[str, Any],
    tier_name: str,
    is_cached: bool,
    is_queued: bool,
) -> None:
    """Adds or updates combination entry in combos_map with test ID and tier."""
    test_id = test.get("test_id", "")
    if combo_key not in combos_map:
        combos_map[combo_key] = {
            "track_id": combo_key[0],
            "track_layout": combo_key[1],
            "car_id": combo_key[2],
            "test_ids": [test_id],
            "tiers": [tier_name],
            "sample_test": test,
            "is_cached": is_cached,
            "is_queued": is_queued,
            "status": _resolve_combo_status(is_cached, is_queued),
        }
        return

    entry = combos_map[combo_key]
    if test_id not in entry["test_ids"]:
        entry["test_ids"].append(test_id)
    if tier_name not in entry["tiers"]:
        entry["tiers"].append(tier_name)


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
    from tools.web_ui.catalog_manager import load_curriculum
    from tools.web_ui.runner import queue_mgr

    curriculum = load_curriculum()
    valid_modes = {"ROLLING", "FLYING_LAP"} if include_flying else {"ROLLING"}
    queued_combos = _get_queued_telemetry_combos(queue_mgr.get_status())

    combos_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    missing_tests: List[Dict[str, Any]] = []
    rolling_tests = _collect_rolling_tests(curriculum, tier, valid_modes)

    for t, tier_name in rolling_tests:
        track_id = t.get("track_id", "")
        layout = t.get("track_layout", "")
        car_id = t.get("car_id", "")
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
                "start_mode": t.get("start_mode", "STANDING"),
            })

        _update_combo_entry(combos_map, combo_key, t, tier_name, is_cached, is_queued)

    unique_missing_combos = [c for c in combos_map.values() if not c["is_cached"]]

    return {
        "success": True,
        "tier": tier or "ALL",
        "include_flying": include_flying,
        "total_rolling_tests": len(rolling_tests),
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


def build_test_miniature(
    test_id: str,
    test_data: Optional[Dict[str, Any]] = None,
    ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    """Fires off the Track Miniature Builder for a specific test."""
    from tools.content.generator import generate_single_miniature
    return generate_single_miniature(test_id=test_id, test_data=test_data, ac_root=ac_root)
