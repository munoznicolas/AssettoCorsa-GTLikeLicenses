#!/usr/bin/env python3
"""
recalculate_all_targets.py
Unified Curriculum Target Times Recalculation Engine for Assetto Corsa GT-Like Licenses.

Recalculates Gold, Silver, and Bronze medal target times across all 58 tests
using the Standard Gran Turismo balance:
  - Rolling Start Sector Tests (40 tests): Ground-truth 95% AI kinematic integration
      t_accum = sum(delta_d / v_AI95)
      Gold   = round(t_accum * 0.98, 3)
      Silver = round(t_accum * 1.05, 3)
      Bronze = round(t_accum * 1.15, 3)
  - Standing Start & Flying Lap Tests (18 tests):
      Gold   = T_gold (optimal proficient baseline)
      Silver = round(T_gold * (1.05 / 0.98), 3)  [~107.1% of Gold, +7.1%]
      Bronze = round(T_gold * (1.15 / 0.98), 3)  [~117.3% of Gold, +17.3%]
"""

import math
import os
import re
import sys
from typing import Any, Dict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.apply_rolling_start_calibrations import compute_calibrations, get_tier_file_for_test
from tools.content.catalog import TEST_CATALOG


def ceil_tenth(val: float) -> float:
    """Rounds up to the nearest first decimal (tenth), formatted with .X00."""
    return math.ceil(round(val, 4) * 10.0) / 10.0


def recalculate_all_targets() -> Dict[str, Dict[str, float]]:
    """Computes authoritative targets for all 58 tests in the curriculum."""
    # 1. Rolling start tests (40 tests)
    rolling_calibrations = compute_calibrations()
    all_targets: Dict[str, Dict[str, float]] = {}

    for t_id, cal in rolling_calibrations.items():
        tg = cal["targets"]
        all_targets[t_id] = {
            "gold_seconds": ceil_tenth(tg["gold_seconds"]),
            "silver_seconds": ceil_tenth(tg["silver_seconds"]),
            "bronze_seconds": ceil_tenth(tg["bronze_seconds"]),
        }

    # 2. Standing start and flying lap tests (18 tests)
    for t in TEST_CATALOG:
        t_id = t["test_id"]
        if t_id in all_targets:
            continue

        gold_raw = float(t["targets"]["gold_seconds"])
        gold = ceil_tenth(gold_raw)
        silver = ceil_tenth(gold_raw * (1.05 / 0.98))
        bronze = ceil_tenth(gold_raw * (1.15 / 0.98))

        all_targets[t_id] = {
            "gold_seconds": gold,
            "silver_seconds": silver,
            "bronze_seconds": bronze,
        }

    return all_targets


def update_catalog_files(all_targets: Dict[str, Dict[str, float]]) -> int:
    """Updates the targets dictionary across all 5 tier catalog files."""
    files_to_update: Dict[str, str] = {}
    for t_id in all_targets:
        fpath = get_tier_file_for_test(t_id)
        if fpath not in files_to_update:
            with open(fpath, "r", encoding="utf-8") as f:
                files_to_update[fpath] = f.read()

    updated_count = 0

    for t_id, tg in all_targets.items():
        fpath = get_tier_file_for_test(t_id)
        content = files_to_update[fpath]

        # Match test dictionary block for this test_id
        pattern = rf'({{\s*"test_id":\s*"{re.escape(t_id)}",.*?}})'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            print(f"[!] Warning: Could not match test block for {t_id} in {os.path.basename(fpath)}")
            continue

        block = match.group(1)

        # Format targets string
        tg_str = (
            f'"targets": {{"gold_seconds": {tg["gold_seconds"]:.3f}, '
            f'"silver_seconds": {tg["silver_seconds"]:.3f}, '
            f'"bronze_seconds": {tg["bronze_seconds"]:.3f}}}'
        )

        # Replace targets block
        new_block = re.sub(r'"targets":\s*\{[^}]+\}', tg_str, block)
        files_to_update[fpath] = content[:match.start(1)] + new_block + content[match.end(1):]
        updated_count += 1

    for fpath, content in files_to_update.items():
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

    return updated_count


def main():
    print("=" * 80)
    print("ASSETTO CORSA GT-LIKE LICENSES - TARGET TIMES RECALCULATION ENGINE")
    print("=" * 80)

    print("\n[Step 1] Computing unified target times for all 58 tests...")
    targets = recalculate_all_targets()
    print(f"  + Calculated targets for {len(targets)} tests.")

    print("\n[Step 2] Updating tier catalog files in tools/content/catalog/...")
    count = update_catalog_files(targets)
    print(f"  + Updated {count} tests across modular catalog files.")

    print("\nTarget times recalculation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

