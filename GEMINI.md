# Assetto Corsa GT-Like Licenses - Development Guidelines & Rules

## Project Overview
Assetto Corsa GT-Like Licenses is a Gran Turismo-style license test mod for Assetto Corsa. It implements driving school tests across 5 progressive tiers (National B, National A, International B, International A, Super License), complete with 3D start/finish gates, rolling/standing countdown sequences, out-in-out trajectories, telemetry adjudication, medal awards, and Content Manager career mode integration.

### Core Environment Paths
- **Assetto Corsa Install (`<AC_ROOT>`)**: Resolved via `AC_ROOT` environment variable or auto-discovered from Steam library folders.
- **AC Documents / Configs (`<AC_DOCS>`)**: `%USERPROFILE%\Documents\Assetto Corsa` (or OneDrive Documents equivalent).
- **CSP Target Mode Directory**: `<AC_ROOT>\extension\lua\new-modes\gt-license\`
- **Official CSP SDK Definition**: `<AC_ROOT>\extension\internal\lua-sdk\ac_new_modes\lib.lua`

---

## 1. Strict INI Formatting Rules (Kunos C++ Parser Compatibility)

Assetto Corsa's internal `INIReader` and Custom Shaders Patch (CSP) C++ parsers have strict requirements that differ from standard INI libraries:

### Critical INI Pitfalls:
1. **NO Whitespace Around Delimiters**:
   - Kunos' `INIReader` does not trim whitespace around the `=` delimiter.
   - Writing `TRACK = ks_vallelunga` causes the key to be read literally as `"TRACK "` (with a trailing space), causing track resolution to fail.
   - Always write `TRACK=ks_vallelunga`. In Python `configparser`, **always specify `space_around_delimiters=False`** when writing.
2. **Strict Uppercase Keys & Sections**:
   - Python's `configparser.ConfigParser` defaults to lowercase keys (`track=ks_vallelunga`).
   - CSP track and car validators (e.g. `csp_utils.cpp require_track`) perform case-sensitive lookups for `TRACK`. If lowercase, CSP receives `null`, triggering `json.exception.type_error.302: type must be string, but is null` and crashes with `"Can't launch the race: invalid race configuration"`.
   - In Python, **always configure `cp.optionxform = str`** to preserve uppercase keys (`TRACK`, `CONFIG_TRACK`, `MODEL`, `CARS`, etc.).
3. **Mandatory Standard Keys**:
   - Always include `MODEL_CONFIG=` in `[RACE]` and `[CAR_0]`.
   - Always include `BALLAST=0` and `RESTRICTOR=0` in `[CAR_0]` to avoid `KEY_NOT_FOUND` warnings.
   - In career `event.ini` and standalone `race.ini`, always include `__CM_CUSTOM_MODE=gt-license` in `[RACE]` so Content Manager passes the custom mode to CSP.

---

## 2. CSP New Modes & Lua Runtime Architecture

The mod runs inside CSP's **New Modes** extension subsystem (`extension/lua/new-modes/gt-license/`).

### Lifecycle Hooks:
* **NO `script.init()` Hook**: CSP New Modes **never calls `script.init()`**. It only executes:
  - `script.prepare(dt)`: Preparation stage before the session begins.
  - `script.update(dt)`: Main simulation frame update.
  - `script.draw3D()`: 3D render hook (for gates, markers, trajectory ribbon).
  - `script.drawUI()`: 2D ImGui/HUD render hook.
* **Top-Level Instantiation**: The master engine (`LicenseEngine.new()`) must be instantiated immediately at the top level when running under CSP (`if script ~= nil`). Never defer instantiation to a callback that CSP won't call.
* **Dynamic Test Configuration Loading & Path Resolution**:
  - The Lua engine dynamically queries `ac.INIConfig.raceConfig()`.
  - It extracts the active test code from `[GTLICENSE] TEST_ID`, `[RACE] TEST_ID`, `[SESSION_0] NAME`, or `[EVENT] NAME` (e.g. `B-3: Out-In-Out Hairpin Trajectory` $\rightarrow$ `B-3`).
  - It resolves base paths using official CSP FolderID enums: `ac.FolderID.ScriptOrigin` (1024), `ac.FolderID.Root` (4), and `ac.FolderID.ExtLua` (32). (Never use non-existent `ExtScript`, which points to `AppData/Roaming`).
  - It resolves the path `data/tests/<tier>/test_<num>.json` (e.g. `national_b/test_b03.json`).
* **Physics & Rolling Starts**:
  - Use authoritative CSP physics APIs from `extension/internal/lua-sdk/ac_new_modes/lib.lua`:
    - `physics.setCarPosition(carIndex, targetPos, vec3(-fwd.x, -fwd.y, -fwd.z))`
      - **CRITICAL ORIENTATION INVERSION RULE**: Assetto Corsa's internal coordinate convention negates the orientation vector relative to `car.look`. To orient the car's headlights forward along $\vec{fwd}$, **pass $-\vec{fwd}$**. Passing $+\vec{fwd}$ faces the vehicle backwards, causing rolling starts to execute in reverse!
    - `physics.setCarVelocity(carIndex, vel)`
    - `physics.engageGear(carIndex, gear)`
    - `physics.setEngineRPM(carIndex, 3500)`
  - **Live Update Frame Spawn**: Because `ac.getCar(0)` is not fully initialized during initial script bytecode compilation, re-assert `setupSpawn` on the first frame of `script.update(dt)`.
  - **Native AI Autopilot Rolling Start Architecture**:
    - Instead of synthetic velocity overrides, rolling starts are driven by Assetto Corsa's native AI autopilot following the official racing line (`fast_lane.ai` / ideal spline).
    - **Spawn Placement & Kinetic Energy**: On initial spawn (`setupSpawn`), teleport vehicle rigid body once with $-\vec{fwd}$ orientation, then impart initial linear velocity and wheel rotation via `PhysicsHooks.applyRollingVelocity`.
    - **AI Autopilot Engagement**:
      - `physics.setCarAutopilot(true, false)` takes over driver inputs for car 0.
      - `physics.setAITopSpeed(carIndex, speedKmh)` caps AI maximum velocity to the exact target rolling speed.
      - `physics.setAILevel(carIndex, 1.0)`, `physics.setAIAggression(carIndex, 0.0)`, `physics.setAICaution(carIndex, 0.1)` ensure smooth, non-aggressive racing line tracking.
      - `physics.setAISplineAbsoluteOffset(carIndex, 0.0, false)` locks the AI directly onto the ideal racing line.
      - User control locks and forced pedals are completely released (`physics.lockUserControlsFor(0)`, `physics.forceUserBrakesFor(0, 0)`) so the native AI has unrestricted throttle, steering, and braking control.
    - **Countdown Maintenance**: During `COUNTDOWN`, call `PhysicsHooks.maintainAIRolling(0, speedKmh, forwardVector, dt)` to continuously preserve AI top speed and zero spline offset. Fall back to linear velocity maintenance if `ac.hasTrackSpline() == false`.
    - **Seamless Handover on "GO!"**:
      - `physics.setCarAutopilot(false)` deactivates autopilot and instantly returns full control to the player.
      - `physics.setAITopSpeed(carIndex, 999999.0)` removes the AI top speed ceiling so the player can accelerate without restriction.
      - `PhysicsHooks.unlockControls(carIndex, targetGear)` asserts gear (`physics.engageGear`) and RPM (`physics.setEngineRPM`) directly, bypassing `physics.lockUserGearboxFor(0, false)`.
      - Maintain a $0.5\text{s}$ guard window in `RUNNING` state inside `LicenseEngine:update(dt)` to re-assert `targetGear` if controller initialization or clutch slip drops it to neutral.
    - **Spawn Distance Calibration**: Set $\text{spawn\_offset} = v_{\text{mps}} \times t_{\text{countdown}}$ (e.g. $58.3\text{m}$ for $70\text{ km/h}$ over $3.0\text{s}$) so the car rolls up to the start gate right as the countdown reaches "GO!".
    - On "GO!", mark `self.adjudicator.hasPassedStartGate = true` for rolling start tests to ensure finish gate crossing registers cleanly.
* **Authoritative Track Limits Adjudication**:
  - Never rely solely on `car.wheelsOutside` or non-existent `car.wheelsOutsideTrack`. In CSP New Modes, `car.wheelsOutside` (Kunos penalty counter) remains `0` unless Kunos cut detection is triggered.
  - The authoritative ground-truth is `car.wheels[i].surfaceValidTrack` (`i = 0..3`) from `ac.StateWheel`. This directly evaluates `IS_VALID_TRACK` from `surfaces.ini` for each tyre contact point.
  - Debounce the condition for **2 consecutive frames** (~33ms at 60Hz) before disqualification to avoid false positives on high kerb hops or geometry seam transitions.

---

## 3. Developer Tooling & Verification Workflow

Always follow this cycle when making modifications:

1. **Regenerate Content & Career**:
   ```powershell
   python tools/generate_all_content.py
   ```
   Generates all test JSONs calibrated from AI splines and Content Manager career series.

2. **Live Sync to Assetto Corsa**:
   ```powershell
   python tools/sync_to_ac.py
   ```
   Synchronizes Lua engine, UI, assets, test JSONs, and career series directly to the AC installation.

3. **Curriculum Validation**:
   ```powershell
   python tools/validate_curriculum.py --all
   ```
   Validates schema compliance, gate geometry, target times, and career chaining.

4. **In-Engine Automated Launch & Evaluation Loop**:
   ```powershell
   python tools/test_and_eval_loop.py --test-id B-3 --timeout 8
   ```
   Orchestrates live launch, validates physics initialization, verifies sector spawn coordinates and initial velocity, and audits zero-crash signatures.

5. **CSP Lua API Symbol Audit**:
   ```powershell
   python tools/audit_csp_api.py
   ```
   Cross-references all Lua API calls against the official CSP SDK (`lib.lua`).

---

## 4. Crash & Diagnostic Runbook

When diagnosing launch issues or crashes:
- **CSP Log**: `<AC_DOCS>\logs\custom_shaders_patch.log`
- **AC Game Log**: `<AC_DOCS>\logs\log.txt`
- **Crash Dumps**: `<AC_DOCS>\logs\crash_*.report` (contains zipped `log.txt`, `custom_shaders_patch.log`, and `race.ini`)
- **Key Crash Signatures**:
  - `Can’t launch the race: invalid race configuration (require_track Line: 141)`:
    Check `race.ini` for lowercase `track=` instead of `TRACK=`, or spaces around `=` (`TRACK = `).
  - `Extension 'New Modes' disabled: not selected`:
    `race.ini` is missing `__CM_CUSTOM_MODE=gt-license` in `[RACE]`.
  - `Car stopped at grid slot #1 / pit box with 0 km/h`:
    Engine was not instantiated at top level or `testConfig` was not loaded dynamically.
  - `Car coasting in neutral / 0 km/h drive power at "GO!" on rolling starts`:
    `lockUserGearboxFor(0, false)` was triggered, resetting engaged gear. Ensure `unlockControls` asserts `targetGear` and the 0.5s `RUNNING` guard window is active.
  - `Tires leaving marks on track / suspension extended into droop during countdown`:
    Never use synthetic `physics.setCarVelocity` or `forceUserThrottleFor(..., 0.0)` frame-by-frame during rolling countdown. Overwriting `vel.y` erases gravitational acceleration ($g = -9.81\text{ m/s}^2$), causing the chassis to float with unweighted suspension droop (chassis drops ~60mm at GO!), while zero throttle forces drivetrain engine braking against the road at 40%+ slip ratio (skid marks). Always use native AI autopilot (`physics.setCarAutopilot(true, false)` with `physics.setAITopSpeed`) to drive the car naturally on the spline.
