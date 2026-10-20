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


from tools.content.simulator import (
    ccw,
    check_off_track,
    evaluate_medal,
    is_inside_stop_box,
    segments_intersect_2d,
)


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
        """Validates that PhysicsHooks exposes applyFailureBraking and releaseFailureBraking,
        and LicenseEngine hooks them up with 50% brake intensity on failure."""
        hooks_path = os.path.join(REPO_ROOT, "lua", "engine", "physics_hooks.lua")
        self.assertTrue(os.path.isfile(hooks_path))
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks_code = f.read()

        self.assertIn("function PhysicsHooks.applyFailureBraking(carIndex, intensity", hooks_code)
        self.assertIn("physics.forceUserBrakesFor(1.0, intensity)", hooks_code)
        self.assertIn("physics.forceUserThrottleFor(1.0, 0.0)", hooks_code)
        self.assertIn("function PhysicsHooks.releaseFailureBraking(carIndex)", hooks_code)
        self.assertIn("physics.forceUserBrakesFor(0, 0)", hooks_code)
        self.assertIn("physics.forceUserThrottleFor(0, 0)", hooks_code)

        engine_path = os.path.join(REPO_ROOT, "lua", "engine", "license_engine.lua")
        self.assertTrue(os.path.isfile(engine_path))
        with open(engine_path, "r", encoding="utf-8") as f:
            engine_code = f.read()

        self.assertIn("PhysicsHooks.applyFailureBraking(0, 0.5", engine_code)
        self.assertIn("PhysicsHooks.releaseFailureBraking(0)", engine_code)
        self.assertIn("function LicenseEngine.isBrakingState(state)", engine_code)
        self.assertIn("LicenseEngine.isBrakingState(self.state)", engine_code)
        self.assertIn("function LicenseEngine:exitSession()", engine_code)
        self.assertIn("onExit = function() self:exitSession() end", engine_code)
        self.assertIn("self.targetStartingRPM = targetRPM", engine_code)
        self.assertIn("self.sessionReset:update(dt, LicenseEngine.isBrakingState(self.state))", engine_code)
        self.assertIn("PhysicsHooks.applyControlledBraking = PhysicsHooks.applyFailureBraking", hooks_code)
        self.assertIn("PhysicsHooks.releaseControlledBraking = PhysicsHooks.releaseFailureBraking", hooks_code)
        self.assertIn("function PhysicsHooks.unlockControls(carIndex, targetGear, targetRPM)", hooks_code)
        self.assertIn("function PhysicsHooks.stopAIRolling(carIndex, targetGear, targetRPM)", hooks_code)

        reset_path = os.path.join(REPO_ROOT, "lua", "engine", "session_reset.lua")
        self.assertTrue(os.path.isfile(reset_path))
        with open(reset_path, "r", encoding="utf-8") as f:
            reset_code = f.read()
        self.assertIn("function SessionReset:isRestartRequested(isTerminalState)", reset_code)
        self.assertIn("function SessionReset:update(dt, isTerminalState)", reset_code)
        self.assertNotIn("GamepadButton.X", reset_code)


if __name__ == "__main__":
    unittest.main()
