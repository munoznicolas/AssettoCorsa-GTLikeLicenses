#!/usr/bin/env python3
"""
evaluate_b3_rolling_start.py
Dedicated In-Engine Telemetry & Log Evaluator for National B-3 (Rolling Start vs Standing Start).

Captures:
1. Curriculum definition & Career Event metadata
2. In-Engine session execution via acs.exe
3. Real-time Assetto Corsa Physics Shared Memory (Local\\acpmf_physics) & Graphics (Local\\acpmf_graphic)
4. CSP Log signatures from custom_shaders_patch.log
5. AC engine initialization from log.txt
"""

import ctypes
import json
import mmap
import os
import struct
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AC_ROOT = r"D:\SteamLibrary\steamapps\common\assettocorsa"
TEST_JSON_PATH = os.path.join(REPO_ROOT, "content", "tests", "national_b", "test_b03.json")
CAREER_EVENT_PATH = os.path.join(REPO_ROOT, "content", "career", "series_gt_license_b", "event3", "event.ini")
CSP_LOG_PATH = r"D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\custom_shaders_patch.log"
AC_LOG_PATH = r"D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\log.txt"
RACE_INI_DOCS = r"D:\Users\Nico\OneDrive\Documents\Assetto Corsa\cfg\race.ini"
RACE_INI_INSTALL = os.path.join(AC_ROOT, "cfg", "race.ini")
CSP_TELEMETRY_JSON = os.path.join(AC_ROOT, "extension", "lua", "new-modes", "gt-license", "data", "telemetry_eval.json")


def sync_codebase():
    """Runs sync_to_ac.py to update Lua scripts and test JSONs."""
    print("[1/5] Synchronizing repository to Assetto Corsa...")
    cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", "sync_to_ac.py")]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[WARNING] Sync returned warnings:\n", res.stderr)
    else:
        print("      Sync successful.")


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def prepare_race_ini():
    """Configures race.ini specifically for National B-3."""
    print("[2/5] Synthesizing race.ini and active_test.json for B-3...")
    with open(TEST_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Deploy active_test.json to CSP mode folder
    gt_mode_dir = os.path.join(AC_ROOT, "extension", "lua", "new-modes", "gt-license")
    for act_path in [
        os.path.join(gt_mode_dir, "active_test.json"),
        os.path.join(gt_mode_dir, "data", "active_test.json"),
        os.path.join(gt_mode_dir, "data", "tests", "active_test.json")
    ]:
        try:
            os.makedirs(os.path.dirname(act_path), exist_ok=True)
            with open(act_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
        except Exception:
            pass

    ini_text = f"""[RACE]
TRACK={data['track_id']}
CONFIG_TRACK={data.get('track_layout', '')}
MODEL={data['car_id']}
MODEL_CONFIG=
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=1
AUTO_START_SESSION=1
__CM_CUSTOM_MODE=gt-license
TEST_ID=B-3

[EVENT]
NAME=B-3: Out-In-Out Hairpin Trajectory

[CAR_0]
MODEL={data['car_id']}
MODEL_CONFIG=
SKIN=00_classic_red
BALLAST=0
RESTRICTOR=0
DRIVER_NAME=GT_AI_Tester
NATIONALITY=ITA

[SESSION_0]
NAME=B-3: Out-In-Out Hairpin Trajectory
TYPE=1
DURATION_MINUTES=5
SPAWN_SET=PIT

[LIGHTING]
SUN_ANGLE=48
TIME_OF_DAY_MULT=1

[WEATHER]
NAME=3_clear

[DYNAMIC_TRACK]
SESSION_START=100
RANDOMNESS=0
LAP_GAIN=0
SESSION_TRANSFER=100

[GTLICENSE]
TEST_ID=B-3
ACTIVE=1
"""
    for path in [
        RACE_INI_DOCS,
        RACE_INI_INSTALL,
        r"C:\Users\munoz\Documents\Assetto Corsa\cfg\race.ini"
    ]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(ini_text)
    print("      race.ini and active_test.json deployed.")


def read_ac_shared_memory() -> Optional[Dict[str, Any]]:
    """Reads one snapshot of AC shared memory physics and graphics."""
    try:
        shm_phys = mmap.mmap(-1, 512, "Local\\acpmf_physics", access=mmap.ACCESS_READ)
        packet_id, gas, brake, fuel, gear, rpms, steer = struct.unpack("i f f f i i f", shm_phys[:28])
        speed_kmh, = struct.unpack("f", shm_phys[28:32])
        vx, vy, vz = struct.unpack("fff", shm_phys[32:44])
        heading, pitch, roll = struct.unpack("fff", shm_phys[124:136])

        # Convert AC gear representation: 0=reverse, 1=neutral, 2=gear 1, 3=gear 2...
        actual_gear = gear - 1

        res = {
            "packet_id": packet_id,
            "speed_kmh": round(speed_kmh, 2),
            "velocity": (round(vx, 2), round(vy, 2), round(vz, 2)),
            "gear": actual_gear,
            "rpms": rpms,
            "gas": round(gas, 2),
            "brake": round(brake, 2),
            "steer": round(steer, 2),
            "heading": round(heading, 3)
        }

        # Try graphics for world position
        try:
            shm_gfx = mmap.mmap(-1, 512, "Local\\acpmf_graphic", access=mmap.ACCESS_READ)
            status, session = struct.unpack("ii", shm_gfx[4:12])
            res["status"] = status
            # carCoordinates is at offset 164: 3 floats
            cx, cy, cz = struct.unpack("fff", shm_gfx[164:176])
            res["pos"] = (round(cx, 2), round(cy, 2), round(cz, 2))
        except Exception:
            pass

        return res
    except Exception:
        return None


def run_session_and_record_telemetry(timeout_seconds: float = 8.5) -> List[Dict[str, Any]]:
    """Spawns acs.exe, samples telemetry in real time, and terminates."""
    print(f"[3/5] Launching acs.exe in-engine (duration: {timeout_seconds}s)...")
    acs_exe = os.path.join(AC_ROOT, "acs.exe")

    # Clear previous CSP log marker or read current length
    csp_log_start_len = 0
    if os.path.isfile(CSP_LOG_PATH):
        try:
            csp_log_start_len = os.path.getsize(CSP_LOG_PATH)
        except Exception:
            pass

    proc = subprocess.Popen(
        [acs_exe],
        cwd=AC_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    telemetry_samples = []
    t_start = time.time()
    last_sample_time = 0

    try:
        while time.time() - t_start < timeout_seconds:
            # Sample shared memory
            now = time.time()
            if now - last_sample_time >= 0.15:
                sample = read_ac_shared_memory()
                if sample and sample.get("speed_kmh") is not None:
                    sample["timestamp_rel"] = round(now - t_start, 2)
                    telemetry_samples.append(sample)
                last_sample_time = now

            if proc.poll() is not None:
                break
            time.sleep(0.05)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()

    print(f"      acs.exe session finished cleanly. Captured {len(telemetry_samples)} telemetry frames.")
    return telemetry_samples


def inspect_logs() -> Dict[str, Any]:
    """Inspects CSP log and AC log for license engine messages."""
    print("[4/5] Inspecting in-engine logs (CSP & AC)...")
    csp_lines = []
    if os.path.isfile(CSP_LOG_PATH):
        try:
            with open(CSP_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "[GTLicense" in line or "[GTPhysics" in line or "New Modes" in line:
                        csp_lines.append(line.strip())
        except Exception as e:
            csp_lines.append(f"Error reading CSP log: {e}")

    ac_lines = []
    if os.path.isfile(AC_LOG_PATH):
        try:
            with open(AC_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "ks_mazda_miata" in line or "STARTING PHYSICS" in line or "SESSION INFO" in line:
                        ac_lines.append(line.strip())
        except Exception as e:
            ac_lines.append(f"Error reading AC log: {e}")

    return {
        "csp_lines": csp_lines,
        "ac_lines": ac_lines
    }


def main():
    sync_codebase()
    prepare_race_ini()
    telemetry = run_session_and_record_telemetry(timeout_seconds=8.5)
    logs = inspect_logs()

    print("\n[5/5] Synthesizing Evaluation Results...")

    # Load test JSON specification
    with open(TEST_JSON_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    # Load career event.ini
    career_info = {}
    if os.path.isfile(CAREER_EVENT_PATH):
        with open(CAREER_EVENT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    career_info[k] = v

    # Lua saved telemetry
    lua_saved_telemetry = None
    if os.path.isfile(CSP_TELEMETRY_JSON):
        try:
            with open(CSP_TELEMETRY_JSON, "r", encoding="utf-8") as f:
                lua_saved_telemetry = json.load(f)
        except Exception:
            pass

    # Print summary output
    result = {
        "test_id": spec.get("test_id"),
        "title": spec.get("title"),
        "curriculum_start_mode": spec.get("start_mode"),
        "curriculum_target_speed_kmh": spec.get("spawn", {}).get("initial_speed_kmh"),
        "curriculum_spawn_pos": spec.get("spawn", {}).get("position"),
        "curriculum_forward_vec": spec.get("spawn", {}).get("forward_vector"),
        "career_event_name": career_info.get("NAME"),
        "career_track": career_info.get("TRACK"),
        "career_car": career_info.get("MODEL"),
        "telemetry_samples_count": len(telemetry),
        "telemetry_samples_preview": telemetry[:10] if telemetry else [],
        "telemetry_latest_sample": telemetry[-1] if telemetry else None,
        "csp_log_entries": logs["csp_lines"][-15:],
        "ac_log_milestones": logs["ac_lines"][-10:],
        "lua_saved_telemetry_present": lua_saved_telemetry is not None
    }

    # Save evaluation dump
    dump_path = os.path.join(REPO_ROOT, "tools", "eval_b3_result.json")
    with open(dump_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 80)
    print(f" EVALUATION SUMMARY FOR NATIONAL B-3")
    print("=" * 80)
    print(f" Test ID:                     {result['test_id']}")
    print(f" Title:                       {result['title']}")
    print(f" Start Mode in Curriculum:    {result['curriculum_start_mode']}")
    print(f" Target Initial Speed:        {result['curriculum_target_speed_kmh']} km/h")
    print(f" Career Event Mapping:        {result['career_event_name']}")
    print(f" Telemetry Samples Logged:    {result['telemetry_samples_count']}")
    if result['telemetry_latest_sample']:
        ls = result['telemetry_latest_sample']
        print(f" Final Telemetry Speed:       {ls.get('speed_kmh')} km/h")
        print(f" Final Telemetry Gear:        Gear {ls.get('gear')}")
        print(f" Final Telemetry RPM:         {ls.get('rpms')} RPM")
        print(f" Final Telemetry Velocity:    {ls.get('velocity')}")
    print(f" CSP Log Markers Found:       {len(result['csp_log_entries'])}")
    for line in result['csp_log_entries']:
        safe_line = line.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
        print(f"   [CSP LOG] {safe_line}")
    print("=" * 80)


if __name__ == "__main__":
    main()
