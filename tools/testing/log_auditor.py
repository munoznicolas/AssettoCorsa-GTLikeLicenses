#!/usr/bin/env python3
"""
tools/testing/log_auditor.py
Assetto Corsa user documents resolution, INI sanitization, skin lookup, and log.txt auditing.
"""

import os
import re
import sys
from typing import Any, List, Tuple

DEFAULT_AC_ROOT = r"D:\SteamLibrary\steamapps\common\assettocorsa"


def get_user_documents_dir() -> str:
    """Dynamically resolves the active Windows Personal/Documents directory from Registry or env."""
    if sys.platform == "win32":
        try:
            import winreg

            sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                val, _ = winreg.QueryValueEx(key, "Personal")
                val = os.path.expandvars(val)
                if os.path.isdir(val):
                    return val
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


USER_DOCS_AC = os.path.join(get_user_documents_dir(), "Assetto Corsa")
ALT_USER_DOCS_AC = os.path.join(os.path.expanduser("~"), "Documents", "Assetto Corsa")
CFG_DIR = os.path.join(USER_DOCS_AC, "cfg")
LOGS_DIR = os.path.join(USER_DOCS_AC, "logs")
RACE_INI_PATH = os.path.join(CFG_DIR, "race.ini")
LOG_TXT_PATH = os.path.join(LOGS_DIR, "log.txt")


def _sanitize_ini_value(val: Any) -> str:
    """Strips newlines, carriage returns, and null bytes to prevent INI key/section injection."""
    s = str(val if val is not None else "")
    return s.replace("\r", "").replace("\n", " ").replace("\x00", "").strip()


def find_car_skin(car_id: str, ac_root: str = DEFAULT_AC_ROOT) -> str:
    """Finds the first valid skin directory for a given car."""
    safe_car = re.sub(r"[^A-Za-z0-9_\-]", "", str(car_id or ""))
    if not safe_car:
        return "0_default"
    cars_base = os.path.realpath(os.path.join(ac_root, "content", "cars"))
    skins_dir = os.path.realpath(os.path.join(cars_base, safe_car, "skins"))
    try:
        if os.path.commonpath([cars_base, skins_dir]) != cars_base:
            return "0_default"
    except ValueError:
        return "0_default"
    if os.path.isdir(skins_dir):
        skins = sorted(os.listdir(skins_dir))
        if skins:
            return _sanitize_ini_value(skins[0])
    return "0_default"


def audit_log(
    log_path: str,
    car_id: str,
    track_id: str,
) -> Tuple[bool, List[str], List[str]]:
    """Audits Assetto Corsa log.txt for initialization milestones and fatal error signatures."""
    candidates = [
        log_path,
        os.path.join(ALT_USER_DOCS_AC, "logs", "log.txt"),
    ]
    target_path = None
    for c in candidates:
        if os.path.isfile(c):
            target_path = c
            break

    if not target_path:
        return False, [], ["Log file does not exist"]

    passed_milestones = []
    detected_errors = []

    fatal_keywords = [
        "FATAL ERROR",
        "ACCESS VIOLATION",
        "ATTEMPT TO INDEX A NIL VALUE",
        "EXCEPTION_ACCESS_VIOLATION",
    ]

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        content_upper = "".join(lines).upper()

        if "PHYSICS" in content_upper or "FMOD" in content_upper or "DIRECTX" in content_upper:
            passed_milestones.append("Engine subsystem initialized")
        if car_id.upper() in content_upper:
            passed_milestones.append(f"Car data referenced ({car_id})")
        if track_id.upper() in content_upper:
            passed_milestones.append(f"Track data referenced ({track_id})")

        for line in lines:
            line_upper = line.upper()
            if "CRASHGUARD" in line_upper:
                continue
            if "CRASH" in line_upper and "CRASHGUARD" not in line_upper:
                detected_errors.append(line.strip())
                continue
            for kw in fatal_keywords:
                if kw in line_upper:
                    if "CANNOT OPEN FILE" in kw and ("SKIN.INI" in line_upper or "CAMERA" in line_upper):
                        continue
                    detected_errors.append(line.strip())
                    break

    except Exception as e:
        detected_errors.append(f"Error reading log file: {e}")

    success = len(detected_errors) == 0
    return success, passed_milestones, detected_errors
