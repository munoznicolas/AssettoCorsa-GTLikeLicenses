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
| `car.wheelsOutside` | `integer` | Total count of wheels detected off the track surface (0 to 4). |
| `car.collidedWith` | `integer` | Index of car collided with, or -1 if none. |

---

## 3. Physics Manipulation & Direct State Hooks

> [!IMPORTANT]
> Calling native CSP physics setters **once** on spawn is insufficient when in `COUNTDOWN` state because AC's native C++ engine resets car linear velocity to zero every frame while player controls are locked. Velocity setters MUST be invoked continuously inside `update(dt)`.

### `ac.setCarPhysicLinearVelocity(index: integer, velocity: vec3)`
Directly sets the 3D linear velocity vector of the specified car in world space ($m/s$).

```lua
-- Example: Apply 70 km/h rolling velocity along forward direction vector
local speedMps = 70.0 / 3.6
local forwardVec = vec3(0.0, 0.0, 1.0)
local velMps = vec3(forwardVec.x * speedMps, forwardVec.y * speedMps, forwardVec.z * speedMps)

ac.setCarPhysicLinearVelocity(0, velMps)
```

### `ac.setCarPhysicAngularVelocity(index: integer, angularVel: vec3)`
Directly sets the rotational velocity vector $(rad/s)$ of the vehicle chassis around its axes. Used to stabilize chassis pitch and roll on rolling launches.

```lua
-- Zero out rotation to prevent unstable vehicle movement at spawn
ac.setCarPhysicAngularVelocity(0, vec3(0, 0, 0))
```

### `ac.setCarPhysicPosition(index: integer, pos: vec3)`
Teleports the vehicle chassis directly to world position `pos`.

### `ac.setCarPhysicHeading(index: integer, forward: vec3, up: vec3)`
Sets the directional orientation of the vehicle chassis using forward and up direction vectors.

### `ac.accessCarPhysics(index: integer) -> CarPhysicsAccess`
Returns a low-level physics mutation accessor allowing control lock overrides:

```lua
local phys = ac.accessCarPhysics(0)
if phys then
  phys:setEngineRPM(3500)
  phys:setGear(2) -- Engage 2nd gear for rolling start launch
end
```

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

### `ac.getTrackSplineLength() -> number`
Returns the total length of the active track AI spline in meters.

### `ac.getTrackSplinePosition(progress: number) -> vec3`
Returns the 3D world coordinate `(x, y, z)` at spline progress `progress` $\in [0.0, 1.0]$.

### `ac.getTrackSplineForward(progress: number) -> vec3`
Returns the normalized 3D forward direction vector tangent to the spline path at `progress`.

---

## 7. Lessons Learned & Best Practices

1. **Continuous Rolling Start Enforcement**:
   Always execute `ac.setCarPhysicLinearVelocity()` on every frame inside `update(dt)` while state is `COUNTDOWN`. Do not rely on single-shot initialization.
2. **Control Lock Synchronization**:
   When locking user inputs (`ac.accessCarPhysics(0)`), ensure gear selection ($2^\text{nd}$ gear for rolling start) matches initial target launch speed to prevent clutch kick or engine stall upon control release (`GO!`).
3. **Pcall Wrapping for Event Callbacks**:
   Always wrap user-defined listeners and UI events in `pcall` to prevent uncaught LUA syntax or state errors from halting the main simulation thread.
