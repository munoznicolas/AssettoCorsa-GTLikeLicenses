# Driving School Content & Career (`content/`)

## Overview
This directory stores the official curriculum data for all license tests across 5 tiers, as well as the Content Manager career progression series.

---

## Directory Structure
```
content/
├── tests/                       # Calibrated JSON test definitions
│   ├── national_b/              # National B tests
│   ├── national_a/              # National A tests
│   ├── international_b/         # International B tests
│   ├── international_a/         # International A tests
│   ├── super_license/           # Super License tests
│   └── README.md
├── career/                      # 5 Content Manager career series
│   ├── series_gt_license_b/     # National B
│   ├── series_gt_license_a/     # National A (requires B)
│   ├── series_gt_license_ib/    # International B (requires A)
│   ├── series_gt_license_ia/    # International A (requires IB)
│   ├── series_gt_license_s/     # Super License (requires IA)
│   └── README.md
└── README.md                    # This content guide
```

---

## Generation & Verification
All files in `content/tests/` and `content/career/` are generated deterministically by `python tools/generate_all_content.py` (or edited via `python tools/designer.py`) using track AI splines (`fast_lane.ai`). Update `tools/content/catalog/{tier}.py` and run `generate_all_content.py` to rebuild.
