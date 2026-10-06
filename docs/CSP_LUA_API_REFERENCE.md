# Custom Shaders Patch (CSP) Lua API Reference

Comprehensive reference guide for Custom Shaders Patch (CSP) LUA APIs utilized in the Assetto Corsa Gran Turismo-Style License Tests mod (`gt-license`).

---

## 1. Core Architecture & Execution Model

Custom Shaders Patch (CSP) extends Assetto Corsa (`acs.exe`) by embedding a Lua runtime directly into the core rendering and physics dispatch loops. Lua scripts execute within dedicated scopes depending on their entry point (e.g. `extension/lua/new-modes/`).

```
+-------------------------------------------------------------------------+
|                        Assetto Corsa (acs.exe)                          |
+-------------------------------------------------------------------------+
                                   |
           +-----------------------+-----------------------+
           |                                               |
           v                                               v
+-----------------------+                       +-----------------------+
|  Native C++ Engine    |                       | Custom Shaders Patch  |
|     Physics Loop      |                       |     Lua Subsystem     |
|   (Reset / Control)   |                       |   (Events & Hooks)    |
+-----------------------+                       +-----------------------+
           |                                               |
           +-----------------------+-----------------------+
                                   |
                                   v
             +-------------------------------------------+
             | update(dt) Callback (GT-License Engine)   |
             | - Evaluates state (COUNTDOWN/RUNNING)     |
             | - Re-applies velocity on COUNTDOWN frames |
             +-------------------------------------------+
```

### Script Entry Point & Lifecycle Callbacks
- `script.update(dt)`: Main simulation loop called once per frame (60–240+ Hz). Primary hook for state machine evaluation, adjudicator rules, and continuous physics overrides.
- `script.draw3D(dt)`: 3D world space rendering callback. Used for rendering holographic 3D ghost cars, checkpoint gate pillars, and countdown banners.
- `script.drawUI(dt)`: 2D screen space Canvas rendering callback. Used for drawing HUD elements, medal targets, stop box indicators, and telemetry overlays.

---

## 2. Vehicle Physics & Telemetry APIs

### `ac.getCar(index: integer) -> CarState`
Retrieves the telemetry and physics state table for a vehicle by zero-based index (`0` for the player vehicle).

#### Key Properties of `CarState`:
| Property | Type | Description |
| :--- | :--- | :--- |
| `car.position` | `vec3` | World position coordinates `(x, y, z)` in meters. |
| `car.velocity` | `vec3` | Linear velocity vector `(vx, vy, vz)` in m/s. |
| `car.speedKmh` | `number` | Scalar forward/reverse velocity in km/h. |
| `car.steer` | `number` | Current steering angle input normalized `[-1.0, 1.0]`. |
| `car.gas` | `number` | Throttle pedal input normalized `[0.0, 1.0]`. |
| `car.brake` | `number` | Brake pedal input normalized `[0.0, 1.0]`. |
| `car.gear` | `integer` | Active gear (-1 = Reverse, 0 = Neutral, 1+ = Forward). |
| `car.wheels` | `ac.StateWheel[]` | 4-element array (`0..3`). Each wheel provides `surfaceValidTrack: boolean` from `surfaces.ini`. |
| `car.wheelsOutside` | `integer` | Native AC penalty counter (0 to 4). Unreliable in New Modes without cut penalty triggers. |
| `car.collidedWith` | `integer` | Index of car collided with, or -1 if none. |

#### Authoritative Track Limits & Off-Track Detection:
In Custom Shaders Patch New Modes, `car.wheelsOutside` (derived from Kunos' `numberOfTyresOut` shared memory) is tied to Kunos' native penalty and cut-detection subroutines. In custom event modes or across non-standard sectors, `car.wheelsOutside` frequently remains `0` even when all four tyres are on grass, sand, or gravel.

The **authoritative ground-truth** for wheel surface contact is `car.wheels[i].surfaceValidTrack` (`i = 0..3`):
- Each wheel raycasts onto track geometry every physics tick and queries `surfaces.ini`.
- If on valid tarmac or curbs (`IS_VALID_TRACK=1`), `surfaceValidTrack` is `true`.
- If on grass, gravel, dirt, or runoff out-of-bounds (`IS_VALID_TRACK=0`), `surfaceValidTrack` is `false`.
- To avoid false positives from instantaneous 1-frame mesh seam raycast drops or high curb hops, debounce the off-track condition over **2 consecutive frames** (~33ms at 60Hz) before issuing disqualification.

---

## 3. Physics Manipulation & Direct State Hooks (`physics.*`)

> [!IMPORTANT]
> Calling native CSP physics setters **once** on spawn is insufficient when in `COUNTDOWN` state because AC's native C++ engine resets car linear velocity to zero every frame while player controls are locked. Velocity, gear, and engine RPM setters MUST be invoked continuously inside `update(dt)`.

### `physics.setCarPosition(carIndex: integer, pos: vec3, dir: vec3)`
Teleports the vehicle chassis directly to world position `pos` and orients it on the track surface.

> [!WARNING]
> **Orientation Inversion Rule**: Assetto Corsa's internal coordinate convention for `physics.setCarPosition` inverts the orientation direction vector relative to `car.look`. To orient the car's headlights forward along $\vec{fwd}$, you **must pass $-\vec{fwd}$**:
> ```lua
> physics.setCarPosition(carIndex, targetPos, vec3(-fwd.x, -fwd.y, -fwd.z))
> ```
> Passing $+\vec{fwd}$ points the car's headlights $180^\circ$ backwards. If forward velocity is then applied along $\vec{fwd}$, the vehicle will launch backwards in reverse!

### `physics.setCarVelocity(carIndex: integer, velocity: vec3)`
Directly sets the 3D linear velocity vector of the specified car in world space ($m/s$).

```lua
-- Example: Apply 70 km/h rolling velocity along forward direction vector
local speedMps = 70.0 / 3.6
local forwardVec = vec3(1.0, 0.0, 0.0)
local velMps = vec3(forwardVec.x * speedMps, forwardVec.y * speedMps, forwardVec.z * speedMps)

physics.setCarVelocity(0, velMps)
```

### `physics.engageGear(carIndex: integer, gear: integer)`
Forces a specific gear to engage (`-1` = Reverse, `0` = Neutral, `1` = 1st, `2` = 2nd, etc.):

```lua
physics.engageGear(0, 2) -- Engage 2nd gear for rolling start launch
```

### `physics.setEngineRPM(carIndex: integer, rpm: number)`
Sets the active engine RPM to prevent engine stall or idle during rolling starts:

```lua
physics.setEngineRPM(0, 3500)
```

### `physics.lockUserControlsFor(seconds: number)`
Locks user steering, throttle, and brake inputs for a specified duration (0 to unlock immediately).

### `physics.forceUserBrakesFor(seconds: number, val: number)`
Forces human player brake pedal input (`0.0` to `1.0`) during standing start countdowns.

---

## 4. UI & Rendering APIs

### 2D Canvas Graphics (`ui.*`)
Available inside `script.drawUI(dt)` or Canvas rendering contexts.

| Function | Description |
| :--- | :--- |
| `ui.drawRectFilled(pMin, pMax, color, rounding)` | Renders a filled 2D rectangle with optional corner rounding. |
| `ui.drawRect(pMin, pMax, color, thickness)` | Renders a 2D rectangle outline. |
| `ui.drawText(pos, text, color, fontSize)` | Renders text string at screen coordinates `pos`. |
| `ui.drawLine(p1, p2, color, thickness)` | Renders a 2D line segment between `p1` and `p2`. |

### 3D World Rendering (`ac.render*`)
Available inside `script.draw3D(dt)`.

| Function | Description |
| :--- | :--- |
| `render.debugLine(p1, p2, color)` | Renders a 3D line segment in world space. Used for start/finish gate pillars. |
| `render.debugBox(center, size, color)` | Renders a 3D bounding box. Used for rendering stop box zones. |
| `render.transparentMesh(mesh, pos, rot, opacity)` | Renders a semi-transparent 3D hologram mesh. Used for Pacer & Ghost car visualization. |

---

## 5. Audio & Event APIs

### `ac.AudioEvent`
Provides FMOD sound event creation and triggering:

```lua
local countdownBeep = ac.AudioEvent("content/gui/sound/countdown_beep.bank")
countdownBeep:play()
```

---

## 6. Track Splines & Geometry APIs

### `ac.hasTrackSpline() -> boolean`
Returns `true` if the track has an AI spline (`ideal_line.ai` or `fast_lane.ai`).

### `ac.worldCoordinateToTrackProgress(worldPos: vec3) -> number`
Finds the nearest point on the track AI spline and returns its normalized position $s \in [0.0, 1.0]$. Returns `-1` if no spline exists.

### `ac.trackProgressToWorldCoordinate(progress: number, linear: boolean?) -> vec3`
Returns the 3D world coordinate `(x, y, z)` on the ideal AI spline at normalized progress `progress`.

### Spline Forward Tangent Vector
In CSP Lua, calculate the forward tangent vector at progress $s$ using a lookahead point:
```lua
local trackLength = ac.getSim().trackLengthM
local lookahead = 2.0 / trackLength
local pTarget = ac.trackProgressToWorldCoordinate(s)
local pAhead  = ac.trackProgressToWorldCoordinate((s + lookahead) % 1.0)
local fwd = (pAhead - pTarget):normalize()
```

---

## 7. Lessons Learned & Best Practices

1. **Continuous Rolling Start Spline Guidance**:
   On curved pre-corner approaches, do not enforce a static linear velocity vector along the spawn heading—the car will travel in a straight line off into the grass. Use `maintainRollingSpline` to advance spline progress $\Delta s = (v_{\text{mps}} \cdot dt) / L_{\text{track}}$ and continuously re-apply position `targetPos`, orientation `-fwd` (Orientation Inversion Rule), and velocity `fwd * v` every frame during `COUNTDOWN`.
2. **Spawn Offset Calibration**:
   Calibrate spawn distance upstream of the start gate to match the countdown time: $\text{spawn\_offset} = v_{\text{mps}} \times t_{\text{countdown}}$. This ensures the vehicle rolls smoothly along the curve and crosses the start gate right at "GO!".
3. **Control Lock Synchronization**:
   When locking user inputs (`physics.lockUserControlsFor(3.0)`), ensure gear selection ($2^\text{nd}$ gear for rolling start) and engine RPM ($3500\text{ RPM}$) match initial target launch speed via `ac.accessCarPhysics(0)` and `physics.engageGear` to prevent clutch kick or engine stall upon control release (`GO!`).
4. **Pcall Wrapping for Event Callbacks**:
   Always wrap user-defined listeners and UI events in `pcall` to prevent uncaught LUA syntax or state errors from halting the main simulation thread.
