#!/usr/bin/env python3
"""
record_ai_telemetry.py
In-Engine 95% AI Telemetry Recorder & Profiler for Assetto Corsa.

Measures and caches ground-truth telemetry of a proficient 95% AI across tracks:
  1. Live In-Engine Recording: launches acs.exe with AI_LEVEL=95, reads 60Hz
     shared memory (Local\\acpmf_physics & Local\\acpmf_graphics), logs a flying lap,
     and saves the full profile.
  2. Calibrated Spline Profile: generates 95% AI speed, gear, and RPM profile
     from fast_lane.ai spline and vehicle drivetrain parameters.
"""

import argparse
import ctypes
from ctypes import c_float, c_int32, c_wchar
import json
import mmap
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from extract_spline_coords import DEFAULT_AC_ROOT, SplineParser, find_spline_file
from tools.telemetry.profile import (
    ERR_MISSING_CAR_ID,
    ERR_MISSING_TRACK_ID,
    PROFILES_DIR,
    TelemetryProfile,
    TelemetrySample,
    _pregenerate_curriculum,
    _print_profile_summary,
    _sanitize_profile_token,
    calibrate_from_spline,
    estimate_gear_and_rpm,
    load_telemetry_profile,
    profile_filename,
    save_telemetry_profile,
)
from tools.testing.ac_launcher import ALT_USER_DOCS_AC, LOG_TXT_PATH, RACE_INI_PATH, generate_race_ini

ACTIVE_TEST_FILENAME = "active_test.json"


class SPageFilePhysics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32), ("gas", c_float), ("brake", c_float), ("fuel", c_float),
        ("gear", c_int32), ("rpms", c_int32), ("steerAngle", c_float), ("speedKmh", c_float),
    ]


class SPageFileGraphic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32), ("status", c_int32), ("session", c_int32),
        ("currentTime", c_wchar * 15), ("lastTime", c_wchar * 15), ("bestTime", c_wchar * 15),
        ("split", c_wchar * 15), ("completedLaps", c_int32), ("position", c_int32),
        ("iCurrentTime", c_int32), ("iLastTime", c_int32), ("iBestTime", c_int32),
        ("sessionTimeLeft", c_float), ("distanceTraveled", c_float), ("isInPit", c_int32),
        ("currentSectorIndex", c_int32), ("lastSectorTime", c_int32), ("numberOfLaps", c_int32),
        ("tyreCompound", c_wchar * 33), ("replayTimeMultiplier", c_float),
        ("normalizedCarPosition", c_float), ("carCoordinates", c_float * 3),
        ("penaltyTime", c_float), ("flag", c_int32), ("idealLineOn", c_int32), ("isInPitLine", c_int32),
    ]


def _get_track_total_len(track_id: str, layout: str, ac_root: str) -> float:
    try:
        spline_file = find_spline_file(track_id, layout, ac_root)
        if spline_file:
            parser = SplineParser(spline_file)
            if parser.total_length > 10.0:
                return parser.total_length
    except Exception as e:
        print(f"[*] Spline length pre-check note: {e}")
    return 1000.0


def _write_file_safely(path: str, content: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def _remove_file_safely(path: str) -> None:
    if os.path.isfile(path):
        try:
            os.remove(path)
        except Exception:
            pass


def _prepare_recording_environment(
    track_id: str, layout: str, car_id: str, ai_level: int, ac_root: str
) -> List[str]:
    test_data = {
        "car_id": car_id, "track_id": track_id, "track_layout": layout,
        "test_id": "AI_TELEMETRY_RECORDER", "session_name": "Hotlap",
        "session_type": 4, "spawn_set": "HOTLAP_START", "duration_minutes": 0,
    }
    race_ini_str = generate_race_ini(test_data, ac_root=ac_root, ai_level=ai_level, ai_test_mode=True)

    for rp in [RACE_INI_PATH, os.path.join(ALT_USER_DOCS_AC, "cfg", "race.ini"), os.path.join(ac_root, "cfg", "race.ini")]:
        _write_file_safely(rp, race_ini_str)

    active_test_payload = {
        "test_id": "AI_TELEMETRY_RECORDER", "is_telemetry_recording": True,
        "title": f"{ai_level}% AI Telemetry Lap Profiler", "start_mode": "FLYING_LAP",
        "car_id": car_id, "track_id": track_id, "track_layout": layout,
    }
    active_test_json_str = json.dumps(active_test_payload, indent=2)
    gt_base = os.path.join(ac_root, "extension", "lua", "new-modes", "gt-license")
    active_test_targets = [
        os.path.join(REPO_ROOT, ACTIVE_TEST_FILENAME),
        os.path.join(REPO_ROOT, "lua", ACTIVE_TEST_FILENAME),
        os.path.join(REPO_ROOT, "lua", "data", ACTIVE_TEST_FILENAME),
        os.path.join(gt_base, ACTIVE_TEST_FILENAME),
        os.path.join(gt_base, "data", ACTIVE_TEST_FILENAME),
    ]
    for atp in active_test_targets:
        _write_file_safely(atp, active_test_json_str)
    for lp in [LOG_TXT_PATH, os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt")]:
        _remove_file_safely(lp)
    return active_test_targets


def _connect_shared_memory(
    proc: subprocess.Popen, stop_event: Optional[Any] = None, timeout_sec: float = 35.0
) -> Tuple[Optional[mmap.mmap], Optional[mmap.mmap]]:
    connect_start = time.time()
    while time.time() - connect_start < timeout_sec:
        if stop_event and getattr(stop_event, "is_set", lambda: False)():
            print("[*] Recording cancelled before shared memory connection.")
            return None, None
        if proc.poll() is not None:
            print(f"[!] acs.exe terminated unexpectedly (code {proc.returncode})")
            return None, None
        try:
            shm_physics = mmap.mmap(0, ctypes.sizeof(SPageFilePhysics), "Local\\acpmf_physics")
            shm_graphics = mmap.mmap(0, ctypes.sizeof(SPageFileGraphic), "Local\\acpmf_graphics")
            print("[+] Connected to Assetto Corsa Shared Memory!")
            return shm_physics, shm_graphics
        except OSError:
            time.sleep(0.5)
    print("[!] Could not connect to Assetto Corsa Shared Memory in time.")
    return None, None


class _LiveTelemetrySession:
    """Manages state transitions and sample collection for live telemetry recording."""

    def __init__(self, track_total_len: float) -> None:
        self.track_total_len = track_total_len
        self.samples: List[TelemetrySample] = []
        self.recording_state = "WAITING"
        self.initial_completed_laps: Optional[int] = None
        self.has_passed_midpoint = False
        self.lap_start_time: Optional[float] = None
        self.prev_progress = -1.0
        self.start_wait_time = time.time()
        self.lap_duration = 0.0

    @staticmethod
    def _map_gear(gear_raw: int, spd_raw: float) -> int:
        if gear_raw <= 1:
            return 1 if spd_raw > 15.0 else 0
        return gear_raw - 1

    def _should_start_lap(self, progress: float, spd_raw: float, is_in_pit: int) -> bool:
        if is_in_pit != 0 or spd_raw <= 30.0:
            return False
        line_crossed = self.prev_progress > 0.75 and progress < 0.25
        spawned_on_flying_lap = (
            self.prev_progress < 0 and progress < 0.10 and spd_raw > 50.0 and (time.time() - self.start_wait_time < 5.0)
        )
        return line_crossed or spawned_on_flying_lap

    def _handle_waiting(self, progress: float, spd_raw: float, completed_laps: int, is_in_pit: int) -> None:
        if not self._should_start_lap(progress, spd_raw, is_in_pit):
            return
        self.recording_state = "RECORDING"
        self.initial_completed_laps = completed_laps
        self.lap_start_time = time.time()
        self.samples.clear()
        self.has_passed_midpoint = False
        print(f"[+] Flying lap STARTED at progress={progress:.3f}, speed={spd_raw:.1f} km/h (laps={completed_laps})! Capturing telemetry...")

    def _should_finish_lap(self, progress: float, completed_laps: int) -> bool:
        if not self.has_passed_midpoint or len(self.samples) < 300:
            return False
        line_finished = self.prev_progress > 0.80 and progress < 0.20
        laps_incremented = self.initial_completed_laps is not None and completed_laps > self.initial_completed_laps
        return line_finished or laps_incremented

    def _handle_recording(
        self, progress: float, spd_raw: float, gear: int, rpm_raw: int,
        steer_angle: float, completed_laps: int, i_last_time: int, session_start_time: float,
    ) -> bool:
        if 0.35 < progress < 0.75:
            self.has_passed_midpoint = True
        dist_m = progress * self.track_total_len
        self.samples.append(TelemetrySample(
            progress=round(progress, 4), distance_m=round(dist_m, 2),
            speed_kmh=round(spd_raw, 1), gear=gear, rpm=rpm_raw, steer_norm=round(steer_angle, 3),
        ))
        if len(self.samples) % 150 == 0:
            print(f"    [Lap Telemetry] Progress: {progress*100:.1f}% | Speed: {spd_raw:.1f} km/h | Gear: {gear} | RPM: {rpm_raw} | Samples: {len(self.samples)}")
        if self._should_finish_lap(progress, completed_laps):
            self.recording_state = "COMPLETED"
            self.lap_duration = (
                round(i_last_time / 1000.0, 3) if i_last_time > 0
                else round(time.time() - (self.lap_start_time or session_start_time), 2)
            )
            print(f"[+] Completed flying lap telemetry capture! ({len(self.samples)} samples, lap time: {self.lap_duration:.2f}s)")
            return True
        return False

    def process_frame(self, phys: SPageFilePhysics, graph: SPageFileGraphic, session_start_time: float) -> bool:
        spd_raw = float(phys.speedKmh)
        gear_raw = int(phys.gear)
        rpm_raw = int(phys.rpms)
        steer_angle = float(phys.steerAngle)
        progress = float(graph.normalizedCarPosition)
        completed_laps = int(graph.completedLaps)
        is_in_pit = int(graph.isInPit) or int(graph.isInPitLine)
        i_last_time = int(graph.iLastTime)
        gear = self._map_gear(gear_raw, spd_raw)

        lap_finished = False
        if self.recording_state == "WAITING":
            self._handle_waiting(progress, spd_raw, completed_laps, is_in_pit)
        elif self.recording_state == "RECORDING":
            lap_finished = self._handle_recording(
                progress, spd_raw, gear, rpm_raw, steer_angle, completed_laps, i_last_time, session_start_time
            )
        self.prev_progress = progress
        return lap_finished


def _record_telemetry_loop(
    shm_physics: mmap.mmap, shm_graphics: mmap.mmap, proc: subprocess.Popen,
    track_total_len: float, timeout_sec: int, stop_event: Optional[Any],
) -> Tuple[List[TelemetrySample], float, float]:
    phys = SPageFilePhysics.from_buffer(shm_physics)
    graph = SPageFileGraphic.from_buffer(shm_graphics)
    session = _LiveTelemetrySession(track_total_len)
    start_time = time.time()
    try:
        while time.time() - start_time < timeout_sec:
            if stop_event and getattr(stop_event, "is_set", lambda: False)():
                print("[*] Recording session received cancellation signal.")
                break
            if proc.poll() is not None or session.process_frame(phys, graph, start_time):
                break
            time.sleep(0.035)
    except Exception as e:
        print(f"[!] Shared memory reading note: {e}")
    return session.samples, session.lap_duration, start_time


def _cleanup_recording_resources(
    shm_physics: Optional[mmap.mmap], shm_graphics: Optional[mmap.mmap],
    proc: Optional[subprocess.Popen], active_test_targets: List[str],
) -> None:
    for shm in (shm_physics, shm_graphics):
        if shm:
            try:
                shm.close()
            except Exception:
                pass
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
    for atp in active_test_targets:
        _remove_file_safely(atp)


def record_live_in_engine_telemetry(
    track_id: str, layout: str = "", car_id: Optional[str] = None,
    ai_level: int = 100, ac_root: str = DEFAULT_AC_ROOT,
    timeout_sec: Optional[int] = None, stop_event: Optional[Any] = None, proc_callback: Optional[Any] = None,
) -> TelemetryProfile:
    if not track_id:
        raise ValueError(ERR_MISSING_TRACK_ID)
    if not car_id:
        raise ValueError(ERR_MISSING_CAR_ID)

    print(f"[*] Initializing live in-engine {ai_level}% AI recording session for {car_id} at {track_id}...")
    track_total_len = _get_track_total_len(track_id, layout, ac_root)
    if timeout_sec is None:
        timeout_sec = max(240, int((track_total_len / 25.0) * 2.5) + 60)

    active_test_targets = _prepare_recording_environment(track_id, layout, car_id, ai_level, ac_root)
    acs_exe = os.path.join(ac_root, "acs.exe")
    if not os.path.isfile(acs_exe):
        print(f"[!] acs.exe not found at {acs_exe}. Falling back to calibrated spline profile.")
        return calibrate_from_spline(track_id, layout, car_id, ai_level, ac_root)

    print(f"[*] Launching {acs_exe} child process (Hotlap mode with HOTLAP_START)...")
    proc = subprocess.Popen([acs_exe], cwd=ac_root)
    if proc_callback:
        proc_callback(proc)

    shm_physics, shm_graphics = None, None
    samples: List[TelemetrySample] = []
    lap_duration = 0.0
    start_time = time.time()

    try:
        shm_physics, shm_graphics = _connect_shared_memory(proc, stop_event=stop_event)
        if not shm_physics or not shm_graphics:
            return calibrate_from_spline(track_id, layout, car_id, ai_level, ac_root)
        samples, lap_duration, start_time = _record_telemetry_loop(
            shm_physics, shm_graphics, proc, track_total_len, timeout_sec, stop_event
        )
    finally:
        _cleanup_recording_resources(shm_physics, shm_graphics, proc, active_test_targets)

    if len(samples) > 100:
        samples.sort(key=lambda s: s.progress)
        print(f"[+] Successfully captured {len(samples)} live telemetry samples across full circuit.")
        return TelemetryProfile(
            track_id=track_id, track_layout=layout, car_id=car_id, ai_level=ai_level,
            source="in_engine_live_telemetry", total_track_length_m=round(track_total_len, 2),
            lap_time_s=lap_duration if lap_duration > 0 else round(time.time() - start_time, 2),
            sample_count=len(samples), samples=samples,
        )

    print("[*] Insufficient live samples collected. Generating high-fidelity calibrated spline profile...")
    return calibrate_from_spline(track_id, layout, car_id, ai_level, ac_root)


def _get_or_create_profile(
    track_id: str, layout: str, car_id: Optional[str],
    ai_level: int, allow_live_engine: bool, ac_root: str,
) -> TelemetryProfile:
    if not track_id:
        raise ValueError(ERR_MISSING_TRACK_ID)
    if not car_id:
        raise ValueError(ERR_MISSING_CAR_ID)

    profile = load_telemetry_profile(track_id, layout, car_id, ai_level)
    if profile is None:
        if allow_live_engine:
            try:
                profile = record_live_in_engine_telemetry(track_id, layout, car_id, ai_level, ac_root)
                save_telemetry_profile(profile)
            except Exception as e:
                print(f"[!] Live in-engine recording encountered an issue: {e}. Falling back to spline.")
                profile = None
        if profile is None:
            profile = calibrate_from_spline(track_id, layout, car_id, ai_level, ac_root)
            save_telemetry_profile(profile)
    return profile


def get_or_calculate_initial_physics(
    track_id: str, layout: str = "", car_id: Optional[str] = None,
    start_s: float = 0.0, countdown_sec: float = 3.0, ai_level: int = 100,
    allow_live_engine: bool = False, ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    profile = _get_or_create_profile(track_id, layout, car_id, ai_level, allow_live_engine, ac_root)
    return profile.calculate_gate_physics(start_s, countdown_sec)


def get_or_calculate_targets(
    track_id: str, layout: str = "", car_id: Optional[str] = None,
    start_s: float = 0.0, finish_s: float = 1.0, start_mode: str = "ROLLING",
    with_stop_box: bool = False, ai_level: int = 100, countdown_sec: float = 3.0,
    allow_live_engine: bool = False, ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    profile = _get_or_create_profile(track_id, layout, car_id, ai_level, allow_live_engine, ac_root)
    targets_info = profile.calculate_sector_targets(
        start_s=start_s, finish_s=finish_s, start_mode=start_mode, with_stop_box=with_stop_box
    )
    physics_info = profile.calculate_gate_physics(start_s, countdown_sec)
    return {
        "success": True,
        "source": profile.source,
        "recorded_at": profile.recorded_at,
        "targets": {
            "gold_seconds": targets_info["gold_seconds"],
            "silver_seconds": targets_info["silver_seconds"],
            "bronze_seconds": targets_info["bronze_seconds"],
        },
        "sector_time_s": targets_info["sector_time_s"],
        "sector_length_m": targets_info["sector_length_m"],
        "physics": physics_info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assetto Corsa 100% AI Telemetry Recorder & Profiler")
    parser.add_argument("--track", type=str, help="Track ID")
    parser.add_argument("--layout", type=str, default="", help="Track layout (default: empty for base layout)")
    parser.add_argument("--car", type=str, help="Car ID")
    parser.add_argument("--ai-level", type=int, default=100, help="AI proficiency level (default: 100)")
    parser.add_argument("--live", action="store_true", help="Launch acs.exe to record live in-engine telemetry")
    parser.add_argument("--all-curriculum", action="store_true", help="Pre-generate telemetry profiles for all curriculum track/car pairings")
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa installation root")

    args = parser.parse_args()
    if args.all_curriculum:
        return _pregenerate_curriculum(args.ai_level, args.ac_root)

    missing = [flag for flag, val in (("--track", args.track), ("--car", args.car)) if not val]
    if missing:
        parser.error(f"missing required parameter: {', '.join(missing)}")

    if args.live:
        profile = record_live_in_engine_telemetry(args.track, args.layout, args.car, args.ai_level, args.ac_root)
    else:
        profile = calibrate_from_spline(args.track, args.layout, args.car, args.ai_level, args.ac_root)

    path = save_telemetry_profile(profile)
    if not os.path.isfile(path):
        return 1
    _print_profile_summary(profile, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
