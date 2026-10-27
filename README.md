# Assetto Corsa: GT License Center

An open-source driving school and license challenge framework for **Assetto Corsa**, inspired by the iconic license tests of **Gran Turismo 2, 4, and 5**.

---

## 🎯 Project Objective

In the classic _Gran Turismo_ series, License Tests served as a masterclass in motorsport fundamentals. They taught players not just how to go fast, but _why_ cars behave the way they do—progressing from basic straight-line braking and low-power cornering up to high-downforce racing and full-circuit mastery.

This project replicates that experience inside **Assetto Corsa**, leveraging modern sim racing modding tools to create:

- Isolated sector challenges (e.g. 100m–1000m braking boxes, single hairpins, S-complexes, high-speed chicanes).
- Strict Gran Turismo-style disqualification rules (instant fail on wall contact, track boundary violation, or vehicle spin).
- 1-second instant retries without reloading track assets.
- Authentic GT HUD elements, 3D timing ribbons, guide lines, and sound effects.
- A structured career progression from National B to Super License.

---

## 📚 Documentation Index

We have conducted a comprehensive investigation divided into two core research documents:

1. **[Gran Turismo License Tests Reference Guide](docs/01_gran_turismo_licenses_reference.md)**
   - Deep dive into the license structures of **GT2, GT4, and GT5**.
   - Breakdown of license tiers: National B, National A, International C/B/A, Super License, and Coffee Breaks.
   - Universal failure mechanics: wall contact thresholds, 4-wheels-off rule, spin detection, stop-box criteria.
   - Comprehensive catalog of tests, car assignments, track sectors, target times (Gold / Silver / Bronze), and core driving lessons.
   - Pedagogical matrix mapping driving skills to vehicle drivetrains (FF, FR, 4WD, MR).

2. **[Assetto Corsa Modding Capabilities & Architecture Investigation](docs/02_assetto_corsa_modding_capabilities.md)**
   - Engine analysis: Vanilla AC vs. Legacy Python API vs. Content Manager vs. Custom Shaders Patch (CSP) Lua.
   - Why pure Vanilla AC fails to support sector tests and strict disqualifications without track mesh surgery.
   - How CSP Lua unlocks mid-track spawns, rolling launches, instant session restarts, collision hooks, 3D gate rendering, and custom audio.
   - Complete software architecture blueprint and feasibility matrix.

3. **[Kunos Official Resources Catalog (All DLCs)](docs/03_kunos_official_resources_catalog.md)**
   * Complete inventory of **19 circuit locations (over 45 unique layouts)** and **178 official vehicles** from *Assetto Corsa: Ultimate Edition*.
   * Technical categorization by track characteristics, surface types, vehicle classes, drivetrains (FWD, RWD, AWD), power, weight, and motorsport eras.

4. **[Curriculum Proposal: 5 Licenses / 58 Tests](docs/04_kunos_licenses_proposal.md)**
   * Complete driver development curriculum designed with **100% official Kunos cars and tracks**.
   * 5 Progressive Tiers: **National B (12 tests)**, **National A (12 tests)**, **International B (12 tests)**, **International A (12 tests)**, and **Super License (10 full-lap tests)**.
   * Every test specified with exact car/track IDs, start type (standing, stop-box, rolling at $X$ km/h), target medal times (Gold, Silver, Bronze), failure rules, and driving lessons.
   * Progressive tier unlocks (Bronze or better) and Gold mastery certifications.

5. **[AI-Agent Autonomous Development Blueprint](docs/05_ai_agent_development_blueprint.md)**
   * Technical skills, knowledge domains, and architectural patterns required for an AI agent to build the mod completely autonomously.
   * **Schema-First Design**: Complete JSON Schema (`test_definition.schema.json`) for declarative, machine-generated test definitions.
   * **AI Calibration Engine**: Automated coordinate extraction from track `.ai` spline files, eliminating manual driving.
   * **Engine vs. Data Architecture**: Universal CSP Lua runtime (`gt_license_engine.lua`) decoupled from test data.
   * **Custom Antigravity Agent Skill Specification** (`ac-license-modding`) and 5-step autonomous execution plan.

6. **[Multi-Agent Parallelization Strategy](docs/06_multi_agent_parallel_strategy.md)**
   * Work Breakdown Structure (WBS), concurrency dependency graph, and agent role roster.
   * Parallel execution model: concurrent Lua engine, HUD/visuals, tooling, and 5-way content authoring swarm.
   * Conflict prevention safeguards: strict directory topology, contract-first schema, and automated verification gates.
   * Sequential vs. parallel performance comparison (~3.5x speedup with higher context fidelity).

7. **[Directory Structure & Packaging Specification](docs/07_directory_structure_and_packaging_spec.md)**
   * Exact directory trees for the Git repository, the Assetto Corsa installation target, and the Content Manager distribution zip.
   * File-by-file breakdown with naming conventions, audio formats, image resolutions, and subagent write boundaries.
   * Automated one-click drag-and-drop packaging protocol for Content Manager.

8. **[Ghost Car & Pace Car Specification](docs/08_ghost_car_and_pace_car_spec.md)**
   * Recording and rendering architecture for transparent Gold medal target ghosts (`gt_ghost_manager.lua`, `gt_render_ghost.lua`).
   * Pace car trajectory tracking and distance-based adjudication for IB-5 pace challenge.

9. **[Automated Testing Framework Specification](docs/09_automated_testing_framework_spec.md)**
   * End-to-end testing pipeline combining static schema linting, dynamic headless math simulation, and in-engine launch loops.

10. **[Rolling Start & AI Physics Integration Guide](docs/10_rolling_start_and_ai_physics_integration.md)**
    * Comprehensive guide to CSP physics hooks, AI spline offset tracking, and pace car regulation.

11. **[CSP Lifecycle & INI Pitfalls Reference](docs/11_csp_lifecycle_and_ini_pitfalls.md)**
    * In-depth documentation of Assetto Corsa and CSP INI parser quirks, New Modes lifecycle hooks, and crash prevention runbooks.

12. **[ADR 001: Native AI Autopilot for Rolling Starts](docs/12_architecture_decision_record_ai_rolling_starts.md)**
    * Architecture Decision Record detailing the migration from synthetic velocity injection to native CSP AI autopilot tracking `fast_lane.ai`.

13. **[CSP Lua SDK API Reference](docs/CSP_LUA_API_REFERENCE.md)**
    * Authoritative symbol catalog extracted from CSP SDK `lib.lua`.

---

## 🏗️ Proposed System Architecture

```
+-------------------------------------------------------------+
|               CONTENT MANAGER (Launcher & Career)           |
|  - Custom License Tiers (B, A, IB, IA, S)                   |
|  - Driving Briefings & Lesson Tips                          |
|  - Medal Tracking (Gold/Silver/Bronze) & Tier Unlocks       |
+-------------------------------------------------------------+
                              |
                     Launches AC session
                              v
+-------------------------------------------------------------+
|             ASSETTO CORSA + CSP (Simulation Runtime)        |
|                                                             |
|  [GT License Lua Engine]                                    |
|   ├── Dynamic Spawn & Rolling Launch Controller             |
|   ├── Start / Finish Timing & Sector Gates                  |
|   ├── Failure Adjudicator (Walls, Off-Track, Stop Box)      |
|   ├── 3D Visualizer (Timing Ribbons, Dynamic Guide Line)    |
|   ├── Audio Engine (Countdown, Fail Buzzer, Gold Fanfare)   |
|   └── Instant In-Memory Restart Manager                     |
+-------------------------------------------------------------+
```

---

## 🚀 Project Status & Quick Start

The mod development is **100% complete across all 5 tiers (58 tests)**, fully integrated into Content Manager Career mode, and packaged as a ready-to-install archive.

### 📦 Installation (Drag & Drop into Content Manager)
1. Locate the built archive: [`release/AssettoCorsa_GT_Licenses.zip`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/release/AssettoCorsa_GT_Licenses.zip).
2. Drag and drop the `.zip` archive into **Content Manager**.
3. In the green installation pop-up in the top-right, click **Install**.
4. Navigate to **Career $\rightarrow$ Gran Turismo Licenses** in Content Manager to begin!

### 🧪 Automated Verification & Tooling
To run the master validation suite locally:
```bash
# Run the complete test suite (Curriculum schemas, Engine math, UI contracts, Ghost profiles, Simulation)
python tools/run_full_validation_suite.py

# Lint Lua codebase against CSP APIs
python tools/lint_lua.py

# Audit CSP API symbol compliance against official SDK lib.lua
python tools/audit_csp_api.py

# Re-build Content Manager drag-and-drop distribution archive
python tools/build_cm_package.py --validate
```

---

## 🗺️ Completed Milestones

- [x] **Phase 0: Schema Contracts & Specifications**: Formal JSON schemas (`test_definition.schema.json`, `career_manifest.schema.json`).
- [x] **Phase 1: Simulation Engine & UI Layer**:
  - [x] Dynamic 3D car teleportation and vector rolling launches (`gt_physics_hooks.lua`).
  - [x] Real-time GT failure adjudicator (`gt_adjudicator.lua`).
  - [x] Instant in-memory session reset (`gt_session_reset.lua`).
  - [x] Gran Turismo vector canvas HUD and 3D ribbons (`gt_license_hud.lua`, `gt_render_gates.lua`).
  - [x] PCM audio cue sound manager (`gt_audio_manager.lua`).
- [x] **Phase 2: Full Curriculum Content (58 Tests)**:
  - [x] **National B** (12 tests: acceleration, braking, stop-boxes, weight transfer, Vallelunga graduation).
  - [x] **National A** (12 tests: Corkscrew, turbo modulation, snap oversteer, Brands Hatch graduation).
  - [x] **International B** (12 tests: high-speed braking, downforce, slipstreaming, Red Bull Ring graduation).
  - [x] **International A** (12 tests: GT3/DTM/GTE downforce, Spa sector graduation).
  - [x] **Super License** (10 tests: full-lap trials at Laguna Seca, Brands Hatch, Mugello, Monza, Silverstone, Imola, Spa, Red Bull Ring, Barcelona, and Nordschleife).
- [x] **Phase 3: Content Manager Career Integration**: 5 career series with progressive unlock prerequisites (`REQUIRES=`).
- [x] **Phase 4: Release Packaging**: Self-contained `release/AssettoCorsa_GT_Licenses.zip` ready for distribution.
