# Feature: AI Telemetry (`tools/telemetry/`)

## Overview
This subsystem captures, synthesizes, and interpolates realistic AI vehicle telemetry via in-engine 60 Hz shared-memory telemetry recording of proficient AI drivers.

---

## Directory & File Structure
```
tools/telemetry/
├── profile.py                   # Telemetry data models & spline calibration
├── recorder.py                  # Live shared memory & spline-calibrated telemetry logger
└── README.md                    # This reference guide
```

---

## Telemetry Profiling
Profiles are persisted to:
`data/telemetry_profiles/<track_id>__[<layout>]__<car_id>__ai<level>.json`

Each profile contains 60 Hz sampled waypoints:
- `progress`: Spline progress ratio $[0.0, 1.0]$
- `distance_m`: Track distance along spline in meters
- `speed_kmh`: True vehicle ground speed
- `gear`: Currently engaged transmission gear
- `rpm`: Engine revolutions per minute

---

## Quick Command Usage
```powershell
# Record or verify telemetry profile
python -m tools.telemetry.recorder --track ks_vallelunga --layout club_circuit --car ks_mazda_miata
```
