#!/usr/bin/env python3
"""
record_ai_telemetry.py
In-Engine 95% AI Telemetry Recorder & Profiler for Assetto Corsa.

CLI Entry Point & Backward-Compatibility Wrapper.
Implementation has been modularized into `tools.telemetry.recorder`.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.telemetry.recorder import (
    PROFILES_DIR,
    TelemetryProfile,
    TelemetrySample,
    calibrate_from_spline,
    estimate_gear_and_rpm,
    get_or_calculate_initial_physics,
    load_telemetry_profile,
    main,
    profile_filename,
    record_live_in_engine_telemetry,
    save_telemetry_profile,
)

get_profile_path = profile_filename
record_live_telemetry = record_live_in_engine_telemetry

__all__ = [
    "PROFILES_DIR",
    "TelemetrySample",
    "TelemetryProfile",
    "estimate_gear_and_rpm",
    "calibrate_from_spline",
    "load_telemetry_profile",
    "save_telemetry_profile",
    "profile_filename",
    "get_profile_path",
    "record_live_in_engine_telemetry",
    "record_live_telemetry",
    "get_or_calculate_initial_physics",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
