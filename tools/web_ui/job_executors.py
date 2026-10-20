"""
job_executors.py
Process management, 3D spatial synthesis, staging, and job execution helpers
for the Assetto Corsa execution queue runner.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import TIER_FOLDER_MAP
from tools.telemetry.recorder import (
    DEFAULT_AC_ROOT,
    record_live_in_engine_telemetry,
    save_telemetry_profile,
)
from tools.testing.ac_launcher import (
    ALT_USER_DOCS_AC,
    LOG_TXT_PATH,
    RACE_INI_PATH,
    generate_race_ini,
)


def is_acs_process_active() -> bool:
    """Checks if acs.exe is actively running on the host system."""
    try:
        res = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "acs.exe" in res.stdout.lower()
    except Exception:
        return False


def terminate_all_acs_instances() -> None:
    """Forcefully terminates any orphan or running acs.exe processes."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "acs.exe", "/T"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        pass


def ensure_complete_test_data(
    test_data: Dict[str, Any],
    ac_root: str = DEFAULT_AC_ROOT,
    repo_root: str = REPO_ROOT,
) -> Dict[str, Any]:
    """
    Ensures test_data contains valid 3D coordinates (spawn.position, spawn.forward_vector)
    and timing gates. If missing or if spatial coordinates need calculation from the spline,
    synthesizes them using track AI spline (fast_lane.ai) or falls back to pre-generated JSON.
    """
    if not isinstance(test_data, dict):
        return test_data

    has_valid_pos = (
        isinstance(test_data.get("spawn"), dict)
        and isinstance(test_data["spawn"].get("position"), (list, tuple))
        and len(test_data["spawn"]["position"]) == 3
        and isinstance(test_data["spawn"].get("forward_vector"), (list, tuple))
        and len(test_data["spawn"]["forward_vector"]) == 3
    )
    has_timing = (
        isinstance(test_data.get("timing"), dict)
        and "start_gate" in test_data["timing"]
        and "finish_gate" in test_data["timing"]
    )

    if has_valid_pos and has_timing:
        return test_data

    test_id = test_data.get("test_id", "")
    track_id = test_data.get("track_id", "")
    layout = test_data.get("track_layout", "")

    # 1. Synthesize 3D spatial parameters from track AI spline
    try:
        from tools.spline.parser import SplineParser, find_spline_file, generate_test_parameters

        spline_file = find_spline_file(track_id, layout, ac_root)
        if spline_file and os.path.isfile(spline_file):
            parser = SplineParser(spline_file)
            start_s = float(test_data.get("start_s", 0.0))
            finish_s = float(test_data.get("finish_s", 1.0))
            spawn_offset = float(test_data.get("spawn_offset", 0.0))
            speed = float(test_data.get("speed", 0.0))
            with_stop_box = bool(test_data.get("with_stop_box", False))
            gear = test_data.get("gear")
            if gear is None and isinstance(test_data.get("spawn"), dict):
                gear = test_data["spawn"].get("initial_gear") or test_data["spawn"].get("gear")
            rpm = test_data.get("rpm")
            if rpm is None and isinstance(test_data.get("spawn"), dict):
                rpm = test_data["spawn"].get("initial_rpm") or test_data["spawn"].get("rpm")

            geom = generate_test_parameters(
                parser=parser,
                start_progress=start_s,
                finish_progress=finish_s,
                spawn_offset_m=spawn_offset,
                initial_speed_kmh=speed,
                with_stop_box=with_stop_box,
                gear=int(gear) if gear is not None else None,
                rpm=int(rpm) if rpm is not None else None,
                gate_width=test_data.get("gate_width"),
                track_id=test_data.get("track_id"),
            )

            test_data["spawn"] = geom["spawn"]
            test_data["timing"] = geom["timing"]
            if "fail_rules" not in test_data:
                test_data["fail_rules"] = {
                    "max_wheels_off": 2,
                    "wall_collision_threshold_n": 1500,
                    "max_yaw_angle_deg": 90,
                    "stop_box_overshoot_fail": with_stop_box,
                }
            return test_data
    except Exception as e:
        print(f"[!] Note: spline synthesis for {test_id}: {e}")

    # 2. Fallback: load existing pre-generated test JSON from repository
    try:
        from tools.testing.eval_loop import find_test_file_by_id
        repo_file = find_test_file_by_id(test_id, repo_root)
        if repo_file and os.path.isfile(repo_file):
            with open(repo_file, "r", encoding="utf-8") as rf:
                saved = json.load(rf)
                if "spawn" in saved and not has_valid_pos:
                    spawn_dict = dict(saved["spawn"])
                    if "speed" in test_data:
                        spawn_dict["initial_speed_kmh"] = float(test_data["speed"])
                    if "gear" in test_data:
                        spawn_dict["gear"] = int(test_data["gear"])
                    if "rpm" in test_data:
                        spawn_dict["rpm"] = int(test_data["rpm"])
                    test_data["spawn"] = spawn_dict
                if "timing" in saved and not has_timing:
                    test_data["timing"] = saved["timing"]
                if "fail_rules" not in test_data and "fail_rules" in saved:
                    test_data["fail_rules"] = saved["fail_rules"]
    except Exception as e:
        print(f"[!] Note: repo test fallback for {test_id}: {e}")

    return test_data


def stage_test_configuration(test_data: Dict[str, Any], ac_root: str = DEFAULT_AC_ROOT) -> None:
    """
    Stages in-memory test configuration into Assetto Corsa's GT-License runtime paths
    without altering the repository's permanent catalog files.
    Ensures complete 3D spatial parameters (spawn.position, timing gates) are synthesized.
    """
    test_data = ensure_complete_test_data(test_data, ac_root, REPO_ROOT)

    gt_mode_base = os.path.realpath(os.path.join(ac_root, "extension", "lua", "new-modes", "gt-license"))
    raw_test_id = str(test_data.get("test_id", "TEST"))
    safe_test_id = re.sub(r"[^A-Za-z0-9_\-]", "", raw_test_id) or "TEST"
    tier = test_data.get("tier", "National B")
    tier_folder = TIER_FOLDER_MAP.get(tier, "national_b")

    # Normalize test filename (e.g. B-1 -> test_b01.json)
    from tools.testing.eval_loop import find_test_file_by_id
    src_path = find_test_file_by_id(safe_test_id, REPO_ROOT)
    filename = os.path.basename(src_path) if src_path else f"test_{safe_test_id.lower().replace('-', '')}.json"

    # Targets in Assetto Corsa
    stage_targets = [
        os.path.realpath(os.path.join(gt_mode_base, "data", "tests", tier_folder, filename)),
        os.path.realpath(os.path.join(gt_mode_base, "data", "active_test.json")),
        os.path.realpath(os.path.join(gt_mode_base, "active_test.json")),
    ]

    test_json_str = json.dumps(test_data, indent=2)
    for target in stage_targets:
        try:
            if os.path.commonpath([gt_mode_base, target]) != gt_mode_base:
                raise ValueError(f"Refusing to stage file outside gt-license base: {target}")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(test_json_str)
        except Exception as e:
            print(f"[!] Staging target note ({target}): {e}")


def sync_assets_if_needed(ac_root: str = DEFAULT_AC_ROOT) -> None:
    """Synchronizes latest repository Lua scripts and UI assets to AC installation."""
    try:
        from tools.deployment.sync import build_sync_mappings
        mappings = build_sync_mappings(REPO_ROOT, ac_root)
        for src, dst in mappings:
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
    except Exception as e:
        print(f"[!] Sync note prior to execution: {e}")


def _run_record_telemetry(job: Any, params: Dict[str, Any], ac_root: str = DEFAULT_AC_ROOT) -> None:
    """Launches Assetto Corsa in the background to capture 100% AI flying lap telemetry."""
    track_id = params.get("track_id", "")
    track_layout = params.get("track_layout", "")
    car_id = params.get("car_id", "")
    start_s = float(params.get("start_s", 0.0))
    countdown_sec = float(params.get("countdown_sec", 3.0))
    ai_level = int(params.get("ai_level", 100))

    def proc_cb(proc: subprocess.Popen) -> None:
        job.proc = proc

    profile = record_live_in_engine_telemetry(
        track_id=track_id,
        layout=track_layout,
        car_id=car_id,
        ai_level=ai_level,
        ac_root=ac_root,
        timeout_sec=None,
        stop_event=job.stop_event,
        proc_callback=proc_cb,
    )

    if job.stop_event.is_set():
        job.status = "cancelled"
        job.error = "Cancelled by user"
        return

    saved_path = save_telemetry_profile(profile)
    physics = profile.calculate_gate_physics(start_s, countdown_sec)
    physics["profile_path"] = saved_path
    physics["success"] = True

    job.result = physics
    job.status = "completed"


def _run_eval(job: Any, params: Dict[str, Any], ac_root: str = DEFAULT_AC_ROOT) -> None:
    """Executes the automated 8s evaluation audit loop."""
    test_id = str(job.test_id)
    if not re.match(r"^[A-Za-z0-9_\-]+$", test_id):
        job.status = "failed"
        job.error = f"Invalid test_id format: {test_id}"
        return
    timeout = max(1, min(120, int(params.get("timeout", 8))))
    test_data = params.get("test_data")
    sync_first = bool(params.get("sync_first", True))

    if sync_first:
        sync_assets_if_needed(ac_root)

    if test_data:
        stage_test_configuration(test_data, ac_root)

    eval_script = os.path.join(REPO_ROOT, "tools", "test_and_eval_loop.py")
    cmd = [sys.executable, eval_script, "--test-id", test_id, "--timeout", str(timeout)]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    job.proc = proc

    try:
        stdout, stderr = proc.communicate(timeout=timeout + 15)
        log = stdout + ("\n" + stderr if stderr else "")
        job.log = log
        if proc.returncode == 0:
            job.status = "completed"
            job.result = {
                "success": True,
                "status": "PASSED",
                "log": log,
            }
        else:
            job.status = "failed"
            job.error = "In-engine evaluation failed audit checks."
            job.result = {
                "success": False,
                "status": "FAILED",
                "log": log,
            }
    except subprocess.TimeoutExpired:
        proc.kill()
        job.status = "failed"
        job.error = "Evaluation loop timed out."


def _run_interactive_session(job: Any, params: Dict[str, Any], ac_root: str = DEFAULT_AC_ROOT) -> None:
    """Spawns acs.exe for live play or AI autopilot demo and monitors process lifetime."""
    is_ai = (job.type == "ai")
    test_id = job.test_id
    test_data = params.get("test_data")
    sync_first = bool(params.get("sync_first", True))

    if sync_first:
        sync_assets_if_needed(ac_root)

    if not test_data:
        from tools.testing.eval_loop import find_test_file_by_id
        t_path = find_test_file_by_id(test_id, REPO_ROOT)
        if t_path and os.path.isfile(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                test_data = json.load(f)
        else:
            from tools.content.catalog import TESTS_BY_ID
            test_data = TESTS_BY_ID.get(test_id)

    if not test_data:
        job.status = "failed"
        job.error = f"Test configuration for {test_id} not found."
        return

    # Ensure complete 3D spatial parameters (spawn.position, timing gates)
    test_data = ensure_complete_test_data(test_data, ac_root, REPO_ROOT)

    # Stage active in-memory test configuration
    stage_test_configuration(test_data, ac_root)

    race_ini_str = generate_race_ini(
        test_data,
        ac_root=ac_root,
        ai_level=95,
        ai_test_mode=is_ai,
    )

    target_race_paths = [
        RACE_INI_PATH,
        os.path.join(ALT_USER_DOCS_AC, "cfg", "race.ini"),
        os.path.join(ac_root, "cfg", "race.ini"),
    ]
    for rp in target_race_paths:
        try:
            os.makedirs(os.path.dirname(rp), exist_ok=True)
            with open(rp, "w", encoding="utf-8") as f:
                f.write(race_ini_str)
        except Exception:
            pass

    for lp in [LOG_TXT_PATH, os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt")]:
        if os.path.isfile(lp):
            try:
                os.remove(lp)
            except Exception:
                pass

    acs_exe_path = os.path.join(ac_root, "acs.exe")
    if not os.path.isfile(acs_exe_path):
        job.status = "failed"
        job.error = f"Assetto Corsa executable not found at {acs_exe_path}"
        return

    proc = subprocess.Popen([acs_exe_path], cwd=ac_root)
    job.proc = proc

    # Monitor acs.exe process until completion or cancellation
    while proc.poll() is None:
        if job.stop_event.is_set():
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            job.status = "cancelled"
            job.error = "Cancelled by user"
            return
        time.sleep(0.5)

    job.status = "completed"
    job.result = {
        "success": True,
        "message": f"Assetto Corsa session for {test_id} finished.",
    }
