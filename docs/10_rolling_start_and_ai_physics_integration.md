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
| `physics.setAITopSpeed(carIndex: int, speedKmh: float)` | Sets an absolute speed ceiling (in km/h) on an AI car. | Controls pace car speed or caps traffic speed during overtaking tests. |
| `physics.setAIThrottleLimit(carIndex: int, limit: float)` | Restricts maximum throttle output (`0.0` to `1.0`). | Prevents AI wheelspin or aggressive overshooting on formation laps/corners. |
| `physics.setAICaution(carIndex: int, level: float)` | Adjusts AI safety/aggression margin (`0.0` aggressive to `3.0+` cautious). | Controls AI overtaking eagerness and collision avoidance during tests. |
| `physics.setAISplineAbsoluteOffset(carIndex: int, offset: float, isRel: bool)` | Sets lateral distance (in meters) from the track ideal spline. | Positions AI in specific lanes, sets up staggered grids, or holds pace lines. |
| `physics.setAIStopCounter(carIndex: int, seconds: float)` | Commands AI car to halt for `seconds` duration. | Holds AI cars on grid slots during countdown or delayed release. |
| `physics.forceUserThrottleFor(seconds: float, val: float)` | Overrides human player throttle input (`0.0` to `1.0`). | Holds player car stationary during grid countdown without stalls. |
| `physics.forceUserBrakesFor(seconds: float, val: float)` | Overrides human player brake input (`0.0` to `1.0`). | Engages player brakes during rolling start control lock phase. |

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

### 2. High-Speed Sector Rolling Starts & Curved Approaches
- **The Curvature Pitfall**: In tests where the pre-sector approach curves (such as B-3 Out-In-Out Hairpin Trajectory at Vallelunga Club Circuit), enforcing a static linear velocity vector along a fixed spawn heading causes the car to travel in a Euclidean straight line, drifting off-track into the grass and accumulating off-track penalties before control is handed to the player.
- **Steering Rack Lock vs. Kinematic Spline Guidance Pitfall**:
  - Attempting to steer the front wheels along the curve via `physics.overrideSteering` while player controls are locked (`physics.lockUserControlsFor(duration)`) is **ineffective**: Assetto Corsa's C++ physics core locks the mechanical steering rack itself during control locks.
  - Omitting chassis positioning during countdown and relying solely on velocity + steering override causes the vehicle to plow straight ahead along its initial spawn heading, drifting into outer barriers.
  - Spline-guided countdowns must reposition and orient the chassis directly via `physics.setCarPosition(carIndex, targetPos, vec3(-fwd.x, -fwd.y, -fwd.z))`.
- **Dynamic Spline Guidance (`maintainRollingSpline`)**:
  - Resolve the initial spline progress $s_0$ using `ac.worldCoordinateToTrackProgress(spawnPos)`.
  - On every frame update during `COUNTDOWN`, advance the progress by $\Delta s = \frac{v_{\text{mps}} \cdot dt}{L_{\text{track}}}$.
  - Compute the world position $P(s)$ and a lookahead tangent vector $\vec{fwd} = \text{normalize}(P(s + \delta s) - P(s))$ via `ac.trackProgressToWorldCoordinate`.
  - **Lookahead Distance Calibration Rule**: Scale lookahead with vehicle speed:
    $$\text{lookaheadDist} = \max(3.5\text{m}, v_{\text{mps}} \times 0.25)$$
    Using an infinitesimal lookahead ($< 3.0\text{m}$, less than one car length) causes the chassis to track the immediate local curb tangent, aiming the vehicle's nose into the outside white line on corner approach. A dynamic lookahead ($\approx 4.9\text{m}$ at $70\text{ km/h}$) smoothly anticipates the corner entry and apex.
  - Apply chassis orientation `vec3(-fwd.x, -fwd.y, -fwd.z)` (Orientation Inversion Rule) and elevation $P(s) + 0.05\text{m}$ using `physics.setCarPosition(0, targetPos, -fwd)`.
  - Apply the matching velocity vector $\vec{fwd} \times v_{\text{mps}}$ using `physics.setCarVelocity(0, vel)`.
  - Continuously enforce gear (2nd) and RPM (3500) via `ac.accessCarPhysics(0)` and `physics.engageGear`.
  - If a track lacks an AI spline (`ac.hasTrackSpline() == false`), automatically fall back to static forward vector maintenance (`maintainRollingVelocity`).
- **Drivetrain & Gear Engagement Retention Across Handover**:
  - **The Starting-Line Neutral Reset Trap**: Calling `physics.lockUserGearboxFor(0, false)` on rolling starts triggers Assetto Corsa's native starting-line subroutine, which disengages any selected gear and drops the transmission back to neutral.
  - **Handover Gear Assertion**: Inside `GTPhysicsHooks.unlockControls(carIndex, targetGear)`, on rolling starts where `targetGear > 0`, **bypass** `lockUserGearboxFor(0, false)` completely. Instead, explicitly call `physics.engageGear(carIndex, targetGear)` and `physics.setEngineRPM(carIndex, 3500)`.
  - **Post-Handover Guard Window**: When transitioning into `RUNNING` state, hardware controller initialization or clutch release can attempt to drop the gearbox back to neutral. Maintain a $0.5\text{s}$ guard window in `GTLicenseEngine:update(dt)` that re-asserts `physics.engageGear(0, targetGear)` if `car.gear == 0`, ensuring instantaneous drive power when the player accelerates.
- **Spawn Distance Calibration Rule**:
  - To ensure the countdown sequence naturally leads up to the start line and crosses the start gate right at "GO!", the spawn offset upstream of the start gate must equal:
    $$\text{spawn\_offset} = \left(\frac{v_{\text{km/h}}}{3.6}\right) \times t_{\text{countdown}}$$
  - Example: for $70.0\text{ km/h}$ over a $3.0\text{s}$ countdown, $\text{spawn\_offset} = 19.444 \times 3.0 \approx 58.3\text{ meters}$.
  - At the green flag ("GO!"), mark `self.adjudicator.hasPassedStartGate = true` to ensure the sector timing completion registers cleanly.

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
