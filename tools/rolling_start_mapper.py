#!/usr/bin/env python3
"""
rolling_start_mapper.py
Assetto Corsa Rolling Start Straight Line Analyzer & Interactive Circuit Mapper

Discovers and analyzes track segments where AI splines go in a straight line,
enabling precise, predictable rolling start test placement with 0-degree steering.

Generates:
  1. Rich CLI terminal summary tables
  2. Standalone interactive HTML circuit map with live, real-time client-side
     parameter adjustment sliders (steering error, min length, speed, countdown, etc.)
  3. JSON export for curriculum integration into tools/generate_all_content.py
"""

import argparse
import json
import math
import os
import sys
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from extract_spline_coords import (
    DEFAULT_AC_ROOT,
    SplineParser,
    find_spline_file,
)
from track_straight_analyzer import (
    RollingStartCandidate,
    StraightSegment,
    TrackStraightAnalyzer,
)

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

        # Check default layout
        sf_def = find_spline_file(track_id, "", ac_root)
        subdirs = [
            s for s in sorted(os.listdir(tdir))
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
        # [x, z, distance, radius, fwd_x, fwd_z, speed_kmh, gear, rpm]
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

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Assetto Corsa // Rolling Start Straight Line Analyzer</title>
<style>
  :root {{
    --bg-dark: #090d16;
    --panel-bg: #111827;
    --panel-border: #1f293d;
    --text-main: #f1f5f9;
    --text-muted: #94a3b8;
    --accent-green: #10b981;
    --accent-cyan: #06b6d4;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --track-curve: #334155;
    --track-straight: #10b981;
    --track-selected: #38bdf8;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }}

  body {{
    background-color: var(--bg-dark);
    color: var(--text-main);
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }}

  header {{
    background: linear-gradient(180deg, #162032 0%, #0f172a 100%);
    border-bottom: 1px solid var(--panel-border);
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    z-index: 10;
  }}

  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .badge-gt {{
    background: linear-gradient(135deg, #e11d48, #be123c);
    color: white;
    font-size: 11px;
    font-weight: 800;
    padding: 4px 8px;
    border-radius: 4px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}

  .title-group h1 {{
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: #fff;
  }}

  .title-group p {{
    font-size: 12px;
    color: var(--text-muted);
  }}

  .track-select-box {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  select.custom-select {{
    background: #1e293b;
    border: 1px solid #334155;
    color: #f8fafc;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    outline: none;
    cursor: pointer;
  }}

  select.custom-select:hover {{
    border-color: var(--accent-cyan);
  }}

  .btn-action {{
    background: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }}

  .btn-action:hover {{
    background: #334155;
    color: #fff;
  }}

  .btn-action.primary {{
    background: #0284c7;
    border-color: #0284c7;
    color: #fff;
  }}

  .btn-action.primary:hover {{
    background: #0369a1;
  }}

  /* Main Workspace */
  .workspace {{
    display: flex;
    flex: 1;
    height: calc(100vh - 65px);
    overflow: hidden;
  }}

  /* Sidebar Controls */
  .sidebar {{
    width: 440px;
    min-width: 400px;
    background: var(--panel-bg);
    border-right: 1px solid var(--panel-border);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }}

  .sidebar-section {{
    padding: 18px;
    border-bottom: 1px solid var(--panel-border);
  }}

  .section-title {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--accent-cyan);
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .control-row {{
    margin-bottom: 16px;
  }}

  .control-row:last-child {{
    margin-bottom: 0;
  }}

  .control-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}

  .control-label {{
    font-size: 13px;
    font-weight: 500;
    color: #e2e8f0;
  }}

  .control-badge {{
    background: #1e293b;
    border: 1px solid #334155;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent-green);
    font-family: monospace;
  }}

  input[type=range] {{
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #1e293b;
    outline: none;
    cursor: pointer;
    accent-color: var(--accent-green);
  }}

  .control-hint {{
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* Quick Presets */
  .preset-pills {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;
  }}

  .pill {{
    background: #1e293b;
    border: 1px solid #334155;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s;
  }}

  .pill:hover {{
    background: #334155;
    color: #fff;
  }}

  .pill.active {{
    background: rgba(16, 185, 129, 0.2);
    border-color: var(--accent-green);
    color: var(--accent-green);
  }}

  /* Stats Cards Grid */
  .stats-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
  }}

  .stat-card {{
    background: #0f172a;
    border: 1px solid var(--panel-border);
    padding: 10px;
    border-radius: 6px;
  }}

  .stat-val {{
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    font-family: monospace;
  }}

  .stat-sub {{
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }}

  /* Candidate List */
  .candidates-scroll {{
    flex: 1;
    overflow-y: auto;
    padding: 14px 18px;
  }}

  .candidate-card {{
    background: #162032;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
  }}

  .candidate-card:hover {{
    border-color: var(--accent-cyan);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }}

  .candidate-card.selected {{
    border-color: var(--accent-green);
    background: #132737;
    box-shadow: 0 0 16px rgba(16, 185, 129, 0.25);
  }}

  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }}

  .rank-badge {{
    background: var(--accent-green);
    color: #000;
    font-weight: 800;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
  }}

  .score-badge {{
    font-size: 12px;
    font-weight: 700;
    color: var(--accent-cyan);
    font-family: monospace;
  }}

  .card-title {{
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
  }}

  .card-meta {{
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 8px;
  }}

  .card-meta-item {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  /* Snippet Box */
  .snippet-box {{
    background: #090d16;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 10px;
    margin-top: 10px;
    font-family: monospace;
    font-size: 11px;
    color: #38bdf8;
    position: relative;
    max-height: 120px;
    overflow-y: auto;
  }}

  /* Map Container */
  .map-container {{
    flex: 1;
    position: relative;
    background: #070b12;
    overflow: hidden;
  }}

  #circuitSvg {{
    width: 100%;
    height: 100%;
    display: block;
    cursor: grab;
  }}

  #circuitSvg:active {{
    cursor: grabbing;
  }}

  /* Map Controls Overlay */
  .map-overlay-controls {{
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 5;
  }}

  .map-btn {{
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid #334155;
    color: #f1f5f9;
    width: 36px;
    height: 36px;
    border-radius: 6px;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    backdrop-filter: blur(8px);
    transition: all 0.2s;
  }}

  .map-btn:hover {{
    background: #1e293b;
    border-color: var(--accent-cyan);
  }}

  /* Compass Rose Overlay */
  .compass-box {{
    position: absolute;
    bottom: 24px;
    right: 24px;
    background: rgba(17, 24, 39, 0.85);
    border: 1px solid #334155;
    padding: 8px 12px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent-cyan);
    backdrop-filter: blur(8px);
  }}

  /* Hover Tooltip */
  .track-tooltip {{
    position: absolute;
    display: none;
    pointer-events: none;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid var(--accent-cyan);
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 12px;
    color: #fff;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    z-index: 20;
    backdrop-filter: blur(8px);
  }}

  .tooltip-row {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 4px;
  }}

  .tooltip-row:last-child {{
    margin-bottom: 0;
  }}

  .tooltip-val {{
    font-weight: 700;
    font-family: monospace;
    color: var(--accent-green);
  }}

  /* Toast Notification */
  .toast {{
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(100px);
    background: var(--accent-green);
    color: #000;
    font-weight: 700;
    padding: 10px 20px;
    border-radius: 30px;
    font-size: 13px;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    z-index: 999;
  }}

  .toast.show {{
    transform: translateX(-50%) translateY(0);
  }}
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="badge-gt">GT Licenses</div>
    <div class="title-group">
      <h1>Rolling Start Straight Line Analyzer</h1>
      <p>Identify optimal straight-line countdown spawns with 0° steering wheel error</p>
    </div>
  </div>

  <div class="track-select-box">
    <label for="trackSelect" style="font-size: 12px; color: var(--text-muted);">Circuit:</label>
    <select id="trackSelect" class="custom-select"></select>
    <button id="btnExportJson" class="btn-action primary">Export JSON</button>
  </div>
</header>

<div class="workspace">
  <!-- Left Sidebar Controls & Results -->
  <div class="sidebar">
    <!-- Live Adjustment Controls -->
    <div class="sidebar-section">
      <div class="section-title">
        <span>Parameters & Tolerance</span>
        <span style="font-size: 10px; color: var(--accent-green);">● LIVE REACTIVE</span>
      </div>

      <!-- Max Steering Angle Slider -->
      <div class="control-row">
        <div class="control-header">
          <span class="control-label">Max Steering Wheel Error (δ)</span>
          <span id="badgeMaxSteer" class="control-badge">±2.0°</span>
        </div>
        <input type="range" id="sliderMaxSteer" min="0.5" max="5.0" step="0.1" value="2.0">
        <div class="control-hint">Primary tolerance: maximum steering wheel deflection from zero.</div>
      </div>

      <!-- Min Segment Length Slider -->
      <div class="control-row">
        <div class="control-header">
          <span class="control-label">Min Straight Length</span>
          <span id="badgeMinLength" class="control-badge">60m</span>
        </div>
        <input type="range" id="sliderMinLength" min="20" max="300" step="5" value="60">
        <div class="control-hint">Ignores micro-straights too short for full countdown.</div>
      </div>

      <!-- 95% AI Telemetry Profile Card (Authoritative, non-modifiable grounding) -->
      <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 10px 12px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-size: 11px; font-weight: 700; color: var(--accent-green); letter-spacing: 0.5px;">● 95% PROFICIENT AI PROFILE</span>
          <span id="badgeProfileSource" class="control-badge" style="font-size: 10px; color: var(--accent-cyan); padding: 1px 6px;">CACHED</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;">
          <span style="color: var(--text-muted);">Vehicle Model:</span>
          <b id="badgeCarId" style="font-family: monospace; color: #fff;">ks_mazda_miata</b>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
          <span style="color: var(--text-muted);">Proficient Flying Lap:</span>
          <b id="badgeLapTime" style="font-family: monospace; color: #fff;">1:45.3s</b>
        </div>
        <div class="control-hint" style="margin-top: 4px; font-size: 10.5px; line-height: 1.35; color: #94a3b8;">
          Rolling start speed, engaged gear, and RPM are strictly governed by the 95% AI telemetry at each straight sector.
        </div>
      </div>

      <!-- Countdown Duration Slider -->
      <div class="control-row">
        <div class="control-header">
          <span class="control-label">Countdown Duration</span>
          <span id="badgeCountdown" class="control-badge">3.0s</span>
        </div>
        <input type="range" id="sliderCountdown" min="1.0" max="5.0" step="0.5" value="3.0">
        <div class="control-hint">Duration (in seconds) the native AI rolls the car before handing over control at 'GO!'.</div>
      </div>

      <!-- Post-GO Straight Duration Slider -->
      <div class="control-row">
        <div class="control-header">
          <span class="control-label">Post-"GO!" Straight Margin</span>
          <span id="badgeMargin" class="control-badge">1.5s</span>
        </div>
        <input type="range" id="sliderMargin" min="0.5" max="5.0" step="0.1" value="1.5">
        <div class="control-hint">Time (in seconds) the player keeps driving straight after 'GO!' before the corner entry.</div>
      </div>

      <!-- Presets -->
      <div style="margin-top: 14px;">
        <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">DRIVING SCHOOL PRESETS:</span>
        <div class="preset-pills">
          <button class="pill active" data-steer="2.0" data-len="60" data-postgo="1.5">Standard Road (±2.0°, 1.5s)</button>
          <button class="pill" data-steer="1.0" data-len="80" data-postgo="2.0">Strict Straight (±1.0°, 2.0s)</button>
          <button class="pill" data-steer="2.5" data-len="50" data-postgo="1.0">Short Sprint (1.0s)</button>
          <button class="pill" data-steer="1.5" data-len="100" data-postgo="2.5">Extended Margin (2.5s)</button>
        </div>
      </div>
    </div>

    <!-- Live Telemetry & Stats -->
    <div class="sidebar-section">
      <div class="section-title">Circuit & Analysis Telemetry</div>
      <div class="stats-grid">
        <div class="stat-card">
          <div id="statTrackLength" class="stat-val">0.0m</div>
          <div class="stat-sub">Track Length</div>
        </div>
        <div class="stat-card">
          <div id="statAILevel" class="stat-val" style="color: var(--accent-cyan); font-size: 14px;">95% AI</div>
          <div class="stat-sub">Driver Skill Target</div>
        </div>
        <div class="stat-card">
          <div id="statStraightsCount" class="stat-val" style="color: var(--accent-green);">0</div>
          <div class="stat-sub">Straights Found</div>
        </div>
        <div class="stat-card">
          <div id="statCandidatesCount" class="stat-val" style="color: var(--accent-cyan);">0</div>
          <div class="stat-sub">Viable Candidates</div>
        </div>
      </div>
    </div>

    <!-- Candidates List -->
    <div class="section-title" style="padding: 14px 18px 0 18px; margin-bottom: 0;">
      <span>Ranked Rolling Start Candidates</span>
    </div>
    <div id="candidatesList" class="candidates-scroll">
      <!-- Populated dynamically -->
    </div>
  </div>

  <!-- Right Visual Map Area -->
  <div class="map-container">
    <svg id="circuitSvg"></svg>

    <!-- Map Zoom / Pan Buttons -->
    <div class="map-overlay-controls">
      <button id="btnZoomIn" class="map-btn" title="Zoom In">+</button>
      <button id="btnZoomOut" class="map-btn" title="Zoom Out">−</button>
      <button id="btnResetView" class="map-btn" title="Reset View">⤢</button>
    </div>

    <!-- Compass -->
    <div class="compass-box">
      <span>⬆ NORTH (Z)</span>
    </div>

    <!-- Tooltip -->
    <div id="trackTooltip" class="track-tooltip"></div>
  </div>
</div>

<div id="toast" class="toast">JSON Copied to Clipboard!</div>

<script>
// Data injected by Python generator
const TRACKS_DATA = {tracks_json_str};
const DEFAULT_TRACK_KEY = "{initial_track_key}";

// Kinematic configuration state
let currentParams = {default_params_json_str};
let activeTrackKey = DEFAULT_TRACK_KEY;
let currentCandidates = [];
let selectedCandidateIdx = 0;

// SVG Map Viewport Transform
let viewState = {{
  viewX: 0,
  viewY: 0,
  scale: 1,
  width: 1000,
  height: 800,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0
}};

// DOM Elements
const trackSelect = document.getElementById("trackSelect");
const sliderMaxSteer = document.getElementById("sliderMaxSteer");
const sliderMinLength = document.getElementById("sliderMinLength");
const sliderCountdown = document.getElementById("sliderCountdown");
const sliderMargin = document.getElementById("sliderMargin");

const badgeMaxSteer = document.getElementById("badgeMaxSteer");
const badgeMinLength = document.getElementById("badgeMinLength");
const badgeCountdown = document.getElementById("badgeCountdown");
const badgeMargin = document.getElementById("badgeMargin");
const badgeProfileSource = document.getElementById("badgeProfileSource");
const badgeCarId = document.getElementById("badgeCarId");
const badgeLapTime = document.getElementById("badgeLapTime");

const statTrackLength = document.getElementById("statTrackLength");
const statAILevel = document.getElementById("statAILevel");
const statStraightsCount = document.getElementById("statStraightsCount");
const statCandidatesCount = document.getElementById("statCandidatesCount");
const candidatesList = document.getElementById("candidatesList");
const circuitSvg = document.getElementById("circuitSvg");
const trackTooltip = document.getElementById("trackTooltip");
const toast = document.getElementById("toast");

function showToast(msg) {{
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}}

// Initialize Track Dropdown
function initTrackDropdown() {{
  trackSelect.innerHTML = "";
  for (const key of Object.keys(TRACKS_DATA)) {{
    const opt = document.createElement("option");
    opt.value = key;
    const t = TRACKS_DATA[key];
    opt.textContent = `${{t.track_id}} [${{t.layout || "default"}}] (${{t.total_length.toFixed(0)}}m)`;
    if (key === activeTrackKey) opt.selected = true;
    trackSelect.appendChild(opt);
  }}

  trackSelect.addEventListener("change", (e) => {{
    activeTrackKey = e.target.value;
    selectedCandidateIdx = 0;
    resetSvgView();
    recalculateAnalysis();
  }});
}}

// Query 95% AI telemetry sample at distance
function querySpeedSample(trackData, distanceM) {{
  const wps = trackData.waypoints;
  const n = wps.length;
  const totalLength = trackData.total_length;
  const dist = ((distanceM % totalLength) + totalLength) % totalLength;

  let low = 0, high = n - 1;
  while (low <= high) {{
    const mid = (low + high) >> 1;
    if (wps[mid][2] <= dist) {{
      low = mid + 1;
    }} else {{
      high = mid - 1;
    }}
  }}
  const i0 = Math.max(0, Math.min(high, n - 1));
  const i1 = (i0 + 1) % n;
  const d0 = wps[i0][2];
  let d1 = wps[i1][2];
  if (i1 === 0) d1 = totalLength;
  const t = (d1 - d0) > 1e-4 ? Math.max(0, Math.min(1, (dist - d0) / (d1 - d0))) : 0;

  const spd = wps[i0][6] * (1 - t) + wps[i1][6] * t;
  const gear = t < 0.5 ? wps[i0][7] : wps[i1][7];
  const rpm = Math.round(wps[i0][8] * (1 - t) + wps[i1][8] * t);
  return {{ speedKmh: spd, gear: gear || 3, rpm: rpm || 4000 }};
}}

// Backward numerical integration along 95% AI speed curve
function integrateBackward(trackData, endDistM, durationSec, stepDt = 0.05) {{
  let currDist = endDistM;
  let tAccum = 0.0;
  const totalLength = trackData.total_length;
  while (tAccum < durationSec) {{
    const s = querySpeedSample(trackData, currDist);
    const vMs = Math.max(5.0, s.speedKmh / 3.6);
    const dt = Math.min(stepDt, durationSec - tAccum);
    const ds = vMs * dt;
    currDist = ((currDist - ds) % totalLength + totalLength) % totalLength;
    tAccum += dt;
  }}
  return currDist;
}}

// Client-Side Kinematic Segmentation Engine
function runKinematicAnalysis(trackData, params) {{
  const wps = trackData.waypoints;
  const n = wps.length;
  const totalLength = trackData.total_length;
  const L = params.wheelbase_m || 2.5;
  const rSteer = params.steer_ratio || 14.5;
  const maxSteerDeg = params.max_steer_deg;
  const minLength = params.min_length_m;

  // 1. Calculate steering angle and headings
  const steerAngles = new Float32Array(n);
  const headings = new Float32Array(n);
  const isStraight = new Uint8Array(n);

  for (let i = 0; i < n; i++) {{
    const radius = Math.max(0.1, wps[i][3]);
    const deltaRoad = Math.atan2(L, radius);
    const deltaWheel = deltaRoad * rSteer * (180.0 / Math.PI);
    steerAngles[i] = deltaWheel;

    // Heading in degrees [0, 360)
    let h = (Math.atan2(wps[i][4], wps[i][5]) * (180.0 / Math.PI) + 360.0) % 360.0;
    headings[i] = h;

    isStraight[i] = (deltaWheel <= maxSteerDeg) ? 1 : 0;
  }}

  // 2. Contiguous runs
  const rawRuns = [];
  let startIdx = null;
  for (let i = 0; i < n; i++) {{
    if (isStraight[i] === 1) {{
      if (startIdx === null) startIdx = i;
    }} else {{
      if (startIdx !== null) {{
        rawRuns.push([startIdx, i - 1]);
        startIdx = null;
      }}
    }}
  }}
  if (startIdx !== null) rawRuns.push([startIdx, n - 1]);

  if (rawRuns.length === 0) return {{ straights: [], candidates: [] }};

  // 3. Bridge small noise gaps (<= 12m)
  const bridgedRuns = [];
  let currStart = rawRuns[0][0];
  let currEnd = rawRuns[0][1];

  for (let k = 1; k < rawRuns.length; k++) {{
    const nextStart = rawRuns[k][0];
    const nextEnd = rawRuns[k][1];
    const gapDist = wps[nextStart][2] - wps[currEnd][2];
    const hDiff = Math.abs((headings[currEnd] - headings[nextStart] + 180.0) % 360.0 - 180.0);

    if (gapDist > 0 && gapDist <= 12.0 && hDiff <= 3.5) {{
      currEnd = nextEnd;
    }} else {{
      bridgedRuns.push([currStart, currEnd]);
      currStart = nextStart;
      currEnd = nextEnd;
    }}
  }}
  bridgedRuns.push([currStart, currEnd]);

  // 4. Circular loop wrap-around across lap finish line
  const finalRuns = [];
  let wrapsLap = false;

  if (bridgedRuns.length >= 2) {{
    const firstStart = bridgedRuns[0][0];
    const firstEnd = bridgedRuns[0][1];
    const lastStart = bridgedRuns[bridgedRuns.length - 1][0];
    const lastEnd = bridgedRuns[bridgedRuns.length - 1][1];

    const gapToZero = wps[firstStart][2];
    const gapToEnd = totalLength - wps[lastEnd][2];
    const wrapGap = gapToZero + gapToEnd;
    const wrapHDiff = Math.abs((headings[lastEnd] - headings[firstStart] + 180.0) % 360.0 - 180.0);

    if (wrapGap <= 15.0 && wrapHDiff <= 3.5) {{
      wrapsLap = true;
      const wrappedLen = (totalLength - wps[lastStart][2]) + wps[firstEnd][2];
      if (wrappedLen >= minLength) {{
        finalRuns.push({{
          startIdx: lastStart,
          endIdx: firstEnd,
          length: wrappedLen,
          startDist: wps[lastStart][2],
          endDist: wps[firstEnd][2],
          wrapsLap: true
        }});
      }}
      for (let k = 1; k < bridgedRuns.length - 1; k++) {{
        const sIdx = bridgedRuns[k][0];
        const eIdx = bridgedRuns[k][1];
        const len = wps[eIdx][2] - wps[sIdx][2];
        if (len >= minLength) {{
          finalRuns.push({{
            startIdx: sIdx,
            endIdx: eIdx,
            length: len,
            startDist: wps[sIdx][2],
            endDist: wps[eIdx][2],
            wrapsLap: false
          }});
        }}
      }}
    }}
  }}

  if (!wrapsLap) {{
    for (const r of bridgedRuns) {{
      const len = wps[r[1]][2] - wps[r[0]][2];
      if (len >= minLength) {{
        finalRuns.push({{
          startIdx: r[0],
          endIdx: r[1],
          length: len,
          startDist: wps[r[0]][2],
          endDist: wps[r[1]][2],
          wrapsLap: false
        }});
      }}
    }}
  }}

  // Build straight segment objects
  const straights = [];
  finalRuns.forEach((r, idx) => {{
    let maxSteer = 0;
    let sumSteer = 0;
    let count = 0;
    let sumSpd = 0;

    let curr = r.startIdx;
    while (true) {{
      const st = steerAngles[curr];
      if (st > maxSteer) maxSteer = st;
      sumSteer += st;
      sumSpd += wps[curr][6];
      count++;
      if (curr === r.endIdx) break;
      curr = (curr + 1) % n;
    }}

    const compass = headings[r.startIdx];

    straights.push({{
      id: idx + 1,
      startDist: r.startDist,
      endDist: r.endDist,
      length: r.length,
      startProgress: r.startDist / totalLength,
      endProgress: r.endDist / totalLength,
      startIdx: r.startIdx,
      endIdx: r.endIdx,
      maxSteer: maxSteer,
      avgSteer: count > 0 ? (sumSteer / count) : 0,
      avgSpeed: count > 0 ? (sumSpd / count) : 0,
      compass: compass,
      wrapsLap: r.wrapsLap
    }});
  }});

  // Sort straights by length descending
  straights.sort((a, b) => b.length - a.length);
  straights.forEach((s, idx) => s.id = idx + 1);

  // 5. Evaluate rolling start candidates grounded in 95% AI telemetry
  const postGoSec = params.post_go_sec !== undefined ? params.post_go_sec : 1.5;
  const countdownSec = params.countdown_sec !== undefined ? params.countdown_sec : 3.0;
  const candidates = [];

  for (const s of straights) {{
    const gateDist = integrateBackward(trackData, s.endDist, postGoSec);
    const spawnDist = integrateBackward(trackData, gateDist, countdownSec);

    const postGoDist = (s.endDist - gateDist + totalLength) % totalLength;
    const countdownDist = (gateDist - spawnDist + totalLength) % totalLength;
    const minReqLen = countdownDist + postGoDist;

    if (s.length < minReqLen) continue;

    const gateTel = querySpeedSample(trackData, gateDist);
    const spawnTel = querySpeedSample(trackData, spawnDist);

    const steerPenalty = Math.min(50.0, s.maxSteer * 15.0);
    const lengthBonus = Math.min(30.0, s.length / 10.0);
    const score = Math.max(0.0, 90.0 - steerPenalty + lengthBonus);

    candidates.push({{
      rank: 0,
      straightId: s.id,
      score: score,
      straightLength: s.length,
      maxSteer: s.maxSteer,
      avgSpeed: s.avgSpeed,
      countdownSec: countdownSec,
      countdownDist: countdownDist,
      postGoSec: postGoSec,
      postGoDist: postGoDist,
      startGateDist: gateDist,
      startProgress: gateDist / totalLength,
      spawnDist: spawnDist,
      spawnProgress: spawnDist / totalLength,
      spawnOffset: countdownDist,
      targetSpeed: gateTel.speedKmh,
      spawnSpeed: spawnTel.speedKmh,
      gear: gateTel.gear,
      rpm: gateTel.rpm,
      wrapsLap: s.wrapsLap
    }});
  }}

  candidates.sort((a, b) => b.score - a.score);
  candidates.forEach((c, idx) => c.rank = idx + 1);

  return {{ straights, candidates }};
}}

// Recalculate and re-render
function recalculateAnalysis() {{
  const track = TRACKS_DATA[activeTrackKey];
  if (!track) return;

  const res = runKinematicAnalysis(track, currentParams);
  currentCandidates = res.candidates;

  // Update telemetry stats & profile card
  statTrackLength.textContent = `${{track.total_length.toFixed(1)}}m`;
  badgeProfileSource.textContent = (track.telemetry_source || "CACHED").toUpperCase();
  badgeCarId.textContent = track.car_id || "ks_mazda_miata";
  const lapTime = track.lap_time_s;
  badgeLapTime.textContent = lapTime ? `${{Math.floor(lapTime / 60)}}:${{(lapTime % 60).toFixed(1).padStart(4, '0')}}s` : "N/A";
  statAILevel.textContent = `${{track.ai_level || 95}}% AI`;
  statStraightsCount.textContent = res.straights.length;
  statCandidatesCount.textContent = res.candidates.length;

  renderCandidatesList(res.candidates, track);
  renderSvgCircuit(track, res.straights, res.candidates);
}}

// Render Candidates List Sidebar
function renderCandidatesList(candidates, track) {{
  candidatesList.innerHTML = "";

  if (candidates.length === 0) {{
    candidatesList.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">
        No straight segments meet current criteria.<br>
        Try increasing <b>Max Steering Error</b> or lowering <b>Min Length</b>.
      </div>
    `;
    return;
  }}

  candidates.forEach((c, idx) => {{
    const isSelected = (idx === selectedCandidateIdx);
    const card = document.createElement("div");
    card.className = `candidate-card ${{isSelected ? "selected" : ""}}`;

    const snippet = {{
      track_id: track.track_id,
      track_layout: track.layout || "",
      car_id: track.car_id || "ks_mazda_miata",
      start_mode: "ROLLING",
      start_s: parseFloat(c.startProgress.toFixed(4)),
      spawn_offset: parseFloat(c.spawnOffset.toFixed(1)),
      speed: parseFloat(c.targetSpeed.toFixed(1)),
      gear: c.gear,
      rpm: c.rpm
    }};

    card.innerHTML = `
      <div class="card-top">
        <span class="rank-badge">RANK #${{c.rank}}</span>
        <span class="score-badge">SCORE: ${{c.score.toFixed(1)}} / 100</span>
      </div>
      <div class="card-title">Straight #${{c.straightId}} (${{c.straightLength.toFixed(0)}}m)</div>
      <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; padding: 4px 8px; margin: 6px 0; font-size: 11.5px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: var(--accent-green); font-weight: 700;">⚡ 95% AI Handover:</span>
        <b style="font-family: monospace; color: #fff;">${{c.targetSpeed.toFixed(1)}} km/h (G${{c.gear}} @ ${{c.rpm}} RPM)</b>
      </div>
      <div class="card-meta">
        <div class="card-meta-item"><span>δ Error:</span> <b>±${{c.maxSteer.toFixed(2)}}°</b></div>
        <div class="card-meta-item"><span>Gate:</span> <b>s=${{c.startProgress.toFixed(4)}} (${{c.startGateDist.toFixed(1)}}m)</b></div>
        <div class="card-meta-item"><span>Run-up:</span> <b>${{c.countdownSec.toFixed(1)}}s (${{c.spawnOffset.toFixed(1)}}m)</b></div>
        <div class="card-meta-item"><span>Straight Time:</span> <b>${{c.postGoSec.toFixed(1)}}s (${{c.postGoDist.toFixed(1)}}m)</b></div>
      </div>
      <div class="snippet-box" title="Click card to view, double-click to copy">
        <pre>${{JSON.stringify(snippet, null, 2)}}</pre>
      </div>
    `;

    card.addEventListener("click", () => {{
      selectedCandidateIdx = idx;
      document.querySelectorAll(".candidate-card").forEach(el => el.classList.remove("selected"));
      card.classList.add("selected");
      highlightCandidateOnMap(track, c);
    }});

    card.querySelector(".snippet-box").addEventListener("click", (e) => {{
      e.stopPropagation();
      navigator.clipboard.writeText(JSON.stringify(snippet, null, 2));
      showToast("Config JSON Copied!");
    }});

    candidatesList.appendChild(card);
  }});
}}


// SVG Rendering
function renderSvgCircuit(track, straights, candidates) {{
  const wps = track.waypoints;
  if (!wps || wps.length === 0) return;

  // Calculate bounding box in 2D ground plane (X, Z)
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
  for (const w of wps) {{
    if (w[0] < minX) minX = w[0];
    if (w[0] > maxX) maxX = w[0];
    if (w[1] < minZ) minZ = w[1];
    if (w[1] > maxZ) maxZ = w[1];
  }}

  const pad = Math.max(maxX - minX, maxZ - minZ) * 0.08;
  viewState.minX = minX - pad;
  viewState.maxX = maxX + pad;
  viewState.minZ = minZ - pad;
  viewState.maxZ = maxZ + pad;

  const width = viewState.maxX - viewState.minX;
  const height = viewState.maxZ - viewState.minZ;

  circuitSvg.setAttribute("viewBox", `${{viewState.minX}} ${{viewState.minZ}} ${{width}} ${{height}}`);
  circuitSvg.innerHTML = "";

  // 1. Draw entire track base curve ribbon (dark slate)
  let dAll = `M ${{wps[0][0]}} ${{wps[0][1]}}`;
  for (let i = 1; i < wps.length; i++) {{
    dAll += ` L ${{wps[i][0]}} ${{wps[i][1]}}`;
  }}
  dAll += " Z";

  const pathBase = document.createElementNS("http://www.w3.org/2000/svg", "path");
  pathBase.setAttribute("d", dAll);
  pathBase.setAttribute("fill", "none");
  pathBase.setAttribute("stroke", "var(--track-curve)");
  pathBase.setAttribute("stroke-width", "8");
  pathBase.setAttribute("stroke-linejoin", "round");
  pathBase.setAttribute("stroke-linecap", "round");
  circuitSvg.appendChild(pathBase);

  // 2. Draw straight segments in glowing emerald green
  const n = wps.length;
  straights.forEach((s) => {{
    let dStraight = `M ${{wps[s.startIdx][0]}} ${{wps[s.startIdx][1]}}`;
    let curr = s.startIdx;
    while (true) {{
      curr = (curr + 1) % n;
      dStraight += ` L ${{wps[curr][0]}} ${{wps[curr][1]}}`;
      if (curr === s.endIdx) break;
    }}

    const pathStraight = document.createElementNS("http://www.w3.org/2000/svg", "path");
    pathStraight.setAttribute("d", dStraight);
    pathStraight.setAttribute("fill", "none");
    pathStraight.setAttribute("stroke", "var(--track-straight)");
    pathStraight.setAttribute("stroke-width", "10");
    pathStraight.setAttribute("stroke-linejoin", "round");
    pathStraight.setAttribute("stroke-linecap", "round");
    pathStraight.style.filter = "drop-shadow(0 0 6px rgba(16, 185, 129, 0.6))";
    circuitSvg.appendChild(pathStraight);
  }});

  // 3. Highlight currently selected candidate overlay
  if (candidates.length > 0 && selectedCandidateIdx < candidates.length) {{
    highlightCandidateOnMap(track, candidates[selectedCandidateIdx]);
  }}
}}

// Highlights spawn point, countdown vector, and start gate on SVG
function highlightCandidateOnMap(track, cand) {{
  // Remove existing active candidate elements
  const oldActive = circuitSvg.querySelectorAll(".candidate-active-layer");
  oldActive.forEach(el => el.remove());

  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.setAttribute("class", "candidate-active-layer");

  const wps = track.waypoints;
  const n = wps.length;

  // Helper to interpolate coordinate at distance
  function getPosAtDist(dist) {{
    dist = (dist % track.total_length + track.total_length) % track.total_length;
    let low = 0, high = n - 1;
    while (low <= high) {{
      const mid = Math.floor((low + high) / 2);
      if (wps[mid][2] <= dist) low = mid + 1;
      else high = mid - 1;
    }}
    const i0 = Math.max(0, Math.min(high, n - 1));
    const i1 = (i0 + 1) % n;
    const d0 = wps[i0][2];
    let d1 = wps[i1][2];
    if (i1 === 0) d1 = track.total_length;
    const t = (d1 > d0) ? (dist - d0) / (d1 - d0) : 0;
    return {{
      x: wps[i0][0] * (1 - t) + wps[i1][0] * t,
      z: wps[i0][1] * (1 - t) + wps[i1][1] * t,
      fx: wps[i0][4] * (1 - t) + wps[i1][4] * t,
      fz: wps[i0][5] * (1 - t) + wps[i1][5] * t
    }};
  }}

  const spawn = getPosAtDist(cand.spawnDist);
  const gate = getPosAtDist(cand.startGateDist);

  // Dashed countdown trajectory line
  const countLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
  countLine.setAttribute("x1", spawn.x);
  countLine.setAttribute("y1", spawn.z);
  countLine.setAttribute("x2", gate.x);
  countLine.setAttribute("y2", gate.z);
  countLine.setAttribute("stroke", "#fbbf24");
  countLine.setAttribute("stroke-width", "6");
  countLine.setAttribute("stroke-dasharray", "8,8");
  g.appendChild(countLine);

  // Spawn Point (Circle with heading needle)
  const spawnCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  spawnCircle.setAttribute("cx", spawn.x);
  spawnCircle.setAttribute("cy", spawn.z);
  spawnCircle.setAttribute("r", "12");
  spawnCircle.setAttribute("fill", "#0284c7");
  spawnCircle.setAttribute("stroke", "#fff");
  spawnCircle.setAttribute("stroke-width", "3");
  g.appendChild(spawnCircle);

  // Start Gate (Perpendicular timing line)
  const lenF = Math.sqrt(gate.fx * gate.fx + gate.fz * gate.fz) || 1;
  const perpX = -gate.fz / lenF;
  const perpZ = gate.fx / lenF;
  const gateWidthHalf = 10;

  const gateLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
  gateLine.setAttribute("x1", gate.x - perpX * gateWidthHalf);
  gateLine.setAttribute("y1", gate.z - perpZ * gateWidthHalf);
  gateLine.setAttribute("x2", gate.x + perpX * gateWidthHalf);
  gateLine.setAttribute("y2", gate.z + perpZ * gateWidthHalf);
  gateLine.setAttribute("stroke", "#ef4444");
  gateLine.setAttribute("stroke-width", "6");
  g.appendChild(gateLine);

  // Labels
  const gateText = document.createElementNS("http://www.w3.org/2000/svg", "text");
  gateText.setAttribute("x", gate.x + perpX * (gateWidthHalf + 4));
  gateText.setAttribute("y", gate.z + perpZ * (gateWidthHalf + 4));
  gateText.setAttribute("fill", "#ef4444");
  gateText.setAttribute("font-size", "14");
  gateText.setAttribute("font-weight", "bold");
  gateText.textContent = `🏁 START GATE (s=${{cand.startProgress.toFixed(3)}})`;
  g.appendChild(gateText);

  circuitSvg.appendChild(g);
}}

// SVG Zoom & Pan Controls
function resetSvgView() {{
  if (!viewState.minX) return;
  const w = viewState.maxX - viewState.minX;
  const h = viewState.maxZ - viewState.minZ;
  circuitSvg.setAttribute("viewBox", `${{viewState.minX}} ${{viewState.minZ}} ${{w}} ${{h}}`);
}}

document.getElementById("btnZoomIn").addEventListener("click", () => {{
  zoomSvg(0.75);
}});

document.getElementById("btnZoomOut").addEventListener("click", () => {{
  zoomSvg(1.33);
}});

document.getElementById("btnResetView").addEventListener("click", () => {{
  resetSvgView();
}});

function zoomSvg(factor) {{
  const vb = circuitSvg.getAttribute("viewBox").split(" ").map(Number);
  const cx = vb[0] + vb[2] / 2;
  const cy = vb[1] + vb[3] / 2;
  const nw = vb[2] * factor;
  const nh = vb[3] * factor;
  circuitSvg.setAttribute("viewBox", `${{cx - nw / 2}} ${{cy - nh / 2}} ${{nw}} ${{nh}}`);
}}

// Mouse dragging pan
circuitSvg.addEventListener("mousedown", (e) => {{
  viewState.isDragging = true;
  viewState.dragStartX = e.clientX;
  viewState.dragStartY = e.clientY;
}});

window.addEventListener("mousemove", (e) => {{
  if (!viewState.isDragging) return;
  const dx = e.clientX - viewState.dragStartX;
  const dy = e.clientY - viewState.dragStartY;
  viewState.dragStartX = e.clientX;
  viewState.dragStartY = e.clientY;

  const vb = circuitSvg.getAttribute("viewBox").split(" ").map(Number);
  const scale = vb[2] / circuitSvg.clientWidth;
  vb[0] -= dx * scale;
  vb[1] -= dy * scale;
  circuitSvg.setAttribute("viewBox", `${{vb[0]}} ${{vb[1]}} ${{vb[2]}} ${{vb[3]}}`);
}});

window.addEventListener("mouseup", () => {{
  viewState.isDragging = false;
}});

// Sliders Event Handlers
sliderMaxSteer.addEventListener("input", (e) => {{
  const val = parseFloat(e.target.value);
  badgeMaxSteer.textContent = `±${{val.toFixed(1)}}°`;
  currentParams.max_steer_deg = val;
  recalculateAnalysis();
}});

sliderMinLength.addEventListener("input", (e) => {{
  const val = parseFloat(e.target.value);
  badgeMinLength.textContent = `${{val.toFixed(0)}}m`;
  currentParams.min_length_m = val;
  recalculateAnalysis();
}});

function updateMarginBadge() {{
  const sec = currentParams.post_go_sec !== undefined ? currentParams.post_go_sec : 1.5;
  badgeMargin.textContent = `${{sec.toFixed(1)}}s`;
}}

sliderCountdown.addEventListener("input", (e) => {{
  const val = parseFloat(e.target.value);
  badgeCountdown.textContent = `${{val.toFixed(1)}}s`;
  currentParams.countdown_sec = val;
  recalculateAnalysis();
}});

sliderMargin.addEventListener("input", (e) => {{
  const val = parseFloat(e.target.value);
  currentParams.post_go_sec = val;
  updateMarginBadge();
  recalculateAnalysis();
}});

// Preset buttons
document.querySelectorAll(".preset-pills .pill").forEach(pill => {{
  pill.addEventListener("click", () => {{
    document.querySelectorAll(".preset-pills .pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");

    const st = parseFloat(pill.dataset.steer);
    const len = parseFloat(pill.dataset.len);
    const pgo = parseFloat(pill.dataset.postgo || 1.5);

    sliderMaxSteer.value = st;
    sliderMinLength.value = len;
    sliderMargin.value = pgo;

    badgeMaxSteer.textContent = `±${{st.toFixed(1)}}°`;
    badgeMinLength.textContent = `${{len.toFixed(0)}}m`;
    badgeMargin.textContent = `${{pgo.toFixed(1)}}s`;

    currentParams.max_steer_deg = st;
    currentParams.min_length_m = len;
    currentParams.post_go_sec = pgo;

    recalculateAnalysis();
  }});
}});

// Export JSON Button
document.getElementById("btnExportJson").addEventListener("click", () => {{
  const track = TRACKS_DATA[activeTrackKey];
  const payload = {{
    track_id: track.track_id,
    track_layout: track.layout || "",
    parameters: currentParams,
    candidates: currentCandidates
  }};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${{track.track_id}}_${{track.layout || "default"}}_rolling_candidates.json`;
  a.click();
  showToast("Candidate JSON Downloaded!");
}});

// Initialize on Load
window.addEventListener("DOMContentLoaded", () => {{
  initTrackDropdown();
  updateMarginBadge();
  recalculateAnalysis();
}});
</script>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)


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
        # Default to ks_vallelunga club_circuit (used in test B-3)
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

            # Store serialized data for client-side JS
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

    # Generate interactive HTML
    output_html = os.path.abspath(args.output_html)
    generate_interactive_html(
        tracks_payload=tracks_payload,
        initial_track_key=initial_key,
        output_html_path=output_html,
        default_params=default_params,
    )
    print(f"\n[+] Interactive HTML circuit map generated:")
    print(f"    file:///{output_html.replace(os.sep, '/')}")

    # Export JSON if requested
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
