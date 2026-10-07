# Feature: Spline Kinematics & Circuit Analysis (`tools/spline/`)

## Overview
This subsystem parses Assetto Corsa's binary AI racing line files (`fast_lane.ai` and `ideal_line.ai`), computes steering wheel angle kinematics, detects pure straight-line sections ($\pm 2.0^\circ$ steer angle), and automatically identifies optimal rolling start spawn locations.

---

## Directory & File Structure
```
tools/spline/
├── parser.py                    # Binary reader for AC AI splines (SplineParser)
├── straight_analyzer.py         # Kinematic steering model & straight segment detector
├── circuit_mapper.py            # CLI discovery engine & interactive map generator
├── templates/
│   └── circuit_mapper.html      # Self-contained Canvas/SVG interactive circuit visualizer
└── README.md                    # This agent reference guide
```

---

## Mathematical Model
The steering wheel angle $\delta_{\text{wheel}}$ is computed directly from track curvature radius $R$, vehicle wheelbase $L$, and steering rack ratio $S_{\text{ratio}}$:
$$\delta_{\text{road}} = \arctan\left(\frac{L}{R}\right) \approx \frac{L}{R} \quad (\text{radians})$$
$$\delta_{\text{wheel}} = \delta_{\text{road}} \cdot S_{\text{ratio}} \cdot \frac{180^\circ}{\pi} \quad (\text{degrees})$$

A segment is classified as straight when $|\delta_{\text{wheel}}| \le \text{tolerance}$ (typically $\pm 2.0^\circ$).

---

## Key Interfaces & Symbols

### `parser.py`
- `SplineParser(spline_path)`: Parses binary waypoint records (x, y, z, distance, walls, forward vector, radius).
- `generate_test_parameters(parser, start_progress, finish_progress, ...)`: Computes spawn coordinates, gate vectors, and stop box dimensions.
- `find_spline_file(track_id, layout, ac_root)`: Locates `fast_lane.ai` on disk.

### `straight_analyzer.py`
- `TrackStraightAnalyzer(parser, track_id, layout, car_id, ...)`: Scans waypoints for straight segments.
- `RollingStartCandidate`: Represents a viable rolling start position with score, spawn offset, target speed, engaged gear, and RPM.

### `circuit_mapper.py`
- `generate_interactive_html(tracks_payload, initial_track_key, output_html_path, default_params)`: Generates interactive HTML map using `templates/circuit_mapper.html`.

---

## Quick Command Usage
```powershell
# Analyze straight segments for Vallelunga Club Circuit
python tools/rolling_start_mapper.py --track ks_vallelunga --layout club_circuit

# Batch scan all official Kunos tracks and generate master HTML map
python tools/rolling_start_mapper.py --all-kunos --output-html output/kunos_rolling_starts_master.html
```

