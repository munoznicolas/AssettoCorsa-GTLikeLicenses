# Feature: Curriculum & Content Generation (`tools/content/`)

## Overview
This subsystem defines the Gran Turismo license test catalog across 5 tiers, generates JSON test specifications calibrated from Assetto Corsa AI splines (`fast_lane.ai`), builds Content Manager career series and events, and provides validation and headless kinematic simulation.

---

## Directory & File Structure
```
tools/content/
├── catalog/                     # Modular driving school curriculum catalog
│   ├── national_b.py            # Tier 1: National B tests
│   ├── national_a.py            # Tier 2: National A tests
│   ├── international_b.py       # Tier 3: International B tests
│   ├── international_a.py       # Tier 4: International A tests
│   ├── super_license.py         # Tier 5: Super License tests
│   ├── tiers.py                 # Career series metadata and tier folder mappings
│   └── __init__.py              # Aggregates TEST_CATALOG, TESTS_BY_ID, TESTS_BY_TIER
├── generator.py                 # Autonomous content generator (JSON tests & career series)
├── validator.py                 # Curriculum schema, geometry, and career progression linter
├── validation_rules.py          # Validation rule mixins and issue reporting models
├── simulator.py                 # 60 Hz headless kinematic simulation harness
└── README.md                    # This reference guide
```

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
