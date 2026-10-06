# 11. CSP Lifecycle, Kunos INI Pitfalls & In-Engine Diagnostics

**Author:** Assetto Corsa GT-Like Licenses Team  
**Date:** October 2026  
**Status:** Active Engineering Specification & Post-Mortem Reference  

---

## Executive Summary

During in-engine integration testing of License Test B-3, the simulator crashed on launch with:
```text
Exception: [json.exception.type_error.302] type must be string, but is null
Can’t launch the race: invalid race configuration. (csp_utils.cpp:141 require_track)
```
Simultaneously, under non-crashing configurations, the vehicle spawned at grid slot #1 / pits at 0 km/h rather than at the target sector coordinates at 70 km/h rolling velocity.

This document serves as the permanent post-mortem and engineering guide detailing:
1. The exact mechanics of Kunos Assetto Corsa's C++ `INIReader` and why standard Python `configparser` outputs fail.
2. The CSP New Modes extension architecture, its true lifecycle hooks, and why `script.init()` fails silently.
3. The dynamic test resolution pipeline between Content Manager, `race.ini`, and the Lua scenario engine.
4. The diagnostic triage runbook for rapid troubleshooting without exhaustive binary disassembly.

---

## 1. Kunos C++ INI Parser vs Python ConfigParser

### The Kunos `INIReader` Implementation
Assetto Corsa's engine uses a lightweight, handwritten C++ INI reader (`acs.exe` / `INIReader`). Unlike modern configuration parsers, it has two critical quirks:

1. **Literal Whitespace Retention Around Keys**:
   When parsing lines such as:
   ```ini
   TRACK = ks_vallelunga
   ```
   The parser splits on the first `=` without trimming whitespace on the key token:
   ```cpp
   std::string key = line.substr(0, delimiter_pos); // Evaluates to "TRACK "
   ```
   When CSP or AC queries `ini.get("TRACK")`, the lookup fails because `"TRACK "` != `"TRACK"`.

2. **Case Sensitivity in CSP Native Validators**:
   Custom Shaders Patch (`dwrite.dll`) hooks the race launch sequence at `source/utility/csp_utils.cpp` inside `require_track` and `require_car`. These functions perform case-sensitive lookups:
   ```cpp
   std::string track = raceIni.get("RACE", "TRACK");
   ```
   If `race.ini` contains lowercase `track=ks_vallelunga`, `raceIni.get` returns `null` or empty string. CSP then passes this empty identifier into an internal JSON metadata parser, throwing:
   ```text
   [json.exception.type_error.302] type must be string, but is null
   Can’t launch the race: invalid race configuration.
   ```

### Python's `configparser` Traps
By default, Python's standard `configparser.ConfigParser`:
* Converts all option names to lowercase (`optionxform = str.lower`).
* Writes spaces around delimiters (`space_around_delimiters = True`), outputting `key = value`.

### The Mandatory Solution
Whenever generating Assetto Corsa INI files (`race.ini`, `event.ini`, `series.ini`, `manifest.ini`):
```python
import configparser

cp = configparser.ConfigParser(interpolation=None)
# 1. Preserve uppercase casing for all sections and keys
cp.optionxform = str

# ... populate dictionary ...

# 2. Never allow spaces around the equals sign
with open(ini_path, "w", encoding="utf-8") as f:
    cp.write(f, space_around_delimiters=False)
```

---

## 2. CSP New Modes Extension Lifecycle & Hooks

### Execution Architecture
Assetto Corsa mod scenarios deployed to `extension/lua/new-modes/<mode_id>/` run under CSP's **New Modes** subsystem.

To activate the extension:
1. `race.ini` must contain under `[RACE]`:
   ```ini
   __CM_CUSTOM_MODE=gt-license
   ```
   If this key is missing, CSP logs:
   ```text
   Extension 'New Modes' disabled: not selected
   ```
2. CSP looks for `extension/lua/new-modes/gt-license/manifest.ini` and `mode.lua`.

### Official CSP SDK Lifecycle Hooks
According to the official CSP SDK (`extension/internal/lua-sdk/ac_new_modes/lib.lua`), CSP provides the following global `script` hooks:

| Hook | Signature | Called When | Purpose |
| :--- | :--- | :--- | :--- |
| `script.prepare` | `function script.prepare(dt) -> bool` | Preparation stage (if start message set) | Waits for warmup conditions before activating event |
| `script.update` | `function script.update(dt)` | Every frame during active simulation | Core scenario updates, physics maintenance, timers |
| `script.draw3D` | `function script.draw3D()` | Post-opaque 3D rendering | Rendering 3D gates, stop boxes, ghost ribbons |
| `script.drawUI` | `function script.drawUI()` | ImGui 2D rendering | Rendering HUD, tachometer, countdown banners, medals |

### The Silent `script.init()` Bug
CSP New Modes **does not have a `script.init()` hook**.
If a script defines:
```lua
if script ~= nil then
  local activeEngine = nil
  function script.init()
    activeEngine = GTLicenseEngine.new()
  end
  function script.update(dt)
    if activeEngine then activeEngine:update(dt) end
  end
end
```
Because `script.init()` is never called by CSP, `activeEngine` remains `nil` indefinitely. As a result:
* Spawn repositioning never occurs.
* Controls remain in native AC state.
* Vehicle spawns at the default pit/grid slot with 0 km/h.

### The Correct Initialization Pattern
Instantiate the engine coordinator **immediately at the top level** upon script load:
```lua
if script ~= nil then
  -- Instantiate immediately upon CSP mode load
  local activeEngine = GTLicenseEngine.new(nil)
  if GTLicenseHUD and GTLicenseHUD.init then
    GTLicenseHUD.init(activeEngine:getActiveTest())
  end
  if GTRenderGates and GTRenderGates.init then
    GTRenderGates.init(activeEngine:getActiveTest())
  end
  if GTAudioManager and GTAudioManager.init then
    GTAudioManager.init()
  end

  function script.update(dt)
    if activeEngine then
      activeEngine:update(dt)
    end
  end

  function script.draw3D(dt)
    if activeEngine then
      activeEngine:draw3D(dt)
    end
  end

  function script.drawUI()
    if activeEngine then
      activeEngine:drawUI()
    end
  end
end
```

---

## 3. Dynamic Test Resolution Pipeline

When a test is launched through Content Manager (career mode or custom race), Content Manager generates `race.ini` on the fly. The Lua engine cannot rely on a static `active_test.json`.

### Resolution Flow:
1. Engine accesses `ac.INIConfig.raceConfig()` via CSP Lua.
2. Queries `[GTLICENSE] TEST_ID`.
3. If empty, falls back to parsing `[EVENT] NAME` via regex:
   ```lua
   local eventName = race:get("EVENT", "NAME", "")
   local testId = eventName:match("^([%w%-]+):") -- e.g. "B-3" from "B-3: Out-In-Out Hairpin Trajectory"
   ```
4. Maps `testId` to the standard curriculum directory:
   * `B-1` through `B-12` $\rightarrow$ `data/tests/national_b/test_b01.json` through `test_b12.json`
   * `A-1` through `A-12` $\rightarrow$ `data/tests/national_a/test_a01.json` through `test_a12.json`
   * `IB-1` through `IB-12` $\rightarrow$ `data/tests/international_b/test_ib01.json` through `test_ib12.json`
   * `IA-1` through `IA-12` $\rightarrow$ `data/tests/international_a/test_ia01.json` through `test_ia12.json`
   * `S-1` through `S-10` $\rightarrow$ `data/tests/super_license/test_s01.json` through `test_s10.json`
5. Loads and parses the JSON definition to configure sector coordinates, target times, stop box parameters, and rolling start speed.

---

## 4. Diagnostics & Crash Triage Guide

| Symptom / Log Output | Root Cause | Resolution |
| :--- | :--- | :--- |
| `Can’t launch the race: invalid race configuration (require_track Line: 141)` | `race.ini` has lowercase `track=` or whitespace `TRACK = ` | Ensure `optionxform=str` and `space_around_delimiters=False` in INI generator. |
| `Extension 'New Modes' disabled: not selected` | `race.ini` missing `__CM_CUSTOM_MODE=gt-license` in `[RACE]` | Add `__CM_CUSTOM_MODE=gt-license` to `event.ini` and `race.ini`. |
| Car stationary at finish line or pit box | Engine initialized in non-existent `script.init()` or test config failed to load | Instantiate `activeEngine` at top level; check test ID regex in `loadTestConfig`. |
| Car rolling start launches in reverse (tail-first) | `physics.setCarPosition` orientation direction convention is inverted relative to `car.look` | Pass `-fwd` (`vec3(-fwd.x, -fwd.y, -fwd.z)`) to `physics.setCarPosition` so headlights face $+fwd$. |
| Car remains in pit box on live simulation start | `setupSpawn` only called during script load before `ac.getCar(0)` is live | Re-assert `setupSpawn` on the first live frame of `script.update(dt)`. |
| Rolling start car has no drive / engine at idle (850 RPM) | Gearbox remains in neutral (`gear=0`) during countdown | Call `physics.engageGear(0, gear)` and `physics.setEngineRPM(0, 3500)` during `maintainRollingVelocity`. |
| `KEY_NOT_FOUND: [CAR_0] BALLAST` / `RESTRICTOR` | Missing ballast/restrictor entries in `[CAR_0]` | Add `BALLAST=0` and `RESTRICTOR=0` to `[CAR_0]`. |
| Car flips or sinks into road mesh on spawn | Spawn coordinates flush with road collision surface | Ensure `verticalOffset` (+0.05m to +0.10m) is applied during `teleportCar`. |
| Rolling start car decelerates during countdown | AC native physics clear linear velocity before lights out | Call `maintainRollingVelocity` on every frame while in `COUNTDOWN` state. |

---

## 5. Verification Tools Reference

Always use the automated evaluation tooling before manual testing:

```powershell
# 1. Regenerate all test definitions and career event files
python tools/generate_all_content.py

# 2. Sync all repository assets and Lua code to Assetto Corsa install
python tools/sync_to_ac.py

# 3. Linter validation of all 58 test JSON definitions
python tools/validate_curriculum.py --all

# 4. In-engine launch and telemetry evaluation loop
python tools/test_and_eval_loop.py --test-id B-3 --timeout 8

# 5. Audit Lua scripts against official CSP SDK symbols
python tools/audit_csp_api.py
```

