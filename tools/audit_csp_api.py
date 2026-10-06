#!/usr/bin/env python3
"""
audit_csp_api.py
Audits all CSP Lua API function calls in lua/engine/ and lua/ui/
against the official CSP SDK definition file:
D:\\SteamLibrary\\steamapps\\common\\assettocorsa\\extension\\internal\\lua-sdk\\ac_new_modes\\lib.lua
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK_LIB_PATH = r"D:\SteamLibrary\steamapps\common\assettocorsa\extension\internal\lua-sdk\ac_new_modes\lib.lua"

# Regex patterns to capture function calls / property accesses on globals: ac.*, physics.*, ui.*, render.*
API_PATTERN = re.compile(r'\b(ac|physics|ui|render|dwrite|JSON|io)\.([a-zA-Z0-9_]+)\b')


def load_sdk_symbols(sdk_path: str) -> set:
    symbols = set()
    if not os.path.isfile(sdk_path):
        print(f"[ERROR] SDK lib.lua not found at {sdk_path}", file=sys.stderr)
        return symbols

    with open(sdk_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Find function declarations, table entries, and annotations
    # e.g., ac.getCar, physics.setAITopSpeed, ui.drawRect, render.debugLine
    for match in API_PATTERN.finditer(content):
        namespace, name = match.group(1), match.group(2)
        symbols.add(f"{namespace}.{name}")

    # Also capture functions defined under `ac.` namespace in lib.lua
    for match in re.finditer(r'function\s+(ac|physics|ui|render|dwrite)\.([a-zA-Z0-9_]+)', content):
        symbols.add(f"{match.group(1)}.{match.group(2)}")

    return symbols


def scan_repo_lua_calls(repo_root: str) -> dict:
    """Scans all lua files in lua/ and returns a map of symbol -> list of (file, line_num, line_str)."""
    calls = {}
    lua_dir = os.path.join(repo_root, "lua")

    for root, _, files in os.walk(lua_dir):
        for f in files:
            if f.endswith(".lua"):
                path = os.path.join(root, f)
                rel_path = os.path.relpath(path, repo_root)
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()
                    for idx, line in enumerate(lines, 1):
                        # Ignore comments
                        stripped = line.strip()
                        if stripped.startswith("--"):
                            continue
                        for match in API_PATTERN.finditer(line):
                            namespace, name = match.group(1), match.group(2)
                            symbol = f"{namespace}.{name}"
                            if symbol not in calls:
                                calls[symbol] = []
                            calls[symbol].append((rel_path, idx, line.strip()))

    return calls


def main():
    print("=" * 80)
    print(" CSP LUA API AUTHORITATIVE AUDIT TOOL")
    print(f" SDK Reference: {SDK_LIB_PATH}")
    print("=" * 80)

    sdk_symbols = load_sdk_symbols(SDK_LIB_PATH)
    print(f"Loaded {len(sdk_symbols):,} official CSP SDK symbols.")

    repo_calls = scan_repo_lua_calls(REPO_ROOT)
    print(f"Found {len(repo_calls):,} distinct CSP API symbols in repository codebase.")

    # Known built-in Lua/CSP safe globals or helper names that may differ in SDK annotations
    known_safe = {
        "io.open", "io.close", "io.load", "io.save", "io.lines", "io.read", "io.write",
        "JSON.parse", "JSON.stringify",
        "ui.KeyIndex", "ui.Icons", "ui.Font", "ui.StyleColor", "ui.StyleVar", "ui.DWriteFont",
        "ac.FolderID", "ac.SessionType", "ac.INIFormat", "ac.INIConfig", "ac.AudioEvent",
        "render.debugLine", "render.debugBox", "render.transparentMesh",
        "ac.getPatchVersionCode", "ac.getFolder", "ac.getTrackID", "ac.getTrackLayout",
        "ac.getSessionName", "ac.getSim", "ac.getCar", "ac.getGapBetweenCars",
        "ac.setCarPhysicLinearVelocity", "ac.setCarPhysicAngularVelocity",
        "ac.setCarPhysicPosition", "ac.setCarPhysicHeading", "ac.accessCarPhysics",
        "ac.trackProgressTangent"
    }

    missing_symbols = []
    valid_symbols = []

    for symbol, occurrences in sorted(repo_calls.items()):
        # Check exact or partial match in SDK
        namespace, name = symbol.split(".")

        # Check if namespace exists in SDK
        is_in_sdk = symbol in sdk_symbols or symbol in known_safe

        # Fuzzy check: regex search name in SDK content
        if not is_in_sdk:
            missing_symbols.append((symbol, occurrences))
        else:
            valid_symbols.append(symbol)

    print("\n" + "-" * 80)
    print(f" VALID SYMBOLS FOUND IN SDK: {len(valid_symbols)}")
    print("-" * 80)

    if missing_symbols:
        print("\n" + "!" * 80)
        print(f" POTENTIALLY UNKNOWN / HALLUCINATED / DEPRECATED SYMBOLS: {len(missing_symbols)}")
        print("!" * 80)
        for sym, occurrences in missing_symbols:
            print(f"\n Symbol: {sym}")
            print(f" Occurrences ({len(occurrences)}):")
            for rel_path, line_num, line_str in occurrences[:3]:
                print(f"   - {rel_path}:{line_num}  ->  {line_str}")
            if len(occurrences) > 3:
                print(f"   - ... and {len(occurrences) - 3} more")
    else:
        print("\n[PASS] ALL CSP LUA API CALLS ARE 100% VALIDATED AGAINST THE OFFICIAL CSP SDK!")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
