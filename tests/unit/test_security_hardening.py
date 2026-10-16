#!/usr/bin/env python3
"""
test_security_hardening.py
Unit tests verifying local security controls across the Web UI server,
path containment, identifier validation, INI injection prevention, and spline parser bounds.
"""

import os
import struct
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.spline.parser import SplineParser, find_spline_file
from tools.telemetry.recorder import profile_filename
from tools.testing.ac_launcher import generate_race_ini
from tools.web_ui.server import is_safe_identifier, is_safe_path_within


class TestSecurityHardening(unittest.TestCase):
    def test_identifier_allowlist(self) -> None:
        self.assertTrue(is_safe_identifier("B-1"))
        self.assertTrue(is_safe_identifier("ks_vallelunga"))
        self.assertTrue(is_safe_identifier("club_circuit", allow_empty=True))
        self.assertTrue(is_safe_identifier("", allow_empty=True))
        self.assertFalse(is_safe_identifier("", allow_empty=False))
        self.assertFalse(is_safe_identifier("../etc/passwd"))
        self.assertFalse(is_safe_identifier(r"..\..\Windows\System32"))
        self.assertFalse(is_safe_identifier("B-1; rm -rf /"))
        self.assertFalse(is_safe_identifier("track\n[INJECT]"))

    def test_canonical_path_containment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sub_file = os.path.join(tmpdir, "sub", "file.txt")
            outside_file = os.path.join(tmpdir, "..", "outside.txt")
            self.assertTrue(is_safe_path_within(tmpdir, sub_file))
            self.assertFalse(is_safe_path_within(tmpdir, outside_file))

    def test_profile_filename_rejects_traversal(self) -> None:
        fname = profile_filename("ks_vallelunga", "club_circuit", "ks_mazda_miata", 100)
        self.assertEqual(fname, "ks_vallelunga__club_circuit__ks_mazda_miata__ai100.json")
        with self.assertRaises(ValueError):
            profile_filename("../../../", "", "!!!", 100)

    def test_generate_race_ini_strips_crlf_injection(self) -> None:
        malicious_test = {
            "test_id": "B-1\r\n[MALICIOUS]\r\nPWNED=1",
            "car_id": "ks_mazda_miata\nINJECT=true",
            "track_id": "ks_vallelunga\r\nEVIL=1",
            "track_layout": "club_circuit\x00\nBAD=1",
        }
        ini_str = generate_race_ini(malicious_test)
        self.assertNotIn("\n[MALICIOUS]", ini_str)
        self.assertNotIn("\nPWNED=1", ini_str)
        self.assertNotIn("\r", ini_str)
        self.assertNotIn("\x00", ini_str)
        self.assertNotIn("\nINJECT=true", ini_str)
        self.assertNotIn("\nEVIL=1", ini_str)

    def test_find_spline_file_rejects_traversal(self) -> None:
        self.assertIsNone(find_spline_file("../../..", "layout"))
        self.assertIsNone(find_spline_file("ks_vallelunga", "../../.."))

    def test_spline_parser_rejects_excessive_waypoints(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ai", delete=False) as tf:
            # Header claiming 500,000 waypoints (> MAX_WAYPOINTS = 100,000)
            tf.write(struct.pack("<4i", 7, 500_000, 0, 0))
            temp_path = tf.name
        try:
            with self.assertRaises(ValueError):
                SplineParser(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
