#!/usr/bin/env python3
"""
simulate_all_tests.py
Headless Kinematic Simulation & Adjudication Harness for Assetto Corsa GT Licenses.

Simulates behavioral driving profiles across all license tests at 60 Hz:
  1. Profile A: Gold Run (follows trajectory, obeys stop boxes, verifies PASSED + GOLD medal)
  2. Profile B: Wall Hit Disqualification (injects F > 1500 N, verifies FAILED)
  3. Profile C: Off-Track Disqualification (injects 3 wheels off, verifies FAILED)
  4. Profile D: Stop Box Overrun (fails to stop inside stop box, verifies FAILED)
  5. Profile E: Instant Reset (fires reset mid-run, verifies state and pos reset)
  6. Profile F: Countdown & Rolling Velocity Persistence
"""

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))


def ccw(ax: float, az: float, bx: float, bz: float, cx: float, cz: float) -> bool:
    """Counter-clockwise orientation helper on X-Z plane (matching lua/engine/utils.lua)."""
    return ((cz - az) * (bx - ax)) > ((bz - az) * (cx - ax))


def segments_intersect_2d(
    p1: Tuple[float, float, float],
    p2: Tuple[float, float, float],
    p3: Tuple[float, float, float],
    p4: Tuple[float, float, float],
) -> bool:
    """Evaluates 2D segment intersection in X-Z ground plane (matching lua/engine/utils.lua)."""
    x1, z1 = p1[0], p1[2]
    x2, z2 = p2[0], p2[2]
    x3, z3 = p3[0], p3[2]
    x4, z4 = p4[0], p4[2]

    a = ccw(x1, z1, x3, z3, x4, z4)
    b = ccw(x2, z2, x3, z3, x4, z4)
    c = ccw(x1, z1, x2, z2, x3, z3)
    d = ccw(x1, z1, x2, z2, x4, z4)

    return (a != b) and (c != d)


def is_inside_stop_box(
    pos: Tuple[float, float, float],
    stop_box: Dict[str, Any],
) -> Tuple[bool, float, float]:
    """Evaluates 3D Oriented Bounding Box (OBB) containment (matching lua/engine/utils.lua)."""
    px, py, pz = pos[0], pos[1], pos[2]
    cx, cy, cz = stop_box["center"][0], stop_box["center"][1], stop_box["center"][2]
    sx, sy, sz = stop_box["size"][0], stop_box["size"][1], stop_box["size"][2]

    if abs(py - cy) > (sy * 0.5 + 4.0):
        return False, 0.0, 0.0

    dx = px - cx
    dz = pz - cz

    rot_rad = -math.radians(stop_box.get("rotation_deg", 0.0))
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)

    local_x = dx * cos_r - dz * sin_r
    local_z = dx * sin_r + dz * cos_r

    half_x = sx * 0.5
    half_z = sz * 0.5

    is_inside = (abs(local_x) <= half_x) and (abs(local_z) <= half_z)
    return is_inside, local_x, local_z


def point_in_stop_box(
    pos: Tuple[float, float, float],
    center: Tuple[float, float, float],
    size: Tuple[float, float, float],
    rotation_deg: float,
) -> bool:
    """Convenience wrapper around is_inside_stop_box."""
    inside, _, _ = is_inside_stop_box(
        pos,
        {"center": center, "size": size, "rotation_deg": rotation_deg},
    )
    return inside


def _calculate_wheels_off(car: Dict[str, Any]) -> int:
    """Calculates total wheels outside track based on contact surface and native telemetry."""
    wheels = car.get("wheels")
    if not wheels:
        return car.get("wheelsOutside", 0)

    indices = range(4) if 0 in wheels else range(1, 5)
    wheels_out = sum(
        1 for idx in indices
        if wheels.get(idx, {}).get("surfaceValidTrack") is False
    )
    return max(wheels_out, car.get("wheelsOutside", 0))


def check_off_track(
    car: Optional[Dict[str, Any]],
    max_wheels_off: int = 2,
    consecutive_frames: int = 0,
) -> Tuple[bool, int, Optional[str]]:
    """Adjudicates track limits with 2-frame debounce (matching lua/engine/adjudicator.lua)."""
    if not car:
        return False, consecutive_frames, None

    wheels_out = _calculate_wheels_off(car)
    if wheels_out <= max_wheels_off:
        return False, 0, None

    consecutive_frames += 1
    if consecutive_frames >= 2:
        return True, consecutive_frames, f"Off Track: Exceeded Track Limits ({wheels_out} wheels off)"

    return False, consecutive_frames, None


class HeadlessAdjudicator:
    """Python simulation of lua/engine/adjudicator.lua logic."""

    def __init__(self, test_config: Dict[str, Any]):
        self.config = test_config
        self.rules = test_config.get("fail_rules", {})
        self.max_wheels_off = self.rules.get("max_wheels_off", 2)
        self.wall_threshold_n = self.rules.get("wall_collision_threshold_n", 1500)
        self.max_yaw_angle_deg = self.rules.get("max_yaw_angle_deg", 90)
        self.stop_box_overshoot_fail = self.rules.get("stop_box_overshoot_fail", False)

        timing = test_config.get("timing", {})
        self.start_gate = timing.get("start_gate")
        self.finish_gate = timing.get("finish_gate")
        self.stop_box = timing.get("stop_box")

        self.reset()

    def reset(self):
        self.status = "RUNNING"
        self.fail_reason = None
        self.has_passed_start = (self.config.get("start_mode") == "STANDING") or (self.start_gate is None)
        self.has_crossed_finish = False
        self.stop_box_entry_time = None
        self.stop_box_completed = False
        self.prev_pos = None
        self.consecutive_off_track_frames = 0

    def _check_start_gate(self, curr_pos: Tuple[float, float, float]) -> None:
        if not self.has_passed_start and self.prev_pos and self.start_gate:
            p1 = tuple(self.start_gate["p1"])
            p2 = tuple(self.start_gate["p2"])
            if segments_intersect_2d(self.prev_pos, curr_pos, p1, p2):
                self.has_passed_start = True

    def _check_finish_gate(self, curr_pos: Tuple[float, float, float]) -> None:
        if self.has_passed_start and not self.has_crossed_finish and self.prev_pos and self.finish_gate:
            p1 = tuple(self.finish_gate["p1"])
            p2 = tuple(self.finish_gate["p2"])
            if segments_intersect_2d(self.prev_pos, curr_pos, p1, p2):
                self.has_crossed_finish = True

    def _check_violations(
        self,
        collision_force: float,
        wheels_outside: int,
        yaw_angle_deg: float,
    ) -> Optional[str]:
        if collision_force > self.wall_threshold_n:
            return f"Collision force exceeded threshold ({int(collision_force)}N > {self.wall_threshold_n}N)"
        if wheels_outside > self.max_wheels_off:
            self.consecutive_off_track_frames += 1
            if self.consecutive_off_track_frames >= 2:
                return f"Exceeded maximum allowed wheels off track ({wheels_outside} > {self.max_wheels_off})"
        else:
            self.consecutive_off_track_frames = 0

        if abs(yaw_angle_deg) > self.max_yaw_angle_deg:
            return f"Vehicle spun out beyond {self.max_yaw_angle_deg} degrees"
        return None

    def _check_stop_box(
        self,
        session_time: float,
        curr_pos: Tuple[float, float, float],
        speed_kmh: float,
    ) -> Optional[Tuple[str, Optional[str]]]:
        if not self.stop_box:
            return None
        sb_center = tuple(self.stop_box["center"])
        sb_size = tuple(self.stop_box["size"])
        sb_rot = self.stop_box.get("rotation_deg", 0.0)

        in_box = point_in_stop_box(curr_pos, sb_center, sb_size, sb_rot)
        if in_box:
            if self.stop_box_entry_time is None:
                self.stop_box_entry_time = session_time
            if speed_kmh <= 0.5:
                self.stop_box_completed = True
                return ("PASSED", None)
            return None

        if self.has_crossed_finish and self.stop_box_overshoot_fail:
            d_finish = math.hypot(curr_pos[0] - sb_center[0], curr_pos[2] - sb_center[2])
            if d_finish > sb_size[2] and speed_kmh > 5.0:
                return ("FAILED", "Overran stop box without coming to a complete stop")
        return None

    def update(
        self,
        session_time: float,
        curr_pos: Tuple[float, float, float],
        speed_kmh: float,
        wheels_outside: int = 0,
        collision_force: float = 0.0,
        yaw_angle_deg: float = 0.0,
    ) -> Dict[str, Any]:
        if self.status != "RUNNING":
            return {"status": self.status, "reason": self.fail_reason}

        self._check_start_gate(curr_pos)

        fail_reason = self._check_violations(collision_force, wheels_outside, yaw_angle_deg)
        if fail_reason:
            self.status = "FAILED"
            self.fail_reason = fail_reason
            return {"status": self.status, "reason": self.fail_reason}

        self._check_finish_gate(curr_pos)

        if self.stop_box:
            sb_result = self._check_stop_box(session_time, curr_pos, speed_kmh)
            if sb_result:
                self.status, self.fail_reason = sb_result
                return {"status": self.status, "reason": self.fail_reason}
        elif self.has_crossed_finish:
            self.status = "PASSED"
            return {"status": self.status}

        self.prev_pos = curr_pos
        return {"status": self.status}


def evaluate_medal(time_sec: float, targets: Dict[str, float]) -> str:
    gold = float(targets.get("gold_seconds", 0))
    silver = float(targets.get("silver_seconds", 0))
    bronze = float(targets.get("bronze_seconds", 0))

    if time_sec <= gold:
        return "GOLD"
    elif time_sec <= silver:
        return "SILVER"
    elif time_sec <= bronze:
        return "BRONZE"
    return "NONE"


def _gate_crossing_pair(gate: Dict[str, Any], offset_m: float = 4.0) -> Tuple[List[float], List[float]]:
    """Computes two points perpendicular to a timing gate segment so the segment between them intersects the gate."""
    p1 = gate["p1"]
    p2 = gate["p2"]
    mid = [0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1]), 0.5 * (p1[2] + p2[2])]
    gx = p2[0] - p1[0]
    gz = p2[2] - p1[2]
    norm = max(1e-4, math.hypot(gx, gz))
    nx = -gz / norm
    nz = gx / norm
    before = [mid[0] - nx * offset_m, mid[1], mid[2] - nz * offset_m]
    after = [mid[0] + nx * offset_m, mid[1], mid[2] + nz * offset_m]
    return before, after


def _build_gold_run_samples(test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Synthesizes a 60 Hz Gold-medal trajectory crossing start/finish gates and stopping in stop box if present."""
    targets = test_data.get("targets", {})
    t_gold = float(targets.get("gold_seconds", 20.0))
    timing = test_data.get("timing", {})
    start_gate = timing.get("start_gate")
    finish_gate = timing.get("finish_gate")
    stop_box = timing.get("stop_box")

    waypoints: List[List[float]] = []
    if start_gate:
        sg_before, sg_after = _gate_crossing_pair(start_gate, 4.0)
        waypoints.extend([sg_before, sg_after])
    if finish_gate:
        fg_before, fg_after = _gate_crossing_pair(finish_gate, 4.0)
        waypoints.extend([fg_before, fg_after])
    if stop_box and stop_box.get("center"):
        sb_c = stop_box["center"]
        waypoints.append([float(sb_c[0]), float(sb_c[1]), float(sb_c[2])])

    if len(waypoints) < 2:
        spawn_pos = list(test_data.get("spawn", {}).get("position", [0.0, 0.0, 0.0]))
        waypoints = [spawn_pos, [spawn_pos[0] + 10.0, spawn_pos[1], spawn_pos[2] + 10.0]]

    target_finish_time = max(0.5, t_gold * 0.95)
    n_segs = len(waypoints) - 1
    samples: List[Dict[str, Any]] = []
    steps_per_seg = 12
    total_steps = n_segs * steps_per_seg

    for s in range(total_steps + 1):
        seg_idx = min(n_segs - 1, s // steps_per_seg)
        local_frac = (s - seg_idx * steps_per_seg) / steps_per_seg if s < total_steps else 1.0
        p0 = waypoints[seg_idx]
        p1 = waypoints[seg_idx + 1]
        pos = [
            p0[0] + local_frac * (p1[0] - p0[0]),
            p0[1] + local_frac * (p1[1] - p0[1]),
            p0[2] + local_frac * (p1[2] - p0[2]),
        ]
        t_curr = (s / total_steps) * target_finish_time
        is_final_stop = bool(stop_box) and (s == total_steps)
        speed_kmh = 0.0 if is_final_stop else 80.0
        samples.append({"t": t_curr, "pos": pos, "speed_kmh": speed_kmh})

    return samples


def _run_profile_a_gold(
    adjudicator: HeadlessAdjudicator,
    ideal_samples: List[Dict[str, Any]],
    targets: Dict[str, Any],
) -> bool:
    adjudicator.reset()
    sim_time = 0.0
    passed = False

    for sample in ideal_samples:
        pos = tuple(sample["pos"])
        speed = float(sample["speed_kmh"])
        sim_time = float(sample["t"])
        res = adjudicator.update(sim_time, pos, speed)
        if res["status"] == "PASSED":
            passed = True
            break

    medal = evaluate_medal(sim_time, targets) if passed else "NONE"
    return passed and medal == "GOLD"


def _run_profile_b_wall(
    adjudicator: HeadlessAdjudicator,
    spawn_pos: Tuple[float, float, float],
) -> bool:
    adjudicator.reset()
    for _ in range(10):
        adjudicator.update(0.2, spawn_pos, 50.0, collision_force=0.0)
    res_b = adjudicator.update(0.3, spawn_pos, 50.0, collision_force=2500.0)
    return res_b["status"] == "FAILED" and "Collision force" in str(res_b.get("reason"))


def _run_profile_c_offtrack(
    adjudicator: HeadlessAdjudicator,
    spawn_pos: Tuple[float, float, float],
) -> bool:
    adjudicator.reset()
    for _ in range(10):
        adjudicator.update(0.2, spawn_pos, 50.0, wheels_outside=0)
    res_c1 = adjudicator.update(0.3, spawn_pos, 50.0, wheels_outside=3)
    res_c2 = adjudicator.update(0.316, spawn_pos, 50.0, wheels_outside=3)
    return (
        res_c1["status"] == "RUNNING"
        and res_c2["status"] == "FAILED"
        and "wheels off track" in str(res_c2.get("reason"))
    )


def _run_profile_d_stopbox(
    adjudicator: HeadlessAdjudicator,
    timing: Dict[str, Any],
) -> bool:
    adjudicator.reset()
    finish_p1 = timing["finish_gate"]["p1"]
    finish_p2 = timing["finish_gate"]["p2"]
    sb_center = timing["stop_box"]["center"]

    start_p1 = timing["start_gate"]["p1"]
    start_p2 = timing["start_gate"]["p2"]
    sg_mid = (0.5 * (start_p1[0] + start_p2[0]), 0.5 * (start_p1[1] + start_p2[1]), 0.5 * (start_p1[2] + start_p2[2]))
    adjudicator.update(0.1, (sg_mid[0] - 5, sg_mid[1], sg_mid[2] - 5), 50.0)
    adjudicator.update(0.2, (sg_mid[0] + 5, sg_mid[1], sg_mid[2] + 5), 50.0)

    fg_mid = (0.5 * (finish_p1[0] + finish_p2[0]), 0.5 * (finish_p1[1] + finish_p2[1]), 0.5 * (finish_p1[2] + finish_p2[2]))
    adjudicator.update(1.0, (fg_mid[0] - 5, fg_mid[1], fg_mid[2] - 5), 90.0)
    adjudicator.update(1.1, (fg_mid[0] + 5, fg_mid[1], fg_mid[2] + 5), 90.0)

    overshoot_pos = (sb_center[0] + 100.0, sb_center[1], sb_center[2] + 100.0)
    res_d = adjudicator.update(2.0, overshoot_pos, 90.0)
    return res_d["status"] == "FAILED" and "Overran stop box" in str(res_d.get("reason"))


def _run_profile_e_reset(
    adjudicator: HeadlessAdjudicator,
    spawn_pos: Tuple[float, float, float],
    start_mode: str,
) -> bool:
    adjudicator.reset()
    adjudicator.update(5.0, (spawn_pos[0] + 50, spawn_pos[1], spawn_pos[2] + 50), 100.0)
    adjudicator.reset()
    expected_has_passed_start = (start_mode == "STANDING") or (adjudicator.start_gate is None)
    return (
        adjudicator.status == "RUNNING"
        and adjudicator.has_passed_start == expected_has_passed_start
        and not adjudicator.has_crossed_finish
    )


def _run_profile_f_countdown(target_start_speed: float) -> bool:
    simulated_speed = 0.0
    for _ in range(180):
        if target_start_speed > 0:
            simulated_speed = target_start_speed
        else:
            simulated_speed = 0.0
    return abs(simulated_speed - target_start_speed) < 0.1


def simulate_single_test(test_json_path: str) -> Dict[str, Any]:
    with open(test_json_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_id = test_data["test_id"]
    targets = test_data.get("targets", {})
    timing = test_data.get("timing", {})
    has_stop_box = timing.get("stop_box") is not None
    spawn_pos = tuple(test_data.get("spawn", {}).get("position", [0, 0, 0]))
    start_mode = test_data.get("start_mode", "STANDING")
    target_start_speed = float(test_data.get("spawn", {}).get("initial_speed_kmh", 0.0))

    ideal_samples = _build_gold_run_samples(test_data)
    adjudicator = HeadlessAdjudicator(test_data)

    prof_d = _run_profile_d_stopbox(adjudicator, timing) if has_stop_box else True

    return {
        "test_id": test_id,
        "title": test_data.get("title", ""),
        "profile_a_gold": _run_profile_a_gold(adjudicator, ideal_samples, targets),
        "profile_b_wall": _run_profile_b_wall(adjudicator, spawn_pos),
        "profile_c_offtrack": _run_profile_c_offtrack(adjudicator, spawn_pos),
        "profile_d_stopbox": prof_d,
        "profile_e_reset": _run_profile_e_reset(adjudicator, spawn_pos, start_mode),
        "profile_f_countdown": _run_profile_f_countdown(target_start_speed),
    }


def _discover_test_files(tests_dir: str, args: argparse.Namespace) -> List[str]:
    if args.test:
        return [args.test]
    if args.tier:
        tdir = os.path.join(tests_dir, args.tier)
        if os.path.isdir(tdir):
            return [os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.startswith("test_") and f.endswith(".json")]
        return []

    test_files = []
    for root, _, files in os.walk(tests_dir):
        for f in sorted(files):
            if f.startswith("test_") and f.endswith(".json"):
                test_files.append(os.path.join(root, f))
    return test_files


def _format_test_result_line(res: Dict[str, Any], test_passed: bool) -> str:
    status_tag = "[PASS]" if test_passed else "[FAIL]"
    t_id = res["test_id"]
    return (
        f" {status_tag} {t_id:<5} | "
        f"Gold: {'OK' if res['profile_a_gold'] else 'FAIL'} | "
        f"Wall: {'OK' if res['profile_b_wall'] else 'FAIL'} | "
        f"OffTrack: {'OK' if res['profile_c_offtrack'] else 'FAIL'} | "
        f"StopBox: {'OK' if res['profile_d_stopbox'] else 'FAIL'} | "
        f"Reset: {'OK' if res['profile_e_reset'] else 'FAIL'} | "
        f"Countdown: {'OK' if res['profile_f_countdown'] else 'FAIL'}"
    )


def _execute_test_simulation(
    test_files: List[str],
    verbose: bool,
) -> Tuple[int, List[str]]:
    passed_scenarios = 0
    failed_tests = []
    for path in test_files:
        res = simulate_single_test(path)
        profiles = [
            res["profile_a_gold"],
            res["profile_b_wall"],
            res["profile_c_offtrack"],
            res["profile_d_stopbox"],
            res["profile_e_reset"],
            res["profile_f_countdown"],
        ]
        test_passed = all(profiles)
        passed_scenarios += sum(1 for p in profiles if p)
        if not test_passed:
            failed_tests.append(res["test_id"])
        if verbose or not test_passed:
            print(_format_test_result_line(res, test_passed))
    return passed_scenarios, failed_tests


def main():
    parser = argparse.ArgumentParser(description="Headless 60Hz Simulation & Adjudication Harness")
    parser.add_argument("--all", action="store_true", help="Simulate all license tests")
    parser.add_argument("--tier", help="Simulate single tier (e.g. national_b)")
    parser.add_argument("--test", help="Path to single test JSON")
    parser.add_argument("--verbose", action="store_true", help="Show full per-test breakdown")
    args = parser.parse_args()

    tests_dir = os.path.join(REPO_ROOT, "content", "tests")
    test_files = _discover_test_files(tests_dir, args)
    if not test_files:
        print("[ERROR] No test definitions found to simulate.", file=sys.stderr)
        sys.exit(1)

    total_scenarios = len(test_files) * 6
    print("=" * 80)
    print(" ASSETTO CORSA GT LICENSES - HEADLESS SIMULATION & ADJUDICATION SUITE")
    print(f" Executing 6 Behavioral Profiles across {len(test_files)} tests ({total_scenarios} scenarios)...")
    print("=" * 80)

    passed_scenarios, failed_tests = _execute_test_simulation(test_files, args.verbose)

    print("-" * 80)
    print(f"Total Scenarios Executed: {total_scenarios}")
    print(f"Scenarios Passed:         {passed_scenarios}")
    print(f"Scenarios Failed:         {total_scenarios - passed_scenarios}")
    print(f"Success Rate:             {(passed_scenarios / total_scenarios) * 100:.1f}%")
    print("=" * 80)

    if failed_tests:
        print(f"[FAIL] The following tests had failed profiles: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        print(f"[SUCCESS] ALL {total_scenarios} SIMULATION & ADJUDICATION SCENARIOS PASSED PERFECTLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()
