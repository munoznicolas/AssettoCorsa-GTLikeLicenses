#!/usr/bin/env python3
"""
run_full_validation_suite.py
Master Verification Suite for Assetto Corsa Gran Turismo-Style License Tests.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.testing.suite_runner`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.testing.suite_runner import (
    main,
    print_header,
    run_stage,
)

__all__ = ["print_header", "run_stage", "main"]

if __name__ == "__main__":
    sys.exit(main())
