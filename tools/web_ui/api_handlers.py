"""
api_handlers.py
REST API route handlers (GET and POST) for the Assetto Corsa GT-Like License Test Designer Web UI.
"""

import json
import os
import re
import shutil
import sys
import traceback
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

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

ERR_MISSING_TRACK_OR_CAR = "Missing track_id or car_id"
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def is_safe_identifier(val: Any, allow_empty: bool = False) -> bool:
    if not isinstance(val, str):
        return False
    if val == "":
        return allow_empty
    return len(val) <= 128 and bool(SAFE_ID_RE.match(val))


def is_safe_path_within(base_dir: str, target_path: str) -> bool:
    try:
        real_base = os.path.realpath(base_dir)
        real_target = os.path.realpath(target_path)
        return os.path.commonpath([real_base, real_target]) == real_base
    except ValueError:
        return False


class DesignerAPIMixin:
    """Mixin providing GET and POST API endpoint handlers for DesignerRequestHandler."""

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
        if not is_safe_identifier(track_id) or not is_safe_identifier(layout, allow_empty=True):
            self.send_json_response({"success": False, "error": "Invalid track_id or layout format"}, status=400)
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
        if (
            not is_safe_identifier(track_id)
            or not is_safe_identifier(car_id)
            or not is_safe_identifier(track_layout, allow_empty=True)
        ):
            self.send_json_response({"success": False, "error": "Invalid identifier format"}, status=400)
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
        if not is_safe_identifier(job_id):
            self.send_json_response({"success": False, "error": "Invalid job_id format"}, status=400)
            return
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
        if not is_safe_identifier(test_id):
            self.send_json_response({"success": False, "error": "Invalid test_id format"}, status=400)
            return
        self._serve_preview_image(test_id)

    def _handle_post_calculate_targets(self, payload: Dict[str, Any]) -> None:
        track_id = payload.get("track_id", "")
        track_layout = payload.get("track_layout", "")
        car_id = payload.get("car_id", "")
        start_s = float(payload.get("start_s", 0.0))
        finish_s = float(payload.get("finish_s", 1.0))
        start_mode = payload.get("start_mode", "ROLLING")
        with_stop_box = bool(payload.get("with_stop_box", False))
        countdown_sec = max(0.5, min(15.0, float(payload.get("countdown_sec", 3.0))))

        if not track_id or not car_id:
            self.send_json_response({"success": False, "error": ERR_MISSING_TRACK_OR_CAR}, status=400)
            return
        if (
            not is_safe_identifier(track_id)
            or not is_safe_identifier(car_id)
            or not is_safe_identifier(track_layout, allow_empty=True)
        ):
            self.send_json_response({"success": False, "error": "Invalid identifier format"}, status=400)
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
        countdown_sec = max(0.5, min(15.0, float(payload.get("countdown_sec", 3.0))))

        if not track_id or not car_id:
            self.send_json_response({"success": False, "error": ERR_MISSING_TRACK_OR_CAR}, status=400)
            return
        if (
            not is_safe_identifier(track_id)
            or not is_safe_identifier(car_id)
            or not is_safe_identifier(track_layout, allow_empty=True)
        ):
            self.send_json_response({"success": False, "error": "Invalid identifier format"}, status=400)
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
        timeout = max(1, min(120, int(payload.get("timeout", 8))))

        if not test_id:
            self.send_json_response({"success": False, "error": "Missing test_id"}, status=400)
            return
        if not is_safe_identifier(test_id):
            self.send_json_response({"success": False, "error": "Invalid test_id format"}, status=400)
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
            sys.stderr.write(f"[ERROR] /api/run_test failed:\n{traceback.format_exc()}\n")
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_queue_cancel(self, payload: Dict[str, Any]) -> None:
        job_id = payload.get("job_id")
        cancel_all = bool(payload.get("cancel_all", False))
        if job_id is not None and not is_safe_identifier(str(job_id)):
            self.send_json_response({"success": False, "error": "Invalid job_id format"}, status=400)
            return
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

    def _handle_post_generate_miniature(self, payload: Dict[str, Any]) -> None:
        test_id = payload.get("test_id", "")
        test_data = payload.get("test_data")
        if not test_id:
            self.send_json_response({"success": False, "error": "Missing test_id"}, status=400)
            return
        if not is_safe_identifier(test_id):
            self.send_json_response({"success": False, "error": "Invalid test_id format"}, status=400)
            return

        try:
            res = build_test_miniature(test_id=test_id, test_data=test_data)
            self.send_json_response(res)
        except Exception as e:
            sys.stderr.write(f"[ERROR] /api/generate_miniature failed:\n{traceback.format_exc()}\n")
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_generate(self, _payload: Dict[str, Any]) -> None:
        try:
            report = generate_and_validate()
            self.send_json_response(report)
        except Exception as e:
            sys.stderr.write(f"[ERROR] /api/generate failed:\n{traceback.format_exc()}\n")
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def _handle_post_sync(self, _payload: Dict[str, Any]) -> None:
        try:
            from tools.deployment.sync import DEFAULT_AC_ROOT, build_sync_mappings
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
