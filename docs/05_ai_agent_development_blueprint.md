# AI-Agent Autonomous Development Blueprint & Skills Specification

## 1. Executive Summary & Vision

This blueprint defines the architecture, technical skills, machine-readable specifications, and tooling needed for an **AI coding agent** (such as Antigravity) to autonomously develop, validate, and package the **Assetto Corsa GT-Like Licenses Mod** from start to finish without requiring human code intervention.

Traditional game modding relies on manual trial-and-error in 3D editors and interactive driving. To enable **complete AI autonomy**, the project must transition to a **declarative, schema-driven, programmatic architecture**:
1. **Core Engine vs. Data Separation**: The AI writes a universal simulation engine *once* in CSP Lua (`gt_license_engine.lua`). All 58 license tests are expressed as declarative data files (`test_definition.json`).
2. **Schema-First Design**: Strict JSON schemas eliminate ambiguity, allowing the agent to generate, lint, and validate tests deterministically.
3. **Programmatic Calibration**: Coordinate extraction from track AI splines (`fast_lane.ai` / `ideal_line.ai`) removes the need for human driving to find $(x, y, z)$ coordinates.
4. **Automated Verification**: Headless validation scripts that verify data integrity, file existence against the Kunos installation, and physical timing plausibility before deployment.

---

## 2. Required AI Agent Competencies & Knowledge Domains

For an AI agent to execute this project autonomously, it must master five core technical disciplines:

```
+-----------------------------------------------------------------------------------------+
|                               REQUIRED AGENT SKILLS                                     |
+-----------------------------------------------------------------------------------------+
|  1. CSP Lua Runtime & Sim Hooks  |  ac.*, physics.*, render.*, ui.*, event loops        |
|  2. 3D Vector & Spline Math      |  Gate plane intersections, projections, quaternions  |
|  3. Schema-Driven Architecture   |  JSON Schemas, declarative test configs, linters      |
|  4. AC Telemetry & AI Splines    |  Parsing .ai files, world coordinates, track progress|
|  5. CM Career & Package Engine   |  career.json, series.ini, directory topologies        |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Custom Shaders Patch (CSP) Lua API Mastery
The agent must understand CSP's execution model and API lifecycle:
- **Session Lifecycle**: `script.init()`, `script.update(dt)`, `script.draw3D()`, `script.drawUI()`.
- **Physics Manipulation**:
  - `physics.setCarPosition(carIndex, pos, forwardVector)` — Instant mid-track teleportation.
  - `physics.setCarVelocity(carIndex, velocityVector)` — Rolling launch without physics instability.
  - `physics.restart()` — In-memory session reset ($< 1\text{ s}$).
- **Failure Adjudication**:
  - `car.wheelsOutsideTrack` — Integer count of wheels beyond legal surface limits ($> 2$ trigger).
  - `physics.getCarCollisions()` — Traversal of collision events, impulse force, and normal vectors.
  - `car.heading` vs. track spline tangent — Detection of vehicle spins ($> 90^\circ$).
- **3D World Graphics**:
  - `render.drawRibbon()` and `render.polyline()` — Rendering start/finish neon gates and guide lines.
  - `render.mesh()` — Rendering 3D apex markers and cones dynamically.
- **In-Game User Interface**:
  - `ui.*` Canvas / ImGui vector API for responsive HUD rendering (timer, medal targets, failure banners).

### 2.2 3D Spatial Geometry & Gate Intersections
The agent must formulate mathematical models for:
- **Planar Gate Intersection**: Representing start and finish gates as vertical 2D segments across the track $[P_1, P_2]$. Checking whether the vehicle's position segment from $t_{prev}$ to $t_{current}$ intersects the gate line using 2D cross-products:
  $$\text{intersect}(\vec{A}_{prev}, \vec{A}_{curr}, \vec{P}_1, \vec{P}_2)$$
- **Stop Box Inclusion**: Testing whether the car's 3D bounding box is fully contained within an oriented bounding box (OBB) on the road surface and confirming $\text{speed} < 0.5\text{ km/h}$.
- **Tangent & Trajectory Alignment**: Aligning the vehicle's forward vector with the track spline normal so rolling starts launch smoothly in the correct direction.

### 2.3 Automated Calibration via AI Splines
Rather than requiring a human to manually drive to Turn 4 of Vallelunga to record $(x, y, z)$ coordinates:
- The agent can inspect Assetto Corsa's official `data/ideal_line.ai` or `fast_lane.ai` files located in each track directory (`content/tracks/<track>/data/`).
- AC `.ai` splines contain sequential waypoints of the entire track containing:
  - World coordinates $(X, Y, Z)$
  - Spline progress index ($0.0$ to $1.0$)
  - Track width left and right
- The agent can write a Python parser to extract exact coordinates for any turn or distance along any official circuit automatically.

---

## 3. Schema-Driven Architecture (Machine-Readable Specifications)

To enable deterministic generation by the AI, all tests follow a strict JSON schema. The agent validates every test against this schema before writing files.

### 3.1 Test Definition Schema (`test_definition.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GTLicenseTestDefinition",
  "type": "object",
  "required": [
    "test_id",
    "tier",
    "title",
    "car_id",
    "track_id",
    "track_layout",
    "start_mode",
    "spawn",
    "timing",
    "fail_rules",
    "targets"
  ],
  "properties": {
    "test_id": { "type": "string", "pattern": "^[B|A|IB|IA|S]-[0-9]{1,2}$" },
    "tier": { "type": "string", "enum": ["National B", "National A", "International B", "International A", "Super License"] },
    "title": { "type": "string" },
    "description": { "type": "string" },
    "lesson_objective": { "type": "string" },
    "car_id": { "type": "string", "description": "Folder ID in content/cars" },
    "track_id": { "type": "string", "description": "Folder ID in content/tracks" },
    "track_layout": { "type": "string", "description": "Layout subfolder or empty for default" },
    "start_mode": { "type": "string", "enum": ["STANDING", "ROLLING", "FLYING_LAP"] },
    "spawn": {
      "type": "object",
      "required": ["position", "forward_vector", "initial_speed_kmh"],
      "properties": {
        "position": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
        "forward_vector": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
        "initial_speed_kmh": { "type": "number", "minimum": 0 }
      }
    },
    "timing": {
      "type": "object",
      "required": ["start_gate", "finish_gate"],
      "properties": {
        "start_gate": {
          "type": "object",
          "required": ["p1", "p2"],
          "properties": {
            "p1": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "p2": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
          }
        },
        "finish_gate": {
          "type": "object",
          "required": ["p1", "p2"],
          "properties": {
            "p1": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "p2": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
          }
        },
        "stop_box": {
          "type": "object",
          "description": "Required only for acceleration & braking tests",
          "properties": {
            "center": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "size": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
            "rotation_deg": { "type": "number" }
          }
        }
      }
    },
    "fail_rules": {
      "type": "object",
      "required": ["max_wheels_off", "wall_collision_threshold_n", "max_yaw_angle_deg"],
      "properties": {
        "max_wheels_off": { "type": "integer", "default": 2 },
        "wall_collision_threshold_n": { "type": "number", "default": 1500 },
        "max_yaw_angle_deg": { "type": "number", "default": 90 },
        "stop_box_overshoot_fail": { "type": "boolean", "default": false }
      }
    },
    "targets": {
      "type": "object",
      "required": ["gold_seconds", "silver_seconds", "bronze_seconds"],
      "properties": {
        "gold_seconds": { "type": "number" },
        "silver_seconds": { "type": "number" },
        "bronze_seconds": { "type": "number" }
      }
    }
  }
}
```

---

## 4. Autonomous Implementation Protocols for the AI Agent

To execute development without getting blocked, the AI agent must follow four sequential operational protocols:

```
[Phase 1: Tooling & Infrastructure]
  └── Build Python AI-spline coordinate extractor & JSON schema validator.

[Phase 2: Core Simulation Engine]
  └── Develop the universal CSP Lua scenario (lifecycle, timing, HUD, sounds, resets).

[Phase 3: Automated Test Generation]
  └── Generate all 58 JSON test files, extract coordinates, and validate data integrity.

[Phase 4: Content Manager Career Integration]
  └── Generate CM career structure, event INIs, briefing texts, and unlock trees.

[Phase 5: Automated Verification & Packaging]
  └── Run integrity suites (file existence, syntax linting, JSON schema conformance).
```

### 4.1 Protocol 1: AI Coordinate Extraction
When configuring a test (e.g. `B-3 Vallelunga Tornantino`):
1. The agent executes a helper Python script `tools/extract_spline_coords.py` targeting `D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\ks_vallelunga\club_circuit\data\ideal_line.ai`.
2. The script queries the spline at the desired normalized progress (e.g., $s = 0.35$ for the Tornantino corner entry).
3. The script returns exact world coordinates $[X, Y, Z]$, track left edge $[X_l, Y_l, Z_l]$, right edge $[X_r, Y_r, Z_r]$, and the forward vector.
4. The agent populates the test's `spawn`, `start_gate`, and `finish_gate` automatically.

### 4.2 Protocol 2: Core Engine Architecture (`gt_license_engine.lua`)
The universal Lua engine runs inside Assetto Corsa via CSP. Its structure is decoupled from individual tests:

```lua
-- gt_license_engine.lua (Conceptual Skeleton)
local testConfig = io.loadJSON(ac.getFolder(ac.FolderID.ExtScript) .. "/active_test.json")

local STATE = { COUNTDOWN = 1, RUNNING = 2, PASSED = 3, FAILED = 4 }
local currentState = STATE.COUNTDOWN
local sessionTime = 0
local failReason = ""

function script.init()
    -- 1. Pre-position car at exact spawn point
    physics.setCarPosition(0, vec3(testConfig.spawn.position), vec3(testConfig.spawn.forward_vector))
    if testConfig.start_mode == "ROLLING" then
        physics.setCarVelocity(0, vec3(testConfig.spawn.forward_vector) * (testConfig.spawn.initial_speed_kmh / 3.6))
    end
end

function script.update(dt)
    if currentState == STATE.COUNTDOWN then
        updateCountdown(dt)
    elseif currentState == STATE.RUNNING then
        sessionTime = sessionTime + dt
        
        -- Adjudicate Fail Rules
        if ac.getCar(0).wheelsOutsideTrack > testConfig.fail_rules.max_wheels_off then
            triggerFail("Off Track: Exceeded Track Limits")
        end
        
        local collisions = physics.getCarCollisions()
        for _, col in ipairs(collisions) do
            if col.force > testConfig.fail_rules.wall_collision_threshold_n then
                triggerFail("Barrier Contact")
            end
        end
        
        if sessionTime > testConfig.targets.bronze_seconds then
            triggerFail("Time Limit Exceeded")
        end
        
        -- Check Finish Line / Stop Box
        if crossedGate(ac.getCar(0).position, testConfig.timing.finish_gate) then
            if testConfig.timing.stop_box then
                checkStopBoxCompletion()
            else
                triggerPass()
            end
        end
    end
end

function script.drawUI()
    renderGTHUD(sessionTime, testConfig.targets, currentState, failReason)
end
```

### 4.3 Protocol 3: Automated Validation Suite (`tools/validate_curriculum.py`)
Before declaring the mod complete, the agent executes an automated validation test suite that verifies:
1. **Content Verification**: Checks that every referenced `car_id` and `track_id` exists in the local Assetto Corsa installation.
2. **Schema Conformance**: Validates all 58 `.json` test files against `test_definition.schema.json`.
3. **Logic Consistency**: Asserts that `gold_seconds < silver_seconds < bronze_seconds` for all tests.
4. **Vector Integrity**: Confirms start and finish gate widths match realistic track boundaries ($8\text{ m} \le \text{width} \le 25\text{ m}$).
5. **No Broken Links**: Verifies that Content Manager `career.json` references valid series prerequisite codes.

---

## 5. Dedicated Antigravity Agent Skill Specification

To allow any AI agent working on this repository to execute mod tasks seamlessly, we define a dedicated Antigravity skill: **`ac-license-modding`**.

### 5.1 Skill Definition File (`skills/ac-license-modding/SKILL.md`)

```yaml
---
name: ac-license-modding
description: Autonomous toolset for generating, validating, calibrating, and packaging Assetto Corsa Gran Turismo-style license tests using CSP Lua and Content Manager.
---

# Assetto Corsa License Modding Skill

## Capabilities & Toolset
1. **Coordinate & Spline Extractor**: Inspects track .ai files and telemetry logs to compute exact 3D coordinates for spawns and timing gates.
2. **Schema Validator**: Enforces schema conformance on all test JSON definitions.
3. **CSP Lua Code Generator**: Generates and lints CSP Lua scenarios, 3D gate rendering, HUD UI, and audio event handlers.
4. **Content Manager Career Builder**: Generates series.ini and career.json structures with proper unlock dependencies.

## Key Local Paths
- AC Installation: `D:\SteamLibrary\steamapps\common\assettocorsa`
- Official Cars: `D:\SteamLibrary\steamapps\common\assettocorsa\content\cars`
- Official Tracks: `D:\SteamLibrary\steamapps\common\assettocorsa\content\tracks`
- CSP Lua SDK: `D:\SteamLibrary\steamapps\common\assettocorsa\extension\internal\lua-sdk`
```

---

## 6. Phased Autonomous Execution Checklist

An AI agent assigned to build the mod should execute the following strict checklist:

- [ ] **Step 1: Environment & Tooling Setup**
  - Create `tools/validate_schema.py` and `tools/extract_coords.py`.
  - Author `schema/test_definition.schema.json`.
  - Commit foundational schemas to Git.

- [ ] **Step 2: Core Simulation Engine Implementation**
  - Implement `lua/gt_license_engine.lua` with lifecycle hooks.
  - Implement 3D visual timing ribbons (`render.drawRibbon`).
  - Implement GT-style responsive HUD (`ui.drawRect`, `ui.drawText`).
  - Implement audio trigger manager for start beeps, fail buzzer, and pass fanfares.
  - Implement 1-key instant in-memory session reset (`physics.restart()`).

- [ ] **Step 3: Test Generation & Automated Calibration**
  - Generate the 12 National B test JSON files with pre-calibrated coordinates.
  - Generate the 12 National A test JSON files.
  - Generate the 12 International B test JSON files.
  - Generate the 12 International A test JSON files.
  - Generate the 10 Super License full-lap test JSON files.

- [ ] **Step 4: Content Manager Career Packaging**
  - Create `content/career/series_gt_license_b/` with `series.ini` and event configs.
  - Create subsequent series folders with sequential `REQUIRES=` prerequisite unlock trees.
  - Generate UI thumbnails, event briefing markdown, and medal threshold metadata.

- [ ] **Step 5: Automated QA & Verification Suite**
  - Execute `python tools/validate_curriculum.py` across all 58 tests.
  - Verify zero schema violations, zero missing vehicle/track references, and 100% prerequisite chain integrity.
  - Package final release zip for one-click installation via Content Manager.
