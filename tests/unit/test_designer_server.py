#!/usr/bin/env python3
"""
test_designer_server.py
Unit tests verifying the Designer Web UI backend server API routing and catalog saving.
Ensures JSON responses are always returned (no HTML error leaks), preventing JSON parse syntax errors.
"""

import json
import re
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

    def test_get_queue_status_endpoint(self):
        status, data, raw = self._make_request("/api/queue/status")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("is_ac_running", data)
        self.assertIn("queue", data)
        self.assertIn("queue_length", data)

    def test_static_host_client_guards(self):
        static_js_dir = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "js")
        with open(os.path.join(static_js_dir, "api.js"), "r", encoding="utf-8") as f:
            api_js = f.read()
        with open(os.path.join(static_js_dir, "queue-runner.js"), "r", encoding="utf-8") as f:
            queue_runner_js = f.read()
        with open(os.path.join(REPO_ROOT, "tools", "web_ui", "static", "app.js"), "r", encoding="utf-8") as f:
            app_js = f.read()

        # Verify api.js guards getQueueStatus on static hosts
        self.assertIn("if (isStaticHost())", api_js)
        self.assertIn("async getQueueStatus()", api_js)

        # Verify queue-runner.js stops pollQueueStatus on static hosts
        self.assertIn("export async function pollQueueStatus()", queue_runner_js)
        self.assertIn("if (isStaticHost())", queue_runner_js)

        # Verify window focus & visibility listeners are conditioned on !isStaticHost()
        self.assertIn("if (!isStaticHost())", queue_runner_js)
        self.assertIn('window.addEventListener("focus", () => void pollQueueStatus());', queue_runner_js)

        # Verify app.js bootstraps pollQueueStatus only when !isStaticHost()
        self.assertIn("if (!isStaticHost())", app_js)
        self.assertIn("pollQueueStatus();", app_js)



    def test_tour_titles_no_emojis(self):
        tour_js_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "js", "tour.js")
        with open(tour_js_path, "r", encoding="utf-8") as f:
            tour_js = f.read()

        # Find all title properties inside popovers
        title_matches = re.findall(r'title:\s*([^\r\n,]+)', tour_js)
        self.assertGreater(len(title_matches), 0)

        # Emoji detection regex for astral symbols and common emoji code points
        emoji_pattern = re.compile(r'[𐀀-􏿿☀-⛿✀-➿⌀-⏿]')
        for raw_title in title_matches:
            self.assertFalse(
                emoji_pattern.search(raw_title),
                f"Tour title contains emoji: {raw_title}"
            )

        # Verify done button has no emoji
        done_matches = re.findall(r'doneBtnText:\s*"([^"]+)"', tour_js)
        for done_text in done_matches:
            self.assertFalse(
                emoji_pattern.search(done_text),
                f"Done button text contains emoji: {done_text}"
            )

        # Verify tour steps dynamically adapt to static vs local host
        self.assertIn('isStaticHost() ? "Save & Export" : "Save, Test Drive & Sync"', tour_js)
        self.assertIn('isStaticHost() ? "#btn-open-submit-pr-modal" : "#btn-sync"', tour_js)

    def test_dynamic_host_button_visibility(self):
        app_js_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()
        qr_js_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "js", "queue-runner.js")
        with open(qr_js_path, "r", encoding="utf-8") as f:
            qr_js = f.read()

        # Verify applyHostVisibility adjusts button visibility dynamically
        self.assertIn("export function applyHostVisibility()", app_js)
        self.assertIn('dom.btnSync.style.display = isStatic ? "none" : ""', app_js)
        self.assertIn('dom.btnRunLive.style.display = isStatic ? "none" : ""', app_js)
        self.assertIn('dom.btnRunMissingTelemetry.style.display = isStatic ? "none" : ""', app_js)
        self.assertIn('dom.btnOpenSubmitPrModal.style.display = isStatic ? "" : "none"', app_js)

        # Verify queue runner conditions btnRunMissingTelemetry listener on isStaticHost()
        self.assertIn("if (dom.btnRunMissingTelemetry)", qr_js)
        self.assertIn('dom.btnRunMissingTelemetry.style.display = "none"', qr_js)

    def test_mobile_unsupported_markup_and_early_detection(self):
        index_html_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "index.html")
        with open(index_html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Verify early mobile device detection script
        self.assertIn("device-mobile", html)
        self.assertIn("isMobile", html)

        # Verify mobile unsupported screen container and accessibility
        self.assertIn('id="mobile-unsupported-screen"', html)
        self.assertIn('class="mobile-unsupported-screen"', html)
        self.assertIn('role="region"', html)
        self.assertIn("Desktop Experience Required", html)
        self.assertIn("Mobile screens are not currently supported", html)

        # Verify interactive actions
        self.assertIn('id="btn-mobile-copy-url"', html)
        self.assertIn("Copy Link for PC", html)
        self.assertIn("View on GitHub", html)

    def test_mobile_unsupported_css_rules(self):
        style_css_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "style.css")
        with open(style_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # Default hidden on desktop
        self.assertIn(".mobile-unsupported-screen {", css)
        self.assertIn("display: none;", css)

        # Media query triggers for phone & small screen blocking
        self.assertIn("@media (max-width: 850px)", css)
        self.assertIn("100dvh", css)

        # Body / #app hidden on mobile viewport or device-mobile class
        self.assertIn("html.device-mobile #app", css)
        self.assertIn("html.device-mobile .mobile-unsupported-screen", css)

        # Light theme adaptation
        self.assertIn("@media (prefers-color-scheme: light)", css)

    def test_mobile_copy_button_integration(self):
        dom_js_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "js", "dom.js")
        with open(dom_js_path, "r", encoding="utf-8") as f:
            dom_js = f.read()
        app_js_path = os.path.join(REPO_ROOT, "tools", "web_ui", "static", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()

        self.assertIn("dom.btnMobileCopyUrl", dom_js)
        self.assertIn("dom.btnMobileCopyText", dom_js)
        self.assertIn("if (dom.btnMobileCopyUrl)", app_js)
        self.assertIn("clipboard.writeText", app_js)


if __name__ == "__main__":
    unittest.main()
