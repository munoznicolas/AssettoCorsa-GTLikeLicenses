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

---

## 🏗️ Proposed System Architecture

```
+-------------------------------------------------------------+
|               CONTENT MANAGER (Launcher & Career)           |
|  - Custom License Tiers (B, A, IB, IA, S)                   |
|  - Driving Briefings & Lesson Tips                          |
|  - Medal Tracking (Gold/Silver/Bronze) & Car Unlocks        |
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
