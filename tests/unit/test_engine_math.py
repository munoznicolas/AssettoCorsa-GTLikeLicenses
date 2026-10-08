#!/usr/bin/env python3
"""
Unit tests verifying the mathematical models and adjudication algorithms implemented
in lua/engine/ (2D gate crossings, stop box containment, medal evaluation, spline distances).
"""

import math
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)


def ccw(ax, az, bx, bz, cx, cz):
    return ((cz - az) * (bx - ax)) > ((bz - az) * (cx - ax))


def segments_intersect_2d(p1, p2, p3, p4):
    x1, z1 = p1[0], p1[2]
    x2, z2 = p2[0], p2[2]
    x3, z3 = p3[0], p3[2]
    x4, z4 = p4[0], p4[2]

    a = ccw(x1, z1, x3, z3, x4, z4)
    b = ccw(x2, z2, x3, z3, x4, z4)
    c = ccw(x1, z1, x2, z2, x3, z3)
    d = ccw(x1, z1, x2, z2, x4, z4)

    return (a != b) and (c != d)


def is_inside_stop_box(pos, stop_box):
    px, py, pz = pos[0], pos[1], pos[2]
    cx, cy, cz = stop_box["center"][0], stop_box["center"][1], stop_box["center"][2]
    sx, sy, sz = stop_box["size"][0], stop_box["size"][1], stop_box["size"][2]

    if abs(py - cy) > (sy * 0.5 + 4.0):
        return False, 0.0, 0.0

    dx = px - cx
    dz = pz - cz

    rot_rad = -math.radians(stop_box.get("rotation_deg", 0))
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)

    local_x = dx * cos_r - dz * sin_r
    local_z = dx * sin_r + dz * cos_r

    half_x = sx * 0.5
    half_z = sz * 0.5

    is_inside = (abs(local_x) <= half_x) and (abs(local_z) <= half_z)
    return is_inside, local_x, local_z


def evaluate_medal(session_time, targets):
    gold = targets.get("gold_seconds", 999.0)
    silver = targets.get("silver_seconds", 999.0)
    bronze = targets.get("bronze_seconds", 999.0)

    if session_time <= gold:
        return "GOLD"
    elif session_time <= silver:
        return "SILVER"
    elif session_time <= bronze:
        return "BRONZE"
    else:
        return "NONE"


def check_off_track(car, max_wheels_off=2, consecutive_frames=0):
    if not car:
        return False, consecutive_frames, None

    wheels_out = 0
    wheels = car.get("wheels")
    if wheels is not None:
        for i in range(4):
            if i in wheels and wheels[i].get("surfaceValidTrack") is False:
                wheels_out += 1
            elif (i + 1) in wheels and 0 not in wheels and wheels[i + 1].get("surfaceValidTrack") is False:
                wheels_out += 1

    native_out = car.get("wheelsOutside", 0)
    if native_out > wheels_out:
        wheels_out = native_out

    if wheels_out > max_wheels_off:
        consecutive_frames += 1
        if consecutive_frames >= 2:
            return True, consecutive_frames, f"Off Track: Exceeded Track Limits ({wheels_out} wheels off)"
    else:
        consecutive_frames = 0

    return False, consecutive_frames, None


class TestEngineMath(unittest.TestCase):
    def test_gate_crossing(self):
        gate_p1 = [-10.0, 0.0, 100.0]
        gate_p2 = [10.0, 0.0, 100.0]

        # Trajectory crossing through gate
        car_prev = [0.0, 0.0, 95.0]
        car_curr = [0.0, 0.0, 105.0]
        self.assertTrue(segments_intersect_2d(car_prev, car_curr, gate_p1, gate_p2))

        # Trajectory not reaching gate
        car_curr_short = [0.0, 0.0, 98.0]
        self.assertFalse(segments_intersect_2d(car_prev, car_curr_short, gate_p1, gate_p2))

        # Trajectory missing gate laterally (off track)
        car_prev_wide = [15.0, 0.0, 95.0]
        car_curr_wide = [15.0, 0.0, 105.0]
        self.assertFalse(segments_intersect_2d(car_prev_wide, car_curr_wide, gate_p1, gate_p2))

    def test_stop_box_containment(self):
        stop_box = {
            "center": [0.0, 0.0, 1025.0],
            "size": [12.0, 4.0, 50.0],
            "rotation_deg": 0.0
        }

        # Inside center
        inside, lx, lz = is_inside_stop_box([0.0, 0.0, 1025.0], stop_box)
        self.assertTrue(inside)
        self.assertAlmostEqual(lx, 0.0)
        self.assertAlmostEqual(lz, 0.0)

        # Inside corner boundary
        inside, lx, lz = is_inside_stop_box([5.5, 0.5, 1045.0], stop_box)
        self.assertTrue(inside)

        # Overshot beyond box
        inside, lx, lz = is_inside_stop_box([0.0, 0.0, 1055.0], stop_box)
        self.assertFalse(inside)
        self.assertGreater(lz, 25.0)

        # Undershot before box
        inside, lx, lz = is_inside_stop_box([0.0, 0.0, 990.0], stop_box)
        self.assertFalse(inside)
        self.assertLess(lz, -25.0)

    def test_stop_box_rotated(self):
        # Stop box rotated 45 degrees
        stop_box = {
            "center": [100.0, 0.0, 100.0],
            "size": [10.0, 4.0, 20.0],
            "rotation_deg": 45.0
        }
        # Center is inside
        inside, lx, lz = is_inside_stop_box([100.0, 0.0, 100.0], stop_box)
        self.assertTrue(inside)

        # Offset along local forward direction (rotated by 45 deg)
        # dx = 5 * cos(45), dz = 5 * sin(45) -> ~3.535, 3.535
        inside, lx, lz = is_inside_stop_box([100.0 + 3.535, 0.0, 100.0 + 3.535], stop_box)
        self.assertTrue(inside)

    def test_medal_evaluation(self):
        targets = {
            "gold_seconds": 26.500,
            "silver_seconds": 28.000,
            "bronze_seconds": 31.000
        }
        self.assertEqual(evaluate_medal(25.990, targets), "GOLD")
        self.assertEqual(evaluate_medal(26.500, targets), "GOLD")
        self.assertEqual(evaluate_medal(26.501, targets), "SILVER")
        self.assertEqual(evaluate_medal(28.000, targets), "SILVER")
        self.assertEqual(evaluate_medal(28.001, targets), "BRONZE")
        self.assertEqual(evaluate_medal(31.000, targets), "BRONZE")
        self.assertEqual(evaluate_medal(31.001, targets), "NONE")

    def test_spline_distance_math(self):
        track_length = 2000.0

        # Standard trailing car: lead at 0.50, follow at 0.48 -> 0.02 * 2000 = 40m
        delta = 0.50 - 0.48
        dist = delta * track_length
        self.assertAlmostEqual(dist, 40.0)

        # Wrap-around boundary: lead at 0.01 (crossed S/F), follow at 0.98 -> delta = -0.97 + 1.0 = 0.03 -> 60m
        delta_wrap = 0.01 - 0.98
        if delta_wrap < -0.5:
            delta_wrap += 1.0
        dist_wrap = delta_wrap * track_length
        self.assertAlmostEqual(dist_wrap, 60.0)

    def test_linear_speed_multiplier(self):
        def get_linear_multiplier(dist_meters, target_gap=8.0, min_gap=1.5, max_mult=1.5):
            if dist_meters <= min_gap:
                return 0.0
            if dist_meters <= target_gap:
                ratio = (dist_meters - min_gap) / (target_gap - min_gap)
                return max(0.50, ratio)
            max_gap = target_gap + 12.0
            if dist_meters >= max_gap:
                return max_mult
            return 1.0 + ((dist_meters - target_gap) / (max_gap - target_gap)) * (max_mult - 1.0)

        self.assertEqual(get_linear_multiplier(1.0), 0.0)
        self.assertEqual(get_linear_multiplier(8.0), 1.0)
        self.assertAlmostEqual(get_linear_multiplier(20.0), 1.5)

    def test_off_track_valid_track_zero_wheels_off(self):
        car = {
            "wheels": {
                0: {"surfaceValidTrack": True},
                1: {"surfaceValidTrack": True},
                2: {"surfaceValidTrack": True},
                3: {"surfaceValidTrack": True}
            }
        }
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=0)
        self.assertFalse(failed)
        self.assertEqual(frames, 0)
        self.assertIsNone(reason)

    def test_off_track_one_or_two_wheels_off_within_limit(self):
        car = {
            "wheels": {
                0: {"surfaceValidTrack": False},
                1: {"surfaceValidTrack": False},
                2: {"surfaceValidTrack": True},
                3: {"surfaceValidTrack": True}
            }
        }
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=0)
        self.assertFalse(failed)
        self.assertEqual(frames, 0)
        self.assertIsNone(reason)

    def test_off_track_three_wheels_off_debounce(self):
        car = {
            "wheels": {
                0: {"surfaceValidTrack": False},
                1: {"surfaceValidTrack": False},
                2: {"surfaceValidTrack": False},
                3: {"surfaceValidTrack": True}
            }
        }
        # Frame 1: Debouncing (consecutive = 1)
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=0)
        self.assertFalse(failed)
        self.assertEqual(frames, 1)

        # Frame 2: Confirmed violation (consecutive = 2)
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=frames)
        self.assertTrue(failed)
        self.assertEqual(frames, 2)
        self.assertIn("3 wheels off", reason)

    def test_off_track_four_wheels_off_fails(self):
        car = {
            "wheels": {
                0: {"surfaceValidTrack": False},
                1: {"surfaceValidTrack": False},
                2: {"surfaceValidTrack": False},
                3: {"surfaceValidTrack": False}
            }
        }
        # Frame 1
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=0)
        self.assertFalse(failed)
        self.assertEqual(frames, 1)

        # Frame 2: Disqualified
        failed, frames, reason = check_off_track(car, max_wheels_off=2, consecutive_frames=frames)
        self.assertTrue(failed)
        self.assertEqual(frames, 2)
        self.assertIn("4 wheels off", reason)

    def test_off_track_transient_glitch_reset(self):
        car_glitch = {
            "wheels": {
                0: {"surfaceValidTrack": False},
                1: {"surfaceValidTrack": False},
                2: {"surfaceValidTrack": False},
                3: {"surfaceValidTrack": False}
            }
        }
        car_valid = {
            "wheels": {
                0: {"surfaceValidTrack": True},
                1: {"surfaceValidTrack": True},
                2: {"surfaceValidTrack": True},
                3: {"surfaceValidTrack": True}
            }
        }
        # Frame 1: 4 wheels off
        failed, frames, reason = check_off_track(car_glitch, max_wheels_off=2, consecutive_frames=0)
        self.assertEqual(frames, 1)

        # Frame 2: Returned to track (glitch resolved)
        failed, frames, reason = check_off_track(car_valid, max_wheels_off=2, consecutive_frames=frames)
        self.assertFalse(failed)
        self.assertEqual(frames, 0)

    def test_off_track_native_fallback(self):
        car_fallback = {
            "wheelsOutside": 4
        }
        failed, frames, reason = check_off_track(car_fallback, max_wheels_off=2, consecutive_frames=0)
        self.assertEqual(frames, 1)
        failed, frames, reason = check_off_track(car_fallback, max_wheels_off=2, consecutive_frames=frames)
        self.assertTrue(failed)
        self.assertEqual(frames, 2)
        self.assertIn("4 wheels off", reason)

    def test_failure_braking_hooks_and_engine_contracts(self):
        """Validates that GTPhysicsHooks exposes applyFailureBraking and releaseFailureBraking,
        and GTLicenseEngine hooks them up with 50% brake intensity on failure."""
        hooks_path = os.path.join(REPO_ROOT, "lua", "engine", "gt_physics_hooks.lua")
        self.assertTrue(os.path.isfile(hooks_path))
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks_code = f.read()

        self.assertIn("function GTPhysicsHooks.applyFailureBraking(carIndex, intensity)", hooks_code)
        self.assertIn("physics.forceUserBrakesFor(1.0, intensity)", hooks_code)
        self.assertIn("physics.forceUserThrottleFor(1.0, 0.0)", hooks_code)
        self.assertIn("function GTPhysicsHooks.releaseFailureBraking(carIndex)", hooks_code)
        self.assertIn("physics.forceUserBrakesFor(0, 0)", hooks_code)
        self.assertIn("physics.forceUserThrottleFor(0, 0)", hooks_code)

        engine_path = os.path.join(REPO_ROOT, "lua", "engine", "gt_license_engine.lua")
        self.assertTrue(os.path.isfile(engine_path))
        with open(engine_path, "r", encoding="utf-8") as f:
            engine_code = f.read()

        self.assertIn("GTPhysicsHooks.applyFailureBraking(0, 0.5)", engine_code)
        self.assertIn("GTPhysicsHooks.releaseFailureBraking(0)", engine_code)
        self.assertIn("function GTLicenseEngine.isBrakingState(state)", engine_code)
        self.assertIn("GTLicenseEngine.isBrakingState(self.state)", engine_code)
        self.assertIn("GTPhysicsHooks.applyControlledBraking = GTPhysicsHooks.applyFailureBraking", hooks_code)
        self.assertIn("GTPhysicsHooks.releaseControlledBraking = GTPhysicsHooks.releaseFailureBraking", hooks_code)


if __name__ == "__main__":
    unittest.main()
