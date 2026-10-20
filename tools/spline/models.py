#!/usr/bin/env python3
"""
tools/spline/models.py
Shared data models and coordinate extraction helpers for Assetto Corsa AI splines.
"""

from dataclasses import asdict, dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Tuple

def _discover_default_ac_root() -> str:
    """Resolves Assetto Corsa root directory via AC_ROOT env var or common Steam library paths."""
    env_root = os.environ.get("AC_ROOT")
    if env_root and os.path.isdir(env_root):
        return env_root
    candidates = [
        r"D:\SteamLibrary\steamapps\common\assettocorsa",
        r"C:\Program Files (x86)\Steam\steamapps\common\assettocorsa",
        r"C:\SteamLibrary\steamapps\common\assettocorsa",
        r"E:\SteamLibrary\steamapps\common\assettocorsa",
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return env_root or candidates[0]


DEFAULT_AC_ROOT = _discover_default_ac_root()


@dataclass
class SplineWaypoint:
    """Represents a single decoded waypoint from an AC AI spline."""
    index: int
    x: float
    y: float
    z: float
    distance: float
    wall_left: float
    wall_right: float
    normal: Tuple[float, float, float]
    forward: Tuple[float, float, float]
    speed_ms: float
    radius: float


@dataclass
class GateDefinition:
    """3D coordinates for a timing gate."""
    p1: List[float]
    p2: List[float]
    width: float


@dataclass
class SpawnDefinition:
    """Spawn parameters for a test definition."""
    position: List[float]
    forward_vector: List[float]
    initial_speed_kmh: float


@dataclass
class StopBoxDefinition:
    """Stop box bounding parameters."""
    center: List[float]
    size: List[float]
    rotation_deg: float


@dataclass
class StraightSegment:
    """Represents a contiguous straight segment along the track spline."""
    segment_id: int
    start_distance_m: float
    end_distance_m: float
    length_m: float
    start_progress: float
    end_progress: float
    start_waypoint_idx: int
    end_waypoint_idx: int
    waypoint_count: int
    max_steer_deg: float
    avg_steer_deg: float
    min_radius_m: float
    avg_radius_m: float
    max_heading_dev_deg: float
    compass_heading_deg: float
    compass_direction: str
    avg_ai_speed_kmh: float
    min_ai_speed_kmh: float
    max_ai_speed_kmh: float
    wraps_lap: bool
    start_pos: List[float] = field(default_factory=list)
    end_pos: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RollingStartCandidate:
    """Candidate rolling start test placement within a straight segment."""
    candidate_id: str
    segment_id: int
    rank: int
    score: float
    placement_type: str  # "exit_corner_approach" or "entry_full_straight"
    target_speed_kmh: float  # Ground-truth 95% AI handover speed
    spawn_speed_kmh: float   # 95% AI speed at countdown spawn
    engaged_gear: int        # 95% AI engaged transmission gear at handover
    engine_rpm: int          # 95% AI engine RPM at handover
    countdown_sec: float
    countdown_distance_m: float
    post_go_sec: float
    post_go_margin_m: float
    start_gate_distance_m: float
    start_gate_progress: float
    spawn_distance_m: float
    spawn_progress: float
    spawn_offset_m: float
    spawn_pos: List[float]
    spawn_forward: List[float]
    start_gate_p1: List[float]
    start_gate_p2: List[float]
    gate_width_m: float
    max_countdown_steer_deg: float
    description: str
    test_config_snippet: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compass_heading_to_label(deg: float) -> str:
    """Converts a heading angle in [0, 360) to 16-point compass direction."""
    deg = deg % 360.0
    labels = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return labels[idx]


def angle_diff_deg(a: float, b: float) -> float:
    """Computes minimum angular difference in degrees between two angles in [0, 360)."""
    diff = (a - b + 180.0) % 360.0 - 180.0
    return abs(diff)


def find_spline_file(
    track_id: str,
    layout: str = "",
    ac_root: str = DEFAULT_AC_ROOT,
) -> Optional[str]:
    """Locates fast_lane.ai or ideal_line.ai inside the Assetto Corsa track directory."""
    if not track_id or not re.match(r"^[A-Za-z0-9_\-]+$", str(track_id)):
        return None
    if layout and not re.match(r"^[A-Za-z0-9_\-]+$", str(layout)):
        return None

    tracks_root = os.path.realpath(os.path.join(ac_root, "content", "tracks"))
    track_base = os.path.realpath(os.path.join(tracks_root, track_id))
    try:
        if os.path.commonpath([tracks_root, track_base]) != tracks_root:
            return None
    except ValueError:
        return None
    if not os.path.isdir(track_base):
        return None

    candidate_subdirs = []
    if layout:
        lay_dir = os.path.realpath(os.path.join(track_base, layout))
        if os.path.commonpath([track_base, lay_dir]) == track_base:
            candidate_subdirs.append(lay_dir)
    candidate_subdirs.append(track_base)

    filename_candidates = [
        os.path.join("ai", "fast_lane.ai"),
        os.path.join("data", "ideal_line.ai"),
        os.path.join("data", "ideal_lane.ai"),
        os.path.join("ai", "ideal_line.ai"),
    ]

    for subdir in candidate_subdirs:
        for rel_file in filename_candidates:
            p = os.path.realpath(os.path.join(subdir, rel_file))
            if os.path.commonpath([track_base, p]) == track_base and os.path.isfile(p):
                return p

    return None


def generate_test_parameters(
    parser: Any,
    start_progress: float,
    finish_progress: float,
    spawn_offset_m: float = 0.0,
    initial_speed_kmh: float = 0.0,
    gate_width: Optional[float] = None,
    with_stop_box: bool = False,
    stop_box_offset_m: float = 0.0,
    gear: Optional[int] = None,
    rpm: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Generates schema-compliant spawn and timing dictionaries centered on trajectory."""
    total_len = parser.total_length

    start_dist = start_progress * total_len
    finish_dist = finish_progress * total_len

    start_gate = parser.compute_gate(start_dist, fixed_width=gate_width)
    finish_gate = parser.compute_gate(finish_dist, fixed_width=gate_width)

    # Spawn position: offset meters before start gate
    spawn_dist = (start_dist - spawn_offset_m) % total_len
    spawn_pos, spawn_fwd, _, _ = parser.query_distance(spawn_dist)

    timing_dict: Dict[str, Any] = {
        "start_gate": {
            "p1": start_gate.p1,
            "p2": start_gate.p2,
        },
        "finish_gate": {
            "p1": finish_gate.p1,
            "p2": finish_gate.p2,
        },
    }

    if with_stop_box:
        box_dist = finish_dist + stop_box_offset_m
        stop_box = parser.compute_stop_box(box_dist)
        timing_dict["stop_box"] = asdict(stop_box)

    spawn_dict: Dict[str, Any] = {
        "position": spawn_pos,
        "forward_vector": list(spawn_fwd),
        "initial_speed_kmh": round(initial_speed_kmh, 1),
    }
    if gear is not None:
        spawn_dict["gear"] = int(gear)
    if rpm is not None:
        spawn_dict["rpm"] = int(rpm)

    metadata = {
        "track_total_length_m": round(total_len, 2),
        "start_gate_distance_m": round(start_dist, 2),
        "finish_gate_distance_m": round(finish_dist, 2),
        "sector_distance_m": round((finish_dist - start_dist) % total_len, 2),
        "start_gate_width_m": start_gate.width,
        "finish_gate_width_m": finish_gate.width,
    }

    return {
        "spawn": spawn_dict,
        "timing": timing_dict,
        "_metadata": metadata,
    }
