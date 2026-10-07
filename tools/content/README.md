# Feature: Curriculum & Content Generation (`tools/content/`)

## Overview
This subsystem defines the 58 Gran Turismo license tests, generates JSON test specifications calibrated from Assetto Corsa AI splines (`fast_lane.ai`), builds Content Manager career series and events, and provides validation and headless kinematic simulation.

---

## Directory & File Structure
```
tools/content/
├── catalog/                     # Modular driving school curriculum catalog
│   ├── national_b.py            # Tier 1: 12 tests (B-1 .. B-12) - longitudinal fundamentals
│   ├── national_a.py            # Tier 2: 12 tests (A-1 .. A-12) - intermediate dynamics
│   ├── international_b.py       # Tier 3: 12 tests (IB-1 .. IB-12) - high-speed & supercars
│   ├── international_a.py       # Tier 4: 12 tests (IA-1 .. IA-12) - GT3/GT4/DTM race machinery
│   ├── super_license.py         # Tier 5: 10 tests (S-1 .. S-10) - full flying laps
│   ├── tiers.py                 # Career series metadata and tier folder mappings
│   └── __init__.py              # Aggregates TEST_CATALOG, TESTS_BY_ID, TESTS_BY_TIER
├── generator.py                 # Autonomous content generator (JSON tests & career series)
├── validator.py                 # Curriculum schema, geometry, and career progression linter
├── simulator.py                 # 60 Hz headless kinematic simulation harness (348 scenarios)
└── README.md                    # This agent reference guide
```

---

## Key Interfaces & Symbols

### `catalog/`
- `TEST_CATALOG: List[Dict]`: Master list of all 58 license tests in canonical order.
- `TESTS_BY_ID: Dict[str, Dict]`: O(1) lookup dictionary by test ID (e.g. `'B-3'`).
- `TESTS_BY_TIER: Dict[str, List[Dict]]`: Grouped dictionary by tier name.
- `SERIES_METADATA: List[Dict]`: Content Manager career metadata and progression prerequisites.

### `generator.py`
- `generate_tests(ac_root)`: Iterates `TEST_CATALOG`, parses splines, writes `content/tests/<tier>/test_*.json`.
- `generate_career()`: Generates `content/career/series_gt_license_<tier>/` with `series.ini` and `eventX/event.ini`.

### `validator.py`
- `CurriculumValidator`: Validates JSON schema, gate widths (8.0m–25.0m), stop boxes, and target times ($T_{\text{gold}} < T_{\text{silver}} < T_{\text{bronze}}$).

### `simulator.py`
- `HeadlessAdjudicator`: Pure-Python simulation of gate crossing and stop box detection at 60 Hz.
- `simulate_single_test(test_json_path)`: Simulates 6 driver profiles (Gold, Wall Hit, Off-Track, Overshoot, Reset).

---

## Quick Command Usage
```powershell
# Regenerate all content
python tools/generate_all_content.py

# Lint & validate curriculum
python tools/validate_curriculum.py --all

# Run headless 60 Hz kinematic simulation
python tools/simulate_all_tests.py
```

