#!/usr/bin/env python3
"""
tools/telemetry/profile.py
Telemetry data models, spline calibration, and profile persistence for Assetto Corsa.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.spline.parser import DEFAULT_AC_ROOT, SplineParser, find_spline_file

PROFILES_DIR = os.path.join(REPO_ROOT, "data", "telemetry_profiles")
ERR_MISSING_TRACK_ID = "Missing required parameter: track_id"
ERR_MISSING_CAR_ID = "Missing required parameter: car_id"


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

        low, high = 0, n - 1
        while low <= high:
            mid = (low + high) // 2
            if self.samples[mid].distance_m <= dist:
                low = mid + 1
            else:
                high = mid - 1

        i0 = max(0, min(high, n - 1))
        i1 = (i0 + 1) % n
        s0, s1 = self.samples[i0], self.samples[i1]

        d0 = s0.distance_m
        d1 = self.total_track_length_m if i1 == 0 else s1.distance_m

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
            curr_dist = (curr_dist - v_ms * dt + self.total_track_length_m) % self.total_track_length_m
            t_accum += dt
        return curr_dist

    def integrate_distance_forward(self, start_dist_m: float, duration_sec: float, step_dt: float = 0.05) -> float:
        """Numerically integrates forward along the velocity curve."""
        curr_dist = start_dist_m
        t_accum = 0.0
        while t_accum < duration_sec:
            spd_kmh, _, _ = self.query_sample(curr_dist)
            v_ms = max(5.0, spd_kmh / 3.6)
            dt = min(step_dt, duration_sec - t_accum)
            curr_dist = (curr_dist + v_ms * dt) % self.total_track_length_m
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
        start_dist, finish_dist = s0 * tot, s1 * tot

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
        t_accum, dist_traveled = 0.0, 0.0

        while dist_traveled < sec_len:
            curr_d = (start_dist + dist_traveled) % tot
            spd_kmh, _, _ = self.query_sample(curr_d)
            v_ms = self._effective_speed(
                max(5.0, spd_kmh / 3.6), dist_traveled, sec_len, start_mode, with_stop_box
            )
            t_accum += step / v_ms
            dist_traveled += step

        if start_mode == "STANDING" and with_stop_box:
            t_accum += 0.5
        return t_accum

    @staticmethod
    def _calculate_medal_targets(t_accum: float, start_mode: str) -> Tuple[float, float, float]:
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
        t_accum = self._integrate_traversal_time(start_dist, sec_len, start_mode, with_stop_box, step_m)
        gold, silver, bronze = self._calculate_medal_targets(t_accum, start_mode)

        return {
            "gold_seconds": gold,
            "silver_seconds": silver,
            "bronze_seconds": bronze,
            "sector_time_s": round(t_accum, 3),
            "sector_length_m": round(sec_len, 1),
        }


def _sanitize_profile_token(val: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "", str(val or ""))
    if not cleaned:
        raise ValueError(f"Invalid telemetry profile identifier: {val!r}")
    return cleaned


def profile_filename(track_id: str, layout: str, car_id: str, ai_level: int = 100) -> str:
    """Standardized profile cache filename."""
    safe_track = _sanitize_profile_token(track_id)
    safe_car = _sanitize_profile_token(car_id)
    safe_layout = _sanitize_profile_token(layout) if layout else ""
    tag = f"{safe_track}__{safe_layout}" if safe_layout else safe_track
    return f"{tag}__{safe_car}__ai{int(ai_level)}.json"


def load_telemetry_profile(
    track_id: str, layout: str, car_id: str, ai_level: int = 100
) -> Optional[TelemetryProfile]:
    """Loads a cached profile from disk if available."""
    try:
        real_profiles_dir = os.path.realpath(PROFILES_DIR)
    except Exception:
        return None

    levels_to_try = [ai_level]
    for fallback_lvl in (100, 95):
        if fallback_lvl not in levels_to_try:
            levels_to_try.append(fallback_lvl)

    path = None
    for lvl in levels_to_try:
        try:
            fname = profile_filename(track_id, layout, car_id, lvl)
        except ValueError:
            return None
        p = os.path.realpath(os.path.join(real_profiles_dir, fname))
        if os.path.commonpath([real_profiles_dir, p]) == real_profiles_dir and os.path.isfile(p):
            path = p
            break

    if not path:
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = [TelemetrySample(**s) for s in data["samples"]]
        recorded_at = data.get("recorded_at") or datetime.fromtimestamp(
            os.path.getmtime(path), tz=timezone.utc
        ).isoformat()
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
    real_profiles_dir = os.path.realpath(PROFILES_DIR)
    os.makedirs(real_profiles_dir, exist_ok=True)
    fname = profile_filename(profile.track_id, profile.track_layout, profile.car_id, profile.ai_level)
    path = os.path.realpath(os.path.join(real_profiles_dir, fname))
    if os.path.commonpath([real_profiles_dir, path]) != real_profiles_dir:
        raise ValueError(f"Refusing to write telemetry profile outside {real_profiles_dir}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2)
    return path


def estimate_gear_and_rpm(speed_kmh: float) -> Tuple[int, int]:
    """Estimates realistic gear and RPM for road/GT cars from speed."""
    if speed_kmh < 40.0:
        return 1, int(2500 + speed_kmh * 70)
    if speed_kmh < 75.0:
        return 2, int(3000 + (speed_kmh - 40) * 85)
    if speed_kmh < 115.0:
        return 3, int(3500 + (speed_kmh - 75) * 65)
    if speed_kmh < 160.0:
        return 4, int(4200 + (speed_kmh - 115) * 55)
    if speed_kmh < 210.0:
        return 5, int(4800 + (speed_kmh - 160) * 45)
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

        samples.append(
            TelemetrySample(
                progress=round(prog, 4),
                distance_m=round(w.distance, 2),
                speed_kmh=round(spd_kmh, 1),
                gear=gear,
                rpm=rpm,
                steer_norm=round(w.forward[0] * 0.05, 3),
            )
        )

    return TelemetryProfile(
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
    print("\n  Sample Telemetry Checkpoints:")
    for dist in [100.0, 500.0, 1000.0, 1500.0]:
        if dist < profile.total_track_length_m:
            spd, gear, rpm = profile.query_sample(dist)
            print(f"    dist {dist:6.1f}m -> Speed: {spd:5.1f} km/h | Gear: {gear} | RPM: {rpm}")
