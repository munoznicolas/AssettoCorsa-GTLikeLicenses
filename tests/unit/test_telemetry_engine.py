#!/usr/bin/env python3
"""
test_telemetry_engine.py
Unit tests verifying the client-side TelemetryEngine and data/curriculum.json integrity.
Asserts mathematical calculation parity between Python and JavaScript calculations.
"""

import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.telemetry.recorder import get_or_calculate_targets


class TestTelemetryEngineParity(unittest.TestCase):
    def test_curriculum_json_exists_and_valid(self):
        cur_file = os.path.join(REPO_ROOT, "data", "curriculum.json")
        self.assertTrue(os.path.isfile(cur_file), "data/curriculum.json must exist")
        with open(cur_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)
        for tier in data:
            self.assertIn("tier_name", tier)
            self.assertIn("tests", tier)
            self.assertGreater(len(tier["tests"]), 0)

    def test_telemetry_engine_node_parity(self):
        """Verifies JS TelemetryEngine produces matching values to Python get_or_calculate_targets."""
        # Run Python calculation
        py_res = get_or_calculate_targets(
            track_id="magione",
            layout="",
            car_id="ks_toyota_gt86",
            start_s=0.1,
            finish_s=0.3,
            start_mode="ROLLING",
            with_stop_box=False,
            countdown_sec=3.0,
            allow_live_engine=False,
        )

        # Run Node.js TelemetryEngine calculation
        node_script = """
import fs from 'fs';
import path from 'path';
import { TelemetryEngine } from './tools/web_ui/static/js/telemetry-engine.js';

const profile = JSON.parse(fs.readFileSync('data/telemetry_profiles/magione__ks_toyota_gt86__ai100.json', 'utf-8'));
const engine = new TelemetryEngine(profile);
const physics = engine.calculateGatePhysics(0.1, 3.0);
const targets = engine.calculateSectorTargets(0.1, 0.3, 'ROLLING', false);

console.log(JSON.stringify({ physics, targets }));
"""
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Node.js script failed: {proc.stderr}")
        js_res = json.loads(proc.stdout)

        # Compare target times
        self.assertEqual(js_res["targets"]["gold_seconds"], py_res["targets"]["gold_seconds"])
        self.assertEqual(js_res["targets"]["silver_seconds"], py_res["targets"]["silver_seconds"])
        self.assertEqual(js_res["targets"]["bronze_seconds"], py_res["targets"]["bronze_seconds"])

        # Compare physics
        self.assertEqual(js_res["physics"]["speed_kmh"], py_res["physics"]["speed_kmh"])
        self.assertEqual(js_res["physics"]["spawn_offset_m"], py_res["physics"]["spawn_offset_m"])
        self.assertEqual(js_res["physics"]["gear"], py_res["physics"]["gear"])


if __name__ == "__main__":
    unittest.main()
