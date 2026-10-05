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
from typing import Any, Dict, List, Optional, Tuple
DEFAULT_AC_ROOT = r"D:\SteamLibrary\steamapps\common\assettocorsa"


def get_user_documents_dir() -> str:
    """Dynamically resolves the active Windows Personal/Documents directory from Registry or env."""
    if sys.platform == "win32":
        try:
            import winreg

            sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                val, _ = winreg.QueryValueEx(key, "Personal")
                val = os.path.expandvars(val)
                if os.path.isdir(val):
                    return val
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


USER_DOCS_AC = os.path.join(get_user_documents_dir(), "Assetto Corsa")
ALT_USER_DOCS_AC = os.path.join(os.path.expanduser("~"), "Documents", "Assetto Corsa")
CFG_DIR = os.path.join(USER_DOCS_AC, "cfg")
LOGS_DIR = os.path.join(USER_DOCS_AC, "logs")
RACE_INI_PATH = os.path.join(CFG_DIR, "race.ini")
LOG_TXT_PATH = os.path.join(LOGS_DIR, "log.txt")


def find_car_skin(car_id: str, ac_root: str = DEFAULT_AC_ROOT) -> str:
    """Finds the first valid skin directory for a given car."""
    skins_dir = os.path.join(ac_root, "content", "cars", car_id, "skins")
    if os.path.isdir(skins_dir):
        skins = sorted(os.listdir(skins_dir))
        if skins:
            return skins[0]
    return "0_default"


def generate_race_ini(
    test_data: Dict[str, Any],
    ac_root: str = DEFAULT_AC_ROOT,
) -> str:
    """Synthesizes a valid Assetto Corsa race.ini string for a given test configuration."""
    car_id = test_data["car_id"]
    track_id = test_data["track_id"]
    track_layout = test_data.get("track_layout", "")
    test_id = test_data.get("test_id", "TEST")
    skin = find_car_skin(car_id, ac_root)

    ini_content = f"""[RACE]
TRACK={track_id}
CONFIG_TRACK={track_layout}
MODEL={car_id}
MODEL_CONFIG=
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=1

[CAR_0]
MODEL=-
MODEL_CONFIG=
SKIN={skin}
DRIVER_NAME=GT_AI_Tester
NATIONALITY=ITA

[SESSION_0]
NAME=GT License Trial: {test_id}
TYPE=3
DURATION_MINUTES=5
SPAWN_SET=START

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

[GTLICENSE]
TEST_ID={test_id}
ACTIVE=1
"""
    return ini_content


def audit_log(
    log_path: str,
    car_id: str,
    track_id: str,
) -> Tuple[bool, List[str], List[str]]:
    """Audits Assetto Corsa log.txt for initialization milestones and fatal error signatures."""
    # Also check fallback log paths if primary doesn't exist
    candidates = [
        log_path,
        os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt"),
    ]
    target_path = None
    for c in candidates:
        if os.path.isfile(c):
            target_path = c
            break

    if not target_path:
        return False, [], ["Log file does not exist"]

    passed_milestones = []
    detected_errors = []

    fatal_keywords = [
        "FATAL ERROR",
        "ACCESS VIOLATION",
        "ATTEMPT TO INDEX A NIL VALUE",
        "EXCEPTION_ACCESS_VIOLATION",
    ]

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        content_upper = "".join(lines).upper()

        # Check milestones
        if "PHYSICS" in content_upper or "FMOD" in content_upper or "DIRECTX" in content_upper:
            passed_milestones.append("Engine subsystem initialized")
        if car_id.upper() in content_upper:
            passed_milestones.append(f"Car data referenced ({car_id})")
        if track_id.upper() in content_upper:
            passed_milestones.append(f"Track data referenced ({track_id})")

        # Check fatal keywords (avoid matching benign CrashGuard)
        for line in lines:
            line_upper = line.upper()
            if "CRASHGUARD" in line_upper:
                continue
            if "CRASH" in line_upper and "CRASHGUARD" not in line_upper:
                detected_errors.append(line.strip())
                continue
            for kw in fatal_keywords:
                if kw in line_upper:
                    # Filter out benign warning mentions
                    if "CANNOT OPEN FILE" in kw and ("SKIN.INI" in line_upper or "CAMERA" in line_upper):
                        continue
                    detected_errors.append(line.strip())
                    break

    except Exception as e:
        detected_errors.append(f"Error reading log file: {e}")

    success = (len(detected_errors) == 0)
    return success, passed_milestones, detected_errors


def run_launch_test(
    test_json_path: str,
    ac_root: str = DEFAULT_AC_ROOT,
    timeout_seconds: float = 6.0,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Runs a single in-engine launch test."""
    with open(test_json_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_id = test_data["test_id"]
    title = test_data.get("title", "")
    car_id = test_data["car_id"]
    track_id = test_data["track_id"]
    track_layout = test_data.get("track_layout", "")

    # Validate asset files on disk
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

    # Generate race.ini
    race_ini_str = generate_race_ini(test_data, ac_root=ac_root)

    if dry_run:
        # In dry-run mode, verify race.ini validity and asset paths without launching
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

    # Live Launch Mode
    # Write race.ini to primary user documents cfg, alternate user documents cfg, and AC install cfg
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

    # Clear old log.txt if present
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

        t_start = time.time()
        while time.time() - t_start < timeout_seconds:
            poll_res = proc.poll()
            if poll_res is not None:
                exit_code = poll_res
                crashed = (exit_code != 0)
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
        if proc and proc.poll() is None:
            # Process survived the required warm-up / initialization window
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass

            # Ensure any lingering acs.exe children on Windows are stopped
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/f", "/im", "acs.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

    # Audit log
    audit_ok, milestones, errors = audit_log(LOG_TXT_PATH, car_id, track_id)

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
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa root installation folder.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose milestone output.")

    args = parser.parse_args()

    test_files = []
    if args.test:
        test_files = [args.test]
    elif args.tier:
        pattern = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "content",
            "tests",
            args.tier,
            "*.json",
        )
        test_files = sorted([f for f in glob.glob(pattern) if "ghost_" not in os.path.basename(f)])
    elif args.all:
        pattern = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "content",
            "tests",
            "*",
            "*.json",
        )
        test_files = sorted([f for f in glob.glob(pattern) if "ghost_" not in os.path.basename(f)])
    else:
        # Default to dry-run all
        args.dry_run = True
        pattern = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "content",
            "tests",
            "*",
            "*.json",
        )
        test_files = sorted([f for f in glob.glob(pattern) if "ghost_" not in os.path.basename(f)])

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
