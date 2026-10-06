#!/usr/bin/env python3
"""
test_off_track_eval.py
Automated In-Engine Verification of Off-Track Failure Adjudication.

Spawns the car into the off-track grass/runoff zone on Vallelunga, launches acs.exe,
and audits custom_shaders_patch.log to ensure the adjudicator triggers:
"[GTLicense] Adjudicator DISQUALIFIED: Off Track: Exceeded Track Limits (4 wheels off)"
"""

import json
import os
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AC_ROOT = r"D:\SteamLibrary\steamapps\common\assettocorsa"
CSP_LOG_PATH = r"D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\custom_shaders_patch.log"
RACE_INI_DOCS = r"D:\Users\Nico\OneDrive\Documents\Assetto Corsa\cfg\race.ini"
GT_MODE_DIR = os.path.join(AC_ROOT, "extension", "lua", "new-modes", "gt-license")


def run_off_track_test(timeout_sec: float = 14.0):
    print("=== Automated In-Engine Off-Track Adjudication Test ===")

    # 1. Sync repository to AC
    print("[1/4] Syncing repository to Assetto Corsa...")
    subprocess.run([sys.executable, os.path.join(REPO_ROOT, "tools", "sync_to_ac.py")], check=True)

    # 2. Synthesize an off-track test definition (B-3 variant spawned on grass at z=125)
    print("[2/4] Synthesizing off-track test configuration...")
    orig_b03_path = os.path.join(REPO_ROOT, "content", "tests", "national_b", "test_b03.json")
    with open(orig_b03_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    # Move spawn 35 meters laterally off the track into the grass
    test_data["test_id"] = "B-3-OFFTRACK"
    test_data["start_mode"] = "STANDING"  # Standing start directly on the grass
    test_data["spawn"] = {
        "position": [113.989, 190.67, 125.0],
        "forward_vector": [0.9984, 0.0032, -0.0564],
        "initial_speed_kmh": 0.0
    }

    # Write active_test.json to CSP mode directories
    for p in [
        os.path.join(GT_MODE_DIR, "active_test.json"),
        os.path.join(GT_MODE_DIR, "data", "active_test.json"),
        os.path.join(GT_MODE_DIR, "data", "tests", "active_test.json"),
    ]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fp:
            json.dump(test_data, fp, indent=2)

    # Synthesize race.ini
    race_ini_content = f"""[RACE]
TRACK={test_data['track_id']}
CONFIG_TRACK={test_data.get('track_layout', '')}
MODEL={test_data['car_id']}
MODEL_CONFIG=
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=1
AUTO_START_SESSION=1
__CM_CUSTOM_MODE=gt-license
TEST_ID=B-3-OFFTRACK

[EVENT]
NAME=B-3-OFFTRACK: Off-Track Detection Verification

[CAR_0]
MODEL={test_data['car_id']}
MODEL_CONFIG=
SKIN=00_classic_red
BALLAST=0
RESTRICTOR=0
DRIVER_NAME=OffTrack_Tester
NATIONALITY=ITA

[SESSION_0]
NAME=B-3-OFFTRACK
TYPE=1
DURATION_MINUTES=5
SPAWN_SET=PIT

[LIGHTING]
SUN_ANGLE=48
TIME_MULT=1
CLOUD_SPEED=0.2

[DYNAMIC_TRACK]
PRESET=5
SESSION_START=100
RANDOMNESS=0
"""
    with open(RACE_INI_DOCS, "w", encoding="utf-8") as f:
        f.write(race_ini_content)

    # Note CSP log position before launch
    initial_log_size = os.path.getsize(CSP_LOG_PATH) if os.path.isfile(CSP_LOG_PATH) else 0

    # 3. Launch acs.exe
    print(f"[3/4] Launching acs.exe in-engine (timeout: {timeout_sec}s)...")
    acs_exe = os.path.join(AC_ROOT, "acs.exe")
    proc = subprocess.Popen([acs_exe], cwd=AC_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        time.sleep(timeout_sec)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("      acs.exe terminated.")

    # 4. Audit CSP log for disqualification signature
    print("[4/4] Auditing CSP log for off-track disqualification...")
    disqualified_found = False
    disqualified_line = None

    if os.path.isfile(CSP_LOG_PATH):
        with open(CSP_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent_logs = all_lines[-300:] if len(all_lines) > 300 else all_lines

        for line in reversed(recent_logs):
            if "Adjudicator DISQUALIFIED" in line and "Off Track" in line:
                disqualified_found = True
                disqualified_line = line.strip()
                break

    # Restore standard B-3 configuration
    try:
        from evaluate_b3_rolling_start import prepare_race_ini
        prepare_race_ini()
        print("      Restored active session to standard B-3 configuration.")
    except Exception as e:
        print(f"      Note: Could not automatically restore B-3: {e}")

    if disqualified_found:
        print(f"[PASS] Off-track disqualification verified!")
        print(f"       Log line: {disqualified_line}")
        return True
    else:
        print("[FAIL] Off-track disqualification was NOT detected in CSP log.")
        print("Recent CSP log lines:")
        if os.path.isfile(CSP_LOG_PATH):
            with open(CSP_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                f.seek(initial_log_size)
                lines = f.readlines()
                for l in lines[-20:]:
                    print("  " + l.strip())
        return False


if __name__ == "__main__":
    success = run_off_track_test(timeout_sec=15.0)
    sys.exit(0 if success else 1)
