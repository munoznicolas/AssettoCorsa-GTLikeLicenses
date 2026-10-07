#!/usr/bin/env python3
"""
build_cm_package.py
Automated Content Manager Drag & Drop Release Package Builder.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.deployment.packager`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.deployment.packager import (
    CMPackageBuilder,
    DEFAULT_MANIFEST_INI,
    DEFAULT_OUTPUT_ZIP,
    DEFAULT_SCENARIO_LUA,
    main,
    run_pre_validation,
)

__all__ = [
    "CMPackageBuilder",
    "DEFAULT_OUTPUT_ZIP",
    "DEFAULT_MANIFEST_INI",
    "DEFAULT_SCENARIO_LUA",
    "run_pre_validation",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
