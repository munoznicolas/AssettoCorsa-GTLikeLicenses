# JSON Schema Specifications (`schema/`)

## Overview
This directory contains formal JSON Schema definitions (Draft-07) used to validate data integrity across tests and Content Manager career definitions.

---

## Files
- `test_definition.schema.json`: Formal schema contract for all test JSON files in `content/tests/<tier>/`. Validates mandatory properties (`test_id`, `tier`, `car_id`, `track_id`, `start_mode`, `spawn`, `timing`, `fail_rules`, `targets`), types, vector dimensions, and numeric ranges.
- `career_manifest.schema.json`: Schema contract for career series manifests.

---

## Verification
Schemas are verified by `python tools/validate_curriculum.py --all` via the `jsonschema` Python library.

