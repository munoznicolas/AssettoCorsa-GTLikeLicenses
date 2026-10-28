"""
catalog/__init__.py
Modular Gran Turismo License Curriculum Catalog.
Aggregates tests from all 5 license tiers into a unified catalog and mapping dictionary.
"""

from typing import Any, Dict, List, Optional

from .national_b import NATIONAL_B_TESTS
from .national_a import NATIONAL_A_TESTS
from .international_b import INTERNATIONAL_B_TESTS
from .international_a import INTERNATIONAL_A_TESTS
from .super_license import SUPER_LICENSE_TESTS
from .tiers import SERIES_METADATA, TIER_FOLDER_MAP

# Unified curriculum list preserving official sequence
TEST_CATALOG: List[Dict[str, Any]] = (
    NATIONAL_B_TESTS
    + NATIONAL_A_TESTS
    + INTERNATIONAL_B_TESTS
    + INTERNATIONAL_A_TESTS
    + SUPER_LICENSE_TESTS
)

TESTS_BY_ID: Dict[str, Dict[str, Any]] = {t["test_id"]: t for t in TEST_CATALOG}

TESTS_BY_TIER: Dict[str, List[Dict[str, Any]]] = {
    "National B": NATIONAL_B_TESTS,
    "National A": NATIONAL_A_TESTS,
    "International B": INTERNATIONAL_B_TESTS,
    "International A": INTERNATIONAL_A_TESTS,
    "Super License": SUPER_LICENSE_TESTS,
}
import json
import os

_CURRICULUM_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "curriculum.json",
)

if os.path.isfile(_CURRICULUM_JSON):
    try:
        with open(_CURRICULUM_JSON, "r", encoding="utf-8") as _f:
            _loaded = json.load(_f)
        if isinstance(_loaded, list) and len(_loaded) > 0:
            _tests_by_tier = {tier["tier_name"]: tier.get("tests", []) for tier in _loaded if "tier_name" in tier}
            if "National B" in _tests_by_tier:
                NATIONAL_B_TESTS = _tests_by_tier["National B"]
            if "National A" in _tests_by_tier:
                NATIONAL_A_TESTS = _tests_by_tier["National A"]
            if "International B" in _tests_by_tier:
                INTERNATIONAL_B_TESTS = _tests_by_tier["International B"]
            if "International A" in _tests_by_tier:
                INTERNATIONAL_A_TESTS = _tests_by_tier["International A"]
            if "Super License" in _tests_by_tier:
                SUPER_LICENSE_TESTS = _tests_by_tier["Super License"]

            TEST_CATALOG = (
                NATIONAL_B_TESTS
                + NATIONAL_A_TESTS
                + INTERNATIONAL_B_TESTS
                + INTERNATIONAL_A_TESTS
                + SUPER_LICENSE_TESTS
            )
            TESTS_BY_ID = {t["test_id"]: t for t in TEST_CATALOG}
            TESTS_BY_TIER = {
                "National B": NATIONAL_B_TESTS,
                "National A": NATIONAL_A_TESTS,
                "International B": INTERNATIONAL_B_TESTS,
                "International A": INTERNATIONAL_A_TESTS,
                "Super License": SUPER_LICENSE_TESTS,
            }
    except Exception:
        pass


__all__ = [
    "TEST_CATALOG",
    "TESTS_BY_ID",
    "TESTS_BY_TIER",
    "NATIONAL_B_TESTS",
    "NATIONAL_A_TESTS",
    "INTERNATIONAL_B_TESTS",
    "INTERNATIONAL_A_TESTS",
    "SUPER_LICENSE_TESTS",
    "SERIES_METADATA",
    "TIER_FOLDER_MAP",
]
