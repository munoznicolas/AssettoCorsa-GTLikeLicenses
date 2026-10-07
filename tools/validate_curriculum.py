#!/usr/bin/env python3
"""
validate_curriculum.py
Gran Turismo License Mod - Curriculum & Test Definition Linter.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.content.validator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.validator import (
    CurriculumValidator,
    DEFAULT_AC_ROOT,
    DEFAULT_CAREER_DIR,
    DEFAULT_SCHEMA_PATH,
    DEFAULT_TESTS_DIR,
    TIER_MAP,
    ValidationIssue,
    ValidationReport,
    main,
)

__all__ = [
    "CurriculumValidator",
    "ValidationIssue",
    "Severity",
    "TIER_MAP",
    "DEFAULT_SCHEMA_PATH",
    "DEFAULT_TESTS_DIR",
    "DEFAULT_CAREER_DIR",
    "DEFAULT_AC_ROOT",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
