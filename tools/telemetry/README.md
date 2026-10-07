# Feature: AI Telemetry & Ghost Trajectories (`tools/telemetry/`)

## Overview
This subsystem captures, synthesizes, and interpolates realistic AI vehicle telemetry. It provides:
1. In-engine 60 Hz shared-memory telemetry recording of proficient AI drivers (95% AI level).
2. Curvature-calibrated Gold medal ghost trajectories with forward acceleration and backward braking kinematic passes.

---

## Directory & File Structure
```
tools/telemetry/
├── recorder.py                  # Live shared memory & spline-calibrated telemetry logger
├── ghost_generator.py           # 2-pass kinematic ghost trajectory generator
└── README.md                    # This agent reference guide
```

---

## Telemetry Profiling
Profiles are persisted to:
`data/telemetry_profiles/<track_id>__[<layout>]__<car_id>__ai95.json`

Each profile contains 60 Hz sampled waypoints:
- `progress`: Spline progress ratio $[0.0, 1.0]$
- `distance_m`: Track distance along spline in meters
- `speed_kmh`: True vehicle ground speed
- `gear`: Currently engaged transmission gear
- `rpm`: Engine revolutions per minute

---

## Ghost Kinematics Model
Ghost trajectories are computed using a physics-calibrated forward/backward pass:
1. Curvature radius $R_i$ from 3 contiguous waypoints:
   $$R = \frac{1}{\kappa}$$
2. Maximum lateral cornering velocity:
   $$v_{\text{corner}} = \sqrt{\mu \cdot g \cdot R} \quad (\mu \approx 1.25)$$
3. Backward braking pass from corner entry speed:
   $$v_i = \sqrt{v_{i+1}^2 + 2 \cdot a_{\text{brake}} \cdot \Delta s}$$
4. Forward acceleration pass from initial launch speed:
   $$v_i = \sqrt{v_{i-1}^2 + 2 \cdot a_{\text{accel}}(v) \cdot \Delta s}$$
5. Time normalization scaling to exactly match $T_{\text{gold}}$.

---

## Key Interfaces & Symbols

### `recorder.py`
- `TelemetryProfile`: Dataclass holding track, car, lap time, and sampled waypoints.
- `calibrate_from_spline(track_id, layout, car_id, spline_parser)`: Calibrates baseline 95% AI speed without launching the game.
- `load_telemetry_profile(track_id, layout, car_id)`: Loads cached JSON profile from disk.

### `ghost_generator.py`
- `generate_ghost_profile(test_config, dt=0.05)`: Generates time-stamped trajectory array.
- `compute_curvature_radius(p_prev, p_curr, p_next)`: 2D curvature radius in meters.

---

## Quick Command Usage
```powershell
# Generate ghost trajectory for test B-3
python tools/generate_ghost_trajectory.py --test content/tests/national_b/test_b03.json

# Record or verify telemetry profile
python tools/record_ai_telemetry.py --track ks_vallelunga --layout club_circuit --car ks_mazda_miata
```

