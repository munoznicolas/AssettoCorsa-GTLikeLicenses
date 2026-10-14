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

ERR_MISSING_TRACK_OR_CAR = "Missing track_id or car_id"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.web_ui.catalog_manager import (
    calculate_test_initial_speed,
    calculate_test_targets_and_physics,
    generate_and_validate,
    get_ac_curriculum_reference_tests,
    get_available_cars,
    get_available_tracks,
    get_missing_telemetry_summary,
    get_track_spline_data,
    load_curriculum,
    run_live_test,
    save_tier_catalog,
    enqueue_missing_telemetry_jobs,
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

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

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

    def _serve_file_from_base(
        self, path: str, prefix: str, base_dir: str, not_found_msg: str, default_mime: str = "application/octet-stream"
    ) -> None:
        rel_path = path[len(prefix):]
        full_path = os.path.join(base_dir, rel_path)
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
        else:
            self.send_error(404, f"Preview not found for test {test_id}")

    def _handle_get_curriculum(self, _query: Dict[str, list]) -> None:
        try:
            curriculum = load_curriculum()
            self.send_json_response({"success": True, "curriculum": curriculum})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_tracks(self, query: Dict[str, list]) -> None:
        try:
            kunos_only = query.get("all", ["0"])[0] != "1"
            tracks = get_available_tracks(kunos_only=kunos_only)
            self.send_json_response({"success": True, "tracks": tracks, "kunos_only": kunos_only})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_cars(self, query: Dict[str, list]) -> None:
        try:
            kunos_only = query.get("all", ["0"])[0] != "1"
            cars = get_available_cars(kunos_only=kunos_only)
            self.send_json_response({"success": True, "cars": cars, "kunos_only": kunos_only})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_reference_tests(self, _query: Dict[str, list]) -> None:
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
                "ac_count": len(ac_tests),
            })
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_spline(self, query: Dict[str, list]) -> None:
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

    def _handle_get_calculate_targets(self, query: Dict[str, list]) -> None:
        track_id = query.get("track_id", [""])[0]
        track_layout = query.get("track_layout", [""])[0] or query.get("layout", [""])[0]
        car_id = query.get("car_id", [""])[0]
        try:
            start_s = float(query.get("start_s", ["0.0"])[0])
            finish_s = float(query.get("finish_s", ["1.0"])[0])
        except ValueError:
            start_s, finish_s = 0.0, 1.0
        start_mode = query.get("start_mode", ["ROLLING"])[0]
        with_stop_box = query.get("with_stop_box", ["0"])[0].lower() in ("1", "true", "yes")

        if not track_id or not car_id:
            self.send_json_response({"success": False, "error": ERR_MISSING_TRACK_OR_CAR}, status=400)
            return

        try:
            res = calculate_test_targets_and_physics(
                track_id=track_id,
                track_layout=track_layout,
                car_id=car_id,
                start_s=start_s,
                finish_s=finish_s,
                start_mode=start_mode,
                with_stop_box=with_stop_box,
            )
            self.send_json_response(res)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_queue_status(self, _query: Dict[str, list]) -> None:
        try:
            from tools.web_ui.runner import queue_mgr
            self.send_json_response(queue_mgr.get_status())
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_telemetry_missing(self, query: Dict[str, list]) -> None:
        tier = query.get("tier", ["ALL"])[0]
        include_flying = query.get("include_flying", ["1"])[0].lower() in ("1", "true", "yes")
        try:
            res = get_missing_telemetry_summary(tier=tier, include_flying=include_flying)
            self.send_json_response(res)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_job(self, path: str) -> None:
        job_id = path[len("/api/job/"):]
        try:
            from tools.web_ui.runner import queue_mgr
            job = queue_mgr.get_job(job_id)
            if job:
                self.send_json_response({"success": True, "job": job.to_dict()})
            else:
                self.send_json_response({"success": False, "error": f"Job {job_id} not found"}, status=404)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_get_test_preview(self, query: Dict[str, list]) -> None:
        test_id = query.get("test_id", [""])[0]
        if not test_id:
            self.send_json_response({"success": False, "error": "Missing test_id"}, status=400)
            return
        self._serve_preview_image(test_id)

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
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except Exception as e:
            self.send_json_response({"success": False, "error": f"Invalid JSON payload: {e}"}, status=400)
            return None

    def _handle_post_calculate_targets(self, payload: Dict[str, Any]) -> None:
        track_id = payload.get("track_id", "")
        track_layout = payload.get("track_layout", "")
        car_id = payload.get("car_id", "")
        start_s = float(payload.get("start_s", 0.0))
        finish_s = float(payload.get("finish_s", 1.0))
        start_mode = payload.get("start_mode", "ROLLING")
        with_stop_box = bool(payload.get("with_stop_box", False))
        countdown_sec = float(payload.get("countdown_sec", 3.0))

        if not track_id or not car_id:
            self.send_json_response({"success": False, "error": ERR_MISSING_TRACK_OR_CAR}, status=400)
            return

        try:
            res = calculate_test_targets_and_physics(
                track_id=track_id,
                track_layout=track_layout,
                car_id=car_id,
                start_s=start_s,
                finish_s=finish_s,
                start_mode=start_mode,
                with_stop_box=with_stop_box,
                countdown_sec=countdown_sec,
            )
            self.send_json_response(res)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_calculate_initial_speed(self, payload: Dict[str, Any]) -> None:
        track_id = payload.get("track_id", "")
        track_layout = payload.get("track_layout", "")
        car_id = payload.get("car_id", "")
        start_s = float(payload.get("start_s", 0.0))
        finish_s = float(payload.get("finish_s", 1.0))
        start_mode = payload.get("start_mode", "ROLLING")
        with_stop_box = bool(payload.get("with_stop_box", False))
        countdown_sec = float(payload.get("countdown_sec", 3.0))

        if not track_id or not car_id:
            self.send_json_response({"success": False, "error": ERR_MISSING_TRACK_OR_CAR}, status=400)
            return

        try:
            res = calculate_test_initial_speed(
                track_id=track_id,
                track_layout=track_layout,
                car_id=car_id,
                start_s=start_s,
                finish_s=finish_s,
                start_mode=start_mode,
                with_stop_box=with_stop_box,
                countdown_sec=countdown_sec,
            )
            self.send_json_response(res)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_run_test(self, payload: Dict[str, Any]) -> None:
        test_id = payload.get("test_id", "")
        mode = payload.get("mode", "play")
        sync_first = bool(payload.get("sync_first", True))
        test_data = payload.get("test_data")
        timeout = int(payload.get("timeout", 8))

        if not test_id:
            self.send_json_response({"success": False, "error": "Missing test_id"}, status=400)
            return

        try:
            res = run_live_test(
                test_id=test_id,
                mode=mode,
                sync_first=sync_first,
                test_data=test_data,
                timeout=timeout,
            )
            self.send_json_response(res)
        except Exception as e:
            import traceback
            self.send_json_response({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }, status=500)

    def _handle_post_queue_cancel(self, payload: Dict[str, Any]) -> None:
        job_id = payload.get("job_id")
        cancel_all = bool(payload.get("cancel_all", False))
        try:
            from tools.web_ui.runner import queue_mgr
            if cancel_all or not job_id:
                queue_mgr.cancel_active()
                self.send_json_response({"success": True, "message": "Cancelled active Assetto Corsa session"})
            else:
                ok = queue_mgr.cancel_job(job_id)
                self.send_json_response({"success": ok, "message": f"Job {job_id} cancellation processed."})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_telemetry_queue_missing(self, payload: Dict[str, Any]) -> None:
        tier = payload.get("tier", "ALL")
        include_flying = bool(payload.get("include_flying", True))
        try:
            res = enqueue_missing_telemetry_jobs(tier=tier, include_flying=include_flying)
            self.send_json_response(res)
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_save_tier(self, payload: Dict[str, Any]) -> None:
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

    def _handle_post_generate(self, _payload: Dict[str, Any]) -> None:
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

    def _handle_post_sync(self, _payload: Dict[str, Any]) -> None:
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

    def do_POST(self) -> None:
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
