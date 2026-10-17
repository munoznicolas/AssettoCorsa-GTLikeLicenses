#!/usr/bin/env python3
"""
extract_spline_coords.py
Assetto Corsa AI Spline & Track Coordinate Extraction Utility

Reads and samples binary Assetto Corsa AI spline files (fast_lane.ai / ideal_line.ai)
from track directories to programmatically generate:
  - Car spawn positions and normalized forward heading vectors
  - Start gate 3D planar vectors (p1, p2)
  - Finish gate 3D planar vectors (p1, p2)
  - Stop box parameters (center, size, rotation_deg)

Binary Structure of Assetto Corsa .ai files:
  - Header (16 bytes): 4x int32 (version, point_count, unknown1, unknown2)
  - Ideal Line Data (point_count * 20 bytes): 4x float32, 1x int32
      [0]: x (meters, AC world X)
      [1]: y (meters, AC world Y elevation)
      [2]: z (meters, AC world Z depth)
      [3]: dist (accumulated distance along spline in meters)
      [4]: id (waypoint sequence index)
  - Detail Line Data (point_count * 72 bytes): 18x float32
      [0]: unknown
      [1]: speed (m/s)
      [2]: gas
      [3]: brake
      [4]: obsoleteLatG
      [5]: radius (meters)
      [6]: wallLeft (distance from centerline to left track limit in meters)
      [7]: wallRight (distance from centerline to right track limit in meters)
      [8]: camber
      [9]: direction
      [10..12]: track normal vector (nx, ny, nz)
      [13]: step length to next waypoint (meters)
      [14..16]: forward tangent vector (fx, fy, fz)
      [17]: tag
"""

import argparse
import json
import math
import os
import struct
import sys
from typing import Any, List, Optional, Tuple

from tools.spline.models import (
    DEFAULT_AC_ROOT,
    GateDefinition,
    SpawnDefinition,
    SplineWaypoint,
    StopBoxDefinition,
    find_spline_file,
    generate_test_parameters,
)


class SplineParser:
    """Parser and query engine for Assetto Corsa binary AI splines."""

    MAX_WAYPOINTS = 100_000

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.waypoints: List[SplineWaypoint] = []
        self.total_length: float = 0.0
        self.version: int = 0
        self._parse()

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        f = float(val)
        return f if math.isfinite(f) else default

    def _parse(self) -> None:
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(f"Spline file not found: {self.filepath}")

        filesize = os.path.getsize(self.filepath)
        if filesize < 16:
            raise ValueError(f"File too small to be a valid .ai file: {self.filepath}")

        with open(self.filepath, "rb") as f:
            header, count, u1, u2 = struct.unpack("<4i", f.read(16))
            self.version = header

            if count <= 0 or count > self.MAX_WAYPOINTS or 16 + count * 20 > filesize:
                raise ValueError(
                    f"Corrupt or incompatible .ai header in {self.filepath}: "
                    f"point_count={count}, filesize={filesize}"
                )

            ideal_raw = [struct.unpack("<4fi", f.read(20)) for _ in range(count)]

            detail_start = 16 + count * 20
            has_details = detail_start + count * 72 <= filesize
            f.seek(detail_start)

            detail_raw: List[Tuple[Any, ...]] = []
            if has_details:
                detail_raw = [struct.unpack("<18f", f.read(72)) for _ in range(count)]

        sf = self._safe_float
        for i in range(count):
            pt = ideal_raw[i]
            x, y, z, dist, _ = sf(pt[0]), sf(pt[1]), sf(pt[2]), sf(pt[3]), pt[4]

            if has_details:
                det = detail_raw[i]
                w_left = sf(det[6], 6.0)
                w_right = sf(det[7], 6.0)
                norm = (sf(det[10], 0.0), sf(det[11], 1.0), sf(det[12], 0.0))
                fwd = (sf(det[14], 0.0), sf(det[15], 0.0), sf(det[16], 1.0))
                spd = sf(det[1], 30.0)
                rad = sf(det[5], 1000.0)
            else:
                w_left, w_right = 6.0, 6.0
                norm = (0.0, 1.0, 0.0)
                spd, rad = 30.0, 1000.0
                if i < count - 1:
                    next_pt = ideal_raw[i + 1]
                    dx, dy, dz = sf(next_pt[0]) - x, sf(next_pt[1]) - y, sf(next_pt[2]) - z
                    length = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                    fwd = (dx / length, dy / length, dz / length)
                else:
                    fwd = (0.0, 0.0, 1.0)

            flen = math.sqrt(fwd[0] ** 2 + fwd[1] ** 2 + fwd[2] ** 2)
            if math.isfinite(flen) and flen > 1e-4:
                fwd = (fwd[0] / flen, fwd[1] / flen, fwd[2] / flen)
            else:
                fwd = (0.0, 0.0, 1.0)

            nlen = math.sqrt(norm[0] ** 2 + norm[1] ** 2 + norm[2] ** 2)
            if math.isfinite(nlen) and nlen > 1e-4:
                norm = (norm[0] / nlen, norm[1] / nlen, norm[2] / nlen)
            else:
                norm = (0.0, 1.0, 0.0)

            if w_left <= 0.5:
                w_left = 6.0
            if w_right <= 0.5:
                w_right = 6.0

            self.waypoints.append(
                SplineWaypoint(
                    index=i,
                    x=x,
                    y=y,
                    z=z,
                    distance=dist,
                    wall_left=w_left,
                    wall_right=w_right,
                    normal=norm,
                    forward=fwd,
                    speed_ms=spd,
                    radius=rad,
                )
            )

        if self.waypoints:
            self.total_length = self.waypoints[-1].distance

    def query_distance(self, target_dist: float) -> Tuple[List[float], Tuple[float, float, float], float, float]:
        """
        Interpolates coordinates, heading, and track borders at a distance in meters.
        Returns: (pos [x, y, z], forward (fx, fy, fz), wall_left, wall_right)
        """
        if not self.waypoints:
            raise ValueError("No waypoints loaded in spline.")

        target_dist = (target_dist % self.total_length) if self.total_length > 0 else 0.0
        n = len(self.waypoints)

        low, high = 0, n - 1
        while low <= high:
            mid = (low + high) // 2
            if self.waypoints[mid].distance <= target_dist:
                low = mid + 1
            else:
                high = mid - 1

        idx0 = max(0, min(high, n - 1))
        idx1 = (idx0 + 1) % n
        wp0, wp1 = self.waypoints[idx0], self.waypoints[idx1]

        d0 = wp0.distance
        d1 = self.total_length if idx1 == 0 else wp1.distance
        denom = d1 - d0
        t = (target_dist - d0) / denom if denom > 1e-4 else 0.0
        t = max(0.0, min(1.0, t))

        pos = [
            round(wp0.x * (1 - t) + wp1.x * t, 3),
            round(wp0.y * (1 - t) + wp1.y * t, 3),
            round(wp0.z * (1 - t) + wp1.z * t, 3),
        ]

        fx = wp0.forward[0] * (1 - t) + wp1.forward[0] * t
        fy = wp0.forward[1] * (1 - t) + wp1.forward[1] * t
        fz = wp0.forward[2] * (1 - t) + wp1.forward[2] * t
        flen = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
        fwd = (round(fx / flen, 4), round(fy / flen, 4), round(fz / flen, 4))

        wl = round(wp0.wall_left * (1 - t) + wp1.wall_left * t, 2)
        wr = round(wp0.wall_right * (1 - t) + wp1.wall_right * t, 2)
        return pos, fwd, wl, wr

    def compute_gate(
        self,
        distance: float,
        fixed_width: Optional[float] = None,
        default_width: float = 12.0,
    ) -> GateDefinition:
        """Computes a planar gate (p1, p2) centered on the AI spline / trajectory with uniform width."""
        pos, fwd, _, _ = self.query_distance(distance)

        lx, lz = -fwd[2], fwd[0]
        llen = math.sqrt(lx * lx + lz * lz)
        if llen > 1e-4:
            lx, lz = lx / llen, lz / llen
        else:
            lx, lz = 1.0, 0.0

        width = fixed_width if (fixed_width is not None and fixed_width > 0) else default_width
        half_w = width / 2.0

        p1 = [round(pos[0] + lx * half_w, 3), round(pos[1], 3), round(pos[2] + lz * half_w, 3)]
        p2 = [round(pos[0] - lx * half_w, 3), round(pos[1], 3), round(pos[2] - lz * half_w, 3)]

        gate_width = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)
        return GateDefinition(p1=p1, p2=p2, width=round(gate_width, 2))

    def compute_stop_box(
        self,
        distance: float,
        width: float = 8.0,
        length: float = 20.0,
        height: float = 4.0,
    ) -> StopBoxDefinition:
        """Computes an oriented bounding box for acceleration & braking tests."""
        pos, fwd, _, _ = self.query_distance(distance)
        yaw_deg = math.degrees(math.atan2(fwd[0], fwd[2]))

        return StopBoxDefinition(
            center=[round(pos[0], 3), round(pos[1] + height / 2.0, 3), round(pos[2], 3)],
            size=[round(width, 1), round(height, 1), round(length, 1)],
            rotation_deg=round(yaw_deg, 2),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Assetto Corsa AI Spline Coordinate Extractor")
    parser.add_argument("--track", "-t", type=str, help="Track ID (folder in content/tracks, e.g. ks_vallelunga, magione)")
    parser.add_argument("--layout", "-l", type=str, default="", help="Layout subfolder (e.g. club_circuit, gp) or empty string")
    parser.add_argument("--file", "-f", type=str, help="Direct path to an .ai spline file (overrides --track and --layout)")
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help=f"Assetto Corsa root installation folder (default: {DEFAULT_AC_ROOT})")
    parser.add_argument("--start-s", type=float, default=0.0, help="Start gate normalized track progress [0.0 - 1.0]")
    parser.add_argument("--finish-s", type=float, default=0.1, help="Finish gate normalized track progress [0.0 - 1.0]")
    parser.add_argument("--spawn-offset", type=float, default=0.0, help="Meters before start gate to position vehicle spawn (e.g. 50 for rolling)")
    parser.add_argument("--speed", type=float, default=0.0, help="Initial spawn speed in km/h (default: 0 for standing start)")
    parser.add_argument("--gate-width", type=float, default=None, help="Optional override for timing gate width in meters")
    parser.add_argument("--stop-box", action="store_true", help="Generate stop_box parameters at finish gate")
    parser.add_argument("--stop-box-offset", type=float, default=0.0, help="Offset in meters past finish gate for stop box center")
    parser.add_argument("--info", action="store_true", help="Display track spline summary and length without generating test JSON")
    parser.add_argument("--output", "-o", type=str, help="Optional output file path to write JSON parameters")

    args = parser.parse_args()

    spline_file = args.file
    if not spline_file:
        if not args.track:
            parser.error("Either --track or --file must be specified.")
        spline_file = find_spline_file(args.track, args.layout, args.ac_root)
        if not spline_file:
            print(
                f"[ERROR] Could not find fast_lane.ai or ideal_line.ai for track '{args.track}' "
                f"(layout '{args.layout}') in {args.ac_root}",
                file=sys.stderr,
            )
            return 1

    try:
        spline = SplineParser(spline_file)
    except Exception as e:
        print(f"[ERROR] Failed to parse spline file '{spline_file}': {e}", file=sys.stderr)
        return 1

    if args.info:
        print(f"Spline File:    {spline_file}")
        print(f"Header Version: {spline.version}")
        print(f"Total Waypoints:{len(spline.waypoints)}")
        print(f"Spline Length:  {spline.total_length:.2f} meters")
        if spline.waypoints:
            p0 = spline.waypoints[0]
            print(f"Start Origin:   X={p0.x:.2f}, Y={p0.y:.2f}, Z={p0.z:.2f}")
        return 0

    result = generate_test_parameters(
        parser=spline,
        start_progress=args.start_s,
        finish_progress=args.finish_s,
        spawn_offset_m=args.spawn_offset,
        initial_speed_kmh=args.speed,
        gate_width=args.gate_width,
        with_stop_box=args.stop_box,
        stop_box_offset_m=args.stop_box_offset,
        track_id=args.track,
    )

    formatted_json = json.dumps(result, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted_json + "\n")
        print(f"[SUCCESS] Test parameters written to {args.output}")
    else:
        print(formatted_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
