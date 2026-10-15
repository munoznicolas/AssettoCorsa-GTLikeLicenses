#!/usr/bin/env python3
"""
runner.py
Central Assetto Corsa Execution Queue & Process Manager for the GT-Like Licenses Web UI.
Manages interactive play sessions, AI demo sessions, evaluation loops, and live telemetry recording.
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import TIER_FOLDER_MAP
from tools.telemetry.recorder import (
    DEFAULT_AC_ROOT,
    load_telemetry_profile,
    record_live_in_engine_telemetry,
    save_telemetry_profile,
)
from tools.testing.ac_launcher import (
    ALT_USER_DOCS_AC,
    LOG_TXT_PATH,
    RACE_INI_PATH,
    generate_race_ini,
)


def is_acs_process_active() -> bool:
    """Checks if acs.exe is actively running on the host system."""
    try:
        res = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "acs.exe" in res.stdout.lower()
    except Exception:
        return False


def terminate_all_acs_instances() -> None:
    """Forcefully terminates any orphan or running acs.exe processes."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "acs.exe", "/T"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        pass


def ensure_complete_test_data(
    test_data: Dict[str, Any],
    ac_root: str = DEFAULT_AC_ROOT,
    repo_root: str = REPO_ROOT,
) -> Dict[str, Any]:
    """
    Ensures test_data contains valid 3D coordinates (spawn.position, spawn.forward_vector)
    and timing gates. If missing or if spatial coordinates need calculation from the spline,
    synthesizes them using track AI spline (fast_lane.ai) or falls back to pre-generated JSON.
    """
    if not isinstance(test_data, dict):
        return test_data

    has_valid_pos = (
        isinstance(test_data.get("spawn"), dict)
        and isinstance(test_data["spawn"].get("position"), (list, tuple))
        and len(test_data["spawn"]["position"]) == 3
        and isinstance(test_data["spawn"].get("forward_vector"), (list, tuple))
        and len(test_data["spawn"]["forward_vector"]) == 3
    )
    has_timing = (
        isinstance(test_data.get("timing"), dict)
        and "start_gate" in test_data["timing"]
        and "finish_gate" in test_data["timing"]
    )

    if has_valid_pos and has_timing:
        return test_data

    test_id = test_data.get("test_id", "")
    track_id = test_data.get("track_id", "")
    layout = test_data.get("track_layout", "")

    # 1. Synthesize 3D spatial parameters from track AI spline
    try:
        from tools.extract_spline_coords import SplineParser, find_spline_file, generate_test_parameters

        spline_file = find_spline_file(track_id, layout, ac_root)
        if spline_file and os.path.isfile(spline_file):
            parser = SplineParser(spline_file)
            start_s = float(test_data.get("start_s", 0.0))
            finish_s = float(test_data.get("finish_s", 1.0))
            spawn_offset = float(test_data.get("spawn_offset", 0.0))
            speed = float(test_data.get("speed", 0.0))
            with_stop_box = bool(test_data.get("with_stop_box", False))
            gear = test_data.get("gear")
            if gear is None and isinstance(test_data.get("spawn"), dict):
                gear = test_data["spawn"].get("initial_gear") or test_data["spawn"].get("gear")
            rpm = test_data.get("rpm")
            if rpm is None and isinstance(test_data.get("spawn"), dict):
                rpm = test_data["spawn"].get("initial_rpm") or test_data["spawn"].get("rpm")

            geom = generate_test_parameters(
                parser=parser,
                start_progress=start_s,
                finish_progress=finish_s,
                spawn_offset_m=spawn_offset,
                initial_speed_kmh=speed,
                with_stop_box=with_stop_box,
                gear=int(gear) if gear is not None else None,
                rpm=int(rpm) if rpm is not None else None,
                gate_width=test_data.get("gate_width"),
                track_id=test_data.get("track_id"),
            )

            test_data["spawn"] = geom["spawn"]
            test_data["timing"] = geom["timing"]
            if "fail_rules" not in test_data:
                test_data["fail_rules"] = {
                    "max_wheels_off": 2,
                    "wall_collision_threshold_n": 1500,
                    "max_yaw_angle_deg": 90,
                    "stop_box_overshoot_fail": with_stop_box,
                }
            return test_data
    except Exception as e:
        print(f"[!] Note: spline synthesis for {test_id}: {e}")

    # 2. Fallback: load existing pre-generated test JSON from repository
    try:
        from tools.testing.eval_loop import find_test_file_by_id
        repo_file = find_test_file_by_id(test_id, repo_root)
        if repo_file and os.path.isfile(repo_file):
            with open(repo_file, "r", encoding="utf-8") as rf:
                saved = json.load(rf)
                if "spawn" in saved and not has_valid_pos:
                    spawn_dict = dict(saved["spawn"])
                    if "speed" in test_data:
                        spawn_dict["initial_speed_kmh"] = float(test_data["speed"])
                    if "gear" in test_data:
                        spawn_dict["gear"] = int(test_data["gear"])
                    if "rpm" in test_data:
                        spawn_dict["rpm"] = int(test_data["rpm"])
                    test_data["spawn"] = spawn_dict
                if "timing" in saved and not has_timing:
                    test_data["timing"] = saved["timing"]
                if "fail_rules" not in test_data and "fail_rules" in saved:
                    test_data["fail_rules"] = saved["fail_rules"]
    except Exception as e:
        print(f"[!] Note: repo test fallback for {test_id}: {e}")

    return test_data


@dataclass
class ACJob:
    id: str
    type: str  # "play", "ai", "eval", "record_telemetry"
    test_id: str
    title: str
    params: Dict[str, Any]
    status: str = "queued"  # "queued", "running", "completed", "failed", "cancelled"
    created_at: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    finish_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    log: Optional[str] = None
    proc: Optional[subprocess.Popen] = None
    stop_event: threading.Event = field(default_factory=threading.Event)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "test_id": self.test_id,
            "title": self.title,
            "params": self.params,
            "status": self.status,
            "created_at": self.created_at,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "result": self.result,
            "error": self.error,
            "log": self.log,
            "pid": self.proc.pid if self.proc and self.proc.poll() is None else None,
        }


class ACQueueManager:
    """
    Thread-safe FIFO execution queue and lifecycle orchestrator for Assetto Corsa runs.
    """

    def __init__(self, ac_root: str = DEFAULT_AC_ROOT):
        self.ac_root = ac_root
        self._queue: queue.Queue = queue.Queue()
        self._jobs: Dict[str, ACJob] = {}
        self._active_job: Optional[ACJob] = None
        self._recent_completed: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def enqueue_job(
        self,
        job_type: str,
        test_id: str,
        title: str,
        params: Dict[str, Any],
    ) -> ACJob:
        """Enqueues a new Assetto Corsa task."""
        job_id = str(uuid.uuid4())[:8]
        job = ACJob(
            id=job_id,
            type=job_type,
            test_id=test_id,
            title=title,
            params=params,
        )

        with self._lock:
            self._jobs[job_id] = job
            self._queue.put(job)

        return job

    def cancel_active(self) -> bool:
        """Cancels the currently running job and terminates Assetto Corsa."""
        with self._lock:
            active = self._active_job

        if active:
            active.stop_event.set()
            active.status = "cancelled"
            active.error = "Cancelled by user"
            if active.proc and active.proc.poll() is None:
                try:
                    active.proc.terminate()
                    active.proc.wait(timeout=2)
                except Exception:
                    try:
                        active.proc.kill()
                    except Exception:
                        pass
            terminate_all_acs_instances()
            return True
        else:
            terminate_all_acs_instances()
            return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a specific job by ID (active or queued)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status == "running":
                return self.cancel_active()

            if job.status == "queued":
                job.status = "cancelled"
                job.error = "Removed from queue by user"
                return True

        return False

    def get_job(self, job_id: str) -> Optional[ACJob]:
        """Retrieves a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_status(self) -> Dict[str, Any]:
        """Returns the live snapshot of queue and process execution."""
        with self._lock:
            active_info = self._active_job.to_dict() if self._active_job else None
            queued_jobs = [
                j.to_dict()
                for j in self._jobs.values()
                if j.status == "queued"
            ]
            recent = list(self._recent_completed[-8:])

        is_running = is_acs_process_active() or (self._active_job is not None)

        return {
            "success": True,
            "is_ac_running": is_running,
            "active_job": active_info,
            "queue": queued_jobs,
            "queue_length": len(queued_jobs),
            "recent_completed": recent,
        }

    def _worker_loop(self) -> None:
        """Dedicated background consumer that executes jobs one by one."""
        while True:
            job: ACJob = self._queue.get()
            try:
                if job.status == "cancelled":
                    self._queue.task_done()
                    continue

                with self._lock:
                    self._active_job = job
                job.status = "running"
                job.start_time = time.time()

                self._execute_job(job)

            except Exception as e:
                job.status = "failed"
                job.error = str(e)
            finally:
                job.finish_time = time.time()
                with self._lock:
                    self._active_job = None
                    self._recent_completed.append(job.to_dict())
                self._queue.task_done()

    def _stage_test_configuration(self, test_data: Dict[str, Any]) -> None:
        """
        Stages in-memory test configuration into Assetto Corsa's GT-License runtime paths
        without altering the repository's permanent catalog files.
        Ensures complete 3D spatial parameters (spawn.position, timing gates) are synthesized.
        """
        test_data = ensure_complete_test_data(test_data, self.ac_root, REPO_ROOT)

        gt_mode_base = os.path.join(self.ac_root, "extension", "lua", "new-modes", "gt-license")
        test_id = test_data.get("test_id", "")
        tier = test_data.get("tier", "National B")
        tier_folder = TIER_FOLDER_MAP.get(tier, "national_b")

        # Normalize test filename (e.g. B-1 -> test_b01.json)
        from tools.testing.eval_loop import find_test_file_by_id
        src_path = find_test_file_by_id(test_id, REPO_ROOT)
        filename = os.path.basename(src_path) if src_path else f"test_{test_id.lower().replace('-', '')}.json"

        # Targets in Assetto Corsa
        stage_targets = [
            os.path.join(gt_mode_base, "data", "tests", tier_folder, filename),
            os.path.join(gt_mode_base, "data", "active_test.json"),
            os.path.join(gt_mode_base, "active_test.json"),
        ]

        test_json_str = json.dumps(test_data, indent=2)
        for target in stage_targets:
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(test_json_str)
            except Exception as e:
                print(f"[!] Staging target note ({target}): {e}")

    def _sync_assets_if_needed(self) -> None:
        """Synchronizes latest repository Lua scripts and UI assets to AC installation."""
        try:
            from tools.deployment.sync import build_sync_mappings
            mappings = build_sync_mappings(REPO_ROOT, self.ac_root)
            for src, dst in mappings:
                if os.path.isfile(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
        except Exception as e:
            print(f"[!] Sync note prior to execution: {e}")

    def _execute_job(self, job: ACJob) -> None:
        """Dispatches execution according to job type."""
        job_type = job.type
        params = job.params

        if job_type == "record_telemetry":
            self._run_record_telemetry(job, params)
        elif job_type == "eval":
            self._run_eval(job, params)
        elif job_type in ("play", "ai"):
            self._run_interactive_session(job, params)
        else:
            job.status = "failed"
            job.error = f"Unknown job type: {job_type}"

    def _run_record_telemetry(self, job: ACJob, params: Dict[str, Any]) -> None:
        """Launches Assetto Corsa in the background to capture 100% AI flying lap telemetry."""
        track_id = params.get("track_id", "")
        track_layout = params.get("track_layout", "")
        car_id = params.get("car_id", "")
        start_s = float(params.get("start_s", 0.0))
        countdown_sec = float(params.get("countdown_sec", 3.0))
        ai_level = int(params.get("ai_level", 100))

        def proc_cb(proc: subprocess.Popen) -> None:
            job.proc = proc

        profile = record_live_in_engine_telemetry(
            track_id=track_id,
            layout=track_layout,
            car_id=car_id,
            ai_level=ai_level,
            ac_root=self.ac_root,
            timeout_sec=None,
            stop_event=job.stop_event,
            proc_callback=proc_cb,
        )

        if job.stop_event.is_set():
            job.status = "cancelled"
            job.error = "Cancelled by user"
            return

        saved_path = save_telemetry_profile(profile)
        physics = profile.calculate_gate_physics(start_s, countdown_sec)
        physics["profile_path"] = saved_path
        physics["success"] = True

        job.result = physics
        job.status = "completed"

    def _run_eval(self, job: ACJob, params: Dict[str, Any]) -> None:
        """Executes the automated 8s evaluation audit loop."""
        test_id = job.test_id
        timeout = int(params.get("timeout", 8))
        test_data = params.get("test_data")
        sync_first = bool(params.get("sync_first", True))

        if sync_first:
            self._sync_assets_if_needed()

        if test_data:
            self._stage_test_configuration(test_data)

        eval_script = os.path.join(REPO_ROOT, "tools", "test_and_eval_loop.py")
        cmd = [sys.executable, eval_script, "--test-id", test_id, "--timeout", str(timeout)]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        job.proc = proc

        try:
            stdout, stderr = proc.communicate(timeout=timeout + 15)
            log = stdout + ("\n" + stderr if stderr else "")
            job.log = log
            if proc.returncode == 0:
                job.status = "completed"
                job.result = {
                    "success": True,
                    "status": "PASSED",
                    "log": log,
                }
            else:
                job.status = "failed"
                job.error = "In-engine evaluation failed audit checks."
                job.result = {
                    "success": False,
                    "status": "FAILED",
                    "log": log,
                }
        except subprocess.TimeoutExpired:
            proc.kill()
            job.status = "failed"
            job.error = "Evaluation loop timed out."

    def _run_interactive_session(self, job: ACJob, params: Dict[str, Any]) -> None:
        """Spawns acs.exe for live play or AI autopilot demo and monitors process lifetime."""
        is_ai = (job.type == "ai")
        test_id = job.test_id
        test_data = params.get("test_data")
        sync_first = bool(params.get("sync_first", True))

        if sync_first:
            self._sync_assets_if_needed()

        if not test_data:
            from tools.testing.eval_loop import find_test_file_by_id
            t_path = find_test_file_by_id(test_id, REPO_ROOT)
            if t_path and os.path.isfile(t_path):
                with open(t_path, "r", encoding="utf-8") as f:
                    test_data = json.load(f)
            else:
                from tools.content.catalog import TESTS_BY_ID
                test_data = TESTS_BY_ID.get(test_id)

        if not test_data:
            job.status = "failed"
            job.error = f"Test configuration for {test_id} not found."
            return

        # Ensure complete 3D spatial parameters (spawn.position, timing gates)
        test_data = ensure_complete_test_data(test_data, self.ac_root, REPO_ROOT)

        # Stage active in-memory test configuration
        self._stage_test_configuration(test_data)

        race_ini_str = generate_race_ini(
            test_data,
            ac_root=self.ac_root,
            ai_level=95,
            ai_test_mode=is_ai,
        )

        target_race_paths = [
            RACE_INI_PATH,
            os.path.join(ALT_USER_DOCS_AC, "cfg", "race.ini"),
            os.path.join(self.ac_root, "cfg", "race.ini"),
        ]
        for rp in target_race_paths:
            try:
                os.makedirs(os.path.dirname(rp), exist_ok=True)
                with open(rp, "w", encoding="utf-8") as f:
                    f.write(race_ini_str)
            except Exception:
                pass

        for lp in [LOG_TXT_PATH, os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt")]:
            if os.path.isfile(lp):
                try:
                    os.remove(lp)
                except Exception:
                    pass

        acs_exe_path = os.path.join(self.ac_root, "acs.exe")
        if not os.path.isfile(acs_exe_path):
            job.status = "failed"
            job.error = f"Assetto Corsa executable not found at {acs_exe_path}"
            return

        proc = subprocess.Popen([acs_exe_path], cwd=self.ac_root)
        job.proc = proc

        # Monitor acs.exe process until completion or cancellation
        while proc.poll() is None:
            if job.stop_event.is_set():
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                job.status = "cancelled"
                job.error = "Cancelled by user"
                return
            time.sleep(0.5)

        job.status = "completed"
        job.result = {
            "success": True,
            "message": f"Assetto Corsa session for {test_id} finished.",
        }


# Singleton Queue Manager Instance
queue_mgr = ACQueueManager()

