#!/usr/bin/env python3
"""
test_designer_server.py
Unit tests verifying the Designer Web UI backend server API routing and catalog saving.
Ensures JSON responses are always returned (no HTML error leaks), preventing JSON parse syntax errors.
"""

import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.web_ui.catalog_manager import (
    load_curriculum,
    save_tier_catalog,
    get_catalog_module_path,
)
from tools.web_ui.server import ThreadedHTTPServer, DesignerRequestHandler


class TestDesignerServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), DesignerRequestHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _make_request(
        self, path: str, method: str = "GET", data: Dict[str, Any] = None
    ) -> tuple[int, Dict[str, Any], str]:
        url = f"http://127.0.0.1:{self.port}{path}"
        headers = {"Host": f"127.0.0.1:{self.port}"}
        req_data = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            req_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw), raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {}
            return e.code, parsed, raw

    def test_unknown_get_api_route_returns_json_404(self):
        status, data, raw = self._make_request("/api/nonexistent_route")
        self.assertEqual(status, 404)
        self.assertFalse(data.get("success"))
        self.assertIn("Unknown API Route", data.get("error", ""))
        self.assertFalse(raw.strip().startswith("<"), "Response must be JSON, not HTML")

    def test_unknown_post_api_route_returns_json_404(self):
        status, data, raw = self._make_request("/api/unknown_post", method="POST", data={"foo": "bar"})
        self.assertEqual(status, 404)
        self.assertFalse(data.get("success"))
        self.assertIn("Unknown API Route", data.get("error", ""))
        self.assertFalse(raw.strip().startswith("<"), "Response must be JSON, not HTML")

    def test_save_tier_missing_name_returns_json_400(self):
        status, data, raw = self._make_request("/api/save_tier", method="POST", data={})
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertIn("Missing tier_name", data.get("error", ""))
        self.assertFalse(raw.strip().startswith("<"), "Response must be JSON, not HTML")

    def test_save_tier_unknown_tier_returns_json_500(self):
        status, data, raw = self._make_request(
            "/api/save_tier", method="POST", data={"tier_name": "Nonexistent Tier", "tests": []}
        )
        self.assertEqual(status, 500)
        self.assertFalse(data.get("success"))
        self.assertIn("Unknown tier", data.get("error", ""))
        self.assertFalse(raw.strip().startswith("<"), "Response must be JSON, not HTML")

    def test_save_tier_catalog_roundtrip(self):
        curriculum = load_curriculum()
        self.assertGreater(len(curriculum), 0)
        tier = curriculum[0]
        tier_name = tier["tier_name"]
        tests = tier["tests"]
        module_path = get_catalog_module_path(tier_name)
        with open(module_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        try:
            # Save original tests through catalog manager
            saved_file = save_tier_catalog(tier_name, tests)
            self.assertTrue(os.path.isfile(saved_file))
            with open(saved_file, "r", encoding="utf-8") as f:
                new_code = f.read()
            self.assertIn(f'TIER_NAME = "{tier_name}"', new_code)
            self.assertIn(tests[0]["test_id"], new_code)
        finally:
            with open(module_path, "w", encoding="utf-8") as f:
                f.write(original_code)


if __name__ == "__main__":
    unittest.main()
