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

## 🗺️ Implementation Roadmap

### Phase 1: Prototype Engine (Proof of Concept)

- [ ] Implement core CSP Lua script for a single test (e.g. B-1 400m Acceleration & Braking on Monza Straight or Vallelunga).
- [ ] Implement stop-box spatial detector and 0 km/h velocity verification.
- [ ] Implement instant off-track and wall contact fail triggers with audio cues.
- [ ] Implement 1-key instant restart.

### Phase 2: National B License Pack (Default AC Content)

- [ ] Curate 10 National B tests using base Kunos cars (Abarth 500, Mazda Miata NA, Toyota GT86, Alfa Romeo Mito) and tracks (Magione, Vallelunga, Silverstone National, Monza).
- [ ] Configure JSON test definitions with calibrated spawn coordinates, gate vectors, and target medal times.
- [ ] Package into Content Manager Custom Career with custom UI banners and briefing texts.

### Phase 3: National A & International Tiers

- [ ] Expand to intermediate corner complexes (Laguna Seca Corkscrew, Brands Hatch, Imola).
- [ ] Implement rolling-start sector tests with pre-set velocities.
- [ ] Add dynamic 3D driving line and ghost car playback.

---

## 🤝 Getting Involved

Contributions, track sector coordinates, car recommendations, and feedback on medal times are welcome! See the [docs](docs/) directory for detailed background research.
