# Python Unit & Contract Tests (`tests/`)

## Overview
This directory contains automated unit and regression tests for core math, 3D ray-cast geometry, UI contracts, and ghost pacer interpolation.

---

## Test Suites (`tests/unit/`)
- `test_engine_math.py`: Validates gate plane ray-casting, 2D stop box containment, rotated bounding boxes, spline distance interpolation, medal adjudication, and 2-frame track limit debounce logic.
- `test_rolling_start_mapper.py`: Validates kinematics angle math ($\delta_{\text{road}}$, $\delta_{\text{wheel}}$), compass directions, straight segment identification, and 95% AI telemetry integration.
- `test_ui_modules.py`: Verifies audio asset PCM parameters (16-bit 44.1kHz), texture dimensions, and Lua UI rendering API contracts.
- `test_ghost_manager.py`: Verifies collinear curvature calculations, finite radius curves, trajectory time normalization, and ensures all 58 tests can generate ghost profiles.

---

## Running Tests
```powershell
# Run all unit tests
python -m unittest discover tests

# Run specific test suite
python -m unittest tests.unit.test_engine_math
```

