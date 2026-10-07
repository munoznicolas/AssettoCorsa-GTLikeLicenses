#!/usr/bin/env python3
"""
check_lua_syntax.py
Lightweight Lua Syntax Checker.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.deployment.lua_syntax`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.deployment.lua_syntax import check_lua_syntax, main

__all__ = ["check_lua_syntax", "main"]

if __name__ == "__main__":
    main()
