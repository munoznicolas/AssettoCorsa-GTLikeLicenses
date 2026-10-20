# CSP Lua Simulation Engine Subsystem (`lua/engine/`)

## Overview
This subsystem runs inside Assetto Corsa Custom Shaders Patch (CSP) New Modes (`gt-license`). It coordinates the lifecycle state machine, rigid-body physics teleportation, rolling start AI autopilot tracking, track limits adjudication, and session resets.

---

## Directory & File Structure
```
lua/engine/
├── license_engine.lua           # Master scenario state machine coordinator
├── engine_runtime.lua           # Runtime frame hooks, input handling, and state transitions
├── config_loader.lua            # Dynamic test JSON & race.ini resolver via CSP FolderID
├── results.lua                  # Target time adjudication & medal calculation (Gold/Silver/Bronze)
├── physics_hooks.lua            # Rigid-body teleportation, orientation vectors, & AI autopilot
├── rolling_start.lua            # Rolling start countdown & handover logic
├── adjudicator.lua              # Gate ray-crossing math & 4-wheel track limits adjudication
├── ai_coordinator.lua           # Native AI racing line lock & pace coordination
├── session_reset.lua            # Standing/rolling restart triggers & crash debounce
├── shared_state.lua             # Zero-copy shared state memory sync with HUD app
├── telemetry_logger.lua         # Telemetry evaluation logger
├── utils.lua                    # Vector math, JSON parsing, & package search paths
└── README.md                    # This reference guide
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
1. **No `script.init()` Hook**: Top-level engine must be instantiated immediately at module load time (`LicenseEngine.new()`).
2. **Coordinate Orientation Inversion**: In `physics.setCarPosition(carIndex, pos, orientation)`, pass $-\vec{fwd}$ to orient headlights forward. Passing $+\vec{fwd}$ faces the vehicle backwards.
3. **AI Autopilot Rolling Starts**:
   - `physics.setCarAutopilot(true, false)` takes over driver inputs during countdown.
   - `physics.setAITopSpeed(carIndex, speedKmh)` caps rolling speed.
   - At "GO!", `physics.setCarAutopilot(false)` and `physics.setAITopSpeed(carIndex, 999999)` handover control seamlessly.
4. **Track Limits**: Adjudicate using `car.wheels[i].surfaceValidTrack` from `ac.StateWheel` (debounce 2 consecutive frames). Never rely solely on `car.wheelsOutside`.
5. **No Synthetic Velocity Overrides or Forced Zero Throttle**:
   Never call `physics.setCarVelocity` or `physics.forceUserThrottleFor(..., 0.0)` on every frame during countdown. Clamping vertical velocity ($v_y$) nullifies gravity ($g = -9.81\text{ m/s}^2$), lifting the vehicle into unweighted suspension droop (~60mm extension), while zero throttle causes internal drivetrain resistance to drag driven wheels at 40%+ slip, producing constant rubber skid marks. Always let native AI autopilot (`physics.setCarAutopilot(true, false)` + `physics.setAITopSpeed`) drive the car smoothly along the spline.
