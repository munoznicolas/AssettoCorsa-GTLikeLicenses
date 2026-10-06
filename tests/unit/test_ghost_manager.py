#!/usr/bin/env python3
"""
Unit and integration tests for the Gold Ghost / Pace Car trajectory generator
and runtime data contracts.
"""

import os
import sys
import unittest

UNIT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(UNIT_DIR))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)
sys.path.insert(0, REPO_ROOT)

from generate_ghost_trajectory import (
    compute_curvature_radius,
    generate_ghost_profile,
)


class TestGhostTrajectoryGenerator(unittest.TestCase):
    """Tests the physics velocity profile and trajectory generation."""

    def test_collinear_curvature(self):
        """Points along a straight line should return a large radius (near 10000m)."""
        p0 = (0.0, 0.0, 0.0)
        p1 = (10.0, 0.0, 0.0)
        p2 = (20.0, 0.0, 0.0)
        r = compute_curvature_radius(p0, p1, p2)
        self.assertGreaterEqual(r, 9000.0)

    def test_curved_radius(self):
        """A curved path should yield a finite radius."""
        p0 = (0.0, 0.0, 0.0)
        p1 = (10.0, 0.0, 5.0)
        p2 = (15.0, 0.0, 15.0)
        r = compute_curvature_radius(p0, p1, p2)
        self.assertGreater(r, 5.0)
        self.assertLess(r, 500.0)

    def test_trajectory_normalization(self):
        """Generated trajectory must finish at exactly T_gold seconds."""
        b1_path = os.path.join(REPO_ROOT, "content", "tests", "national_b", "test_b01.json")
        profile = generate_ghost_profile(b1_path)

        self.assertEqual(profile["test_id"], "B-1")
        self.assertEqual(profile["gold_time"], 11.2)
        samples = profile["trajectory"]
        self.assertGreater(len(samples), 10)

        # First sample t=0.0
        self.assertAlmostEqual(samples[0]["t"], 0.0, places=2)
        # Last sample t=11.2
        self.assertAlmostEqual(samples[-1]["t"], 11.2, places=2)

        # Check velocities are bounded and physical
        for s in samples:
            self.assertGreaterEqual(s["speed_kmh"], 0.0)
            self.assertLessEqual(s["speed_kmh"], 300.0)
            self.assertEqual(len(s["pos"]), 3)
            self.assertEqual(len(s["heading"]), 3)

    def test_all_58_ghost_files_exist(self):
        """Ensure all 58 license tests have a corresponding ghost trajectory file."""
        tests_dir = os.path.join(REPO_ROOT, "content", "tests")
        tiers = ["national_b", "national_a", "international_b", "international_a", "super_license"]

        total_tests = 0
        total_ghosts = 0

        for tier in tiers:
            tdir = os.path.join(tests_dir, tier)
            self.assertTrue(os.path.isdir(tdir), f"Tier dir not found: {tdir}")
            test_files = [f for f in os.listdir(tdir) if f.startswith("test_") and f.endswith(".json")]
            for tf in test_files:
                total_tests += 1
                ghost_name = f"ghost_{tf}"
                ghost_path = os.path.join(tdir, ghost_name)
                self.assertTrue(
                    os.path.isfile(ghost_path),
                    f"Missing ghost file: {ghost_path} for test {tf}"
                )
                total_ghosts += 1

        self.assertEqual(total_tests, 58)
        self.assertEqual(total_ghosts, 58)


if __name__ == "__main__":
    unittest.main()

