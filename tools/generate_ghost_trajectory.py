#!/usr/bin/env python3
"""
generate_ghost_trajectory.py
Generates physics-calibrated Gold medal ghost trajectories for Assetto Corsa GT License tests.

Calculates:
1. Curvature radius R_i along track waypoints between start and finish gates.
2. Curvature-limited cornering speed v_corner = sqrt(mu * g * R).
3. Backward braking pass with realistic tire deceleration (a_brake ~ 1.2g).
4. Forward acceleration pass from initial launch velocity.
5. Time normalization scaling so the Ghost crosses the finish gate at exactly T_gold.

Output format:
JSON file content/tests/<tier>/ghost_<test_id>.json or embedded ghost object containing:
[
  { "t": 0.0, "pos": [x,y,z], "heading": [dx,dy,dz], "speed_kmh": v, "is_braking": false },
  ...
]
"""

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)


def compute_curvature_radius(
    p_prev: Tuple[float, float, float],
    p_curr: Tuple[float, float, float],
    p_next: Tuple[float, float, float],
) -> float:
    """Computes the 2D radius of curvature from 3 sequential waypoints."""
    # Vectors in X-Z plane (ground plane in AC)
    v1 = (p_curr[0] - p_prev[0], p_curr[2] - p_prev[2])
    v2 = (p_next[0] - p_curr[0], p_next[2] - p_curr[2])

    d1 = math.hypot(v1[0], v1[1])
    d2 = math.hypot(v2[0], v2[1])

    if d1 < 1e-4 or d2 < 1e-4:
        return 10000.0

    # Cross product (2D determinant) to get sin(theta)
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    dot = v1[0] * v2[0] + v1[1] * v2[1]

    angle = math.atan2(cross, dot)
    if abs(angle) < 1e-4:
        return 10000.0  # Straight line

    # Arc length ds
    ds = 0.5 * (d1 + d2)
    radius = abs(ds / angle)
    return max(5.0, min(10000.0, radius))


def segments_intersect_2d(p1, p2, p3, p4) -> bool:
    """Checks if line segment (p1, p2) intersects with (p3, p4) in X-Z ground plane."""
    x1, z1 = p1[0], p1[2]
    x2, z2 = p2[0], p2[2]
    x3, z3 = p3[0], p3[2]
    x4, z4 = p4[0], p4[2]

    def ccw(ax, az, bx, bz, cx, cz):
        return (cz - az) * (bx - ax) > (bz - az) * (cx - ax)

    return ccw(x1, z1, x3, z3, x4, z4) != ccw(x2, z2, x3, z3, x4, z4) and ccw(
        x1, z1, x2, z2, x3, z3
    ) != ccw(x1, z1, x2, z2, x4, z4)


def generate_ghost_profile(
    test_json_path: str,
    ac_root: str = DEFAULT_AC_ROOT,
    sample_rate_hz: float = 10.0,
    mu: float = 1.25,
) -> Dict[str, Any]:
    """Generates a calibrated Gold Ghost trajectory for a given test definition."""
    with open(test_json_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    test_id = test_data["test_id"]
    targets = test_data.get("targets", {})
    t_gold = float(targets.get("gold_seconds", 20.0))
    start_mode = test_data.get("start_mode", "STANDING")
    spawn = test_data.get("spawn", {})
    initial_speed_kmh = float(spawn.get("initial_speed_kmh", 0.0))
    initial_v_ms = initial_speed_kmh / 3.6

    track_id = test_data.get("track_id", "")
    layout = test_data.get("track_layout", "")

    # Try to load track spline
    spline_path = find_spline_file(track_id, layout, ac_root=ac_root)
    spline_waypoints = []
    if spline_path and os.path.isfile(spline_path):
        try:
            parser = SplineParser(spline_path)
            spline_waypoints = parser.waypoints
        except Exception:
            spline_waypoints = []

    # Timing gates and stop box
    start_gate = test_data.get("timing", {}).get("start_gate", {})
    finish_gate = test_data.get("timing", {}).get("finish_gate", {})
    stop_box = test_data.get("timing", {}).get("stop_box")

    p_start_center = [
        0.5 * (start_gate["p1"][0] + start_gate["p2"][0]),
        0.5 * (start_gate["p1"][1] + start_gate["p2"][1]),
        0.5 * (start_gate["p1"][2] + start_gate["p2"][2]),
    ]
    p_finish_center = [
        0.5 * (finish_gate["p1"][0] + finish_gate["p2"][0]),
        0.5 * (finish_gate["p1"][1] + finish_gate["p2"][1]),
        0.5 * (finish_gate["p1"][2] + finish_gate["p2"][2]),
    ]
    spawn_pos = spawn.get("position", p_start_center)

    path_points = []

    if spline_waypoints and len(spline_waypoints) > 20:
        n_wps = len(spline_waypoints)

        def dist_sq(wp, target):
            return (wp.x - target[0]) ** 2 + (wp.z - target[2]) ** 2

        idx_start = min(range(n_wps), key=lambda i: dist_sq(spline_waypoints[i], spawn_pos))

        is_full_lap = (
            start_mode == "FLYING_LAP"
            or "Full Lap" in test_data.get("title", "")
            or "Graduation" in test_data.get("title", "")
            or test_id.startswith("S-")
        )

        # Detect gate crossings along spline segments
        sg_cross = [
            i
            for i in range(n_wps)
            if segments_intersect_2d(
                (spline_waypoints[i].x, spline_waypoints[i].y, spline_waypoints[i].z),
                (spline_waypoints[(i + 1) % n_wps].x, spline_waypoints[(i + 1) % n_wps].y, spline_waypoints[(i + 1) % n_wps].z),
                start_gate["p1"],
                start_gate["p2"],
            )
        ]
        fg_cross = [
            i
            for i in range(n_wps)
            if segments_intersect_2d(
                (spline_waypoints[i].x, spline_waypoints[i].y, spline_waypoints[i].z),
                (spline_waypoints[(i + 1) % n_wps].x, spline_waypoints[(i + 1) % n_wps].y, spline_waypoints[(i + 1) % n_wps].z),
                finish_gate["p1"],
                finish_gate["p2"],
            )
        ]

        if fg_cross:
            # Pick crossing based on forward progress from idx_start
            def fg_cost(c):
                st = (c - idx_start) % n_wps
                if is_full_lap and st < n_wps // 2:
                    st += n_wps
                return st

            c_fg = min(fg_cross, key=fg_cost)
            steps = (c_fg - idx_start) % n_wps
            if is_full_lap and steps < n_wps // 2:
                steps += n_wps
            steps += 4
            indices = [(idx_start + i) % n_wps for i in range(steps)]
        else:
            idx_finish = min(range(n_wps), key=lambda i: dist_sq(spline_waypoints[i], p_finish_center))
            steps = (idx_finish - idx_start) % n_wps
            if is_full_lap and steps < n_wps // 2:
                steps += n_wps
            steps += 4
            indices = [(idx_start + i) % n_wps for i in range(steps)]

        # Sample waypoints preserving high resolution
        step = max(1, len(indices) // 150)
        selected = set(indices[i] for i in range(0, len(indices), step))
        # Ensure exact gate crossing segment endpoints are included
        if sg_cross:
            for c in sg_cross:
                selected.add(c)
                selected.add((c + 1) % n_wps)
        if fg_cross:
            for c in fg_cross:
                selected.add(c)
                selected.add((c + 1) % n_wps)

        ordered = [idx for idx in indices if idx in selected]
        cleaned = [ordered[0]]
        for idx in ordered[1:]:
            if idx != cleaned[-1]:
                cleaned.append(idx)

        for idx in cleaned:
            wp = spline_waypoints[idx]
            path_points.append([float(wp.x), float(wp.y), float(wp.z)])
    else:
        # Fallback linear interpolation with points before start and after finish
        n_steps = 60
        path_points.append(spawn_pos)
        for i in range(0, n_steps + 1):
            alpha = i / n_steps
            px = p_start_center[0] + alpha * (p_finish_center[0] - p_start_center[0])
            py = p_start_center[1] + alpha * (p_finish_center[1] - p_start_center[1])
            pz = p_start_center[2] + alpha * (p_finish_center[2] - p_start_center[2])
            path_points.append([px, py, pz])
        # Add 5m overshoot point beyond finish
        fx = p_finish_center[0] - p_start_center[0]
        fz = p_finish_center[2] - p_start_center[2]
        flen = max(1e-4, math.hypot(fx, fz))
        path_points.append([p_finish_center[0] + (fx / flen) * 8.0, p_finish_center[1], p_finish_center[2] + (fz / flen) * 8.0])

    # If stop box is present, add deceleration to stop box center
    if stop_box and stop_box.get("center"):
        sb_center = stop_box["center"]
        path_points.append([float(sb_center[0]), float(sb_center[1]), float(sb_center[2])])

    # Compute segment distances
    n = len(path_points)
    seg_dists = [0.0]
    total_dist = 0.0
    for i in range(n - 1):
        p1 = path_points[i]
        p2 = path_points[i + 1]
        d = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2)
        d = max(0.1, d)
        seg_dists.append(d)
        total_dist += d

    # 1. Curvature pass: compute maximum cornering speed
    g = 9.81
    v_corner = []
    for i in range(n):
        if i == 0:
            rad = compute_curvature_radius(path_points[0], path_points[0], path_points[min(1, n - 1)])
        elif i == n - 1:
            rad = compute_curvature_radius(path_points[max(0, n - 2)], path_points[n - 1], path_points[n - 1])
        else:
            rad = compute_curvature_radius(path_points[i - 1], path_points[i], path_points[i + 1])

        v_max = math.sqrt(mu * g * rad)
        # Cap straight line max speed to 330 km/h (91.6 m/s)
        v_max = min(91.6, v_max)
        v_corner.append(v_max)

    # If stop box required, final point velocity must be 0
    if stop_box:
        v_corner[-1] = 0.0

    # 2. Backward pass: deceleration under braking (a_brake = 1.15g ~ 11.3 m/s^2)
    a_brake = 11.3
    v_prof = list(v_corner)
    for i in range(n - 2, -1, -1):
        ds = seg_dists[i + 1]
        v_limit = math.sqrt(v_prof[i + 1] ** 2 + 2.0 * a_brake * ds)
        if v_limit < v_prof[i]:
            v_prof[i] = v_limit

    # 3. Forward pass: acceleration (a_accel = 0.55g ~ 5.4 m/s^2 decreasing with speed)
    v_prof[0] = max(initial_v_ms, 0.0)
    for i in range(1, n):
        ds = seg_dists[i]
        curr_v = v_prof[i - 1]
        # Power-limited acceleration decay
        a_accel = max(1.5, 6.0 * (1.0 - curr_v / 100.0))
        v_limit = math.sqrt(curr_v ** 2 + 2.0 * a_accel * ds)
        if v_limit < v_prof[i]:
            v_prof[i] = v_limit

    # 4. Compute cumulative unscaled time
    t_cum = [0.0]
    for i in range(1, n):
        ds = seg_dists[i]
        v_avg = max(0.5, 0.5 * (v_prof[i - 1] + v_prof[i]))
        dt_seg = ds / v_avg
        t_cum.append(t_cum[-1] + dt_seg)

    t_raw = t_cum[-1]
    if t_raw <= 0:
        t_raw = t_gold

    # Time normalization scalar to match exact Gold time
    time_scale = t_gold / t_raw

    # Scale times so finish gate is crossed at exactly t = T_gold
    scaled_times = [t * time_scale for t in t_cum]
    scaled_velocities = [v / time_scale for v in v_prof]

    # Resample uniformly at sample_rate_hz (e.g. 10 Hz)
    dt_sample = 1.0 / sample_rate_hz
    n_samples = max(2, int(math.ceil(t_gold * sample_rate_hz)))

    trajectory = []
    seg_idx = 0

    for step in range(n_samples + 1):
        t_curr = min(t_gold, step * dt_sample)

        # Find segment in scaled_times
        while seg_idx < n - 2 and scaled_times[seg_idx + 1] < t_curr:
            seg_idx += 1

        t0 = scaled_times[seg_idx]
        t1 = scaled_times[seg_idx + 1]
        dt_span = max(1e-4, t1 - t0)
        frac = max(0.0, min(1.0, (t_curr - t0) / dt_span))

        p0 = path_points[seg_idx]
        p1 = path_points[seg_idx + 1]

        px = p0[0] + frac * (p1[0] - p0[0])
        py = p0[1] + frac * (p1[1] - p0[1])
        pz = p0[2] + frac * (p1[2] - p0[2])

        # Heading direction
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dz = p1[2] - p0[2]
        mag = math.sqrt(dx * dx + dy * dy + dz * dz)
        if mag > 1e-4:
            heading = [round(dx / mag, 4), round(dy / mag, 4), round(dz / mag, 4)]
        else:
            heading = [0.0, 0.0, 1.0]

        v_curr = scaled_velocities[seg_idx] + frac * (scaled_velocities[seg_idx + 1] - scaled_velocities[seg_idx])
        v_next = scaled_velocities[min(n - 1, seg_idx + 1)]
        is_braking = (v_next - v_curr) < -0.5

        trajectory.append({
            "t": round(t_curr, 3),
            "pos": [round(px, 3), round(py, 3), round(pz, 3)],
            "heading": heading,
            "speed_kmh": round(v_curr * 3.6, 1),
            "is_braking": bool(is_braking),
        })

    return {
        "test_id": test_id,
        "gold_time": round(t_gold, 3),
        "total_distance_m": round(total_dist, 1),
        "sample_rate_hz": sample_rate_hz,
        "trajectory": trajectory,
    }


def main():
    parser = argparse.ArgumentParser(description="Assetto Corsa Ghost Trajectory Generator")
    parser.add_argument("--test", help="Path to single test JSON file")
    parser.add_argument("--tier", help="Tier to process (e.g. national_b)")
    parser.add_argument("--all", action="store_true", help="Process all 58 tests")
    parser.add_argument("--out-dir", help="Custom output directory for ghost files")
    args = parser.parse_args()

    tests_dir = os.path.join(REPO_ROOT, "content", "tests")

    test_files = []
    if args.test:
        test_files.append(args.test)
    elif args.tier:
        tier_dir = os.path.join(tests_dir, args.tier)
        if os.path.isdir(tier_dir):
            test_files.extend(
                [os.path.join(tier_dir, f) for f in sorted(os.listdir(tier_dir)) if f.endswith(".json") and not f.startswith("ghost_")]
            )
    elif args.all:
        for root, _, files in os.walk(tests_dir):
            for f in sorted(files):
                if f.endswith(".json") and not f.startswith("ghost_"):
                    test_files.append(os.path.join(root, f))
    else:
        # Default: process B-1 as test run
        b1_path = os.path.join(tests_dir, "national_b", "test_b01.json")
        if os.path.isfile(b1_path):
            test_files.append(b1_path)

    if not test_files:
        print("[ERROR] No test JSON files found.")
        sys.exit(1)

    print(f"Generating ghost profiles for {len(test_files)} test(s)...")
    success_count = 0

    for path in test_files:
        try:
            profile = generate_ghost_profile(path)
            test_dir = os.path.dirname(path)
            test_filename = os.path.basename(path)
            ghost_filename = f"ghost_{test_filename}"
            out_path = os.path.join(test_dir, ghost_filename) if not args.out_dir else os.path.join(args.out_dir, ghost_filename)

            with open(out_path, "w", encoding="utf-8") as out_f:
                json.dump(profile, out_f, indent=2)

            print(f"  + {profile['test_id']} ({profile['gold_time']}s, {len(profile['trajectory'])} samples) -> {os.path.basename(out_path)}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to generate ghost for {path}: {e}", file=sys.stderr)

    print(f"\n[DONE] Successfully generated {success_count}/{len(test_files)} ghost trajectory profile(s).")


if __name__ == "__main__":
    main()
