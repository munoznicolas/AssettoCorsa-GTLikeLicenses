# CSP Lua Simulation Engine Subsystem (`lua/engine/`)

## Overview
This subsystem runs inside Assetto Corsa Custom Shaders Patch (CSP) New Modes (`gt-license`). It coordinates the lifecycle state machine, rigid-body physics teleportation, rolling start AI autopilot tracking, track limits adjudication, ghost playback, and session resets.

---

## Directory & File Structure
```
lua/engine/
├── gt_license_engine.lua        # Master scenario state machine coordinator & lifecycle hooks
├── gt_config_loader.lua         # Dynamic test JSON & race.ini resolver via CSP FolderID
├── gt_results.lua               # Target time adjudication & medal calculation (Gold/Silver/Bronze)
├── gt_physics_hooks.lua         # Rigid-body teleportation, orientation vectors, & AI autopilot
├── gt_adjudicator.lua           # Gate ray-crossing math & 4-wheel track limits adjudication
├── gt_ghost_manager.lua         # 60Hz Ghost & Pacer car telemetry interpolation & state
├── gt_ai_coordinator.lua        # Native AI racing line lock & pace coordination
├── gt_session_reset.lua         # Standing/rolling restart triggers & crash debounce
├── gt_utils.lua                 # Vector math, JSON parsing, & package search paths
└── README.md                    # This agent reference guide
```

---

## Lifecycle State Machine
```
[INITIALIZING]
      │ (First update frame: spawnRigidBody, engageGear, AI autopilot)
      ▼
 [COUNTDOWN] ──(Session Reset: Esc/Pit/Off-track)──► [COUNTDOWN]
      │
      │ 3-2-1-GO! (Handover: AI autopilot OFF, controls UNLOCKED)
      ▼
  [RUNNING]  ──(Violation: off-track / wall hit)──► [FAILED]
      │                                                │
      │ Finish Gate Crossing                           │ Reset / Retry
      ▼                                                ▼
  [PASSED] ──► [RESULTS] ──────────────────────────► [COUNTDOWN]
```

---

## Critical CSP Rules & Gotchas
1. **No `script.init()` Hook**: Top-level engine must be instantiated immediately at module load time (`GTLicenseEngine.new()`).
2. **Coordinate Orientation Inversion**: In `physics.setCarPosition(carIndex, pos, orientation)`, pass $-\vec{fwd}$ to orient headlights forward. Passing $+\vec{fwd}$ faces the vehicle backwards.
3. **AI Autopilot Rolling Starts**:
   - `physics.setCarAutopilot(true, false)` takes over driver inputs during countdown.
   - `physics.setAITopSpeed(carIndex, speedKmh)` caps rolling speed.
   - At "GO!", `physics.setCarAutopilot(false)` and `physics.setAITopSpeed(carIndex, 999999)` handover control seamlessly.
4. **Track Limits**: Adjudicate using `car.wheels[i].surfaceValidTrack` from `ac.StateWheel` (debounce 2 consecutive frames). Never rely solely on `car.wheelsOutside`.

