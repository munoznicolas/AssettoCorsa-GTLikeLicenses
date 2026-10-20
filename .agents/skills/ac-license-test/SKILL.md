---
name: ac-license-test
description: >-
  Automated build, sync, in-engine launch, and starting conditions evaluation workflow
  for Assetto Corsa GT-Like Licenses. Use whenever running license tests, debugging launch crashes,
  or evaluating rolling start physics conditions.
---

# Assetto Corsa GT-Like Licenses - Test & Evaluation Workflow

This skill guides the automated testing and validation of driving license scenarios in Assetto Corsa with Custom Shaders Patch (CSP).

---

## When to Use This Skill

Activate this workflow when:
* Testing any license scenario (e.g. `B-1`, `B-3`, `A-5`, `IB-10`).
* Debugging in-engine session crashes (`Can't launch the race: invalid race configuration`).
* Validating that rolling start conditions (spawn position, target initial speed) are satisfied.
* Syncing updated Lua scripts or curriculum content to the Assetto Corsa directory.

---

## Quick Execution Recipes

### 1. Full Test & Evaluation Loop (Recommended)
Runs live sync, synthesizes `race.ini`, spawns `acs.exe`, verifies starting conditions, and checks for clean physics and zero crash signatures:
```powershell
python tools/test_and_eval_loop.py --test-id B-3 --timeout 8
```

For standing start tests:
```powershell
python tools/test_and_eval_loop.py --test-id B-1 --timeout 6
```

### 2. Full Curriculum Build & Sync Cycle
Run when changing any test definitions, curriculum parameters, or career series:
```powershell
# 1. Regenerate curriculum JSONs & Content Manager career series
python tools/generate_all_content.py

# 2. Sync all repository assets and Lua code to Assetto Corsa install
python tools/sync_to_ac.py

# 3. Lint all test definitions against JSON schema
python tools/validate_curriculum.py --all
```

### 3. CSP Lua API Symbol Audit
Verifies that all Lua functions exist in the official CSP SDK at `<AC_ROOT>/extension/internal/lua-sdk/ac_new_modes/lib.lua`:
```powershell
python tools/audit_csp_api.py
```

---

## Diagnostic Quick Reference

When troubleshooting crashes or anomalies:

1. **Check CSP Log**:
   ```powershell
   Get-Content "$env:USERPROFILE\Documents\Assetto Corsa\logs\custom_shaders_patch.log" -Tail 30
   ```
2. **Check Game Engine Log**:
   ```powershell
   Get-Content "$env:USERPROFILE\Documents\Assetto Corsa\logs\log.txt" -Tail 30
   ```
3. **Common Signatures**:
   * `Can’t launch the race: invalid race configuration (require_track Line: 141)`:
     `race.ini` has lowercase `track=` instead of `TRACK=`, or spaces around `=` (`TRACK = `).
   * `Extension 'New Modes' disabled: not selected`:
     `race.ini` is missing `__CM_CUSTOM_MODE=gt-license` in `[RACE]`.
   * `Car stationary at grid slot #1 with 0 km/h`:
     Engine coordinator was not instantiated at top level or `testConfig` was not loaded dynamically.
