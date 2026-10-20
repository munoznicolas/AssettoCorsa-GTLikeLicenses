# Feature: In-Engine Testing & Orchestration (`tools/testing/`)

## Overview
This subsystem coordinates headless dry-runs and live in-engine test launches by synthesizing Assetto Corsa's `race.ini` configuration, executing `acs.exe`, asserting physics stability, and verifying that no crash logs or parser errors are emitted.

---

## Directory & File Structure
```
tools/testing/
├── ac_launcher.py               # Generates race.ini, launches acs.exe, monitors log.txt
├── log_auditor.py               # User documents resolution & log.txt crash signature auditor
├── eval_loop.py                 # Automated sync -> launch -> audit loop
├── restart_telemetry.py         # In-engine session restart telemetry evaluator
├── record_ai_times.py           # Automated AI lap/sector time recorder
├── suite_runner.py              # Master automated verification suite
└── README.md                    # This reference guide
```

---

## Quick Command Usage
```powershell
# In-engine launch test dry-run for all tests
python tools/test_ac_launch.py --dry-run --all

# Launch and audit live test B-3 with 8-second timeout
python tools/test_and_eval_loop.py --test-id B-3 --timeout 8

# Run master automated test suite
python tools/run_full_validation_suite.py
```
