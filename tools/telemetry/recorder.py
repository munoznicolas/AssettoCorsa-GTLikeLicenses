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

Profiles are saved to:
  data/telemetry_profiles/<track_id>__[<layout>]__<car_id>__ai95.json
"""

import argparse
import ctypes
from ctypes import c_int32, c_float, c_wchar
import json
import math
import mmap
import os
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)
from tools.testing.ac_launcher import (
    generate_race_ini,
    RACE_INI_PATH,
    ALT_USER_DOCS_AC,
    LOG_TXT_PATH,
)

PROFILES_DIR = os.path.join(REPO_ROOT, "data", "telemetry_profiles")
ACTIVE_TEST_FILENAME = "active_test.json"
ERR_MISSING_TRACK_ID = "Missing required parameter: track_id"
ERR_MISSING_CAR_ID = "Missing required parameter: car_id"


class SPageFilePhysics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("gas", c_float),
        ("brake", c_float),
        ("fuel", c_float),
        ("gear", c_int32),
        ("rpms", c_int32),
        ("steerAngle", c_float),
        ("speedKmh", c_float),
    ]


class SPageFileGraphic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("status", c_int32),
        ("session", c_int32),
        ("currentTime", c_wchar * 15),
        ("lastTime", c_wchar * 15),
        ("bestTime", c_wchar * 15),
        ("split", c_wchar * 15),
        ("completedLaps", c_int32),
        ("position", c_int32),
        ("iCurrentTime", c_int32),
        ("iLastTime", c_int32),
        ("iBestTime", c_int32),
        ("sessionTimeLeft", c_float),
        ("distanceTraveled", c_float),
        ("isInPit", c_int32),
        ("currentSectorIndex", c_int32),
        ("lastSectorTime", c_int32),
        ("numberOfLaps", c_int32),
        ("tyreCompound", c_wchar * 33),
        ("replayTimeMultiplier", c_float),
        ("normalizedCarPosition", c_float),
        ("carCoordinates", c_float * 3),
        ("penaltyTime", c_float),
        ("flag", c_int32),
        ("idealLineOn", c_int32),
        ("isInPitLine", c_int32),
    ]


@dataclass
class TelemetrySample:
    progress: float
    distance_m: float
    speed_kmh: float
    gear: int
    rpm: int
    steer_norm: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TelemetryProfile:
    track_id: str
    track_layout: str
    car_id: str
    ai_level: int
    source: str
    total_track_length_m: float
    lap_time_s: float
    sample_count: int
    samples: List[TelemetrySample]
    recorded_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.recorded_at:
            self.recorded_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "track_layout": self.track_layout,
            "car_id": self.car_id,
            "ai_level": self.ai_level,
            "recorded_at": self.recorded_at,
            "source": self.source,
            "total_track_length_m": round(self.total_track_length_m, 2),
            "lap_time_s": round(self.lap_time_s, 2),
            "sample_count": len(self.samples),
            "samples": [s.to_dict() for s in self.samples],
        }

    def query_sample(self, distance_m: float) -> Tuple[float, int, int]:
        """Interpolates (speed_kmh, gear, rpm) at a given distance in meters."""
        if not self.samples:
            return 70.0, 3, 4000

        dist = (distance_m % self.total_track_length_m + self.total_track_length_m) % self.total_track_length_m
        n = len(self.samples)

        low = 0
        high = n - 1
        while low <= high:
            mid = (low + high) // 2
            if self.samples[mid].distance_m <= dist:
                low = mid + 1
            else:
                high = mid - 1

        i0 = max(0, min(high, n - 1))
        i1 = (i0 + 1) % n

        s0 = self.samples[i0]
        s1 = self.samples[i1]

        d0 = s0.distance_m
        d1 = s1.distance_m
        if i1 == 0:
            d1 = self.total_track_length_m

        t = (dist - d0) / (d1 - d0) if (d1 - d0) > 1e-4 else 0.0
        t = max(0.0, min(1.0, t))

        spd = s0.speed_kmh * (1.0 - t) + s1.speed_kmh * t
        gear = s0.gear if t < 0.5 else s1.gear
        rpm = int(s0.rpm * (1.0 - t) + s1.rpm * t)

        return float(spd), int(gear), int(rpm)

    def integrate_distance_backward(self, end_dist_m: float, duration_sec: float, step_dt: float = 0.05) -> float:
        """
        Numerically integrates backward along the velocity curve to find the exact
        spawn distance needed so traveling to end_dist_m takes duration_sec.
        """
        curr_dist = end_dist_m
        t_accum = 0.0

        while t_accum < duration_sec:
            spd_kmh, _, _ = self.query_sample(curr_dist)
            v_ms = max(5.0, spd_kmh / 3.6)
            dt = min(step_dt, duration_sec - t_accum)
            ds = v_ms * dt
            curr_dist = (curr_dist - ds + self.total_track_length_m) % self.total_track_length_m
            t_accum += dt

        return curr_dist

    def integrate_distance_forward(self, start_dist_m: float, duration_sec: float, step_dt: float = 0.05) -> float:
        """
        Numerically integrates forward along the velocity curve.
        """
        curr_dist = start_dist_m
        t_accum = 0.0

        while t_accum < duration_sec:
            spd_kmh, _, _ = self.query_sample(curr_dist)
            v_ms = max(5.0, spd_kmh / 3.6)
            dt = min(step_dt, duration_sec - t_accum)
            ds = v_ms * dt
            curr_dist = (curr_dist + ds) % self.total_track_length_m
            t_accum += dt

        return curr_dist

    def calculate_gate_physics(self, gate_progress: float, countdown_sec: float = 3.0) -> Dict[str, Any]:
        """
        Calculates ground-truth AI handover speed, engaged gear, RPM, and
        the exact backward-integrated countdown run-up distance (spawn_offset).
        """
        gate_prog_norm = (gate_progress % 1.0 + 1.0) % 1.0
        gate_dist = (gate_prog_norm * self.total_track_length_m) % self.total_track_length_m
        gate_spd, gate_gear, gate_rpm = self.query_sample(gate_dist)

        spawn_dist = self.integrate_distance_backward(gate_dist, countdown_sec)
        spawn_offset = (gate_dist - spawn_dist + self.total_track_length_m) % self.total_track_length_m
        spawn_spd, spawn_gear, spawn_rpm = self.query_sample(spawn_dist)
        spawn_prog = (spawn_dist / self.total_track_length_m) if self.total_track_length_m > 0 else 0.0

        return {
            "gate_progress": round(gate_prog_norm, 4),
            "gate_distance_m": round(gate_dist, 2),
            "speed_kmh": round(gate_spd, 1),
            "gear": gate_gear,
            "rpm": gate_rpm,
            "spawn_offset_m": round(spawn_offset, 1),
            "spawn_progress": round(spawn_prog, 4),
            "spawn_distance_m": round(spawn_dist, 2),
            "spawn_speed_kmh": round(spawn_spd, 1),
            "spawn_gear": spawn_gear,
            "spawn_rpm": spawn_rpm,
            "countdown_sec": countdown_sec,
            "total_track_length_m": round(self.total_track_length_m, 2),
            "source": self.source,
            "recorded_at": self.recorded_at,
        }

    @staticmethod
    def _compute_sector_length(
        tot: float, start_s: float, finish_s: float, start_mode: str
    ) -> Tuple[float, float]:
        s0 = (start_s % 1.0 + 1.0) % 1.0
        s1 = 1.0 if abs(finish_s - 1.0) < 1e-4 else ((finish_s % 1.0 + 1.0) % 1.0)
        start_dist = s0 * tot
        finish_dist = s1 * tot

        is_full_lap = (
            start_mode == "FLYING_LAP"
            or (s0 <= 0.005 and s1 >= 0.99)
            or (abs(s0 - s1) < 0.002 and start_mode in ("FLYING_LAP", "STANDING"))
        )

        if is_full_lap:
            sec_len = tot
        elif s1 >= s0:
            sec_len = finish_dist - start_dist
        else:
            sec_len = tot - start_dist + finish_dist

        if sec_len <= 1.0:
            sec_len = tot if is_full_lap else 100.0

        return start_dist, sec_len

    @staticmethod
    def _effective_speed(
        v_flying_ms: float,
        dist_traveled: float,
        sec_len: float,
        start_mode: str,
        with_stop_box: bool,
        a_launch: float = 6.0,
        a_brake: float = 9.0,
    ) -> float:
        if start_mode != "STANDING":
            return v_flying_ms

        v_launch = math.sqrt(2.0 * a_launch * max(0.2, dist_traveled))
        v_eff = min(v_flying_ms, v_launch)
        if with_stop_box:
            dist_rem = max(0.0, sec_len - dist_traveled)
            v_stop = math.sqrt(2.0 * a_brake * max(0.2, dist_rem))
            v_eff = min(v_eff, v_stop)
        return max(2.5, v_eff)

    def _integrate_traversal_time(
        self,
        start_dist: float,
        sec_len: float,
        start_mode: str,
        with_stop_box: bool,
        step_m: float,
    ) -> float:
        tot = self.total_track_length_m
        step = max(0.5, min(step_m, sec_len / 500.0))
        t_accum = 0.0
        dist_traveled = 0.0

        while dist_traveled < sec_len:
            curr_d = (start_dist + dist_traveled) % tot
            spd_kmh, _, _ = self.query_sample(curr_d)
            v_ms = self._effective_speed(
                max(5.0, spd_kmh / 3.6),
                dist_traveled,
                sec_len,
                start_mode,
                with_stop_box,
            )
            t_accum += step / v_ms
            dist_traveled += step

        if start_mode == "STANDING" and with_stop_box:
            # 0.5s pause window to register complete vehicle standstill inside stop box
            t_accum += 0.5

        return t_accum

    @staticmethod
    def _calculate_medal_targets(t_accum: float, start_mode: str) -> Tuple[float, float, float]:
        # Gran Turismo balance target calculation
        if start_mode in ("ROLLING", "FLYING_LAP"):
            gold = math.ceil(round(t_accum * 0.98, 4) * 10.0) / 10.0
            silver = math.ceil(round(t_accum * 1.05, 4) * 10.0) / 10.0
            bronze = math.ceil(round(t_accum * 1.15, 4) * 10.0) / 10.0
        else:
            gold = math.ceil(round(t_accum, 4) * 10.0) / 10.0
            silver = math.ceil(round(gold * (1.05 / 0.98), 4) * 10.0) / 10.0
            bronze = math.ceil(round(gold * (1.15 / 0.98), 4) * 10.0) / 10.0
        return gold, silver, bronze

    def calculate_sector_targets(
        self,
        start_s: float,
        finish_s: float,
        start_mode: str = "ROLLING",
        with_stop_box: bool = False,
        step_m: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Numerically integrates traversal time between start_s and finish_s
        along the telemetry velocity profile, inferring authentic Gold, Silver,
        and Bronze target times calibrated to standard Gran Turismo balance.
        """
        tot = self.total_track_length_m
        if tot <= 0:
            return {
                "gold_seconds": 10.0,
                "silver_seconds": 12.0,
                "bronze_seconds": 15.0,
                "sector_time_s": 10.0,
                "sector_length_m": 0.0,
            }

        start_dist, sec_len = self._compute_sector_length(tot, start_s, finish_s, start_mode)
        t_accum = self._integrate_traversal_time(
            start_dist, sec_len, start_mode, with_stop_box, step_m
        )
        gold, silver, bronze = self._calculate_medal_targets(t_accum, start_mode)

        return {
            "gold_seconds": gold,
            "silver_seconds": silver,
            "bronze_seconds": bronze,
            "sector_time_s": round(t_accum, 3),
            "sector_length_m": round(sec_len, 1),
        }



def profile_filename(track_id: str, layout: str, car_id: str, ai_level: int = 100) -> str:
    """Standardized profile cache filename."""
    tag = f"{track_id}__{layout}" if layout else track_id
    return f"{tag}__{car_id}__ai{ai_level}.json"


def load_telemetry_profile(track_id: str, layout: str, car_id: str, ai_level: int = 100) -> Optional[TelemetryProfile]:
    """Loads a cached profile from disk if available."""
    levels_to_try = [ai_level]
    if 100 not in levels_to_try:
        levels_to_try.append(100)
    if 95 not in levels_to_try:
        levels_to_try.append(95)

    path = None
    for lvl in levels_to_try:
        fname = profile_filename(track_id, layout, car_id, lvl)
        p = os.path.join(PROFILES_DIR, fname)
        if os.path.isfile(p):
            path = p
            break

    if not path:
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = [TelemetrySample(**s) for s in data["samples"]]
        recorded_at = data.get("recorded_at")
        if not recorded_at:
            recorded_at = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()
        return TelemetryProfile(
            track_id=data["track_id"],
            track_layout=data["track_layout"],
            car_id=data["car_id"],
            ai_level=data["ai_level"],
            source=data.get("source", "cached"),
            total_track_length_m=data["total_track_length_m"],
            lap_time_s=data.get("lap_time_s", 0.0),
            sample_count=len(samples),
            samples=samples,
            recorded_at=recorded_at,
        )
    except Exception:
        return None


def save_telemetry_profile(profile: TelemetryProfile) -> str:
    """Saves a profile to data/telemetry_profiles/."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    fname = profile_filename(profile.track_id, profile.track_layout, profile.car_id, profile.ai_level)
    path = os.path.join(PROFILES_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2)
    return path


def estimate_gear_and_rpm(speed_kmh: float) -> Tuple[int, int]:
    """Estimates realistic gear and RPM for road/GT cars from speed."""
    if speed_kmh < 40.0:
        return 1, int(2500 + speed_kmh * 70)
    elif speed_kmh < 75.0:
        return 2, int(3000 + (speed_kmh - 40) * 85)
    elif speed_kmh < 115.0:
        return 3, int(3500 + (speed_kmh - 75) * 65)
    elif speed_kmh < 160.0:
        return 4, int(4200 + (speed_kmh - 115) * 55)
    elif speed_kmh < 210.0:
        return 5, int(4800 + (speed_kmh - 160) * 45)
    else:
        return 6, int(5400 + min(1800, (speed_kmh - 210) * 35))


def calibrate_from_spline(
    track_id: str,
    layout: str = "",
    car_id: Optional[str] = None,
    ai_level: int = 100,
    ac_root: str = DEFAULT_AC_ROOT,
) -> TelemetryProfile:
    """
    Synthesizes an authentic 100% AI speed profile from the track's binary fast_lane.ai.
    Scales recorded reference speed by (ai_level / 100.0) and derives transmission states.
    """
    if not track_id:
        raise ValueError(ERR_MISSING_TRACK_ID)
    if not car_id:
        raise ValueError(ERR_MISSING_CAR_ID)

    spline_path = find_spline_file(track_id, layout, ac_root)
    if not spline_path:
        raise FileNotFoundError(f"AI spline not found for track {track_id} [{layout}]")

    parser = SplineParser(spline_path)
    factor = ai_level / 100.0
    samples: List[TelemetrySample] = []
    total_time = 0.0

    for i, w in enumerate(parser.waypoints):
        spd_kmh = max(20.0, (w.speed_ms * 3.6) * factor)
        gear, rpm = estimate_gear_and_rpm(spd_kmh)
        prog = w.distance / parser.total_length if parser.total_length > 0 else 0.0

        if i > 0:
            ds = w.distance - parser.waypoints[i - 1].distance
            v_avg = ((parser.waypoints[i - 1].speed_ms + w.speed_ms) * 0.5 * factor) or 10.0
            total_time += ds / v_avg

        samples.append(TelemetrySample(
            progress=round(prog, 4),
            distance_m=round(w.distance, 2),
            speed_kmh=round(spd_kmh, 1),
            gear=gear,
            rpm=rpm,
            steer_norm=round(w.forward[0] * 0.05, 3),
        ))

    profile = TelemetryProfile(
        track_id=track_id,
        track_layout=layout,
        car_id=car_id,
        ai_level=ai_level,
        source=f"spline_calibrated_ai{ai_level}",
        total_track_length_m=round(parser.total_length, 2),
        lap_time_s=round(total_time, 2),
        sample_count=len(samples),
        samples=samples,
    )
    return profile


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
    track_id: str,
    layout: str,
    car_id: str,
    ai_level: int,
    ac_root: str,
) -> List[str]:
    test_data = {
        "car_id": car_id,
        "track_id": track_id,
        "track_layout": layout,
        "test_id": "AI_TELEMETRY_RECORDER",
        "session_name": "Hotlap",
        "session_type": 4,
        "spawn_set": "HOTLAP_START",
        "duration_minutes": 0,
    }
    race_ini_str = generate_race_ini(
        test_data,
        ac_root=ac_root,
        ai_level=ai_level,
        ai_test_mode=True,
    )

    for rp in [
        RACE_INI_PATH,
        os.path.join(ALT_USER_DOCS_AC, "cfg", "race.ini"),
        os.path.join(ac_root, "cfg", "race.ini"),
    ]:
        _write_file_safely(rp, race_ini_str)

    active_test_payload = {
        "test_id": "AI_TELEMETRY_RECORDER",
        "is_telemetry_recording": True,
        "title": f"{ai_level}% AI Telemetry Lap Profiler",
        "start_mode": "FLYING_LAP",
        "car_id": car_id,
        "track_id": track_id,
        "track_layout": layout,
    }
    active_test_json_str = json.dumps(active_test_payload, indent=2)

    active_test_targets = [
        os.path.join(REPO_ROOT, ACTIVE_TEST_FILENAME),
        os.path.join(REPO_ROOT, "lua", ACTIVE_TEST_FILENAME),
        os.path.join(REPO_ROOT, "lua", "data", ACTIVE_TEST_FILENAME),
        os.path.join(ac_root, "extension", "lua", "new-modes", "gt-license", ACTIVE_TEST_FILENAME),
        os.path.join(ac_root, "extension", "lua", "new-modes", "gt-license", "data", ACTIVE_TEST_FILENAME),
    ]
    for atp in active_test_targets:
        _write_file_safely(atp, active_test_json_str)

    for lp in [LOG_TXT_PATH, os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt")]:
        _remove_file_safely(lp)

    return active_test_targets


def _connect_shared_memory(
    proc: subprocess.Popen,
    stop_event: Optional[Any] = None,
    timeout_sec: float = 35.0,
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
        line_crossed = (self.prev_progress > 0.75 and progress < 0.25)
        spawned_on_flying_lap = (
            self.prev_progress < 0
            and progress < 0.10
            and spd_raw > 50.0
            and (time.time() - self.start_wait_time < 5.0)
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
        print(
            f"[+] Flying lap STARTED at progress={progress:.3f}, speed={spd_raw:.1f} km/h (laps={completed_laps})! Capturing telemetry..."
        )

    def _should_finish_lap(self, progress: float, completed_laps: int) -> bool:
        if not self.has_passed_midpoint or len(self.samples) < 300:
            return False
        line_finished = (self.prev_progress > 0.80 and progress < 0.20)
        laps_incremented = (
            self.initial_completed_laps is not None and completed_laps > self.initial_completed_laps
        )
        return line_finished or laps_incremented

    def _handle_recording(
        self,
        progress: float,
        spd_raw: float,
        gear: int,
        rpm_raw: int,
        steer_angle: float,
        completed_laps: int,
        i_last_time: int,
        session_start_time: float,
    ) -> bool:
        if 0.35 < progress < 0.75:
            self.has_passed_midpoint = True

        dist_m = progress * self.track_total_len
        self.samples.append(
            TelemetrySample(
                progress=round(progress, 4),
                distance_m=round(dist_m, 2),
                speed_kmh=round(spd_raw, 1),
                gear=gear,
                rpm=rpm_raw,
                steer_norm=round(steer_angle, 3),
            )
        )

        if len(self.samples) % 150 == 0:
            print(
                f"    [Lap Telemetry] Progress: {progress*100:.1f}% | Speed: {spd_raw:.1f} km/h | Gear: {gear} | RPM: {rpm_raw} | Samples: {len(self.samples)}"
            )

        if self._should_finish_lap(progress, completed_laps):
            self.recording_state = "COMPLETED"
            self.lap_duration = (
                round(i_last_time / 1000.0, 3)
                if i_last_time > 0
                else round(time.time() - (self.lap_start_time or session_start_time), 2)
            )
            print(
                f"[+] Completed flying lap telemetry capture! ({len(self.samples)} samples, lap time: {self.lap_duration:.2f}s)"
            )
            return True
        return False

    def process_frame(
        self,
        phys: SPageFilePhysics,
        graph: SPageFileGraphic,
        session_start_time: float,
    ) -> bool:
        """Processes a single telemetry frame. Returns True if lap completed."""
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
    shm_physics: mmap.mmap,
    shm_graphics: mmap.mmap,
    proc: subprocess.Popen,
    track_total_len: float,
    timeout_sec: int,
    stop_event: Optional[Any],
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
            if proc.poll() is not None:
                break

            if session.process_frame(phys, graph, start_time):
                break

            time.sleep(0.035)
    except Exception as e:
        print(f"[!] Shared memory reading note: {e}")

    return session.samples, session.lap_duration, start_time


def _cleanup_recording_resources(
    shm_physics: Optional[mmap.mmap],
    shm_graphics: Optional[mmap.mmap],
    proc: Optional[subprocess.Popen],
    active_test_targets: List[str],
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
    track_id: str,
    layout: str = "",
    car_id: Optional[str] = None,
    ai_level: int = 100,
    ac_root: str = DEFAULT_AC_ROOT,
    timeout_sec: Optional[int] = None,
    stop_event: Optional[Any] = None,
    proc_callback: Optional[Any] = None,
) -> TelemetryProfile:
    """
    Launches acs.exe with AI_LEVEL=100 in Hotlap mode (HOTLAP_START flying lap)
    and logs live 60Hz telemetry via Assetto Corsa Shared Memory.
    Arms on start/finish line crossing and records exactly one full flying lap.
    Falls back to calibrated spline profile if shared memory is inaccessible or run is cancelled.
    """
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

    shm_physics = None
    shm_graphics = None
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
            track_id=track_id,
            track_layout=layout,
            car_id=car_id,
            ai_level=ai_level,
            source="in_engine_live_telemetry",
            total_track_length_m=round(track_total_len, 2),
            lap_time_s=lap_duration if lap_duration > 0 else round(time.time() - start_time, 2),
            sample_count=len(samples),
            samples=samples,
        )

    print("[*] Insufficient live samples collected. Generating high-fidelity calibrated spline profile...")
    return calibrate_from_spline(track_id, layout, car_id, ai_level, ac_root)


def get_or_calculate_initial_physics(
    track_id: str,
    layout: str = "",
    car_id: Optional[str] = None,
    start_s: float = 0.0,
    countdown_sec: float = 3.0,
    ai_level: int = 100,
    allow_live_engine: bool = False,
    ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    """
    Retrieves or generates an authentic AI telemetry profile and calculates
    the exact gate speed, spawn offset, gear, and RPM for a rolling start or flying lap.
    """
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

    return profile.calculate_gate_physics(start_s, countdown_sec)


def get_or_calculate_targets(
    track_id: str,
    layout: str = "",
    car_id: Optional[str] = None,
    start_s: float = 0.0,
    finish_s: float = 1.0,
    start_mode: str = "ROLLING",
    with_stop_box: bool = False,
    ai_level: int = 100,
    countdown_sec: float = 3.0,
    allow_live_engine: bool = False,
    ac_root: str = DEFAULT_AC_ROOT,
) -> Dict[str, Any]:
    """
    Retrieves or generates an authentic AI telemetry profile and computes:
      1. Target times (Gold, Silver, Bronze) via numerical integration along the trajectory
      2. Initial speed, spawn offset, gear, and RPM for start countdown
    """
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

    targets_info = profile.calculate_sector_targets(
        start_s=start_s,
        finish_s=finish_s,
        start_mode=start_mode,
        with_stop_box=with_stop_box,
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


def _pregenerate_curriculum(ai_level: int, ac_root: str) -> int:
    from generate_all_content import TEST_CATALOG

    pairings = {(t["track_id"], t.get("track_layout", ""), t["car_id"]) for t in TEST_CATALOG}
    print(f"[*] Pre-generating 95% AI telemetry profiles for {len(pairings)} curriculum track/car pairings...")
    count = 0
    for tid, lay, cid in sorted(pairings):
        try:
            prof = calibrate_from_spline(tid, lay, cid, ai_level, ac_root)
            save_telemetry_profile(prof)
            count += 1
            print(f"  [{count:02d}/{len(pairings)}] Cached: {tid} [{lay or 'default'}] + {cid} (lap: {prof.lap_time_s:.1f}s)")
        except Exception as e:
            print(f"  [!] Skipped {tid} [{lay}]: {e}")
    print(f"[+] Pre-generation complete! {count} telemetry profiles ready in {PROFILES_DIR}")
    return 0 if count == len(pairings) else 1


def _print_profile_summary(profile: TelemetryProfile, path: str) -> None:
    print("\n[+] 95% AI Telemetry Profile saved:")
    print(f"    Path: {path}")
    print(f"    Track: {profile.track_id} [{profile.track_layout or 'default'}]")
    print(f"    Car: {profile.car_id} | AI Level: {profile.ai_level}%")
    print(
        f"    Length: {profile.total_track_length_m:.1f}m | Lap Time: {profile.lap_time_s:.1f}s | Samples: {profile.sample_count}"
    )

    # Display sample straight speeds
    print("\n  Sample Telemetry Checkpoints:")
    for dist in [100.0, 500.0, 1000.0, 1500.0]:
        if dist < profile.total_track_length_m:
            spd, gear, rpm = profile.query_sample(dist)
            print(f"    dist {dist:6.1f}m -> Speed: {spd:5.1f} km/h | Gear: {gear} | RPM: {rpm}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assetto Corsa 100% AI Telemetry Recorder & Profiler")
    parser.add_argument("--track", type=str, help="Track ID")
    parser.add_argument("--layout", type=str, default="", help="Track layout (default: empty for base layout)")
    parser.add_argument("--car", type=str, help="Car ID")
    parser.add_argument("--ai-level", type=int, default=100, help="AI proficiency level (default: 100)")
    parser.add_argument("--live", action="store_true", help="Launch acs.exe to record live in-engine telemetry")
    parser.add_argument(
        "--all-curriculum",
        action="store_true",
        help="Pre-generate telemetry profiles for all curriculum track/car pairings",
    )
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa installation root")

    args = parser.parse_args()

    if args.all_curriculum:
        return _pregenerate_curriculum(args.ai_level, args.ac_root)

    missing = []
    if not args.track:
        missing.append("--track")
    if not args.car:
        missing.append("--car")
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

