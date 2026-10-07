#!/usr/bin/env python3
"""
sync_to_ac.py
Assetto Corsa Live Directory Auto-Sync Tool.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.deployment.sync`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.deployment.sync import (
    DEFAULT_AC_ROOT,
    DEFAULT_MANIFEST_INI,
    DEFAULT_SCENARIO_LUA,
    build_sync_mappings,
    main,
)

__all__ = [
    "DEFAULT_AC_ROOT",
    "DEFAULT_MANIFEST_INI",
    "DEFAULT_SCENARIO_LUA",
    "build_sync_mappings",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
