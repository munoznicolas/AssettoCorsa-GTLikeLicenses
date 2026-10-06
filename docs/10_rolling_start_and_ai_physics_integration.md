# Rolling Start & AI Physics Integration Guide

Documentation of reusable architectural patterns, algorithms, and CSP physics APIs extracted from reference rolling start mods (`fcy_yellow_rollingstart` and `rapidough1s_Rolling_Start_App_V0.9`) for application in **Assetto Corsa GT-Like Licenses** (`gt-license`).

---

## 1. Executive Summary & Purpose

License tests in Gran Turismo frequently require dynamic AI traffic, pace car guidance (e.g., IB-5 Pace Car Following), or rolling start launches for high-speed sector challenges (e.g., Spa Eau Rouge, Suzuka 130R, Monza Parabolica).

By analyzing community reference mods, we identified key technical mechanisms powered by the Custom Shaders Patch (CSP) `physics.*` Lua namespace. These patterns allow us to precisely manipulate AI speed, lane positioning, gap tracking, player controls, and smooth green-flag transitions within the `gt-license` engine.

---

## 2. Key CSP Physics APIs (`physics.*` Namespace)

| Function Signature | Description | License Test Application |
| :--- | :--- | :--- |
| `physics.setCarAutopilot(active: bool, chooseTyres: bool)` | Activates or deactivates native Assetto Corsa AI driver takeover of user car (`0`). | Core driver takeover during rolling start countdown (`3-2-1`). Released on "GO!". |
| `physics.setAITopSpeed(carIndex: int, speedKmh: float)` | Sets an absolute speed ceiling (in km/h) on an AI car. | Caps vehicle speed to target rolling launch velocity (e.g. 70 km/h) or pace car speed. |
| `physics.setAILevel(carIndex: int, level: float)` | Sets AI driver skill rating (`0.0` to `2.0`, standard `1.0`). | Calibrates smooth racing line adherence and corner navigation without errors. |
| `physics.setAIAggression(carIndex: int, aggression: float)` | Controls AI overtaking assertiveness (`0.0` to `1.0`). | Set to `0.0` during rolling countdown to prevent erratic steering or aggressive slides. |
| `physics.setAICaution(carIndex: int, level: float)` | Adjusts AI safety/aggression margin (`0.0` aggressive to `3.0+` cautious). | Set to `0.1` during rolling countdown so AI maintains rolling speed through sweeps. |
| `physics.setAISplineAbsoluteOffset(carIndex: int, offset: float, isRel: bool)` | Sets lateral distance (in meters) from the track ideal spline. | Set to `0.0` to lock rolling car strictly to the official racing line (`fast_lane.ai`). |
| `physics.setAIThrottleLimit(carIndex: int, limit: float)` | Restricts maximum throttle output (`0.0` to `1.0`). | Prevents wheelspin or aggressive overshooting on formation laps/corners. |
| `physics.setAIStopCounter(carIndex: int, seconds: float)` | Commands AI car to halt for `seconds` duration. | Holds AI cars on grid slots during countdown or delayed release. |
| `physics.forceUserThrottleFor(seconds: float, val: float)` | Overrides human player throttle input (`0.0` to `1.0`). | Prevents accidental rev-limiter bouncing during countdown. |
| `physics.forceUserBrakesFor(seconds: float, val: float)` | Overrides human player brake input (`0.0` to `1.0`). | Engages brakes on standing starts; explicitly set to `0` during rolling starts. |
| `physics.engageGear(carIndex: int, gear: int)` | Asserts instantaneous gearbox gear selection. | Retains appropriate transmission gear (e.g. 2nd) across rolling start handover. |

---

## 3. Core Architectural Patterns

### A. Two-Phase Rolling Start & Pace Sequence

To ensure stable multi-car movement without AI pileups, rolling starts should be split into distinct phases:

```
[ Session Start ]
       │
       ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 1: Single-File Pace / Warm-Up Lap                   │
│ - Speed Limit: formationLapSpeedLimit (e.g. 100 km/h)     │
│ - Alignment: Single file along track center spline        │
│ - Gap Control: Catch-up if dist > 40m, brake if dist < 20m│
└───────────────────────────────────────────────────────────┘
       │
       │ (Reached spline progress threshold, e.g. 67%)
       ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 2: Double-File Grid Alignment                       │
│ - Speed Limit: rollingStartSpeedLimit (e.g. 70 km/h)      │
│ - Alignment: Staggered Left/Right lateral spline offsets  │
│ - Row & Column pairing math keeps grid locked            │
└───────────────────────────────────────────────────────────┘
       │
       │ (Leader crosses S/F line / License Start Zone)
       ▼
┌───────────────────────────────────────────────────────────┐
│ Phase 3: Green Flag Release & Smooth Transition           │
│ - Uncap top speeds (setAITopSpeed = 999999)               │
│ - Linearly decay spline offsets to 0.0 at 0.5 m/s         │
│ - Gradually restore AI caution over 10 seconds            │
└───────────────────────────────────────────────────────────┘
```

---

### B. Track Distance & Spline Progress Calculations

Converting abstract spline progress deltas ($\Delta s$) into physical meters on track:

$$\text{distanceMeters} = (s_{\text{ahead}} - s_{\text{behind}}) \times L_{\text{track}}$$

```lua
local function GetSplineDistanceMeters(carAheadIdx, carBehindIdx)
  local carAhead = ac.getCar(carAheadIdx)
  local carBehind = ac.getCar(carBehindIdx)
  if not carAhead or not carBehind then return 0.0 end

  local trackLength = ac.getSim().trackLengthM
  local splineDelta = carAhead.splinePosition - carBehind.splinePosition

  -- Handle lap wrap-around if carAhead has crossed S/F line
  if splineDelta < -0.5 then
    splineDelta = splineDelta + 1.0
  end

  return splineDelta * trackLength
end
```

---

### C. Proportional Catch-Up & Speed Scaling

To maintain fixed longitudinal gaps ($D_{\text{target}} \approx 8\text{m}$) between cars in a column, a linear speed multiplier function scales the target speed:

```lua
local function GetLinearMultiplier(distMeters, minDist, maxDist, maxMult)
  maxMult = maxMult or 1.5
  if distMeters <= minDist then return 1.0 end
  if distMeters >= maxDist then return maxMult end
  return 1.0 + ((distMeters - minDist) / (maxDist - minDist)) * (maxMult - 1.0)
end
```

- **If gap exceeds target ($> 8\text{m}$)**: Speed multiplier increases target speed up to $1.5\times$ to close the gap.
- **If gap shrinks below threshold ($< 1.5\text{m}$)**: Speed and throttle are limited to prevent rear-end collisions.

---

### D. Organic Micro-Weaving (Humanizing AI)

To prevent AI pace cars or rolling grid cars from looking like rigid on-rail models, small sine/cosine perturbations are added to the lateral spline offset:

```lua
local function GetOrganicLaneOffset(driverIdx, sessionTimer)
  local wave1 = math.sin(sessionTimer * 0.25 + driverIdx * 1.7) * 0.40
  local wave2 = math.cos(sessionTimer * 0.40 - driverIdx * 2.3) * 0.10
  return wave1 + wave2
end
```

---

### E. Smooth Green-Flag Spline Offset Decay

> [!WARNING]
> Abruptly setting `physics.setAISplineAbsoluteOffset(i, 0.0)` at the moment of Green Flag causes AI cars to jerk violently toward the racing line at high speed, resulting in instant collisions.

Offsets must decay smoothly back to zero at a maximum rate of $\approx 0.5\text{ m/s}$:

```lua
local function SmoothGreenFlagTransition(dt)
  local maxMove = 0.5 * dt
  for i = 0, driverCount - 1 do
    local currentOffset = currentSplineOffset[i] or 0.0
    if math.abs(currentOffset) > 0.001 then
      local diff = -currentOffset
      if math.abs(diff) > maxMove then
        currentOffset = currentOffset + (diff > 0 and maxMove or -maxMove)
      else
        currentOffset = 0.0
      end
      currentSplineOffset[i] = currentOffset
      physics.setAISplineAbsoluteOffset(i, currentOffset, false)
    end
  end
end
```

---

## 4. Application Blueprint for GT-Like Licenses

### 1. Pace Car License Tests (IB-5 Pace Car Challenge)
- **Mechanism**: Spawn Pace Car as car `1` (or dedicated AI slot).
- **Pace Speed Control**: Use `physics.setAITopSpeed(1, targetPaceSpeedKmh)`.
- **Distance Adjudication**: Track `GetSplineDistanceMeters(1, 0)`.
  - Fail test if player falls $> 30\text{m}$ behind or overtakes pace car before green zone.
  - Award Gold/Silver/Bronze based on precision of maintaining target gap ($\pm 3\text{m}$).

### 2. High-Speed Sector Rolling Starts & Native AI Autopilot
- **The Architecture**: Rather than relying on synthetic velocity vectors or manual steering calculations, rolling starts are driven by Assetto Corsa's native AI autopilot following the official track racing line (`ideal_line.ai` / `fast_lane.ai`).
- **Setup & Autopilot Engagement (`startAIRolling`)**:
  - Teleport the car rigid body once at spawn facing $-\vec{fwd}$ and impart initial kinetic velocity and wheel omega matching target speed.
  - Assert `physics.setCarAutopilot(true, false)` to transfer driving inputs directly to Assetto Corsa's native AI.
  - Assert `physics.setAITopSpeed(carIndex, targetSpeedKmh)` to cap the AI velocity ceiling to the exact target rolling speed.
  - Configure `physics.setAILevel(carIndex, 1.0)`, `physics.setAIAggression(carIndex, 0.0)`, and `physics.setAICaution(carIndex, 0.1)` for clean, non-erratic, professional racing line adherence.
  - Assert `physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)` to keep the vehicle locked directly to the ideal racing line.
  - Release all user control locks and forced brakes (`lockUserControlsFor(0)`, `forceUserBrakesFor(0, 0)`) so the native AI operates without friction.
- **Countdown Maintenance (`maintainAIRolling`)**:
  - On frame updates during `COUNTDOWN`, continuously reinforce `physics.setAITopSpeed(carIndex, targetSpeedKmh)` and `physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)`.
  - The native AI naturally steers the front wheels, engages gears, works the clutch, and modulates throttle along track curves.
  - If a track lacks an AI spline (`ac.hasTrackSpline() == false`), automatically fall back to linear velocity maintenance (`maintainRollingVelocity`).
- **Seamless Handover on "GO!" (`stopAIRolling`)**:
  - Call `physics.setCarAutopilot(false)` to deactivate autopilot and immediately return vehicle control to the human player.
  - Call `physics.setAITopSpeed(carIndex, 999999.0)` to remove the AI top speed ceiling so the player can accelerate to maximum velocity.
  - Inside `GTPhysicsHooks.unlockControls(carIndex, targetGear)`, directly assert `physics.engageGear(carIndex, targetGear)` and `physics.setEngineRPM(carIndex, 3500)` without triggering AC's starting-line neutral reset subroutine.
  - Maintain a $0.5\text{s}$ guard window in `RUNNING` state inside `GTLicenseEngine:update(dt)` to re-assert `targetGear` if controller initialization or clutch slip drops it to neutral.
- **Spawn Distance Calibration Rule**:
  - Set $\text{spawn\_offset} = v_{\text{mps}} \times t_{\text{countdown}}$ (e.g. $58.3\text{m}$ for $70\text{ km/h}$ over $3.0\text{s}$) so the car rolls up to the start gate right as the countdown reaches "GO!".
  - On "GO!", mark `self.adjudicator.hasPassedStartGate = true` for rolling start tests to ensure finish gate crossing registers cleanly.

### 3. Overtaking & Traffic License Tests (IA / Super License)
- **Mechanism**: Populate track with multiple AI cars.
- **Traffic Speed Capping**: Use `physics.setAITopSpeed(i, trafficSpeedKmh)` and `physics.setAISplineAbsoluteOffset(i, laneOffset, false)` to create realistic traffic scenarios (defending inside line, slow exit on corner, etc.) for the player to negotiate cleanly.

---

## 5. Track Physics Compatibility Fallback

If `physics.allowed()` returns `false` on older CSP installations or unconfigured custom tracks, `data/surfaces.ini` can be updated dynamically:

```ini
[SURFACE_0]
WAV_PITCH=extended-0

[_SCRIPTING_PHYSICS]
ALLOW_APPS=1
```

*(This fallback should be gated behind a setup utility or CM configuration check).*
