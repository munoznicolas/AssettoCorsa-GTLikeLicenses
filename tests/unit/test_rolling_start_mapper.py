#!/usr/bin/env python3
"""
test_rolling_start_mapper.py
Unit and integration tests for TrackStraightAnalyzer & rolling_start_mapper.
"""

import json
import math
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)
from track_straight_analyzer import (
    RollingStartCandidate,
    StraightSegment,
    TrackStraightAnalyzer,
    angle_diff_deg,
    compass_heading_to_label,
)


class TestTrackStraightAnalyzer(unittest.TestCase):
    """Tests kinematic calculations and straight segment extraction."""

    def test_compass_heading_labels(self):
        self.assertEqual(compass_heading_to_label(0.0), "N")
        self.assertEqual(compass_heading_to_label(90.0), "E")
        self.assertEqual(compass_heading_to_label(180.0), "S")
        self.assertEqual(compass_heading_to_label(270.0), "W")
        self.assertEqual(compass_heading_to_label(45.0), "NE")
        self.assertEqual(compass_heading_to_label(360.0), "N")

    def test_angle_diff_deg(self):
        self.assertAlmostEqual(angle_diff_deg(10.0, 20.0), 10.0)
        self.assertAlmostEqual(angle_diff_deg(355.0, 5.0), 10.0)
        self.assertAlmostEqual(angle_diff_deg(5.0, 355.0), 10.0)
        self.assertAlmostEqual(angle_diff_deg(180.0, 180.0), 0.0)

    def test_steering_kinematics(self):
        # Wheelbase = 2.5m, steer ratio = 14.5
        # delta_road = arctan(2.5 / R)
        # delta_wheel = delta_road * 14.5 * (180 / pi)
        class DummyParser:
            total_length = 1000.0
            waypoints = []

        analyzer = TrackStraightAnalyzer(DummyParser(), wheelbase_m=2.5, steer_ratio=14.5)

        # R = 10,000m -> ~0.21 deg
        st_10k = analyzer.compute_steering_angle_deg(10000.0)
        self.assertAlmostEqual(st_10k, 0.20769, places=3)

        # R = 2,000m -> ~1.04 deg
        st_2k = analyzer.compute_steering_angle_deg(2000.0)
        self.assertAlmostEqual(st_2k, 1.0384, places=3)

        # R = 1,000m -> ~2.08 deg
        st_1k = analyzer.compute_steering_angle_deg(1000.0)
        self.assertAlmostEqual(st_1k, 2.0768, places=3)

        # R <= 0 -> 0.0 deg
        self.assertEqual(analyzer.compute_steering_angle_deg(0.0), 0.0)

    def test_vallelunga_club_straights(self):
        spline_path = find_spline_file("ks_vallelunga", "club_circuit")
        if not spline_path or not os.path.isfile(spline_path):
            self.skipTest("Vallelunga club_circuit spline not found in AC install.")

        parser = SplineParser(spline_path)
        analyzer = TrackStraightAnalyzer(parser, track_id="ks_vallelunga", layout="club_circuit")

        straights = analyzer.find_straight_segments(
            max_steer_deg=2.0,
            min_length_m=60.0,
        )

        # Must find at least 2 distinct straights (Main Straight and Back Straight)
        self.assertGreaterEqual(len(straights), 2)

        # The longest straight must wrap across the lap finish line (Pit Straight)
        longest = straights[0]
        self.assertTrue(longest.wraps_lap)
        self.assertGreater(longest.length_m, 300.0)
        self.assertLess(longest.max_steer_deg, 2.0)

        # Evaluate rolling candidates (at 70 km/h, 3s countdown = 58.3m, 1.5s post-GO straight)
        candidates = analyzer.evaluate_rolling_candidates(
            straights,
            target_speed_kmh=70.0,
            countdown_sec=3.0,
            post_go_sec=1.5,
        )

        self.assertGreaterEqual(len(candidates), 2)
        top = candidates[0]
        self.assertEqual(top.rank, 1)
        self.assertEqual(top.post_go_sec, 1.5)
        self.assertAlmostEqual(top.post_go_margin_m, 29.2, places=1)
        self.assertGreater(top.score, 75.0)
        self.assertAlmostEqual(top.spawn_offset_m, 58.3, places=1)
        self.assertIn("start_s", top.test_config_snippet)
        self.assertIn("spawn_offset", top.test_config_snippet)

    def test_monza_straights(self):
        spline_path = find_spline_file("monza", "")
        if not spline_path or not os.path.isfile(spline_path):
            self.skipTest("Monza spline not found in AC install.")

        parser = SplineParser(spline_path)
        analyzer = TrackStraightAnalyzer(parser, track_id="monza", layout="")

        straights = analyzer.find_straight_segments(
            max_steer_deg=2.0,
            min_length_m=100.0,
        )

        # Monza is famous for high-speed straights (Rettifilo, Curva Grande exit, Serraglio)
        self.assertGreaterEqual(len(straights), 3)

        # At least one straight exceeds 500 meters
        has_mega_straight = any(s.length_m > 500.0 for s in straights)
        self.assertTrue(has_mega_straight)

    def test_magione_straights(self):
        spline_path = find_spline_file("magione", "")
        if not spline_path or not os.path.isfile(spline_path):
            self.skipTest("Magione spline not found in AC install.")

        parser = SplineParser(spline_path)
        analyzer = TrackStraightAnalyzer(parser, track_id="magione", layout="")

        straights = analyzer.find_straight_segments(
            max_steer_deg=2.0,
            min_length_m=60.0,
        )

        self.assertGreaterEqual(len(straights), 2)
        # Magione has a ~600m back straight
        has_long_straight = any(s.length_m > 400.0 for s in straights)
        self.assertTrue(has_long_straight)

    def test_drag_strip_handling(self):
        spline_path = find_spline_file("ks_drag", "drag200")
        if not spline_path or not os.path.isfile(spline_path):
            self.skipTest("ks_drag spline not found in AC install.")

        parser = SplineParser(spline_path)
        analyzer = TrackStraightAnalyzer(parser, track_id="ks_drag", layout="drag200")

        straights = analyzer.find_straight_segments(
            max_steer_deg=3.5,
            min_length_m=100.0,
        )

    def test_proficient_ai_telemetry_integration(self):
        spline_path = find_spline_file("ks_vallelunga", "club_circuit")
        if not spline_path or not os.path.isfile(spline_path):
            self.skipTest("Vallelunga club_circuit spline not found in AC install.")

        parser = SplineParser(spline_path)
        analyzer = TrackStraightAnalyzer(parser, track_id="ks_vallelunga", layout="club_circuit", car_id="ks_mazda_miata")

        # Ensure telemetry profile is loaded
        self.assertEqual(analyzer.telemetry.ai_level, 95)
        self.assertGreater(len(analyzer.telemetry.samples), 50)

        straights = analyzer.find_straight_segments(max_steer_deg=2.0, min_length_m=60.0)
        # Evaluate without speed override (natural 95% AI speed)
        candidates = analyzer.evaluate_rolling_candidates(
            straights,
            countdown_sec=3.0,
            post_go_sec=1.5,
        )

        self.assertGreaterEqual(len(candidates), 1)
        top = candidates[0]
        # Target rolling speed must be grounded in AI velocity
        self.assertGreater(top.target_speed_kmh, 150.0)
        self.assertGreater(top.spawn_speed_kmh, 100.0)
        self.assertGreaterEqual(top.engaged_gear, 3)
        self.assertGreaterEqual(top.engine_rpm, 3000)
        self.assertEqual(top.test_config_snippet["gear"], top.engaged_gear)
        self.assertEqual(top.test_config_snippet["rpm"], top.engine_rpm)
        self.assertEqual(top.test_config_snippet["speed"], top.target_speed_kmh)


if __name__ == "__main__":
    unittest.main()

