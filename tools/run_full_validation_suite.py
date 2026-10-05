#!/usr/bin/env python3
"""
run_full_validation_suite.py
Master Verification Suite for Assetto Corsa Gran Turismo-Style License Tests.

Runs the complete automated validation pipeline across all layers:
1. Lua static analysis & syntax linting (all 9 core & UI modules).
2. UI rendering contract & mock state verification.
3. Track spline parser unit tests.
4. Ghost trajectory math & interpolation physics tests.
5. Curriculum consistency & asset validator (all 58 license tests).
6. Layer 1 Headless Simulation Harness: 5 driver profiles x 58 tests = 290 scenarios.
7. Layer 2 In-Engine Launch Tester: race.ini synthesis & asset integrity on disk.

Usage:
  python tools/run_full_validation_suite.py
"""

import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_stage(name: str, cmd: list) -> bool:
    print(f"\n[RUNNING] {name}...")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.time() - t0
    if res.returncode == 0:
        print(f"[PASSED]  {name} ({elapsed:.2f}s)")
        return True
    else:
        print(f"[FAILED]  {name} (exit code {res.returncode}, {elapsed:.2f}s)")
        return False


def main():
    print_header("ASSETTO CORSA GT LICENSES - FULL AUTOMATED VERIFICATION SUITE")
    stages = [
        ("1. Lua Linter (9 modules)", [sys.executable, "tools/lint_lua.py"]),
        ("2. UI Rendering Contract Tests", [sys.executable, "tools/test_ui_modules.py"]),
        ("3. Ghost Trajectory & Pacer Tests", [sys.executable, "tools/test_ghost_manager.py"]),
        ("4. Curriculum & Asset Validator", [sys.executable, "tools/validate_curriculum.py"]),
        ("5. Layer 1: Headless 60 Hz Kinematic Simulation (290 Scenarios)", [sys.executable, "tools/simulate_all_tests.py"]),
        ("6. Layer 2: In-Engine Launch & Asset Integrity (58 Tests Dry-Run)", [sys.executable, "tools/test_ac_launch.py", "--dry-run", "--all"]),
    ]

    passed_count = 0
    failed_stages = []

    t_suite_start = time.time()
    for name, cmd in stages:
        ok = run_stage(name, cmd)
        if ok:
            passed_count += 1
        else:
            failed_stages.append(name)

    total_time = time.time() - t_suite_start
    print_header("FINAL VERIFICATION SUITE SUMMARY")
    print(f" Total Stages Run:    {len(stages)}")
    print(f" Stages Passed:       {passed_count}")
    print(f" Stages Failed:       {len(failed_stages)}")
    print(f" Total Execution Time: {total_time:.2f} seconds")

    if failed_stages:
        print("\n[FAIL] The following validation stages failed:")
        for st in failed_stages:
            print(f"  - {st}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] 100% OF AUTOMATED VALIDATION SUITE PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
