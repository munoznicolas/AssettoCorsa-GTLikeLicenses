# Python Unit & Contract Tests (`tests/`)

## Overview
This directory contains automated unit and regression tests for core math, 3D ray-cast geometry, UI contracts, and security hardening.

---

## Test Suites (`tests/unit/`)
- `test_engine_math.py`: Validates gate plane ray-casting, 2D stop box containment, rotated bounding boxes, spline distance interpolation, medal adjudication, and 2-frame track limit debounce logic.
- `test_rolling_start_mapper.py`: Validates kinematics angle math ($\delta_{\text{road}}$, $\delta_{\text{wheel}}$), compass directions, straight segment identification, and AI telemetry integration.
- `test_ui_modules.py`: Verifies audio asset PCM parameters (16-bit 44.1kHz), texture dimensions, and Lua UI rendering API contracts.
- `test_security_hardening.py`: Verifies Web UI origin validation, path traversal containment, INI CRLF injection sanitization, and binary spline parser bounds.

---

## Running Tests
```powershell
# Run all unit tests
python -m unittest discover tests

# Run specific test suite
python -m unittest tests.unit.test_engine_math
```
