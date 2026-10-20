# Assetto Corsa: GT-Like License Tests Mod

An open-source driving school and license challenge framework for **Assetto Corsa**, inspired by the iconic license tests of **Gran Turismo 2, 4, and 5**.

---

## 🎯 Project Objective

In the classic _Gran Turismo_ series, License Tests served as a masterclass in motorsport fundamentals. They taught players not just how to go fast, but _why_ cars behave the way they do—progressing from basic straight-line braking and low-power cornering up to high-downforce racing and full-circuit mastery.

This project replicates that experience inside **Assetto Corsa**, leveraging modern sim racing modding tools to create:

- Isolated sector challenges (e.g. 100m–1000m braking boxes, single hairpins, S-complexes, high-speed chicanes).
- Strict Gran Turismo-style disqualification rules (instant fail on wall contact, track boundary violation, or vehicle spin).
- 1-second instant retries without reloading track assets.
- Authentic GT HUD elements, 3D timing ribbons, guide lines, and sound effects.
- A structured career progression across 5 license tiers from **National B** to **Super License**.

---

## 📚 Documentation Index

1. **[Gran Turismo License Tests Reference Guide](docs/01_gran_turismo_licenses_reference.md)**
   - Deep dive into the license structures of **GT2, GT4, and GT5**.
   - Breakdown of license tiers: National B, National A, International C/B/A, Super License, and Coffee Breaks.
   - Universal failure mechanics: wall contact thresholds, 4-wheels-off rule, spin detection, stop-box criteria.
   - Pedagogical matrix mapping driving skills to vehicle drivetrains (FF, FR, 4WD, MR).

2. **[Assetto Corsa Modding Capabilities & Architecture Investigation](docs/02_assetto_corsa_modding_capabilities.md)**
   - Engine analysis: Vanilla AC vs. Legacy Python API vs. Content Manager vs. Custom Shaders Patch (CSP) Lua.
   - How CSP Lua unlocks mid-track spawns, rolling launches, instant session restarts, collision hooks, 3D gate rendering, and custom audio.
   - Complete software architecture blueprint and feasibility matrix.

3. **[Kunos Official Resources Catalog (All DLCs)](docs/03_kunos_official_resources_catalog.md)**
   - Complete inventory of official circuit locations, layouts, and vehicles from *Assetto Corsa: Ultimate Edition*.
   - Technical categorization by track characteristics, surface types, vehicle classes, drivetrains (FWD, RWD, AWD), power, weight, and motorsport eras.

4. **[Curriculum Proposal](docs/04_kunos_licenses_proposal.md)**
   - Complete driver development curriculum designed with **100% official Kunos cars and tracks**.
   - 5 Progressive Tiers: **National B**, **National A**, **International B**, **International A**, and **Super License**.
   - Every test specified with exact car/track IDs, start type (standing, stop-box, rolling, flying lap), target medal times (Gold, Silver, Bronze), failure rules, and driving lessons.

5. **[AI-Agent Autonomous Development Blueprint](docs/05_ai_agent_development_blueprint.md)**
   - Schema-first design (`test_definition.schema.json`) for declarative test definitions.
   - Automated coordinate extraction from track `.ai` spline files.
   - Universal CSP Lua runtime decoupled from test data.

6. **[Multi-Agent Parallelization Strategy](docs/06_multi_agent_parallel_strategy.md)**
   - Work Breakdown Structure (WBS), concurrency dependency graph, and agent role roster.

7. **[Directory Structure & Packaging Specification](docs/07_directory_structure_and_packaging_spec.md)**
   - Directory trees for the Git repository, the Assetto Corsa installation target, and the Content Manager distribution zip.

8. **[Automated Testing Framework Specification](docs/09_automated_testing_framework_spec.md)**
   - End-to-end testing pipeline combining static schema linting, dynamic headless math simulation, and in-engine launch loops.

9. **[Rolling Start & AI Physics Integration Guide](docs/10_rolling_start_and_ai_physics_integration.md)**
   - Comprehensive guide to CSP physics hooks, AI spline offset tracking, and pace car regulation.

10. **[CSP Lifecycle & INI Pitfalls Reference](docs/11_csp_lifecycle_and_ini_pitfalls.md)**
    - In-depth documentation of Assetto Corsa and CSP INI parser quirks, New Modes lifecycle hooks, and crash prevention runbooks.

11. **[ADR 001: Native AI Autopilot for Rolling Starts](docs/12_architecture_decision_record_ai_rolling_starts.md)**
    - Architecture Decision Record detailing the migration from synthetic velocity injection to native CSP AI autopilot tracking `fast_lane.ai`.

12. **[Rolling Start Candidate Straight Line Analyzer](docs/13_rolling_start_candidate_straight_line_analyzer.md)**
    - Kinematic straight-line detection and rolling start placement scoring engine.

13. **[CSP Lua SDK API Reference](docs/CSP_LUA_API_REFERENCE.md)**
    - Authoritative symbol catalog extracted from CSP SDK `lib.lua`.

---

## 🏗️ System Architecture

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

## 🚀 Quick Start & Installation

### 📦 Option A: Build & Install via Content Manager (Drag & Drop)
1. Build the distribution archive (or download it from the **Releases** page):
   ```bash
   python tools/build_cm_package.py --validate
   ```
2. Locate the generated archive at `release/AssettoCorsa_GT_Licenses.zip`.
3. Drag and drop the `.zip` archive directly into **Content Manager**.
4. In the green installation pop-up in the top-right, click **Install**.
5. Navigate to **Career $\rightarrow$ Gran Turismo Licenses** in Content Manager to begin!

### 🔄 Option B: Live Sync for Development
Synchronize the repository directly into your local Assetto Corsa installation:
```bash
python tools/sync_to_ac.py --ac-root "C:/Program Files (x86)/Steam/steamapps/common/assettocorsa"
```
*(Or set the `AC_ROOT` environment variable).*

### 🎨 Interactive License Test Designer Web UI
Launch the built-in Web UI to browse tiers, edit or add tests on an interactive 2D track spline canvas, calibrate target times, and sync directly to Assetto Corsa:
```bash
python tools/designer.py
```

### 🧪 Automated Verification & Tooling
To run the master validation suite locally:
```bash
# Run the complete test suite (Lua linter, Engine math, UI contracts, Curriculum schemas, Simulation, Dry-run)
python tools/run_full_validation_suite.py

# Lint Lua codebase
python tools/lint_lua.py

# Audit CSP API symbol compliance against official SDK lib.lua
python tools/audit_csp_api.py

# Re-build Content Manager drag-and-drop distribution archive
python tools/build_cm_package.py --validate
```

---

## 🗺️ Core Features

- [x] **Schema Contracts & Specifications**: Formal JSON schemas (`test_definition.schema.json`, `career_manifest.schema.json`).
- [x] **Simulation Engine & UI Layer**:
  - [x] Dynamic 3D car teleportation and native AI autopilot rolling launches (`lua/engine/physics_hooks.lua`, `lua/engine/rolling_start.lua`).
  - [x] Real-time GT failure adjudicator (`lua/engine/adjudicator.lua`).
  - [x] Instant in-memory session reset (`lua/engine/session_reset.lua`).
  - [x] Gran Turismo vector canvas HUD, movable AC Lua App (`apps/lua/gt_license`), and 3D ribbons (`lua/ui/license_hud.lua`, `lua/ui/render_gates.lua`).
  - [x] PCM audio cue sound manager (`lua/ui/audio_manager.lua`).
- [x] **5-Tier Driving School Curriculum**:
  - [x] **National B** (acceleration, braking, stop-boxes, weight transfer, graduation trial).
  - [x] **National A** (Corkscrew, turbo modulation, snap oversteer, graduation trial).
  - [x] **International B** (high-speed braking, downforce, slipstreaming, graduation trial).
  - [x] **International A** (GT3/DTM/GTE downforce, sector mastery, graduation trial).
  - [x] **Super License** (full-lap trials across iconic GP circuits and Nordschleife).
- [x] **Content Manager Career Integration**: 5 career series with progressive unlock prerequisites (`REQUIRES=`).
- [x] **Web-Based License Test Designer**: Visual 2D track spline editor, telemetry profiler, and one-click Content Manager builder (`tools/designer.py`).

---

## 📄 License

Distributed under the [MIT License](LICENSE).
