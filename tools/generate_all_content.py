#!/usr/bin/env python3
"""
generate_all_content.py
Autonomous Content Generator for Assetto Corsa Gran Turismo Licenses Mod.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.content.catalog` and `tools.content.generator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import (
    INTERNATIONAL_A_TESTS,
    INTERNATIONAL_B_TESTS,
    NATIONAL_A_TESTS,
    NATIONAL_B_TESTS,
    SERIES_METADATA,
    SUPER_LICENSE_TESTS,
    TEST_CATALOG,
    TESTS_BY_ID,
    TESTS_BY_TIER,
    TIER_FOLDER_MAP,
)
from tools.content.generator import generate_career, generate_miniatures, generate_tests, main
from tools.spline.parser import DEFAULT_AC_ROOT

__all__ = [
    "TEST_CATALOG",
    "SERIES_METADATA",
    "TIER_FOLDER_MAP",
    "NATIONAL_B_TESTS",
    "NATIONAL_A_TESTS",
    "INTERNATIONAL_B_TESTS",
    "INTERNATIONAL_A_TESTS",
    "SUPER_LICENSE_TESTS",
    "TESTS_BY_ID",
    "TESTS_BY_TIER",
    "generate_tests",
    "generate_miniatures",
    "generate_career",
    "main",
    "DEFAULT_AC_ROOT",
]

if __name__ == "__main__":
    sys.exit(main())
