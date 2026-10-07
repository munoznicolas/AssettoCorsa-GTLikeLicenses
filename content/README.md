# Driving School Content & Career (`content/`)

## Overview
This directory stores the official curriculum data for all 58 license tests across 5 tiers, as well as the Content Manager career progression series.

---

## Directory Structure
```
content/
├── tests/                       # 58 calibrated JSON test definitions
│   ├── national_b/              # 12 tests: B-1 to B-12
│   ├── national_a/              # 12 tests: A-1 to A-12
│   ├── international_b/         # 12 tests: IB-1 to IB-12
│   ├── international_a/         # 12 tests: IA-1 to IA-12
│   ├── super_license/           # 10 tests: S-1 to S-10
│   └── README.md
├── career/                      # 5 Content Manager career series
│   ├── series_gt_license_b/     # National B (12 events)
│   ├── series_gt_license_a/     # National A (12 events, requires B)
│   ├── series_gt_license_ib/    # International B (12 events, requires A)
│   ├── series_gt_license_ia/    # International A (12 events, requires IB)
│   ├── series_gt_license_s/     # Super License (10 events, requires IA)
│   └── README.md
└── README.md                    # This content guide
```

---

## Generation & Verification
All files in `content/tests/` and `content/career/` are generated deterministically by `python tools/generate_all_content.py` using track AI splines (`fast_lane.ai`). Never edit them manually; update `tools/content/catalog/{tier}.py` and run `generate_all_content.py`.

