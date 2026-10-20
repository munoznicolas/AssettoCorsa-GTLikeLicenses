#!/usr/bin/env python3
"""
track_straight_analyzer.py
Assetto Corsa Spline Kinematics & Straight Segment Detection Engine

Analyzes binary Assetto Corsa AI splines (fast_lane.ai) to find straight segments
suitable for rolling start license tests.

Kinematic Model:
  delta_road = arctan(wheelbase / radius) ~= wheelbase / radius (radians)
  delta_wheel = delta_road * steer_ratio * (180.0 / pi) (degrees)
"""

import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.spline.parser import (
    DEFAULT_AC_ROOT,
    SplineParser,
    SplineWaypoint,
    find_spline_file,
)
from tools.telemetry.recorder import (
    TelemetryProfile,
    TelemetrySample,
    calibrate_from_spline,
    estimate_gear_and_rpm,
    load_telemetry_profile,
)
from tools.spline.models import (
    RollingStartCandidate,
    StraightSegment,
    angle_diff_deg,
    compass_heading_to_label,
)


class TrackStraightAnalyzer:
    """
    Kinematic analyzer and candidate detector for Assetto Corsa AI splines.
    """

    def __init__(
        self,
        parser: SplineParser,
        track_id: str = "",
        layout: str = "",
        wheelbase_m: float = 2.5,
        steer_ratio: float = 14.5,
        car_id: str = "ks_mazda_miata",
        telemetry_profile: Optional[TelemetryProfile] = None,
    ):
        self.parser = parser
        self.track_id = track_id
        self.layout = layout
        self.wheelbase = wheelbase_m
        self.steer_ratio = steer_ratio
        self.car_id = car_id
        self.total_length = parser.total_length
        self.waypoints = parser.waypoints
        self.num_waypoints = len(parser.waypoints)

        # Ground-truth 95% AI Telemetry Profile
        if telemetry_profile is not None:
            self.telemetry = telemetry_profile
        else:
            cached = load_telemetry_profile(track_id, layout, car_id, 95) if track_id else None
            if cached is not None:
                self.telemetry = cached
            elif track_id:
                try:
                    self.telemetry = calibrate_from_spline(track_id, layout, car_id, 95)
                except Exception:
                    self.telemetry = self._synthetic_profile(track_id, layout, car_id)
            else:
                self.telemetry = self._synthetic_profile(track_id, layout, car_id)

    def _synthetic_profile(self, track_id: str, layout: str, car_id: str) -> TelemetryProfile:
        samples = []
        if self.waypoints:
            for w in self.waypoints:
                spd = max(40.0, w.speed_ms * 3.6 if hasattr(w, "speed_ms") and w.speed_ms > 0 else 70.0)
                g, r = estimate_gear_and_rpm(spd)
                samples.append(
                    TelemetrySample(
                        progress=round(w.distance / self.total_length, 4) if self.total_length > 0 else 0.0,
                        distance_m=w.distance,
                        speed_kmh=round(spd, 1),
                        gear=g,
                        rpm=r,
                    )
                )
        return TelemetryProfile(
            track_id=track_id,
            track_layout=layout,
            car_id=car_id,
            ai_level=95,
            source="synthetic",
            total_track_length_m=self.total_length,
            lap_time_s=60.0,
            sample_count=len(samples),
            samples=samples,
        )

    def compute_steering_angle_deg(self, radius_m: float) -> float:
        """
        Converts turn radius to estimated physical steering wheel angle.
        delta_wheel = arctan(wheelbase / radius) * steer_ratio * (180 / pi)
        """
        if radius_m <= 0.1 or math.isinf(radius_m) or math.isnan(radius_m):
            return 0.0
        delta_road_rad = math.atan2(self.wheelbase, radius_m)
        delta_wheel_deg = delta_road_rad * self.steer_ratio * (180.0 / math.pi)
        return float(delta_wheel_deg)

    def find_straight_segments(
        self,
        max_steer_deg: float = 2.0,
        min_length_m: float = 60.0,
        max_heading_dev_deg: float = 3.5,
        bridge_gap_m: float = 12.0,
    ) -> List[StraightSegment]:
        """
        Extracts all contiguous straight segments meeting kinematic tolerance,
        handling bridge gaps and circular track lap wrap-around.
        """
        if not self.waypoints or self.total_length <= 0:
            return []

        n = self.num_waypoints
        steer_angles = [self.compute_steering_angle_deg(w.radius) for w in self.waypoints]

        headings = [
            (math.degrees(math.atan2(w.forward[0], w.forward[2])) + 360.0) % 360.0
            for w in self.waypoints
        ]

        is_straight = [sa <= max_steer_deg for sa in steer_angles]

        raw_runs: List[Tuple[int, int]] = []
        start_idx: Optional[int] = None
        for i in range(n):
            if is_straight[i]:
                if start_idx is None:
                    start_idx = i
            elif start_idx is not None:
                raw_runs.append((start_idx, i - 1))
                start_idx = None
        if start_idx is not None:
            raw_runs.append((start_idx, n - 1))

        if not raw_runs:
            return []

        bridged_runs: List[Tuple[int, int]] = []
        curr_start, curr_end = raw_runs[0]

        for next_start, next_end in raw_runs[1:]:
            gap_dist = self.waypoints[next_start].distance - self.waypoints[curr_end].distance
            h_diff = angle_diff_deg(headings[curr_end], headings[next_start])
            gap_max_steer = max(steer_angles[curr_end + 1 : next_start]) if next_start > curr_end + 1 else 0.0

            if 0 < gap_dist <= bridge_gap_m and h_diff <= max_heading_dev_deg and gap_max_steer <= 5.0:
                curr_end = next_end
            else:
                bridged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        bridged_runs.append((curr_start, curr_end))

        final_runs: List[Dict[str, Any]] = []
        wraps_first_last = False

        if len(bridged_runs) >= 2:
            first_start, first_end = bridged_runs[0]
            last_start, last_end = bridged_runs[-1]

            gap_to_zero = self.waypoints[first_start].distance
            gap_to_end = self.total_length - self.waypoints[last_end].distance
            wrap_gap = gap_to_zero + gap_to_end
            wrap_h_diff = angle_diff_deg(headings[last_end], headings[first_start])

            if wrap_gap <= bridge_gap_m and wrap_h_diff <= max_heading_dev_deg:
                wraps_first_last = True
                wrapped_indices = list(range(last_start, n)) + list(range(0, first_end + 1))
                wrapped_length = (
                    self.total_length - self.waypoints[last_start].distance
                ) + self.waypoints[first_end].distance

                if wrapped_length >= min_length_m:
                    final_runs.append({
                        "start_idx": last_start,
                        "end_idx": first_end,
                        "indices": wrapped_indices,
                        "length": wrapped_length,
                        "start_dist": self.waypoints[last_start].distance,
                        "end_dist": self.waypoints[first_end].distance,
                        "wraps_lap": True,
                    })

                for s_idx, e_idx in bridged_runs[1:-1]:
                    l_dist = self.waypoints[e_idx].distance - self.waypoints[s_idx].distance
                    if l_dist >= min_length_m:
                        final_runs.append({
                            "start_idx": s_idx,
                            "end_idx": e_idx,
                            "indices": list(range(s_idx, e_idx + 1)),
                            "length": l_dist,
                            "start_dist": self.waypoints[s_idx].distance,
                            "end_dist": self.waypoints[e_idx].distance,
                            "wraps_lap": False,
                        })

        if not wraps_first_last:
            for s_idx, e_idx in bridged_runs:
                l_dist = self.waypoints[e_idx].distance - self.waypoints[s_idx].distance
                if l_dist >= min_length_m:
                    final_runs.append({
                        "start_idx": s_idx,
                        "end_idx": e_idx,
                        "indices": list(range(s_idx, e_idx + 1)),
                        "length": l_dist,
                        "start_dist": self.waypoints[s_idx].distance,
                        "end_dist": self.waypoints[e_idx].distance,
                        "wraps_lap": False,
                    })

        segments: List[StraightSegment] = []
        for seg_idx, run in enumerate(final_runs, start=1):
            indices = run["indices"]
            seg_wps = [self.waypoints[i] for i in indices]
            seg_steers = [steer_angles[i] for i in indices]
            seg_radii = [w.radius for w in seg_wps if w.radius > 0]
            seg_speeds = [w.speed_ms * 3.6 for w in seg_wps]
            seg_headings = [headings[i] for i in indices]

            seg_headings_clean = [
                h for h in seg_headings if angle_diff_deg(h, seg_headings[len(seg_headings) // 2]) < 90.0
            ]
            if seg_headings_clean:
                sorted_clean = sorted(seg_headings_clean)
                ref_heading = sorted_clean[len(sorted_clean) // 2]
            else:
                ref_heading = seg_headings[0]

            h_devs = [angle_diff_deg(h, ref_heading) for h in seg_headings_clean]
            max_h_dev = max(h_devs) if h_devs else 0.0

            if max_h_dev > max_heading_dev_deg * 2.0:
                continue

            chord_heading = ref_heading
            start_wp = self.waypoints[run["start_idx"]]
            end_wp = self.waypoints[run["end_idx"]]

            start_dist = run["start_dist"]
            end_dist = run["end_dist"]
            seg_len = run["length"]

            segments.append(
                StraightSegment(
                    segment_id=seg_idx,
                    start_distance_m=round(start_dist, 2),
                    end_distance_m=round(end_dist, 2),
                    length_m=round(seg_len, 2),
                    start_progress=round(start_dist / self.total_length, 4),
                    end_progress=round(end_dist / self.total_length, 4),
                    start_waypoint_idx=run["start_idx"],
                    end_waypoint_idx=run["end_idx"],
                    waypoint_count=len(indices),
                    max_steer_deg=round(max(seg_steers) if seg_steers else 0.0, 2),
                    avg_steer_deg=round(sum(seg_steers) / len(seg_steers) if seg_steers else 0.0, 2),
                    min_radius_m=round(min(seg_radii) if seg_radii else 99999.0, 1),
                    avg_radius_m=round(sum(seg_radii) / len(seg_radii) if seg_radii else 99999.0, 1),
                    max_heading_dev_deg=round(max_h_dev, 2),
                    compass_heading_deg=round(chord_heading, 1),
                    compass_direction=compass_heading_to_label(chord_heading),
                    avg_ai_speed_kmh=round(sum(seg_speeds) / len(seg_speeds) if seg_speeds else 0.0, 1),
                    min_ai_speed_kmh=round(min(seg_speeds) if seg_speeds else 0.0, 1),
                    max_ai_speed_kmh=round(max(seg_speeds) if seg_speeds else 0.0, 1),
                    wraps_lap=run["wraps_lap"],
                    start_pos=[round(start_wp.x, 2), round(start_wp.y, 2), round(start_wp.z, 2)],
                    end_pos=[round(end_wp.x, 2), round(end_wp.y, 2), round(end_wp.z, 2)],
                )
            )

        segments.sort(key=lambda s: s.length_m, reverse=True)
        for idx, seg in enumerate(segments, start=1):
            seg.segment_id = idx

        return segments

    def evaluate_rolling_candidates(
        self,
        segments: List[StraightSegment],
        countdown_sec: float = 3.0,
        post_go_sec: float = 1.5,
        target_speed_kmh: Optional[float] = None,
        post_go_margin_m: Optional[float] = None,
    ) -> List[RollingStartCandidate]:
        """
        Calculates optimal rolling start test placements for each straight segment
        using ground-truth 95% AI telemetry speeds, engaged gears, and RPMs.
        """
        candidates: List[RollingStartCandidate] = []

        for seg in segments:
            if target_speed_kmh is not None and target_speed_kmh > 0:
                effective_sec = post_go_sec
                effective_margin_m = (
                    (target_speed_kmh / 3.6) * post_go_sec if post_go_margin_m is None else post_go_margin_m
                )
                gate_dist = (seg.end_distance_m - effective_margin_m + self.total_length) % self.total_length
                countdown_dist = (target_speed_kmh / 3.6) * countdown_sec
                spawn_dist = (gate_dist - countdown_dist + self.total_length) % self.total_length
                handover_spd = target_speed_kmh
                spawn_spd = target_speed_kmh
                engaged_gear, engine_rpm = estimate_gear_and_rpm(target_speed_kmh)
            else:
                if post_go_margin_m is not None:
                    gate_dist = (seg.end_distance_m - post_go_margin_m + self.total_length) % self.total_length
                    effective_margin_m = post_go_margin_m
                    gate_spd, _, _ = self.telemetry.query_sample(gate_dist)
                    effective_sec = round(effective_margin_m / (gate_spd / 3.6), 2) if gate_spd > 0 else post_go_sec
                else:
                    effective_sec = post_go_sec
                    gate_dist = self.telemetry.integrate_distance_backward(seg.end_distance_m, post_go_sec)
                    effective_margin_m = (seg.end_distance_m - gate_dist + self.total_length) % self.total_length

                spawn_dist = self.telemetry.integrate_distance_backward(gate_dist, countdown_sec)
                countdown_dist = (gate_dist - spawn_dist + self.total_length) % self.total_length

                handover_spd, engaged_gear, engine_rpm = self.telemetry.query_sample(gate_dist)
                spawn_spd, _, _ = self.telemetry.query_sample(spawn_dist)

            min_required_len = countdown_dist + effective_margin_m
            if seg.length_m < min_required_len:
                continue

            spawn_pos, spawn_fwd, _, _ = self.parser.query_distance(spawn_dist)
            gate_def = self.parser.compute_gate(gate_dist)

            steer_penalty = min(50.0, seg.max_steer_deg * 15.0)
            length_bonus = min(30.0, seg.length_m / 10.0)
            heading_penalty = min(20.0, seg.max_heading_dev_deg * 5.0)
            score = round(max(0.0, 90.0 - steer_penalty + length_bonus - heading_penalty), 1)

            start_s = round(gate_dist / self.total_length, 4)
            spawn_s = round(spawn_dist / self.total_length, 4)
            spawn_offset = round(countdown_dist, 1)

            snippet = {
                "track_id": self.track_id or "track_id",
                "track_layout": self.layout,
                "car_id": self.car_id,
                "start_mode": "ROLLING",
                "start_s": start_s,
                "spawn_offset": spawn_offset,
                "speed": round(handover_spd, 1),
                "gear": engaged_gear,
                "rpm": engine_rpm,
            }

            desc = (
                f"Straight #{seg.segment_id} ({seg.length_m:.0f}m, {seg.compass_direction}): "
                f"95% AI handover at {handover_spd:.1f} km/h (Gear {engaged_gear}, {engine_rpm} RPM), "
                f"leaving {effective_sec:.1f}s ({effective_margin_m:.0f}m) straight time before corner."
            )

            candidates.append(
                RollingStartCandidate(
                    candidate_id=f"SEG_{seg.segment_id}_CORNER",
                    segment_id=seg.segment_id,
                    rank=0,
                    score=score,
                    placement_type="exit_corner_approach",
                    target_speed_kmh=round(handover_spd, 1),
                    spawn_speed_kmh=round(spawn_spd, 1),
                    engaged_gear=engaged_gear,
                    engine_rpm=engine_rpm,
                    countdown_sec=round(countdown_sec, 1),
                    countdown_distance_m=round(countdown_dist, 1),
                    post_go_sec=round(effective_sec, 2),
                    post_go_margin_m=round(effective_margin_m, 1),
                    start_gate_distance_m=round(gate_dist, 2),
                    start_gate_progress=start_s,
                    spawn_distance_m=round(spawn_dist, 2),
                    spawn_progress=spawn_s,
                    spawn_offset_m=spawn_offset,
                    spawn_pos=[round(p, 3) for p in spawn_pos],
                    spawn_forward=[round(f, 4) for f in spawn_fwd],
                    start_gate_p1=[round(p, 3) for p in gate_def.p1],
                    start_gate_p2=[round(p, 3) for p in gate_def.p2],
                    gate_width_m=gate_def.width,
                    max_countdown_steer_deg=seg.max_steer_deg,
                    description=desc,
                    test_config_snippet=snippet,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        for rank, cand in enumerate(candidates, start=1):
            cand.rank = rank

        return candidates

    def export_full_analysis(
        self,
        max_steer_deg: float = 2.0,
        min_length_m: float = 60.0,
        countdown_sec: float = 3.0,
        post_go_sec: float = 1.5,
        target_speed_kmh: Optional[float] = None,
        post_go_margin_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generates full serializable dictionary summary."""
        straights = self.find_straight_segments(max_steer_deg=max_steer_deg, min_length_m=min_length_m)
        candidates = self.evaluate_rolling_candidates(
            segments=straights,
            countdown_sec=countdown_sec,
            post_go_sec=post_go_sec,
            target_speed_kmh=target_speed_kmh,
            post_go_margin_m=post_go_margin_m,
        )

        return {
            "track_id": self.track_id,
            "track_layout": self.layout,
            "car_id": self.car_id,
            "total_track_length_m": round(self.total_length, 2),
            "waypoint_count": self.num_waypoints,
            "telemetry_source": self.telemetry.source,
            "telemetry_lap_time_s": self.telemetry.lap_time_s,
            "parameters": {
                "max_steer_deg": max_steer_deg,
                "min_length_m": min_length_m,
                "countdown_sec": countdown_sec,
                "post_go_sec": post_go_sec,
                "wheelbase_m": self.wheelbase,
                "steer_ratio": self.steer_ratio,
            },
            "straight_segments_count": len(straights),
            "candidates_count": len(candidates),
            "straight_segments": [s.to_dict() for s in straights],
            "candidates": [c.to_dict() for c in candidates],
        }
