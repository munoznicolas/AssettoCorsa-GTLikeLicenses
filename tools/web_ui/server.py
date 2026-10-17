#!/usr/bin/env python3
"""
server.py
Lightweight HTTP Web Server for the Assetto Corsa GT-Like License Test Designer.
Uses Python standard library (http.server) - no external web frameworks required.

Usage:
  python tools/web_ui/server.py [--port 8080] [--no-browser]
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.web_ui.api_handlers import (
    DesignerAPIMixin,
    ERR_MISSING_TRACK_OR_CAR,
    SAFE_ID_RE,
    is_safe_identifier,
    is_safe_path_within,
)
from tools.web_ui.catalog_manager import (
    build_test_miniature,
    calculate_test_initial_speed,
    calculate_test_targets_and_physics,
    enqueue_missing_telemetry_jobs,
    generate_and_validate,
    get_ac_curriculum_reference_tests,
    get_available_cars,
    get_available_tracks,
    get_missing_telemetry_summary,
    get_track_spline_data,
    load_curriculum,
    run_live_test,
    save_tier_catalog,
)

MAX_JSON_PAYLOAD_BYTES = 2 * 1024 * 1024  # 2 MB max payload
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DesignerRequestHandler(DesignerAPIMixin, SimpleHTTPRequestHandler):
    """Handles API REST requests and serves static web UI assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine queue status polling noise from console logs
        msg = format % args
        if "/api/queue/status" in msg and " 200 " in msg:
            return
        sys.stdout.write(f"[{self.log_date_time_string()}] {msg}\n")

    def _is_trusted_origin(self, origin: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(origin)
            return parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() in ALLOWED_HOSTS
        except Exception:
            return False

    def _validate_request_security(self, is_post: bool = False) -> bool:
        # 1. Host header check against DNS rebinding
        host_header = self.headers.get("Host", "")
        if host_header:
            host_only = host_header.split(":")[0].strip().lower()
            if host_only not in ALLOWED_HOSTS:
                self.send_json_response({"success": False, "error": "Forbidden: Untrusted Host header"}, status=403)
                return False

        # 2. Origin header check against Cross-Origin / CSRF requests
        origin = self.headers.get("Origin")
        if origin and not self._is_trusted_origin(origin):
            self.send_json_response({"success": False, "error": "Forbidden: Cross-origin request denied"}, status=403)
            return False

        # 3. Sec-Fetch-Site check for modern browsers
        sec_fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        if sec_fetch_site and sec_fetch_site not in ("same-origin", "none"):
            self.send_json_response({"success": False, "error": "Forbidden: Cross-site request denied"}, status=403)
            return False

        # 4. Require application/json on POST requests to enforce CORS preflight
        if is_post:
            ctype = self.headers.get("Content-Type", "").lower()
            if not ctype.startswith("application/json"):
                self.send_json_response(
                    {"success": False, "error": "Unsupported Media Type: Expected application/json"},
                    status=415,
                )
                return False

        return True

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def send_json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self.headers.get("Origin")
        if origin and self._is_trusted_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if origin and not self._is_trusted_origin(origin):
            self.send_error(403, "Forbidden: Cross-origin preflight denied")
            return
        self.send_response(204)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_file_from_base(
        self, path: str, prefix: str, base_dir: str, not_found_msg: str, default_mime: str = "application/octet-stream"
    ) -> None:
        raw_rel = urllib.parse.unquote(path[len(prefix):]).lstrip("/\\")
        full_path = os.path.realpath(os.path.join(base_dir, raw_rel))
        if not is_safe_path_within(base_dir, full_path):
            self.send_error(403, "Forbidden: Path traversal rejected")
            return
        if os.path.isfile(full_path):
            mime, _ = mimetypes.guess_type(full_path)
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime or default_mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404, not_found_msg)

    def _serve_preview_image(self, test_id: str) -> None:
        if not is_safe_identifier(test_id):
            self.send_error(400, "Invalid test_id format")
            return
        from tools.generate_test_previews import build_test_to_event_path_map, get_preview_path_for_test
        preview_map = build_test_to_event_path_map()
        preview_file = preview_map.get(test_id) or get_preview_path_for_test(test_id)
        if preview_file and is_safe_path_within(REPO_ROOT, preview_file) and os.path.isfile(preview_file):
            with open(preview_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, f"Preview not found for test {test_id}")

    def _dispatch_get_prefix(self, path: str) -> bool:
        if path.startswith("/api/job/"):
            self._handle_get_job(path)
            return True
        if path.startswith("/assets/previews/tests/"):
            test_id = os.path.splitext(os.path.basename(path))[0]
            self._serve_preview_image(test_id)
            return True
        if path.startswith("/assets/"):
            self._serve_file_from_base(path, "/assets/", ASSETS_DIR, "Asset Not Found")
            return True
        if path.startswith("/content/"):
            self._serve_file_from_base(path, "/content/", os.path.join(REPO_ROOT, "content"), "Content Not Found")
            return True
        if path.startswith("/docs/"):
            self._serve_file_from_base(
                path, "/docs/", os.path.join(REPO_ROOT, "docs"), "Doc Not Found", default_mime="image/svg+xml"
            )
            return True
        return False

    def do_GET(self) -> None:
        if not self._validate_request_security(is_post=False):
            return

        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        routes = {
            "/api/curriculum": self._handle_get_curriculum,
            "/api/tracks": self._handle_get_tracks,
            "/api/cars": self._handle_get_cars,
            "/api/reference_tests": self._handle_get_reference_tests,
            "/api/spline": self._handle_get_spline,
            "/api/calculate_targets": self._handle_get_calculate_targets,
            "/api/queue/status": self._handle_get_queue_status,
            "/api/telemetry/missing": self._handle_get_telemetry_missing,
            "/api/test_preview": self._handle_get_test_preview,
        }

        handler = routes.get(path)
        if handler:
            handler(query)
            return

        if self._dispatch_get_prefix(path):
            return

        super().do_GET()

    def _read_json_payload(self) -> Optional[Dict[str, Any]]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_json_response({"success": False, "error": "Invalid Content-Length header"}, status=400)
            return None

        if content_length < 0 or content_length > MAX_JSON_PAYLOAD_BYTES:
            self.send_json_response(
                {"success": False, "error": f"Payload too large (max {MAX_JSON_PAYLOAD_BYTES} bytes)"},
                status=413,
            )
            return None

        body = self.rfile.read(content_length) if content_length > 0 else b""
        if not body:
            return {}
        try:
            parsed = json.loads(body.decode("utf-8"))
            if not isinstance(parsed, dict):
                self.send_json_response({"success": False, "error": "Expected JSON object payload"}, status=400)
                return None
            return parsed
        except Exception as e:
            self.send_json_response({"success": False, "error": f"Invalid JSON payload: {e}"}, status=400)
            return None

    def do_POST(self) -> None:
        if not self._validate_request_security(is_post=True):
            return

        payload = self._read_json_payload()
        if payload is None:
            return

        path = urllib.parse.urlparse(self.path).path
        routes = {
            "/api/calculate_targets": self._handle_post_calculate_targets,
            "/api/calculate_initial_speed": self._handle_post_calculate_initial_speed,
            "/api/run_test": self._handle_post_run_test,
            "/api/queue/cancel": self._handle_post_queue_cancel,
            "/api/telemetry/queue_missing": self._handle_post_telemetry_queue_missing,
            "/api/save_tier": self._handle_post_save_tier,
            "/api/generate_miniature": self._handle_post_generate_miniature,
            "/api/generate": self._handle_post_generate,
            "/api/sync": self._handle_post_sync,
        }

        handler = routes.get(path)
        if handler:
            handler(payload)
        else:
            self.send_error(404, "Unknown API Route")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assetto Corsa GT License Test Designer Web UI")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind server (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser")
    args = parser.parse_args()

    port = args.port
    # Find next open port if 8080 is in use
    server = None
    for p in range(port, port + 10):
        try:
            server = ThreadedHTTPServer(("127.0.0.1", p), DesignerRequestHandler)
            port = p
            break
        except OSError:
            continue

    if not server:
        print(f"[ERROR] Could not bind server to ports {args.port}-{args.port + 9}", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{port}/"
    print("=" * 70)
    print(" ASSETTO CORSA GT-LIKE LICENSE TEST DESIGNER - LOCAL WEB SERVER")
    print("=" * 70)
    print(f" Web UI Running at: {url}")
    print(" Press Ctrl+C in terminal to stop.")
    print("=" * 70)

    if not args.no_browser:
        webbrowser.open(url)

    try:
        # Local development HTTP server (offline desktop tool for Assetto Corsa)
        server.serve_forever()  # NOSONAR
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
