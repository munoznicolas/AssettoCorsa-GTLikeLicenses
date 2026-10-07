#!/usr/bin/env python3
"""
test_and_eval_loop.py
Automated Iterative Test Launch & Evaluation Loop for Assetto Corsa GT-Like Licenses.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.testing.eval_loop`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.testing.eval_loop import (
    evaluate_starting_conditions,
    find_test_file_by_id,
    main,
    run_sync,
    run_test_launch,
)

__all__ = [
    "find_test_file_by_id",
    "run_sync",
    "run_test_launch",
    "evaluate_starting_conditions",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
