#!/usr/bin/env python3
"""
designer.py
CLI entry point to launch the local Assetto Corsa GT License Test Designer Web UI.

Usage:
  python tools/designer.py
  python tools/designer.py --port 8080 --no-browser
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.web_ui.server import main

if __name__ == "__main__":
    sys.exit(main())

