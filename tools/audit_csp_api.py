#!/usr/bin/env python3
"""
audit_csp_api.py
Audits all CSP Lua API function calls in lua/engine/ and lua/ui/
against the official CSP SDK definition file.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.deployment.api_auditor`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.deployment.api_auditor import (
    API_PATTERN,
    SDK_LIB_PATH,
    load_sdk_symbols,
    main,
    scan_repo_lua_calls,
)

__all__ = [
    "SDK_LIB_PATH",
    "API_PATTERN",
    "load_sdk_symbols",
    "scan_repo_lua_calls",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
