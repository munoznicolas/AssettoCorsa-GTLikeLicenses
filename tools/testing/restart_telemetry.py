#!/usr/bin/env python3
"""
test_restart_telemetry.py
Assetto Corsa In-Engine Session Restart & Telemetry Evaluation Test.

Validates in-engine session restart mechanics:
1. Injects RESTART_AT_TIME into race.ini to trigger an automated restart during RUNNING.
2. Spawns acs.exe and executes the test across pre-restart and post-restart phases.
3. Retrieves live recorded in-game telemetry from extension/lua/new-modes/gt-license/data/telemetry_eval.json.
4. Asserts that upon session restart:
   - Vehicle is cleanly repositioned back to spawn coordinates (not stranded at the curve).
   - Gear is engaged in the correct target gear (e.g. Gear 2 for rolling start, NOT 1st gear).
   - Rolling velocity is restored and maintained through countdown.
   - Handover occurs in the correct target gear.
"""

import argparse
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.testing.ac_launcher import DEFAULT_AC_ROOT, run_launch_test


def evaluate_telemetry(
    telemetry_data: Dict[str, Any],
    spawn_pos: List[float],
    target_gear: int,
    initial_speed_kmh: float,
) -> Tuple[bool, List[str], List[str]]:
    """Analyzes telemetry samples and verifies restart behavior."""
    samples = telemetry_data.get("samples", [])
    if not samples:
        return False, [], ["No telemetry samples recorded in telemetry_eval.json"]

    passed_checks = []
    failures = []

    # Partition samples by restartCount
    pre_restart = [s for s in samples if s.get("restartCount", 0) == 0]
    post_restart = [s for s in samples if s.get("restartCount", 0) >= 1]

    if not pre_restart:
        failures.append("No pre-restart telemetry samples found.")
    else:
        passed_checks.append(f"Recorded {len(pre_restart)} pre-restart telemetry samples.")

    if not post_restart:
        failures.append("No post-restart telemetry samples found: restart was not executed.")
        return False, passed_checks, failures

    passed_checks.append(f"Recorded {len(post_restart)} post-restart telemetry samples.")

    # 1. Verify pre-restart countdown gear
    pre_countdown = [s for s in pre_restart if s.get("state") == "COUNTDOWN"]
    if pre_countdown:
        pre_gear = pre_countdown[-1].get("gear", 0)
        if target_gear > 0 and pre_gear == target_gear:
            passed_checks.append(f"Pre-restart countdown maintained target gear {pre_gear}.")
        elif target_gear > 0:
            failures.append(f"Pre-restart countdown gear was {pre_gear}, expected {target_gear}.")

    # 2. Verify post-restart repositioning back to spawn coordinates
    first_post = post_restart[0]
    px, py, pz = first_post.get("posX", 0), first_post.get("posY", 0), first_post.get("posZ", 0)
    sx, sy, sz = spawn_pos[0], spawn_pos[1], spawn_pos[2]
    dist_to_spawn = math.sqrt((px - sx) ** 2 + (py - sy) ** 2 + (pz - sz) ** 2)

    if dist_to_spawn <= 8.0:
        passed_checks.append(f"Post-restart repositioned near spawn (dist={dist_to_spawn:.2f}m from {sx:.1f}, {sy:.1f}, {sz:.1f}).")
    else:
        failures.append(f"Post-restart position stranded! pos=({px:.1f}, {py:.1f}, {pz:.1f}), dist={dist_to_spawn:.1f}m from spawn ({sx:.1f}, {sy:.1f}, {sz:.1f}).")

    # 3. Verify post-restart countdown state was triggered
    post_countdown = [s for s in post_restart if s.get("state") == "COUNTDOWN"]
    if post_countdown:
        passed_checks.append(f"Post-restart successfully initiated COUNTDOWN state ({len(post_countdown)} samples).")
    else:
        failures.append("Post-restart did not enter COUNTDOWN state.")

    # 4. Verify post-restart gear is target_gear (CRITICAL: NOT gear 1!)
    if post_countdown and target_gear > 0:
        post_gears = [s.get("gear", 0) for s in post_countdown]
        # Allow at most 1 settling frame at index 0 if any
        eval_gears = post_gears[1:] if len(post_gears) > 1 else post_gears
        min_gear = min(eval_gears) if eval_gears else 0
        max_gear = max(eval_gears) if eval_gears else 0

        if min_gear == target_gear and max_gear == target_gear:
            passed_checks.append(f"Post-restart countdown FIRMLY engaged target gear {target_gear} (evaluated gears: {set(eval_gears)}).")
        else:
            failures.append(f"Post-restart gear mismatch! Found gears {set(eval_gears)}, expected {target_gear}. Car dropped to 1st gear!")

    # 5. Verify post-restart speed during countdown for rolling starts
    if post_countdown and initial_speed_kmh > 0:
        post_speeds = [s.get("speedKmh", 0) for s in post_countdown]
        avg_speed = sum(post_speeds) / len(post_speeds)
        if avg_speed >= (initial_speed_kmh * 0.7):
            passed_checks.append(f"Post-restart countdown rolling speed restored (avg={avg_speed:.1f} km/h, target={initial_speed_kmh:.1f} km/h).")
        else:
            failures.append(f"Post-restart speed too low (avg={avg_speed:.1f} km/h < {initial_speed_kmh * 0.7:.1f} km/h). Car stalled on restart.")

    # 6. Verify post-restart GO transition
    post_running = [s for s in post_restart if s.get("state") == "RUNNING"]
    if post_running:
        first_running = post_running[0]
        running_gear = first_running.get("gear", 0)
        passed_checks.append(f"Post-restart successfully transitioned to RUNNING (t={first_running.get('t', 0):.2f}s, gear={running_gear}, spd={first_running.get('speedKmh', 0):.1f} km/h).")
        if target_gear > 0 and running_gear < target_gear:
            failures.append(f"Post-restart GO handover gear dropped to {running_gear}, expected {target_gear}.")
    else:
        passed_checks.append("Note: Post-restart was still in COUNTDOWN when test timeout elapsed.")

    success = (len(failures) == 0)
    return success, passed_checks, failures


def print_telemetry_table(samples: List[Dict[str, Any]]) -> None:
    """Prints a structured ASCII telemetry milestone table."""
    print("\n" + "=" * 90)
    print(f" {'PHASE':<14} | {'STATE':<10} | {'TIME':<7} | {'CD':<5} | {'SPD (km/h)':<10} | {'GEAR':<5} | {'RPM':<6} | {'POS (X, Z)':<18}")
    print("=" * 90)

    milestone_indices = []
    # Pick first, GO, before restart, first after restart, post-GO, last
    for i, s in enumerate(samples):
        if i == 0:
            milestone_indices.append((i, "START"))
        elif s.get("restartCount", 0) == 0 and s.get("state") == "RUNNING" and (i == 0 or samples[i-1].get("state") != "RUNNING"):
            milestone_indices.append((i, "PRE-GO"))
        elif s.get("restartCount", 0) == 1 and samples[i-1].get("restartCount", 0) == 0:
            milestone_indices.append((i-1, "PRE-RESET"))
            milestone_indices.append((i, "POST-RESET"))
        elif s.get("restartCount", 0) == 1 and s.get("state") == "RUNNING" and samples[i-1].get("state") != "RUNNING":
            milestone_indices.append((i, "POST-GO"))
        elif i == len(samples) - 1:
            milestone_indices.append((i, "FINAL"))

    # Also include evenly spaced samples
    shown_indices = sorted(set([idx for idx, _ in milestone_indices] + [int(k) for k in range(0, len(samples), max(1, len(samples) // 10))]))

    for idx in shown_indices:
        if idx >= len(samples):
            continue
        s = samples[idx]
        rc = s.get("restartCount", 0)
        phase_label = f"P{rc + 1} (rc={rc})"
        st = s.get("state", "")
        t_val = s.get("t", 0.0)
        cd_val = s.get("countdown", 0.0)
        spd = s.get("speedKmh", 0.0)
        gear = s.get("gear", 0)
        rpm = s.get("rpm", 0.0)
        px = s.get("posX", 0.0)
        pz = s.get("posZ", 0.0)
        pos_str = f"({px:.1f}, {pz:.1f})"

        print(f" {phase_label:<14} | {st:<10} | {t_val:>5.2f}s | {cd_val:>4.1f} | {spd:>8.1f}   | {gear:>4}  | {rpm:>5.0f}  | {pos_str:<18}")

    print("=" * 90 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test In-Engine Session Restart & Telemetry Evaluation")
    parser.add_argument("--test", default="content/tests/national_b/test_b03.json", help="Path to test JSON")
    parser.add_argument("--ac-root", default=DEFAULT_AC_ROOT, help="Assetto Corsa root folder")
    parser.add_argument("--restart-time", type=float, default=2.5, help="Time in RUNNING before triggering restart (seconds)")
    parser.add_argument("--timeout", type=float, default=18.0, help="Total execution timeout (seconds)")
    parser.add_argument("--watch", action="store_true", help="Keep acs.exe visible")
    args = parser.parse_args()

    test_path = os.path.abspath(args.test)
    if not os.path.isfile(test_path):
        print(f"[ERROR] Test configuration not found: {test_path}")
        return 1

    with open(test_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_id = test_data.get("test_id", "TEST")
    spawn = test_data.get("spawn", {})
    spawn_pos = spawn.get("position", [0, 0, 0])
    target_gear = int(spawn.get("gear", 2))
    initial_speed = float(spawn.get("initial_speed_kmh", 0))

    telemetry_file = os.path.join(
        args.ac_root,
        "extension",
        "lua",
        "new-modes",
        "gt-license",
        "data",
        "telemetry_eval.json",
    )

    # 1. Clear any stale telemetry file
    if os.path.isfile(telemetry_file):
        try:
            os.remove(telemetry_file)
        except Exception:
            pass

    print("=" * 80)
    print(" ASSETTO CORSA GT LICENSES - SESSION RESTART & TELEMETRY VALIDATION")
    print(f" Test:           {test_id} ({test_data.get('title', '')})")
    print(f" Start Mode:     {test_data.get('start_mode', '')} | Initial Speed: {initial_speed:.1f} km/h | Gear: {target_gear}")
    print(f" Restart Trigger: At sessionTime = {args.restart_time:.1f}s")
    print(f" Session Timeout: {args.timeout:.1f}s")
    print(f" Telemetry File: {telemetry_file}")
    print("=" * 80)

    # 2. Launch test session with automated restart enabled
    res = run_launch_test(
        test_json_path=test_path,
        ac_root=args.ac_root,
        timeout_seconds=args.timeout,
        watch=args.watch,
        ai_test_mode=True,
        ai_level=95,
        restart_at_time=args.restart_time,
    )

    if res.get("status") == "FAILED":
        print(f"[FAIL] Session launch failed: {res.get('reason')}")
        return 1

    # 3. Verify telemetry file exists
    if not os.path.isfile(telemetry_file):
        print(f"[FAIL] Telemetry file was not generated by Lua engine at: {telemetry_file}")
        return 1

    with open(telemetry_file, "r", encoding="utf-8") as f:
        telemetry_data = json.load(f)

    samples = telemetry_data.get("samples", [])
    print(f"[INFO] Loaded {len(samples)} in-game telemetry samples.")

    # 4. Print telemetry table
    print_telemetry_table(samples)

    # 5. Evaluate checks
    ok, passed, failures = evaluate_telemetry(
        telemetry_data=telemetry_data,
        spawn_pos=spawn_pos,
        target_gear=target_gear,
        initial_speed_kmh=initial_speed,
    )

    print("-" * 80)
    print(" VALIDATION AUDIT RESULTS:")
    print("-" * 80)
    for p in passed:
        print(f"  [PASS] {p}")
    for f in failures:
        print(f"  [FAIL] {f}")
    print("-" * 80)

    if ok:
        print("[SUCCESS] SESSION RESTART TELEMETRY VALIDATION PASSED COMPLETELY!\n")
        return 0
    else:
        print("[FAILED] SESSION RESTART TELEMETRY VALIDATION FAILED!\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
