# License Test JSON Specifications (`content/tests/`)

## Overview
Stores the 58 test JSON definition files calibrated against Assetto Corsa tracks and vehicles.

---

## JSON Structure Contract
Each test definition conforms to `schema/test_definition.schema.json`:
- `test_id`: e.g. `"B-3"`
- `tier`: e.g. `"National B"`
- `car_id`: e.g. `"ks_mazda_miata"`
- `track_id` & `track_layout`: e.g. `"ks_vallelunga"`, `"club_circuit"`
- `start_mode`: `"STANDING"` or `"ROLLING"`
- `spawn`: `{ position: [x,y,z], forward_vector: [dx,dy,dz], initial_speed_kmh, gear, rpm }`
- `timing`:
  - `start_gate`: `{ p1: [x,y,z], p2: [x,y,z], width_m }`
  - `finish_gate`: `{ p1: [x,y,z], p2: [x,y,z], width_m }`
  - `stop_box` (optional): `{ center: [x,y,z], size: [w,h,l], rotation_deg }`
- `fail_rules`: `{ max_wheels_off, wall_collision_threshold_n, stop_box_overshoot_fail }`
- `targets`: `{ gold_seconds, silver_seconds, bronze_seconds }`

