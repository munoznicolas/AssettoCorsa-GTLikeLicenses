#!/usr/bin/env python3
"""
circuit_mapper.py
Assetto Corsa Rolling Start Straight Line Analyzer & Interactive Circuit Mapper.

Discovers and analyzes track segments where AI splines go in a straight line,
enabling precise, predictable rolling start test placement with 0-degree steering.

Generates:
  1. Rich CLI terminal summary tables
  2. Standalone interactive HTML circuit map with live, real-time client-side
     parameter adjustment sliders
  3. JSON export for curriculum integration into tools/generate_all_content.py
"""

import argparse
import json
import math
import os
import sys
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.spline.parser import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)
from tools.spline.straight_analyzer import (
    RollingStartCandidate,
    StraightSegment,
    TrackStraightAnalyzer,
)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "circuit_mapper.html")

OFFICIAL_KUNOS_TRACKS = [
    "imola",
    "ks_barcelona",
    "ks_brands_hatch",
    "ks_drag",
    "ks_highlands",
    "ks_laguna_seca",
    "ks_monza66",
    "ks_nordschleife",
    "ks_nurburgring",
    "ks_red_bull_ring",
    "ks_silverstone",
    "ks_silverstone1967",
    "ks_vallelunga",
    "ks_zandvoort",
    "magione",
    "monza",
    "mugello",
    "spa",
    "drift",
]

CURRICULUM_TRACKS = [
    ("ks_vallelunga", "club_circuit"),
    ("ks_vallelunga", "classic_circuit"),
    ("ks_vallelunga", "extended_circuit"),
    ("monza", ""),
    ("spa", ""),
    ("magione", ""),
    ("mugello", ""),
    ("imola", ""),
    ("ks_silverstone", "national"),
    ("ks_silverstone", "gp"),
    ("ks_silverstone1967", ""),
    ("ks_brands_hatch", "indy"),
    ("ks_brands_hatch", "gp"),
    ("ks_nurburgring", "layout_sprint_a"),
    ("ks_nurburgring", "layout_gp_a"),
    ("ks_barcelona", "layout_gp"),
    ("ks_red_bull_ring", "layout_national"),
    ("ks_red_bull_ring", "layout_gp"),
    ("ks_laguna_seca", ""),
    ("ks_zandvoort", ""),
    ("ks_highlands", "layout_short"),
    ("ks_monza66", "road"),
    ("ks_nordschleife", "nordschleife"),
    ("drift", "karting"),
    ("ks_drag", "drag200"),
    ("ks_drag", "drag500"),
    ("ks_drag", "drag1000"),
]


def discover_kunos_tracks(ac_root: str = DEFAULT_AC_ROOT) -> List[Tuple[str, str, str]]:
    """
    Discovers all official Kunos tracks and configurations with valid AI splines.
    Returns: List of (track_id, layout, spline_path)
    """
    tracks_dir = os.path.join(ac_root, "content", "tracks")
    if not os.path.isdir(tracks_dir):
        return []

    discovered: List[Tuple[str, str, str]] = []
    seen = set()

    for track_id in OFFICIAL_KUNOS_TRACKS:
        tdir = os.path.join(tracks_dir, track_id)
        if not os.path.isdir(tdir):
            continue

        sf_def = find_spline_file(track_id, "", ac_root)
        subdirs = [
            s
            for s in sorted(os.listdir(tdir))
            if os.path.isdir(os.path.join(tdir, s))
            and s not in ("ui", "ai", "data", "skins", "texture")
            and not s.endswith("_wet")
            and not s.endswith("_osrw")
        ]

        if not subdirs and sf_def:
            key = (track_id, "")
            if key not in seen:
                seen.add(key)
                discovered.append((track_id, "", sf_def))
        else:
            found_sub = False
            for sub in subdirs:
                sf_sub = find_spline_file(track_id, sub, ac_root)
                if sf_sub:
                    key = (track_id, sub)
                    if key not in seen:
                        seen.add(key)
                        discovered.append((track_id, sub, sf_sub))
                        found_sub = True
            if not found_sub and sf_def:
                key = (track_id, "")
                if key not in seen:
                    seen.add(key)
                    discovered.append((track_id, "", sf_def))

    return discovered


def serialize_spline_data(
    parser: SplineParser,
    analyzer: Optional[TrackStraightAnalyzer] = None,
) -> Dict[str, Any]:
    """Serializes spline waypoints into compact structure with 95% AI telemetry for client-side JS."""
    wps = []
    for w in parser.waypoints:
        if analyzer and analyzer.telemetry:
            spd, gear, rpm = analyzer.telemetry.query_sample(w.distance)
        else:
            spd = w.speed_ms * 3.6
            gear, rpm = 3, 4000
        wps.append([
            round(w.x, 2),
            round(w.z, 2),
            round(w.distance, 2),
            round(w.radius, 1),
            round(w.forward[0], 4),
            round(w.forward[2], 4),
            round(spd, 1),
            int(gear),
            int(rpm),
        ])

    return {
        "total_length": round(parser.total_length, 2),
        "waypoints": wps,
    }


def print_cli_summary(analysis: Dict[str, Any]) -> None:
    """Prints a clean, formatted terminal summary."""
    t_id = analysis["track_id"]
    layout = analysis["track_layout"] or "(default)"
    total_len = analysis["total_track_length_m"]
    params = analysis["parameters"]
    car_id = analysis.get("car_id", "ks_mazda_miata")
    tel_src = analysis.get("telemetry_source", "cached")
    lap_time = analysis.get("telemetry_lap_time_s", 0.0)

    print("\n" + "=" * 80)
    print(f"  ASSETTO CORSA ROLLING START CANDIDATE ANALYZER")
    print(f"  Track: {t_id} [{layout}] | Circuit Length: {total_len:.1f}m")
    print(f"  Proficient 95% AI Profile: {car_id} ({tel_src}, Flying Lap: {lap_time:.1f}s)")
    print(f"  Kinematic Tolerance: ±{params['max_steer_deg']:.1f}° steer | Min Length: {params['min_length_m']:.0f}m")
    print(f"  Countdown Duration: {params['countdown_sec']:.1f}s | Post-'GO!' Straight Time: {params['post_go_sec']:.1f}s")
    print("=" * 80)

    straights = analysis["straight_segments"]
    if not straights:
        print("  [!] No straight segments found meeting the current criteria.")
        print("      Try increasing --max-steer-deg or decreasing --min-length.")
        print("-" * 80)
        return

    print(f"\n  [1] DETECTED STRAIGHT SEGMENTS ({len(straights)} found):")
    print(f"  {'#':<3} {'Start (m)':<10} {'End (m)':<10} {'Length':<10} {'Max Steer':<11} {'Heading':<12} {'AI Spd':<10} {'Notes'}")
    print("  " + "-" * 76)
    for s in straights:
        notes = "Wraps finish line" if s["wraps_lap"] else ""
        print(
            f"  {s['segment_id']:<3} "
            f"{s['start_distance_m']:<10.1f} "
            f"{s['end_distance_m']:<10.1f} "
            f"{s['length_m']:<10.1f} "
            f"±{s['max_steer_deg']:<9.2f}° "
            f"{s['compass_heading_deg']:<5.1f}° {s['compass_direction']:<4} "
            f"{s['avg_ai_speed_kmh']:<10.1f} "
            f"{notes}"
        )

    candidates = analysis["candidates"]
    print(f"\n  [2] RECOMMENDED ROLLING START CANDIDATES ({len(candidates)} viable):")
    print(f"  {'Rank':<5} {'Score':<7} {'Start Gate (s)':<16} {'Run-up (m)':<14} {'95% AI Spd':<12} {'Gear/RPM':<12} {'Post-GO (m)'}")
    print("  " + "-" * 80)
    for c in candidates:
        print(
            f"  #{c['rank']:<4} "
            f"{c['score']:<7.1f} "
            f"dist {c['start_gate_distance_m']:.1f}m (s={c['start_gate_progress']:.4f})  "
            f"{c['spawn_offset_m']:.1f}m ({c['countdown_sec']:.1f}s) "
            f"{c['target_speed_kmh']:.1f} km/h   "
            f"G{c['engaged_gear']} @ {c['engine_rpm']}   "
            f"{c['post_go_margin_m']:.1f}m ({c['post_go_sec']:.1f}s)"
        )

    if candidates:
        top = candidates[0]
        print(f"\n  [3] TOP CANDIDATE CURRICULUM DEFINITION (Ready for generate_all_content.py):")
        print("  " + "-" * 76)
        snip = top["test_config_snippet"]
        print("  " + json.dumps(snip, indent=4).replace("\n", "\n  "))

    print("=" * 80 + "\n")


def generate_interactive_html(
    tracks_payload: Dict[str, Any],
    initial_track_key: str,
    output_html_path: str,
    default_params: Dict[str, Any],
) -> None:
    """Generates a standalone, self-contained interactive HTML circuit map."""
    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)

    tracks_json_str = json.dumps(tracks_payload)
    default_params_json_str = json.dumps(default_params)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    rendered = (
        template
        .replace("__INITIAL_TRACK_KEY__", initial_track_key)
        .replace("__TRACKS_JSON__", tracks_json_str)
        .replace("__DEFAULT_PARAMS_JSON__", default_params_json_str)
    )

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(rendered)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Assetto Corsa Rolling Start Straight Line Analyzer & Interactive Circuit Mapper"
    )
    parser.add_argument("--track", type=str, default="", help="Track ID (e.g. ks_vallelunga, monza, spa)")
    parser.add_argument("--layout", type=str, default="", help="Track layout (e.g. club_circuit, gp, national)")
    parser.add_argument("--all-kunos", action="store_true", help="Batch analyze all official Kunos tracks")
    parser.add_argument("--curriculum", action="store_true", help="Batch analyze all 27 tracks used across GT license tests")
    parser.add_argument("--max-steer-deg", type=float, default=2.0, help="Max steering wheel error tolerance in degrees (default: 2.0)")
    parser.add_argument("--min-length", type=float, default=60.0, help="Min straight segment length in meters (default: 60.0)")
    parser.add_argument("--car", type=str, default="ks_mazda_miata", help="Car ID for 95% AI telemetry profile (default: ks_mazda_miata)")
    parser.add_argument("--speed-kmh", type=float, default=None, help="Optional target speed override in km/h (defaults to 95% AI telemetry)")
    parser.add_argument("--countdown-sec", type=float, default=3.0, help="Countdown duration in seconds (default: 3.0)")
    parser.add_argument("--wheelbase", type=float, default=2.5, help="Vehicle wheelbase in meters (default: 2.5)")
    parser.add_argument("--steer-ratio", type=float, default=14.5, help="Steering rack ratio (default: 14.5)")
    parser.add_argument("--post-go-sec", type=float, default=1.5, help="Post-GO straight duration in seconds before next corner (default: 1.5)")
    parser.add_argument("--post-go-margin", type=float, default=None, help="Backwards-compatible alias for margin in meters")
    parser.add_argument("--output-html", type=str, default="output/rolling_start_map.html", help="Path to generate interactive HTML circuit map")
    parser.add_argument("--output-json", type=str, default="", help="Optional path to export JSON candidate catalog")
    parser.add_argument("--open", action="store_true", help="Automatically open generated HTML map in default browser")
    parser.add_argument("--ac-root", type=str, default=DEFAULT_AC_ROOT, help="Assetto Corsa root installation directory")

    args = parser.parse_args()

    tracks_to_process: List[Tuple[str, str, str]] = []

    if args.all_kunos:
        print("[*] Scanning Assetto Corsa for official Kunos track AI splines...")
        tracks_to_process = discover_kunos_tracks(args.ac_root)
        print(f"[*] Discovered {len(tracks_to_process)} official Kunos track configurations.")
    elif args.curriculum:
        print("[*] Loading all 27 tracks from the Gran Turismo license curriculum...")
        for t_id, t_lay in CURRICULUM_TRACKS:
            sf = find_spline_file(t_id, t_lay, args.ac_root)
            if sf:
                tracks_to_process.append((t_id, t_lay, sf))
        print(f"[*] Loaded {len(tracks_to_process)} curriculum track configurations.")
    elif args.track:
        sf = find_spline_file(args.track, args.layout, args.ac_root)
        if not sf:
            print(f"[ERROR] Could not locate AI spline for track '{args.track}' layout '{args.layout}'.", file=sys.stderr)
            return 1
        tracks_to_process = [(args.track, args.layout, sf)]
    else:
        sf = find_spline_file("ks_vallelunga", "club_circuit", args.ac_root)
        if sf:
            tracks_to_process = [("ks_vallelunga", "club_circuit", sf)]
        else:
            print("[ERROR] Please specify --track or --all-kunos.", file=sys.stderr)
            return 1

    tracks_payload: Dict[str, Any] = {}
    combined_analyses: Dict[str, Any] = {}
    primary_analysis = None
    initial_key = ""

    eff_post_go_sec = args.post_go_sec
    if args.post_go_margin is not None:
        spd_ref = args.speed_kmh if args.speed_kmh is not None and args.speed_kmh > 0 else 70.0
        eff_post_go_sec = args.post_go_margin / (spd_ref / 3.6)

    default_params = {
        "max_steer_deg": args.max_steer_deg,
        "min_length_m": args.min_length,
        "countdown_sec": args.countdown_sec,
        "wheelbase_m": args.wheelbase,
        "steer_ratio": args.steer_ratio,
        "post_go_sec": round(eff_post_go_sec, 2),
    }

    for track_id, layout, spline_path in tracks_to_process:
        key = f"{track_id}__{layout}" if layout else track_id
        if not initial_key:
            initial_key = key

        try:
            parser_spline = SplineParser(spline_path)
            analyzer = TrackStraightAnalyzer(
                parser=parser_spline,
                track_id=track_id,
                layout=layout,
                car_id=args.car,
                wheelbase_m=args.wheelbase,
                steer_ratio=args.steer_ratio,
            )
            analysis = analyzer.export_full_analysis(
                max_steer_deg=args.max_steer_deg,
                min_length_m=args.min_length,
                target_speed_kmh=args.speed_kmh,
                countdown_sec=args.countdown_sec,
                post_go_sec=eff_post_go_sec,
            )

            spline_data = serialize_spline_data(parser_spline, analyzer)
            tracks_payload[key] = {
                "track_id": track_id,
                "layout": layout,
                "car_id": analyzer.car_id,
                "telemetry_source": analyzer.telemetry.source,
                "ai_level": analyzer.telemetry.ai_level,
                "lap_time_s": analyzer.telemetry.lap_time_s,
                "total_length": spline_data["total_length"],
                "waypoints": spline_data["waypoints"],
            }
            combined_analyses[key] = analysis

            if len(tracks_to_process) == 1:
                primary_analysis = analysis
                print_cli_summary(analysis)
        except Exception as e:
            print(f"[!] Warning: Error processing {track_id} [{layout}]: {e}", file=sys.stderr)

    if len(tracks_to_process) > 1:
        print(f"\n[+] Batch processed {len(tracks_payload)} tracks successfully.")
        total_candidates = sum(len(a["candidates"]) for a in combined_analyses.values())
        print(f"[+] Cataloged {total_candidates} viable rolling start candidates across Kunos circuits.")

    output_html = os.path.abspath(args.output_html)
    generate_interactive_html(
        tracks_payload=tracks_payload,
        initial_track_key=initial_key,
        output_html_path=output_html,
        default_params=default_params,
    )
    print(f"\n[+] Interactive HTML circuit map generated:")
    print(f"    file:///{output_html.replace(os.sep, '/')}")

    if args.output_json:
        out_json = os.path.abspath(args.output_json)
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            if primary_analysis:
                json.dump(primary_analysis, f, indent=2)
            else:
                json.dump(combined_analyses, f, indent=2)
        print(f"[+] JSON candidate catalog exported: {out_json}")

    if args.open:
        print(f"[*] Opening {output_html} in default web browser...")
        webbrowser.open(f"file:///{output_html}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

