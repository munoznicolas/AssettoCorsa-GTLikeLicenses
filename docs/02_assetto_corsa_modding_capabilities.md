# Assetto Corsa Modding Capabilities & Architecture Investigation

## 1. Introduction

To faithfully reproduce the Gran Turismo (GT) License Test experience in _Assetto Corsa_ (AC), the mod must deliver specific gameplay features that do not exist out of the box:

1. **Isolated Sector Testing**: Starting mid-track at an arbitrary point (with either a standing start or a high-speed rolling launch) and finishing at a designated timing line.
2. **Instant Disqualification Logic**: Real-time detection of off-track infractions (2 or 4 wheels off), barrier/wall collisions, spinning out, or failing to stop within a designated box.
3. **Rapid Retry Loop**: Immediate test restarts within 1–2 seconds upon failure without reloading track assets or exiting the session.
4. **Pedagogical Aids**: Ideal driving lines, 3D start/finish ribbons, apex markers, and demonstration ghost cars.
5. **Presentation & Audio-Visuals**: GT-style HUD overlays (target medal times, live deltas, fail banners, gold/silver/bronze celebratory fanfares).
6. **Career & License Progression**: Structured unlock trees where completing tests awards licenses and prize cars.

This document investigates the capabilities, limitations, and architectural possibilities across **Vanilla Assetto Corsa**, the **Python API**, **Content Manager (CM)**, and the **Custom Shaders Patch (CSP) Lua framework**.

---

## 2. Technical Comparison of AC Modding Layers

| Feature / Capability                        |    Vanilla AC (.ini Career)     |      Legacy Python API      |      Content Manager (CM)       |            CSP Lua Environment            |
| :------------------------------------------ | :-----------------------------: | :-------------------------: | :-----------------------------: | :---------------------------------------: |
| **Custom Career & Progression**             |     Limited (`series.ini`)      |            ❌ No            | ✅ Full support (`career.json`) |           N/A (runtime engine)            |
| **Mid-Track Start (Sector Tests)**          | ❌ No (requires new track mesh) |            ❌ No            |              ❌ No              |     ✅ Yes (`physics.setCarPosition`)     |
| **Rolling Start at Target Velocity**        |              ❌ No              |            ❌ No            |              ❌ No              |     ✅ Yes (`physics.setCarVelocity`)     |
| **Instant Collision Disqualification**      |     ❌ No (only car damage)     | ⚠️ Partial (telemetry read) |              ❌ No              |    ✅ Yes (`physics.getCarCollisions`)    |
| **Strict Off-Track Disqualification**       |  ❌ No (5s throttle cut only)   | ⚠️ Partial (telemetry read) |              ❌ No              |     ✅ Yes (`car.wheelsOutsideTrack`)     |
| **Acceleration & Stop Box Detection**       |              ❌ No              |  ⚠️ Logic only (no reset)   |              ❌ No              | ✅ Yes (spatial trigger + velocity check) |
| **Instant In-Memory Session Restart**       |       ❌ No (menu reload)       |            ❌ No            |              ❌ No              |       ✅ Yes (`physics.restart()`)        |
| **3D World Rendering (Gates, Cones, Line)** |    ❌ No (static track KN5)     |            ❌ No            |              ❌ No              | ✅ Yes (`render.polyline`, `render.mesh`) |
| **Custom Audio & Jingle Triggering**        |              ❌ No              |  ⚠️ Requires external libs  |              ❌ No              |      ✅ Yes (`ui.playSound` / FMOD)       |
| **Ghost Car Recording & Offset Playback**   |  ⚠️ Vanilla full hotlap ghost   |            ❌ No            |    ⚠️ Via vanilla ghost file    |       ✅ Yes (CSP custom ghost API)       |

---

## 3. Deep Dive into AC Modding Layers

### 3.1 Vanilla Assetto Corsa Engine (Special Events & Career)

#### How it works:

Vanilla Assetto Corsa organizes non-multiplayer challenges through two systems:

- **Career Mode**: Located in `assettocorsa/content/career/seriesX/`. Controlled by `series.ini` (series definition, prerequisite series via `REQUIRES=`) and `eventX/event.ini` (event parameters, car, track, AI opponents, conditions).
- **Special Events**: Located in `assettocorsa/content/specialevents/SE_XXX/`. Controlled by `event.ini`.

#### Supported Modes:

- `HOTLAP`: Player spawns on the track before the final corner to start a flying lap.
- `TIME_ATTACK`: Player navigates checkpoints before a global countdown expires.
- `DRIFT`: Points awarded for slip angle and speed.
- `RACE`: Grid start against AI opponents.

#### Critical Limitations for GT License Modding:

1. **Full Track Constraint**: In `HOTLAP` mode, the game requires driving a full lap. There is **no native mechanism** to start at Turn 4 and end at Turn 5 without cutting the physical 3D track mesh into a separate custom track layout (`models_sector.ini`, `surfaces.ini`). Creating 80 separate track layouts for 80 license tests would be maintenance-heavy and require multi-gigabyte downloads.
2. **Soft Penalties**: Vanilla penalties apply an artificial 5-second 80 km/h speed limiter when leaving track bounds. It **cannot abort the run immediately** with a "FAILED" banner.
3. **No Wall Contact Disqualification**: Hitting a wall merely incurs visual body damage or suspension damage; the lap time is flagged as invalid, but the session continues.
4. **No Stop-Box Logic**: Vanilla AC has no concept of checking if a vehicle comes to a complete rest ($0\text{ km/h}$) inside a specific spatial box on a straightaway.

---

### 3.2 Legacy Python App Environment (`apps/python/`)

#### How it works:

Assetto Corsa embeds a Python 3.3 runtime. Modders can create in-game desktop windows using the `ac` module and read shared memory telemetry (`sim_info.py`).

#### Capabilities:

- Can read telemetry: vehicle speed, gear, throttle, brake, steering angle, lap time, coordinates $(x, y, z)$, number of wheels off-track (`physics.numberOfTyresOut`).
- Can render basic 2D HUD UI in an AC desktop window.

#### Limitations:

- **Read-Only Telemetry**: The Python API has no write access to the simulation physics. It cannot reposition the vehicle, impart starting velocity, or command the physics engine to restart.
- **No 3D World Injection**: Python apps cannot draw 3D gates, ribbons, cones, or driving lines in the simulation viewport.
- **Sluggish UI**: The legacy AC Python UI is slow, lacks modern styling, and cannot easily create full-screen cinematic banners.

---

### 3.3 Content Manager (CM) Integration

#### How it works:

Content Manager (created by x4fab) is the modern replacement launcher for Assetto Corsa, used by over 95% of the active sim racing community.

#### Capabilities for the Project:

1. **Custom Career System**:
   - Modders can build custom careers packaged in `assettocorsa/content/career/` or standalone CM career packs.
   - CM supports custom event cards, thumbnail artwork, detailed markdown descriptions (explaining the driving lesson), target medal lap times, and prerequisite unlocks (`REQUIRES=GT_LICENSE_B`).
2. **Missing Content Auto-Detection**:
   - CM checks if the required car or track mod is installed and can provide a direct download link.
3. **Seamless Game Launching**:
   - CM launches AC directly into the configured session with CSP parameters enabled, bypassing the deprecated Kunos menu.

---

### 3.4 Custom Shaders Patch (CSP) Lua Scripting Engine

The Custom Shaders Patch provides an embedded **Lua runtime** that has direct hooks into Assetto Corsa's C++ engine, physics loop, graphics pipeline, and audio system. This is the **essential technology** that makes a 1:1 Gran Turismo license system possible in Assetto Corsa.

#### 1. Session & Physics Control

- **Arbitrary Teleportation & Rolling Launch**:
  ```lua
  -- Teleport car to arbitrary sector start coordinate
  physics.setCarPosition(0, vec3(x, y, z), vec3(dirX, dirY, dirZ))
  -- Impart rolling start velocity (e.g. 120 km/h)
  physics.setCarVelocity(0, forwardVector * (speedKmh / 3.6))
  ```
  This completely eliminates the need to create custom track meshes! Any sector of any track (e.g., Spa, Nürburgring, Laguna Seca) can be isolated dynamically.
- **Instant Reset**:
  ```lua
  -- Restarts session instantly without reloading track assets
  physics.restart()
  ```
  Allows the player to tap a restart key or automatically reset within 1 second of failure.

#### 2. Disqualification Detection

- **Off-Track Detection**:
  ```lua
  local car = ac.getCar(0)
  if car.wheelsOutsideTrack > 2 then
      triggerDisqualification("Off Track: Exceeded Track Limits")
  end
  ```
- **Wall / Barrier Impact Detection**:
  ```lua
  -- Detect collision events and check impact force threshold
  local collisions = physics.getCarCollisions()
  for _, col in ipairs(collisions) do
      if col.force > MIN_FAIL_FORCE then
          triggerDisqualification("Barrier Contact")
      end
  end
  ```
- **Spin Detection**:
  ```lua
  -- Yaw angle vs track spline tangent
  local carHeading = car.heading
  local trackHeading = ac.trackProgressTangent()
  if math.abs(carHeading - trackHeading) > math.rad(90) then
      triggerDisqualification("Vehicle Spin Out")
  end
  ```
- **Braking Stop Box Detection**:
  ```lua
  -- Checks if car reached 0 km/h inside target boundaries [z_min, z_max]
  if car.speedKmh < 0.5 then
      if isInsideBox(car.position, stopBox) then
          triggerSuccess("Test Completed!")
      else
          triggerDisqualification("Stopped Outside Target Box")
      end
  end
  ```

#### 3. 3D World Visualization

- **Start & Finish Timing Ribbons**:
  Using `render.polyline()` and `render.drawRibbon()`, the mod can project 3D neon or chequered finish lines across the track at the exact finish gate.
- **Dynamic GT Driving Line**:
  CSP allows drawing a dynamic 3D spline along the track with colored braking indicators (blue for acceleration, red for braking zone).
- **Dynamic Cone Placement**:
  Lua track scripts can spawn 3D cone meshes dynamically at runtime without modifying the track's source files.

#### 4. Audio & Presentation

- **Audio Triggers**:
  `ui.playSound(soundPath)` can play authentic Gran Turismo audio cues:
  - 3-2-1-GO countdown beeps.
  - Harsh failure buzzer upon barrier contact or off-track violation.
  - Pass fanfare and Gold medal jingles.
- **Modern HUD Overlay**:
  Built with CSP's `ui.*` vector/canvas system:
  - Floating test title and objective banner.
  - Live timer with real-time Gold, Silver, and Bronze ghost deltas.
  - Full-screen "DISQUALIFIED" red overlay on failure.
  - Results screen displaying medal achieved, target comparison, and "Retry / Next Test" buttons.

---

## 4. Architectural Blueprint for the Mod

To deliver the best balance of maintainability, user experience, and visual fidelity, we adopt a **hybrid Content Manager + CSP Lua Scenario** architecture:

```
+-------------------------------------------------------------------------+
|                        CONTENT MANAGER (UI LAYER)                       |
|  - Custom Career / License Menu (License B, License A, IC, IB, IA, S)   |
|  - Test Selection, Driver Briefing, Car/Track Mod Verification          |
|  - Medal Tracking (Gold/Silver/Bronze) & License Completion Rewards     |
+-------------------------------------------------------------------------+
                                     |
                             Launches AC with
                          Scenario / New-Mode Hook
                                     v
+-------------------------------------------------------------------------+
|                  ASSETTO CORSA + CSP (SIMULATION RUNTIME)               |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                 "GT LICENSE ENGINE" (CSP LUA SCRIPT)              |  |
|  |                                                                   |  |
|  |  1. Configuration Parser: Reads `test_definition.json`            |  |
|  |     (Start Pos/Vel, Gate Pos, Stop Box, Medals, Fail Conditions)  |  |
|  |                                                                   |  |
|  |  2. Session Lifecycle Controller:                                 |  |
|  |     - Teleports car to start line at specified speed              |  |
|  |     - Manages 3-2-1 Countdown & Control Lock                      |  |
|  |     - Watches Sector Start Gate -> Sector Finish Gate             |  |
|  |                                                                   |  |
|  |  3. Real-Time Adjudicator (Failure Monitor):                      |  |
|  |     - Wheels off-track check (Instant Fail)                       |  |
|  |     - Collision / Wall impact check (Instant Fail)                |  |
|  |     - Stop-box compliance check                                   |  |
|  |     - Time limit > Bronze expiration                              |  |
|  |                                                                   |  |
|  |  4. Presentation & Audio Engine:                                  |  |
|  |     - 3D Visual Gates, Dynamic Racing Line, Cones                 |  |
|  |     - GT HUD (Current Time, Medals, Live Split Delta)             |  |
|  |     - Sound FX (Countdown, Pass Fanfare, Fail Buzzer)             |  |
|  |     - Instant In-Memory Restart on fail or keypress               |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 5. Feasibility Assessment & Risk Mitigation

| Challenge                            | Risk Level | Mitigation Strategy                                                                                                                                                                                                                                                                      |
| :----------------------------------- | :--------: | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Track Coordinates Calibration**    |   Medium   | Build a developer calibration tool in CSP Lua that lets the author drive to a corner, hit a hotkey, and automatically copy the current coordinates and tangent vector into the test configuration.                                                                                       |
| **Rolling Start Physics Glitches**   |    Low     | Teleport car slightly above the road ($+0.05\text{m}$) with suspension pre-compressed and linear velocity vector aligned with the track spline tangent to avoid sudden physics jolts.                                                                                                    |
| **Content Dependency (Cars/Tracks)** |    Low     | Primary license tiers (B and A) will use **100% Kunos default content** (e.g. Abarth 500, Mazda Miata NA, Toyota GT86, BMW M3 E30, Vallelunga, Magione, Silverstone, Imola, Nürburgring GP). Higher tiers can recommend verified high-quality community mods with CM auto-install links. |
| **User Compatibility**               |    Low     | Require CSP version 0.1.79 or higher (standard baseline across the AC community). Content Manager provides automated one-click installation of CSP.                                                                                                                                      |

---

## 6. Conclusion & Recommendation

The investigation confirms that **it is 100% technically feasible** to recreate Gran Turismo's license test system in Assetto Corsa with high fidelity.

- Creating the mod purely through vanilla `.ini` files is **infeasible** due to the inability to isolate sectors and enforce strict disqualification rules without modifying 3D track meshes.
- Using **CSP Lua** unlocks the exact required toolset: coordinate teleportation, instant restarts, strict off-track and collision tripwires, 3D gate rendering, and custom audio/HUD overlays.
- Coupled with **Content Manager Custom Careers**, this architecture provides a seamless, authentic, and modern Gran Turismo driving school in Assetto Corsa.
