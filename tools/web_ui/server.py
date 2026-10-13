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
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.web_ui.catalog_manager import (
    generate_and_validate,
    get_ac_curriculum_reference_tests,
    get_available_cars,
    get_available_tracks,
    get_track_spline_data,
    load_curriculum,
    save_tier_catalog,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DesignerRequestHandler(SimpleHTTPRequestHandler):
    """Handles API REST requests and serves static web UI assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep terminal output clean
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def send_json_response(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # API Endpoints
        if path == "/api/curriculum":
            try:
                curriculum = load_curriculum()
                self.send_json_response({"success": True, "curriculum": curriculum})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/tracks":
            try:
                kunos_only = query.get("all", ["0"])[0] != "1"
                tracks = get_available_tracks(kunos_only=kunos_only)
                self.send_json_response({"success": True, "tracks": tracks, "kunos_only": kunos_only})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/cars":
            try:
                kunos_only = query.get("all", ["0"])[0] != "1"
                cars = get_available_cars(kunos_only=kunos_only)
                self.send_json_response({"success": True, "cars": cars, "kunos_only": kunos_only})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/reference_tests":
            try:
                json_path = os.path.join(REPO_ROOT, "docs", "Gran_Turismo_License_Tests.json")
                ref_tests = []
                if os.path.isfile(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        ref_tests = json.load(f)

                # Append live Assetto Corsa Mod tests
                ac_tests = get_ac_curriculum_reference_tests()
                combined_tests = ref_tests + ac_tests

                self.send_json_response({
                    "success": True,
                    "tests": combined_tests,
                    "count": len(combined_tests),
                    "gt_count": len(ref_tests),
                    "ac_count": len(ac_tests)
                })
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/spline":
            track_id = query.get("track_id", [""])[0]
            layout = query.get("layout", [""])[0]
            if not track_id:
                self.send_json_response({"success": False, "error": "Missing track_id parameter"}, status=400)
                return

            try:
                data = get_track_spline_data(track_id, layout)
                if data is None:
                    self.send_json_response({"success": False, "error": f"No AI spline found for track {track_id}"}, status=404)
                else:
                    self.send_json_response({"success": True, "spline": data})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/test_preview":
            test_id = query.get("test_id", [""])[0]
            if not test_id:
                self.send_json_response({"success": False, "error": "Missing test_id"}, status=400)
                return
            from tools.generate_test_previews import build_test_to_event_path_map
            preview_map = build_test_to_event_path_map()
            preview_file = preview_map.get(test_id)
            if preview_file and os.path.isfile(preview_file):
                with open(preview_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, f"Preview not found for test {test_id}")
                return

        # Backward compatibility for legacy /assets/previews/ paths
        if path.startswith("/assets/previews/tests/"):
            test_id = os.path.splitext(os.path.basename(path))[0]
            from tools.generate_test_previews import build_test_to_event_path_map
            preview_map = build_test_to_event_path_map()
            preview_file = preview_map.get(test_id)
            if preview_file and os.path.isfile(preview_file):
                with open(preview_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # Asset files (e.g. badge icons, fonts, textures)
        if path.startswith("/assets/"):
            rel_asset_path = path[len("/assets/"):]
            full_asset_path = os.path.join(ASSETS_DIR, rel_asset_path)
            if os.path.isfile(full_asset_path):
                mime, _ = mimetypes.guess_type(full_asset_path)
                with open(full_asset_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Asset Not Found")
                return

        # Content files (e.g. career event previews: /content/career/.../preview.png)
        if path.startswith("/content/"):
            rel_content_path = path[len("/content/"):]
            full_content_path = os.path.join(REPO_ROOT, "content", rel_content_path)
            if os.path.isfile(full_content_path):
                mime, _ = mimetypes.guess_type(full_content_path)
                with open(full_content_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Content Not Found")
                return

        # Document assets (e.g. SVG test maps)
        if path.startswith("/docs/"):
            rel_doc_path = path[len("/docs/"):]
            full_doc_path = os.path.join(REPO_ROOT, "docs", rel_doc_path)
            if os.path.isfile(full_doc_path):
                mime, _ = mimetypes.guess_type(full_doc_path)
                with open(full_doc_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "image/svg+xml")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Doc Not Found")
                return

        # Default static file handler (index.html, style.css, app.js)
        return super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                self.send_json_response({"success": False, "error": f"Invalid JSON payload: {e}"}, status=400)
                return

        if path == "/api/save_tier":
            tier_name = payload.get("tier_name")
            tests = payload.get("tests", [])
            if not tier_name:
                self.send_json_response({"success": False, "error": "Missing tier_name in request"}, status=400)
                return

            try:
                saved_path = save_tier_catalog(tier_name, tests)
                self.send_json_response({
                    "success": True,
                    "tier_name": tier_name,
                    "test_count": len(tests),
                    "file": os.path.relpath(saved_path, REPO_ROOT),
                })
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if path == "/api/generate":
            try:
                report = generate_and_validate()
                self.send_json_response(report)
            except Exception as e:
                import traceback
                self.send_json_response({
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }, status=500)
            return

        if path == "/api/sync":
            try:
                from tools.deployment.sync import build_sync_mappings, DEFAULT_AC_ROOT
                import shutil
                mappings = build_sync_mappings(REPO_ROOT, DEFAULT_AC_ROOT)
                copied = 0
                for src, dst in mappings:
                    if os.path.isfile(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        copied += 1
                self.send_json_response({
                    "success": True,
                    "message": f"Successfully synchronized {copied} files to {DEFAULT_AC_ROOT}",
                    "file_count": copied,
                })
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

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
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

