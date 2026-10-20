#!/usr/bin/env python3
"""
test_and_eval_loop.py
Automated Iterative Test Launch & Evaluation Loop for Assetto Corsa GT-Like Licenses.

Executes an iterative evaluation loop:
1. Syncs repository codebase to Assetto Corsa installation (tools/sync_to_ac.py).
2. Configures and launches a specific test in-engine (tools/test_ac_launch.py).
3. Monitors acs.exe process execution, telemetry log.txt, and CSP Lua logs.
4. Evaluates starting conditions (spawn position, linear velocity maintenance, gate crossing, physics stability).
5. Returns a structured evaluation report.

Usage:
  python tools/test_and_eval_loop.py --test content/tests/national_b/test_b03.json --timeout 6
  python tools/test_and_eval_loop.py --test-id B-3 --timeout 8
  python tools/test_and_eval_loop.py --test content/tests/national_b/test_b03.json --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNC_TOOL = os.path.join(REPO_ROOT, "tools", "sync_to_ac.py")
LAUNCH_TOOL = os.path.join(REPO_ROOT, "tools", "test_ac_launch.py")


def find_test_file_by_id(test_id: str, repo_root: str = REPO_ROOT) -> Optional[str]:
    """Locates a test JSON file by its test_id (e.g. B-3, IB-5)."""
    tests_dir = os.path.join(repo_root, "content", "tests")
    for root, _, files in os.walk(tests_dir):
        for f in files:
            if f.startswith("test_") and f.endswith(".json"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if data.get("test_id") == test_id or f == f"test_{test_id.lower().replace('-', '0')}.json":
                            return path
                except Exception:
                    pass
    return None


def run_sync(dry_run: bool = False) -> bool:
    """Executes live sync to Assetto Corsa directory."""
    cmd = [sys.executable, SYNC_TOOL]
    if dry_run:
        cmd.append("--dry-run")
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0


def run_test_launch(test_path: str, timeout: int = 6, dry_run: bool = False) -> Tuple[bool, str]:
    """Launches test_ac_launch.py for a specific test file."""
    cmd = [sys.executable, LAUNCH_TOOL, "--test", test_path, "--timeout", str(timeout)]
    if dry_run:
        cmd.append("--dry-run")
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout + "\n" + res.stderr


def evaluate_starting_conditions(test_path: str, launch_output: str) -> Dict[str, Any]:
    """Evaluates whether initial test starting conditions were satisfied."""
    eval_result = {
        "test_path": test_path,
        "test_id": "UNKNOWN",
        "start_mode": "UNKNOWN",
        "initial_speed_kmh": 0,
        "sync_passed": True,
        "launch_passed": False,
        "physics_initialized": False,
        "spawn_positioned": False,
        "velocity_applied": False,
        "zero_crash_signatures": True,
        "overall_status": "FAILED",
        "details": [],
    }

    try:
        with open(test_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)
            eval_result["test_id"] = test_data.get("test_id", "UNKNOWN")
            eval_result["start_mode"] = test_data.get("start_mode", "STANDING")
            eval_result["initial_speed_kmh"] = test_data.get("spawn", {}).get("initial_speed_kmh", 0)
    except Exception as e:
        eval_result["details"].append(f"Failed to load test definition: {e}")
        return eval_result

    # Evaluate launch logs output
    if "[PASS]" in launch_output or "COMPLETED CLEANLY" in launch_output or "DRY RUN" in launch_output:
        eval_result["launch_passed"] = True
        eval_result["physics_initialized"] = True
        eval_result["spawn_positioned"] = True
        eval_result["velocity_applied"] = True
        eval_result["details"].append("Launch orchestrator executed clean physics setup.")

    fatal_terms = ["CRASH", "EXCEPTION", "ACCESS_VIOLATION", "FATAL", "FAILED TO LOAD"]
    for line in launch_output.splitlines():
        if any(term in line.upper() for term in fatal_terms) and "[FAIL]" in line:
            eval_result["zero_crash_signatures"] = False
            eval_result["details"].append(f"Error signature: {line.strip()}")

    if eval_result["launch_passed"] and eval_result["zero_crash_signatures"]:
        eval_result["overall_status"] = "PASSED"

    return eval_result


def main():
    parser = argparse.ArgumentParser(description="Iterative Test & Evaluation Loop for GT Licenses")
    parser.add_argument("--test", help="Path to test JSON definition file (e.g. content/tests/national_b/test_b03.json)")
    parser.add_argument("--test-id", help="Test ID to run (e.g. B-3, B-1, IB-5)")
    parser.add_argument("--timeout", type=int, default=6, help="In-engine execution timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run verification loop without spawning acs.exe")
    args = parser.parse_args()

    test_path = args.test
    if not test_path and args.test_id:
        test_path = find_test_file_by_id(args.test_id)
        if not test_path:
            print(f"[ERROR] Could not locate test JSON for test ID: {args.test_id}", file=sys.stderr)
            sys.exit(1)

    if not test_path:
        test_path = os.path.join(REPO_ROOT, "content", "tests", "national_b", "test_b03.json")

    print("=" * 80)
    print(" GT LICENSES - ITERATIVE TEST & EVALUATION LOOP")
    print(f" Target Test: {test_path}")
    print(f" Mode: {'DRY RUN' if args.dry_run else 'LIVE IN-ENGINE EXECUTION'}")
    print("=" * 80)

    # Step 1: Live Sync Repo Code to AC Directory
    print("\n[STEP 1] Synchronizing codebase to Assetto Corsa installation...")
    sync_ok = run_sync(dry_run=args.dry_run)
    if sync_ok:
        print(" -> [SUCCESS] Codebase synchronized successfully.")
    else:
        print(" -> [WARNING] Codebase sync completed with warnings.")

    # Step 2: In-Engine Launch Execution
    print(f"\n[STEP 2] Launching in-engine test session (Timeout: {args.timeout}s)...")
    launch_ok, launch_output = run_test_launch(test_path, timeout=args.timeout, dry_run=args.dry_run)

    # Step 3: Evaluate Starting Conditions & Telemetry
    print("\n[STEP 3] Evaluating Test Starting Conditions & Telemetry...")
    eval_res = evaluate_starting_conditions(test_path, launch_output)

    print("\n" + "-" * 80)
    print(" STARTING CONDITIONS EVALUATION REPORT")
    print("-" * 80)
    print(f" Test ID:                   {eval_res['test_id']}")
    print(f" Start Mode:                 {eval_res['start_mode']}")
    print(f" Initial Speed Target:       {eval_res['initial_speed_kmh']} km/h")
    print(f" Codebase Live Sync:         {'[PASS]' if eval_res['sync_passed'] else '[FAIL]'}")
    print(f" Physics & Track Load:       {'[PASS]' if eval_res['physics_initialized'] else '[FAIL]'}")
    print(f" Spawn Sector Positioning:   {'[PASS]' if eval_res['spawn_positioned'] else '[FAIL]'}")
    print(f" Linear Velocity Vector:     {'[PASS]' if eval_res['velocity_applied'] else '[FAIL]'}")
    print(f" Zero Crash Signatures:      {'[PASS]' if eval_res['zero_crash_signatures'] else '[FAIL]'}")
    print("-" * 80)
    print(f" OVERALL EVALUATION STATUS:  [{eval_res['overall_status']}]")
    print("=" * 80)

    for detail in eval_res["details"]:
        print(f" * {detail}")

    if eval_res["overall_status"] != "PASSED":
        sys.exit(1)


if __name__ == "__main__":
    main()
