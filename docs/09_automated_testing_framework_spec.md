# Assetto Corsa GT Licenses: Automated Testing Framework Specification

**Document Version:** 1.0.0  
**Status:** Approved Architecture Plan  
**Target Capabilities:** Headless Kinematic Simulation + In-Engine CLI Batch Launcher

---

## 1. Executive Summary & Testing Objectives

Manually playtesting 58 driving tests across 5 tiers (each with multiple failure conditions and medal times) requires over 4 hours of repetitive driving. To achieve full autonomous quality assurance without human driving, this document specifies a two-layer automated testing framework executable entirely from the command line:

```
========================================================================================
                              AUTOMATED TESTING SUITE
========================================================================================

 [Layer 1: Headless Simulation Harness]           [Layer 2: In-Engine Batch Launcher]
      tools/simulate_all_tests.py                       tools/test_ac_launch.py
 --------------------------------------          -------------------------------------
 • 100% headless, runs in ~3-5 seconds           • Automates real Assetto Corsa (acs.exe)
 • Simulates 5 dynamic driver profiles           • Synthesizes race.ini from test JSON
 • 58 tests x 5 profiles = 290 scenarios         • Verifies 3D mesh, sound & CSP Lua load
 • Verifies gate math, stop-box & medals         • Audits logs for zero exceptions & zero NaNs
========================================================================================
```

---

## 2. Layer 1: Headless Simulation & Adjudication Harness

### 2.1 Concept & Mechanism
`tools/simulate_all_tests.py` evaluates all 58 test definitions against a 60 Hz kinematic virtual vehicle simulation. It exercises the exact mathematical adjudication algorithms used in `lua/engine/gt_adjudicator.lua` and state coordinator `gt_license_engine.lua`.

### 2.2 The 5 Behavioral Profiles (290 Scenarios Total)
For each test (B-1 through S-10), the harness executes 5 distinct driver profiles:

| Profile | Simulated Driver Behavior | Expected State Transition | Assertion |
| :--- | :--- | :--- | :--- |
| **Profile A: Gold Run** | Teleports to spawn, launches at $v_{\text{initial}}$, follows ghost trajectory to finish line / stop box at $T \le T_{\text{gold}}$. | `COUNTDOWN` $\rightarrow$ `RUNNING` $\rightarrow$ `PASSED` | `medal == "GOLD"`, timer $\le T_{\text{gold}}$, stop-box speed $\le 0.5\text{ km/h}$. |
| **Profile B: Wall Impact** | Injects an impact impulse $F = 2,500\text{ N} > 1,500\text{ N}$ barrier threshold. | `RUNNING` $\rightarrow$ `FAILED` | `fail_reason == "Collision force exceeded threshold"`. |
| **Profile C: Off-Track** | Injects 3 wheels outside track limits ($> \text{max\_wheels\_off}$). | `RUNNING` $\rightarrow$ `FAILED` | `fail_reason == "Exceeded maximum allowed wheels off track"`. |
| **Profile D: Stop Box Overrun** | On tests with stop boxes (B-1, B-2, A-1), drives past finish gate at $80\text{ km/h}$ without braking. | `RUNNING` $\rightarrow$ `FAILED` | `fail_reason == "Overran stop box"`. |
| **Profile E: Instant Reset** | Sends reset signal (`'R'` key) mid-run. | `RUNNING` $\rightarrow$ `COUNTDOWN` | Position returns to spawn, timer $= 0.000\text{s}$, state resets cleanly. |

### 2.3 Mathematical Model & Kinematic Step
Each simulation tick ($\Delta t = 0.0166\text{s}$):
1. **Pose Update**: $P_{t+\Delta t} = P_t + V_t \cdot \Delta t$.
2. **Gate Crossing Intersection**: Evaluates 2D segment intersection:
   $$\text{Intersect}\left(P_t, P_{t+\Delta t}, G_{p1}, G_{p2}\right)$$
3. **Stop Box OBB Containment**: Projects car center $P_c$ into local stop box coordinate frame and verifies:
   $$|x_{\text{local}}| \le \frac{w}{2}, \quad |y_{\text{local}}| \le \frac{h}{2}, \quad |z_{\text{local}}| \le \frac{l}{2}$$
4. **Standstill Trigger**: Checks speed threshold $v \le 0.5\text{ km/h}$.

### 2.4 Command Line Interface
```bash
# Run all 58 tests across all 5 profiles (290 tests)
python tools/simulate_all_tests.py --all

# Run specific tier
python tools/simulate_all_tests.py --tier national_b

# Run single test with verbose telemetry logging
python tools/simulate_all_tests.py --test content/tests/national_b/test_b01.json --verbose
```

---

## 3. Layer 2: In-Engine Batch Launch Tester

### 3.1 Concept & Mechanism
Assetto Corsa's simulation engine (`D:\SteamLibrary\steamapps\common\assettocorsa\acs.exe`) does not rely on Content Manager GUI to launch; it executes whatever session is defined in:
`C:\Users\munoz\Documents\Assetto Corsa\cfg\race.ini`

`tools/test_ac_launch.py` acts as an automated headless session orchestrator:
1. Synthesizes a valid `race.ini` pointing to the exact `car_id`, `track_id`, and `track_layout` of the test.
2. Configures CSP Lua Scenario Mode `gt-license`.
3. Launches `acs.exe` in a child process.
4. Monitors process lifecycle and stdout/file logs for $5\text{ to }10$ seconds.
5. Verifies 0 crashes, 0 missing texture/mesh errors, 0 Lua nil dereferences.
6. Gracefully terminates `acs.exe` and outputs an audit report.

### 3.2 Race Configuration Template (`race.ini`)
```ini
[RACE]
TRACK={track_id}
CONFIG_TRACK={track_layout}
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=1

[CAR_0]
MODEL={car_id}
MODEL_CONFIG=
SKIN=0_default
DRIVER_NAME=GT_AI_Tester
NATIONALITY=ITA

[SESSION_0]
NAME=Quick Challenge
TYPE=3
DURATION_MINUTES=5
SPAWN_SET=START

[LIGHTING]
SUN_ANGLE=48
TIME_OF_DAY_MULT=1

[WEATHER]
NAME=3_clear

[GROOVE]
VIRTUAL_LM=0.1
MAX_LAPS=30
STARTING_LAPS=0

[DYNAMIC_TRACK]
SESSION_START=100
RANDOMNESS=0
LAP_GAIN=0
SESSION_TRANSFER=100
```

### 3.3 Log Auditor Rules (`log.txt` & CSP Logs)
The runner parses `Documents/Assetto Corsa/logs/log.txt` and verifies:
- `[PASS]` Physics initialization: `"PHYSICS ENGINE INITIALIZED"`
- `[PASS]` Car data loaded: `"CAR DATA LOADED: {car_id}"`
- `[PASS]` Track meshes loaded: `"TRACK SURFACES INITIALIZED"`
- `[PASS]` Lua scenario loaded: `"LUA MODE: gt-license initialized"`
- `[FAIL IF DETECTED]` `"CRASH"`, `"FATAL ERROR"`, `"access violation"`, `"cannot open file"`, `"attempt to index a nil value"`

### 3.4 Command Line Interface
```bash
# Validate that race.ini can be synthesized for all tests without launching acs.exe (Dry Run)
python tools/test_ac_launch.py --dry-run --all

# Launch real Assetto Corsa session for test B-1 with 8-second auto-termination
python tools/test_ac_launch.py --test content/tests/national_b/test_b01.json --timeout 8

# Launch sequential smoke tests for an entire tier
python tools/test_ac_launch.py --tier national_b --timeout 6
```

---

## 4. Implementation Steps & Work Breakdown Structure (WBS)

| Step | Deliverable | Description |
| :---: | :--- | :--- |
| **1** | `tools/simulate_all_tests.py` | Develop the 60 Hz kinematic test harness with the 5 driver profiles (Gold, Wall, Offtrack, Stop-box overrun, Reset). |
| **2** | `tools/test_ac_launch.py` | Develop the `race.ini` generator, `acs.exe` process manager, timeout handler, and log auditor. |
| **3** | Test Suite Validation | Run Layer 1 across all 58 tests (assert 290/290 passes). Test Layer 2 with `--dry-run --all` and live smoke run. |
| **4** | CI & Automation Scripts | Add `run_all_tests.bat` / PowerShell runner to execute full verification in one command. |
| **5** | Documentation & Packaging | Update README and rebuild `release/AssettoCorsa_GT_Licenses.zip`. |
