# Assetto Corsa GT Licenses: Ghost Car & Pace Car Specification

**Document Version:** 1.0.0  
**Status:** Approved Architecture Plan  
**Target System:** Custom Shaders Patch (CSP) Lua Simulation Engine + GT License HUD

---

## 1. Feature Objective & Player Value

In classic *Gran Turismo* licenses (GT2, GT4, GT5, GT7), the **Demonstration / Ghost Car** is the primary pedagogical tool:
- It removes ambiguity regarding braking points and turn-in speeds.
- It visualizes the **Gold Medal delta** directly in 3D world space rather than solely as a numeric timer on the HUD.
- It teaches proper corner apex clipping, trail braking, and weight transfer pacing.

### Core Requirements
1. **Accurate Gold Pace**: The ghost car must represent the exact driving line and velocity profile corresponding to the Gold medal target time $T_{\text{gold}}$ of each test.
2. **Zero Collision Interference**: Must be fully intangible (cannot block or collide with the player car).
3. **Adjustable Lead Offset**: Support an adjustable lead offset (e.g. $+0.5\text{s}$ lead) so the ghost paces ahead to guide the driver into braking zones without obstructing immediate apex visibility.
4. **Visual Telemetry Cues**: Color-coded brake lighting (bright red during deceleration, cyan/translucent during acceleration) to teach braking threshold points.
5. **Instant Reset Synchronization**: 100% synchronous with the existing `'R'` key instant session reset.
6. **Player Control**: On-the-fly toggle via hotkey (`'G'`) between `OFF`, `EXACT GOLD (0.0s)`, and `PACER (+0.5s)`.

---

## 2. Technical Architecture & Component Breakdown

```
+---------------------------------------------------------------------------------+
|                                 TEST DEFINITION                                 |
|  - Track AI Spline Reference (fast_lane.ai / ideal_line.ai)                     |
|  - Targets: Gold, Silver, Bronze times                                          |
|  - Start Gate s_start -> Finish Gate s_finish (Length L)                         |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                       tools/generate_ghost_trajectory.py                        |
|  - Physics-based velocity profile solver: v_max(curvature), a_accel, a_brake    |
|  - Calibrates total travel time to exactly match T_gold                         |
|  - Generates compact trajectory spline lookup: [s, x, y, z, v, is_braking]      |
+---------------------------------------------------------------------------------+
                                       |
                                       v
+---------------------------------------------------------------------------------+
|                         lua/engine/gt_ghost_manager.lua                         |
|  - Evaluates Ghost state at active session time t:                              |
|      * Position (x, y, z) and Heading vector                                    |
|      * Current speed v_kmh and braking state                                    |
|      * Player vs. Ghost time/distance delta (Δt, Δd)                            |
|  - Hotkey handling ('G' toggles OFF / EXACT / LEAD)                             |
|  - Resets on physics.restart()                                                  |
+---------------------------------------------------------------------------------+
                         |                                 |
                         v                                 v
+----------------------------------+     +----------------------------------+
|     lua/ui/gt_render_ghost.lua   |     |      lua/ui/gt_license_hud.lua    |
|  - 3D Hologram Car Wireframe     |     |  - Live Ghost Delta widget       |
|  - Dynamic Brake Light Illum.    |     |  - Hotkey notification OSD       |
|  - Overhead 3D Pacer Chevron     |     |    ("[G] Ghost: PACER (+0.5s)")  |
|  - Trailing Guidance Ribbon      |     |  - Target delta comparison       |
+----------------------------------+     +----------------------------------+
```

---

## 3. Physics & Velocity Profile Formulation

To ensure the Gold Ghost travels from start gate $s_0$ to finish gate $s_1$ in exactly $T_{\text{gold}}$ seconds, we formulate a two-pass speed profile solver:

### Pass 1: Curvature-Limited Cornering Speed
For any waypoint on the spline with local curvature radius $R_i$, the lateral acceleration limit is defined by tire grip coefficient $\mu$:
$$v_{\text{corner}, i} = \sqrt{\mu \cdot g \cdot R_i}$$
Where $\mu$ is derived from the car class (e.g. $\mu \approx 1.05$ for street tires, $\mu \approx 1.55$ for GT3 slicks).

### Pass 2: Forward & Backward Acceleration Integration
1. **Backward Pass (Braking Zones)**:
   $$v_{i-1} = \min\left(v_{i-1}, \sqrt{v_i^2 + 2 \cdot a_{\text{brake}} \cdot \Delta d}\right)$$
   Where $a_{\text{brake}} \approx 1.1g \text{ to } 1.3g$.
2. **Forward Pass (Acceleration / Launch)**:
   $$v_{i+1} = \min\left(v_{i+1}, \sqrt{v_i^2 + 2 \cdot a_{\text{accel}}(v_i) \cdot \Delta d}\right)$$
   Starting from $v_0 = v_{\text{initial}}$ (0 km/h for Standing, $V_{\text{target}}$ for Rolling).

### Pass 3: Time Normalization to $T_{\text{gold}}$
The raw uncalibrated time is:
$$T_{\text{raw}} = \sum_{i} \frac{\Delta d_i}{\frac{v_i + v_{i+1}}{2}}$$
We apply a scaling scalar $\lambda = \frac{T_{\text{raw}}}{T_{\text{gold}}}$ to fine-tune the profile so the Ghost crosses the finish ribbon at exactly $t = T_{\text{gold}}$.

---

## 4. Visual Presentation (3D Hologram & HUD)

### 4.1 In-World 3D Ghost Rendering (`gt_render_ghost.lua`)
- **Translucent Hologram Chassis**: Rendered using CSP vector rendering / semi-transparent shaded bounding box matching the car's dimensions (width, height, wheelbase).
- **Dynamic Tail / Brake Lights**:
  - When accelerating: soft translucent cyan/white markers.
  - When braking ($a < -1.5\text{ m/s}^2$): intense bright red glowing light panels ($255, 20, 20$).
- **Overhead 3D Pacer Chevron**:
  - Floating 1.5 meters above the ghost roof.
  - Displays a clean GT Gold Badge and live delta text: `GOLD PACER [+0.5s]`.
- **Dynamic Trailing Ribbon**:
  - Emits a smooth ground ribbon 15 meters behind the ghost showing the exact driving line through the corner.

### 4.2 HUD Delta & Hotkey UI (`gt_license_hud.lua`)
- **Split Delta Bar**: An additional bar below the speedometer comparing the driver directly against the Gold Ghost.
- **Cycle Mode (`'G'` key)**:
  1. `GHOST: PACER (+0.5s LEAD)` *(Default — guides player ahead without obstructing vision)*
  2. `GHOST: EXACT (0.0s DELTA)` *(Parallels player at the true Gold pace)*
  3. `GHOST: DISABLED` *(Clean screen for purists)*

---

## 5. Work Breakdown Structure (WBS) & Implementation Steps

| Step | Component | Tasks | Output Artifacts |
| :---: | :--- | :--- | :--- |
| **1** | **Trajectory Profiler** | Create `tools/generate_ghost_trajectory.py` to calculate curvature-limited speed profiles from track splines normalized to $T_{\text{gold}}$ | `tools/generate_ghost_trajectory.py` |
| **2** | **Engine Ghost State** | Implement `lua/engine/gt_ghost_manager.lua` handling time evaluation, spline lookup, lead offsets, and instant reset | `lua/engine/gt_ghost_manager.lua` |
| **3** | **3D Visualizer** | Implement `lua/ui/gt_render_ghost.lua` rendering 3D translucent chassis, brake light triggers, 3D chevron, and ribbon | `lua/ui/gt_render_ghost.lua` |
| **4** | **HUD & Controls** | Integrate Ghost toggle hotkey (`'G'`), OSD pop-up, and real-time ghost delta in `lua/ui/gt_license_hud.lua` | `lua/ui/gt_license_hud.lua` |
| **5** | **Batch Trajectory Computation** | Dynamically solve ghost profiles on-demand in engine / test harness | On-demand Ghost Profile solver |
| **6** | **Packaging & Verification** | Run validation suite (`run_full_validation_suite.py`, `lint_lua.py`), rebuild CM package zip | `release/AssettoCorsa_GT_Licenses.zip` |
