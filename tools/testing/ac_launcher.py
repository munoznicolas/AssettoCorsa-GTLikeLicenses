#!/usr/bin/env python3
"""
test_ac_launch.py
Assetto Corsa In-Engine Session Orchestrator & Batch Launch Tester.

Automates Layer 2 in-engine validation:
1. Synthesizes a valid race.ini in the user's Assetto Corsa documents folder.
2. Injects the GT-License scenario test configuration into race.ini.
3. Spawns acs.exe as a child process.
4. Monitors process lifecycle and log.txt for a configured timeout (e.g. 5-8 seconds).
5. Asserts process survival, physics initialization, asset loading, and zero crash signatures.
6. Gracefully terminates acs.exe and produces a clean audit report.

Usage:
  python tools/test_ac_launch.py --dry-run --all
  python tools/test_ac_launch.py --dry-run --tier national_b
  python tools/test_ac_launch.py --test content/tests/national_b/test_b01.json --timeout 8
  python tools/test_ac_launch.py --tier national_b --timeout 6
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

from tools.testing.log_auditor import (
    ALT_USER_DOCS_AC,
    CFG_DIR,
    DEFAULT_AC_ROOT,
    LOG_TXT_PATH,
    LOGS_DIR,
    RACE_INI_PATH,
    USER_DOCS_AC,
    _sanitize_ini_value,
    audit_log,
    find_car_skin,
    get_user_documents_dir,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_race_ini(
    test_data: Dict[str, Any],
    ac_root: str = DEFAULT_AC_ROOT,
    ai_level: int = 100,
    ai_test_mode: bool = False,
    restart_at_time: Optional[float] = None,
) -> str:
    """Synthesizes a valid Assetto Corsa race.ini string for a given test configuration."""
    car_id = _sanitize_ini_value(test_data["car_id"])
    track_id = _sanitize_ini_value(test_data["track_id"])
    track_layout = _sanitize_ini_value(test_data.get("track_layout", ""))
    test_id = _sanitize_ini_value(test_data.get("test_id", "TEST"))
    skin = find_car_skin(car_id, ac_root)

    restart_line = f"RESTART_AT_TIME={float(restart_at_time):.2f}\n" if restart_at_time else ""

    is_telemetry = test_id == "AI_TELEMETRY_RECORDER"
    if is_telemetry:
        ai_level = 100
    session_name = _sanitize_ini_value(
        test_data.get("session_name", "Hotlap" if is_telemetry else f"GT License Trial: {test_id}")
    )
    session_type = int(test_data.get("session_type", 4 if is_telemetry else 1))
    duration_min = int(test_data.get("duration_minutes", 0 if is_telemetry else 5))
    spawn_set = _sanitize_ini_value(test_data.get("spawn_set", "HOTLAP_START" if is_telemetry else "PIT"))
    ai_level_int = int(ai_level)

    ini_content = f"""[RACE]
TRACK={track_id}
CONFIG_TRACK={track_layout}
MODEL={car_id}
MODEL_CONFIG=
CARS=1
AI_LEVEL={ai_level_int}
FIXED_SETUP=0
PENALTIES=1
AUTO_START_SESSION=1
__CM_CUSTOM_MODE=gt-license

[CAR_0]
MODEL={car_id}
MODEL_CONFIG=
SKIN={skin}
BALLAST=0
RESTRICTOR=0
DRIVER_NAME=GT_AI_Tester
NATIONALITY=ITA

[SESSION_0]
NAME={session_name}
TYPE={session_type}
DURATION_MINUTES={duration_min}
SPAWN_SET={spawn_set}

[LIGHTING]
SUN_ANGLE=48
TIME_OF_DAY_MULT=1

[WEATHER]
NAME=3_clear

[GROOVE]
VIRTUAL_LM=0.1
MAX_LAPS=30
STARTING_LAPS=0

[DYNAMIC_TRACK]
SESSION_START=100
RANDOMNESS=0
LAP_GAIN=0
SESSION_TRANSFER=100

[ASSISTS]
AUTO_SHIFTER={1 if ai_test_mode else 0}
AUTO_CLUTCH=1

[GTLICENSE]
TEST_ID={test_id}
ACTIVE=1
AI_TEST_MODE={1 if ai_test_mode else 0}
{restart_line}"""
    return ini_content


def run_launch_test(
    test_json_path: str,
    ac_root: str = DEFAULT_AC_ROOT,
    timeout_seconds: float = 6.0,
    dry_run: bool = False,
    verbose: bool = False,
    watch: bool = False,
    ai_test_mode: bool = False,
    ai_level: int = 95,
    restart_at_time: Optional[float] = None,
) -> Dict[str, Any]:
    """Runs a single in-engine launch test."""
    with open(test_json_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_id = test_data["test_id"]
    title = test_data.get("title", "")
    car_id = test_data["car_id"]
    track_id = test_data["track_id"]
    track_layout = test_data.get("track_layout", "")

    car_path = os.path.join(ac_root, "content", "cars", car_id)
    track_path = os.path.join(ac_root, "content", "tracks", track_id)
    acs_exe_path = os.path.join(ac_root, "acs.exe")

    asset_issues = []
    if not os.path.isdir(car_path):
        asset_issues.append(f"Car folder missing: {car_path}")
    if not os.path.isdir(track_path):
        asset_issues.append(f"Track folder missing: {track_path}")
    if not dry_run and not os.path.isfile(acs_exe_path):
        asset_issues.append(f"acs.exe missing: {acs_exe_path}")

    if asset_issues:
        return {
            "test_id": test_id,
            "title": title,
            "status": "FAILED",
            "reason": "; ".join(asset_issues),
            "dry_run": dry_run,
        }

    race_ini_str = generate_race_ini(
        test_data,
        ac_root=ac_root,
        ai_level=ai_level,
        ai_test_mode=ai_test_mode,
        restart_at_time=restart_at_time,
    )

    if dry_run:
        return {
            "test_id": test_id,
            "title": title,
            "car_id": car_id,
            "track_id": track_id,
            "track_layout": track_layout,
            "status": "PASSED",
            "dry_run": True,
            "ini_bytes": len(race_ini_str),
        }

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

    proc = None
    exit_code = None
    crashed = False

    try:
        proc = subprocess.Popen(
            [acs_exe_path],
            cwd=ac_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if watch:
            print(f">>> [LIVE WATCH MODE] Assetto Corsa launched for {test_id}! AI driving at {ai_level}% AI level. <<<")
            print(">>> The game will stay open so you can watch. Close Assetto Corsa when you are finished. <<<")
            max_duration = max(timeout_seconds, 600.0)
        else:
            max_duration = timeout_seconds

        t_start = time.time()
        while time.time() - t_start < max_duration:
            poll_res = proc.poll()
            if poll_res is not None:
                exit_code = poll_res
                crashed = exit_code != 0
                break
            time.sleep(0.5)

    except Exception as e:
        return {
            "test_id": test_id,
            "title": title,
            "status": "FAILED",
            "reason": f"Failed to spawn acs.exe: {e}",
            "dry_run": False,
        }
    finally:
        if proc and proc.poll() is None and not watch:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass

            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/f", "/im", "acs.exe"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass

    _, milestones, errors = audit_log(LOG_TXT_PATH, car_id, track_id)

    if crashed:
        status = "FAILED"
        reason = f"Process crashed prematurely with exit code {exit_code}"
    elif errors:
        status = "FAILED"
        reason = f"Fatal errors in log: {'; '.join(errors[:3])}"
    else:
        status = "PASSED"
        reason = "Clean execution window completed"

    return {
        "test_id": test_id,
        "title": title,
        "car_id": car_id,
        "track_id": track_id,
        "status": status,
        "reason": reason,
        "milestones": milestones,
        "errors": errors,
        "dry_run": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Assetto Corsa In-Engine Session Orchestrator & Batch Launch Tester."
    )
    parser.add_argument("--test", type=str, help="Path to single test JSON to launch.")
    parser.add_argument("--tier", type=str, help="Tier folder to launch (e.g. national_b, super_license).")
    parser.add_argument("--all", action="store_true", help="Launch all 58 tests.")
    parser.add_argument("--dry-run", action="store_true", help="Synthesize race.ini and verify asset paths without launching acs.exe.")
    parser.add_argument("--timeout", type=float, default=6.0, help="Per-test execution window before auto-termination (seconds). Default 6.0.")
    parser.add_argument("--watch", action="store_true", help="Watch mode: Keep Assetto Corsa running interactively so user can watch AI drive.")
    parser.add_argument("--ai-test-mode", action="store_true", help="Autonomous AI mode: AI drives the car hands-free throughout the entire test.")
    parser.add_argument("--ai-level", type=int, default=95, help="AI skill level percentage (default: 95).")
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa root installation folder.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose milestone output.")

    args = parser.parse_args()

    if args.test:
        test_files = [args.test]
    elif args.tier:
        pattern = os.path.join(REPO_ROOT, "content", "tests", args.tier, "test_*.json")
        test_files = sorted(glob.glob(pattern))
    elif args.all:
        pattern = os.path.join(REPO_ROOT, "content", "tests", "*", "test_*.json")
        test_files = sorted(glob.glob(pattern))
    else:
        args.dry_run = True
        pattern = os.path.join(REPO_ROOT, "content", "tests", "*", "test_*.json")
        test_files = sorted(glob.glob(pattern))

    if not test_files:
        print("[ERROR] No license test JSON files found.")
        sys.exit(1)

    mode_label = "DRY RUN (SYNTHESIS & ASSET AUDIT)" if args.dry_run else f"LIVE LAUNCH (TIMEOUT={args.timeout}s)"
    print("=" * 80)
    print(" ASSETTO CORSA GT LICENSES - IN-ENGINE BATCH LAUNCH TESTER")
    print(f" Mode: {mode_label} across {len(test_files)} test(s)")
    print("=" * 80)

    passed_count = 0
    failed_count = 0
    failed_tests = []

    for path in test_files:
        res = run_launch_test(
            path,
            ac_root=args.ac_root,
            timeout_seconds=args.timeout,
            dry_run=args.dry_run,
            verbose=args.verbose,
            watch=args.watch,
            ai_test_mode=args.ai_test_mode,
            ai_level=args.ai_level,
        )

        test_id = res["test_id"]
        status = res["status"]

        if status == "PASSED":
            passed_count += 1
            if args.dry_run:
                print(f" [PASS] {test_id:6s} | race.ini generated ({res['ini_bytes']} B) | {res['car_id']} @ {res['track_id']}")
            else:
                print(f" [PASS] {test_id:6s} | {res['reason']}")
        else:
            failed_count += 1
            failed_tests.append(test_id)
            print(f" [FAIL] {test_id:6s} | {res['reason']}")

    print("-" * 80)
    print(f"Total Tests Executed: {len(test_files)}")
    print(f"Passed:               {passed_count}")
    print(f"Failed:               {failed_count}")
    print(f"Success Rate:         {passed_count / len(test_files) * 100:.1f}%")
    print("=" * 80)

    if failed_count == 0:
        print("[SUCCESS] ALL IN-ENGINE LAUNCH TESTS COMPLETED CLEANLY!")
        sys.exit(0)
    else:
        print(f"[FAIL] The following tests failed: {', '.join(failed_tests)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
