# Feature: In-Engine Testing & Orchestration (`tools/testing/`)

## Overview
This subsystem coordinates headless dry-runs and live in-engine test launches by synthesizing Assetto Corsa's `race.ini` configuration, executing `acs.exe`, asserting physics stability, and verifying that no crash logs or parser errors are emitted.

---

## Directory & File Structure
```
tools/testing/
├── ac_launcher.py               # Generates race.ini, launches acs.exe, monitors log.txt
├── eval_loop.py                 # Automated sync -> launch -> audit loop
├── suite_runner.py              # Master 7-stage automated verification suite
└── README.md                    # This agent reference guide
```

---

## In-Engine Launch Mechanics
1. **Documents Resolution**: Automatically discovers `%USERPROFILE%\Documents\Assetto Corsa` or Registry shell folder `Personal`.
2. **`race.ini` Synthesis**:
   - Case-sensitive uppercase keys (`TRACK`, `MODEL`, `CONFIG_TRACK`).
   - Standard defaults (`BALLAST=0`, `RESTRICTOR=0`).
   - `__CM_CUSTOM_MODE=gt-license` to instruct CSP to load the custom mode.
3. **Execution Monitoring**:
   - Launches `acs.exe` with `cwd = AC_ROOT`.
   - Polls `log.txt` for physics initialization (`PHYSICS LATENCY`, `TRACK GENERATION COMPLETE`).
   - Scans for crash signatures (`require_track Line: 141`, `Extension 'New Modes' disabled`).
   - Gracefully terminates after timeout.

---

## Key Interfaces & Symbols

### `ac_launcher.py`
- `generate_race_ini(test_config, race_ini_path)`: Writes authoritative Kunos C++ compliant `race.ini`.
- `launch_and_evaluate_test(test_json_path, timeout, dry_run)`: Manages subprocess lifecycle and log auditing.

### `eval_loop.py`
- `run_eval_loop(test_id_or_path, timeout, dry_run)`: Synchronizes files to AC directory and evaluates test launch.

### `suite_runner.py`
- `run_stage(name, cmd)`: Executes individual pipeline verification stages with timing benchmarks.

---

## Quick Command Usage
```powershell
# In-engine launch test dry-run for all 58 tests
python tools/test_ac_launch.py --dry-run --all

# Launch and audit live test B-3 with 8-second timeout
python tools/test_and_eval_loop.py --test-id B-3 --timeout 8

# Run master automated test suite
python tools/run_full_validation_suite.py
```

