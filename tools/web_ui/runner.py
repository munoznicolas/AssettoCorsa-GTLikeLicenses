#!/usr/bin/env python3
"""
runner.py
Central Assetto Corsa Execution Queue & Process Manager for the GT-Like Licenses Web UI.
Manages interactive play sessions, AI demo sessions, evaluation loops, and live telemetry recording.
"""

import os
import queue
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

from tools.telemetry.recorder import (
    DEFAULT_AC_ROOT,
    load_telemetry_profile,
    record_live_in_engine_telemetry,
    save_telemetry_profile,
)
from tools.web_ui.job_executors import (
    _run_eval,
    _run_interactive_session,
    _run_record_telemetry,
    ensure_complete_test_data,
    is_acs_process_active,
    stage_test_configuration,
    sync_assets_if_needed,
    terminate_all_acs_instances,
)


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

    MAX_STORED_JOBS = 100

    def __init__(self, ac_root: str = DEFAULT_AC_ROOT):
        self.ac_root = ac_root
        self._queue: queue.Queue = queue.Queue()
        self._jobs: Dict[str, ACJob] = {}
        self._active_job: Optional[ACJob] = None
        self._recent_completed: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _prune_old_jobs_locked(self) -> None:
        if len(self._jobs) <= self.MAX_STORED_JOBS:
            return
        removable = [
            jid
            for jid, j in sorted(self._jobs.items(), key=lambda kv: kv[1].created_at)
            if j.status not in ("queued", "running")
        ]
        for jid in removable[: max(0, len(self._jobs) - self.MAX_STORED_JOBS)]:
            self._jobs.pop(jid, None)

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
            self._prune_old_jobs_locked()
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
                    if len(self._recent_completed) > 25:
                        self._recent_completed = self._recent_completed[-25:]
                    self._prune_old_jobs_locked()
                self._queue.task_done()

    def _stage_test_configuration(self, test_data: Dict[str, Any]) -> None:
        stage_test_configuration(test_data, self.ac_root)

    def _sync_assets_if_needed(self) -> None:
        sync_assets_if_needed(self.ac_root)

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
        _run_record_telemetry(job, params, self.ac_root)

    def _run_eval(self, job: ACJob, params: Dict[str, Any]) -> None:
        _run_eval(job, params, self.ac_root)

    def _run_interactive_session(self, job: ACJob, params: Dict[str, Any]) -> None:
        _run_interactive_session(job, params, self.ac_root)


# Singleton Queue Manager Instance
queue_mgr = ACQueueManager()
GLOBAL_QUEUE = queue_mgr

__all__ = [
    "ACJob",
    "ACQueueManager",
    "GLOBAL_QUEUE",
    "_run_eval",
    "_run_interactive_session",
    "_run_record_telemetry",
    "asdict",
    "ensure_complete_test_data",
    "is_acs_process_active",
    "load_telemetry_profile",
    "queue_mgr",
    "record_live_in_engine_telemetry",
    "save_telemetry_profile",
    "stage_test_configuration",
    "sync_assets_if_needed",
    "terminate_all_acs_instances",
]
