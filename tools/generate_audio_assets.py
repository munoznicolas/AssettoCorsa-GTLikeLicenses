#!/usr/bin/env python3
"""
generate_audio_assets.py
Procedural 16-bit PCM 44.1kHz WAV Audio Asset Generator for Assetto Corsa GT Licenses.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.assets.audio_generator`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.assets.audio_generator import (
    create_wave,
    generate_countdown_beep,
    generate_countdown_go,
    generate_fail_buzzer,
    generate_gold_fanfare,
    generate_pass_fanfare,
    main,
)

__all__ = [
    "create_wave",
    "generate_countdown_beep",
    "generate_countdown_go",
    "generate_fail_buzzer",
    "generate_pass_fanfare",
    "generate_gold_fanfare",
    "main",
]

if __name__ == "__main__":
    main()
