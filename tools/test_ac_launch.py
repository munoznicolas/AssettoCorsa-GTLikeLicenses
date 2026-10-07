#!/usr/bin/env python3
"""
test_ac_launch.py
Assetto Corsa In-Engine Session Orchestrator & Batch Launch Tester.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.testing.ac_launcher`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.testing.ac_launcher import (
    CFG_DIR,
    DEFAULT_AC_ROOT,
    LOG_TXT_PATH,
    LOGS_DIR,
    RACE_INI_PATH,
    USER_DOCS_AC,
    audit_log,
    find_car_skin,
    generate_race_ini,
    get_user_documents_dir,
    main,
    run_launch_test,
)

__all__ = [
    "DEFAULT_AC_ROOT",
    "USER_DOCS_AC",
    "CFG_DIR",
    "LOGS_DIR",
    "RACE_INI_PATH",
    "LOG_TXT_PATH",
    "get_user_documents_dir",
    "find_car_skin",
    "generate_race_ini",
    "audit_log",
    "run_launch_test",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
