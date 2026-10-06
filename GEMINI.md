# Assetto Corsa GT-Like Licenses - Development Guidelines & Rules

## Project Overview
Assetto Corsa GT-Like Licenses is a Gran Turismo-style license test mod for Assetto Corsa. It implements 58 driving school tests across 5 tiers (National B, National A, International B, International A, Super License), complete with 3D start/finish gates, rolling/standing countdown sequences, out-in-out trajectories, telemetry adjudication, medal awards, and Content Manager career mode integration.

### Core Environment Paths
- **Repository Root**: `d:\Repositories\AssettoCorsa-GTLikeLicenses`
- **Assetto Corsa Install**: `D:\SteamLibrary\steamapps\common\assettocorsa`
- **AC Documents / Configs**: `D:\Users\Nico\OneDrive\Documents\Assetto Corsa`
- **CSP Target Mode Directory**: `D:\SteamLibrary\steamapps\common\assettocorsa\extension\lua\new-modes\gt-license\`
- **Official CSP SDK Definition**: `D:\SteamLibrary\steamapps\common\assettocorsa\extension\internal\lua-sdk\ac_new_modes\lib.lua`

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
* **Top-Level Instantiation**: The master engine (`GTLicenseEngine.new()`) must be instantiated immediately at the top level when running under CSP (`if script ~= nil`). Never defer instantiation to a callback that CSP won't call.
* **Dynamic Test Configuration Loading**:
  - The Lua engine dynamically queries `ac.INIConfig.raceConfig()`.
  - It extracts the active test code from `[GTLICENSE] TEST_ID` or regex parses `[EVENT] NAME` (e.g. `B-3: Out-In-Out Hairpin Trajectory` $\rightarrow$ `B-3`).
  - It resolves the path `data/tests/<tier>/test_<num>.json` (e.g. `national_b/test_b03.json`).
* **Physics & Rolling Starts**:
  - Use official CSP APIs: `ac.setCarPhysicPosition()`, `ac.setCarPhysicHeading()`, `ac.setCarPhysicLinearVelocity()`.
  - Use `ac.accessCarPhysics(0):setGear(gear)` and `:setEngineRPM(3500)`.
  - During `COUNTDOWN`, continuously apply linear velocity via `maintainRollingVelocity` so the AC engine does not bleed off vehicle momentum.

---

## 3. Developer Tooling & Verification Workflow

Always follow this 4-step cycle when making modifications:

1. **Regenerate Content & Career**:
   ```powershell
   python tools/generate_all_content.py
   ```
   Generates all 58 test JSONs calibrated from AI splines and 5 Content Manager career series.

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
- **CSP Log**: `D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\custom_shaders_patch.log`
- **AC Game Log**: `D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\log.txt`
- **Crash Dumps**: `D:\Users\Nico\OneDrive\Documents\Assetto Corsa\logs\crash_*.report` (contains zipped `log.txt`, `custom_shaders_patch.log`, and `race.ini`)
- **Key Crash Signatures**:
  - `Can’t launch the race: invalid race configuration (require_track Line: 141)`:
    Check `race.ini` for lowercase `track=` instead of `TRACK=`, or spaces around `=` (`TRACK = `).
  - `Extension 'New Modes' disabled: not selected`:
    `race.ini` is missing `__CM_CUSTOM_MODE=gt-license` in `[RACE]`.
  - `Car stopped at grid slot #1 / pit box with 0 km/h`:
    Engine was not instantiated at top level or `testConfig` was not loaded dynamically.
