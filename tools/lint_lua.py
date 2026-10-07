#!/usr/bin/env python3
"""
lint_lua.py
Static Analysis & Syntax Validator for CSP Lua Scripts.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.deployment.lua_linter`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.deployment.lua_linter import lint_lua, main

__all__ = ["lint_lua", "main"]

if __name__ == "__main__":
    main()
