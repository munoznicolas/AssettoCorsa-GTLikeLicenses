#!/usr/bin/env python3
"""
tools/content/validation_rules.py
Domain validation rules, data structures, and tier mappings for Assetto Corsa GT License tests.
"""

from dataclasses import dataclass, field
import math
import os
import re
from typing import Any, Dict, List, Optional, Set

# Standard Tier Mappings
TIER_MAP = {
    "national_b": ("National B", "B"),
    "national-b": ("National B", "B"),
    "b": ("National B", "B"),
    "national_a": ("National A", "A"),
    "national-a": ("National A", "A"),
    "a": ("National A", "A"),
    "international_b": ("International B", "IB"),
    "international-b": ("International B", "IB"),
    "ib": ("International B", "IB"),
    "international_a": ("International A", "IA"),
    "international-a": ("International A", "IA"),
    "ia": ("International A", "IA"),
    "super_license": ("Super License", "S"),
    "super-license": ("Super License", "S"),
    "super": ("Super License", "S"),
    "s": ("Super License", "S"),
}

TIER_FOLDER_NAMES = {
    "National B": "national_b",
    "National A": "national_a",
    "International B": "international_b",
    "International A": "international_a",
    "Super License": "super_license",
}

TIER_ORDER = [
    "National B",
    "National A",
    "International B",
    "International A",
    "Super License",
]

TIER_PREFIX = {
    "National B": "B",
    "National A": "A",
    "International B": "IB",
    "International A": "IA",
    "Super License": "S",
}


@dataclass
class ValidationIssue:
    severity: str  # "ERROR" or "WARNING"
    category: str
    message: str
    test_id: Optional[str] = None
    file_path: Optional[str] = None


@dataclass
class ValidationReport:
    total_files_checked: int = 0
    passed_files: int = 0
    failed_files: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "ERROR" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "WARNING")


class ValidationRulesMixin:
    """Domain validation rule checks mixed into CurriculumValidator."""

    ac_root: str
    strict: bool
    _ac_cars_cache: Optional[Set[str]]
    _ac_tracks_cache: Optional[Dict[str, Set[str]]]

    def _check_test_id_conformance(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        test_id = str(data.get("test_id", ""))
        tier = str(data.get("tier", ""))
        filename = os.path.basename(filepath)

        # Regex validation: B-1, A-12, IB-5, IA-8, S-10
        m = re.match(r"^(B|A|IB|IA|S)-([0-9]{1,2})$", test_id)
        if not m:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="TEST_ID",
                    message=f"test_id '{test_id}' does not match standard pattern (e.g. B-1, A-12, IB-3, IA-7, S-10)",
                    test_id=test_id,
                    file_path=filepath,
                )
            )
            return

        prefix, num_str = m.groups()
        num = int(num_str)

        if tier in TIER_PREFIX and TIER_PREFIX[tier] != prefix:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="TIER_MISMATCH",
                    message=f"test_id '{test_id}' has prefix '{prefix}', but tier is '{tier}' (expected '{TIER_PREFIX[tier]}')",
                    test_id=test_id,
                    file_path=filepath,
                )
            )

        # Check test number range based on active catalog tier capacity
        from tools.content.catalog import TESTS_BY_TIER

        max_num = len(TESTS_BY_TIER.get(tier, [])) or (15 if tier == "Super License" else 17)
        if num < 1 or num > max_num:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="TEST_NUMBER",
                    message=f"Test number {num} out of bounds for {tier} (valid: 1-{max_num})",
                    test_id=test_id,
                    file_path=filepath,
                )
            )

        # Check filename consistency (e.g. test_b01.json or test_b1.json)
        expected_filename_stem = f"test_{prefix.lower()}{num:02d}"
        expected_filename_stem_short = f"test_{prefix.lower()}{num}"
        current_stem = os.path.splitext(filename)[0].lower()
        if current_stem not in (expected_filename_stem, expected_filename_stem_short):
            issues.append(
                ValidationIssue(
                    severity="WARNING" if not self.strict else "ERROR",
                    category="FILENAME",
                    message=f"File name '{filename}' does not follow convention '{expected_filename_stem}.json'",
                    test_id=test_id,
                    file_path=filepath,
                )
            )

    def _check_target_times(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        targets = data.get("targets", {})
        if not isinstance(targets, dict):
            return

        gold = targets.get("gold_seconds")
        silver = targets.get("silver_seconds")
        bronze = targets.get("bronze_seconds")
        test_id = data.get("test_id", "")

        if any(v is None for v in (gold, silver, bronze)):
            return

        for name, val in [("gold", gold), ("silver", silver), ("bronze", bronze)]:
            if not isinstance(val, (int, float)) or val <= 0:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="TARGET_TIMES",
                        message=f"{name}_seconds ({val}) must be a positive number",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
                return

        # Crucial Rule: gold < silver < bronze
        if not (gold < silver < bronze):
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="TARGET_TIMES",
                    message=(
                        f"Target times must strictly satisfy gold < silver < bronze. "
                        f"Received: Gold={gold:.3f}s, Silver={silver:.3f}s, Bronze={bronze:.3f}s"
                    ),
                    test_id=test_id,
                    file_path=filepath,
                )
            )

        # Plausibility gap check
        if silver - gold < 0.1:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="TARGET_TIMES",
                    message=f"Silver target ({silver:.2f}s) is suspiciously close to Gold ({gold:.2f}s) (delta < 0.1s)",
                    test_id=test_id,
                    file_path=filepath,
                )
            )
        if bronze - silver < 0.1:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="TARGET_TIMES",
                    message=f"Bronze target ({bronze:.2f}s) is suspiciously close to Silver ({silver:.2f}s) (delta < 0.1s)",
                    test_id=test_id,
                    file_path=filepath,
                )
            )

    def _check_gate_geometry(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        timing = data.get("timing", {})
        if not isinstance(timing, dict):
            return

        test_id = data.get("test_id", "")

        for gate_name in ("start_gate", "finish_gate"):
            gate = timing.get(gate_name)
            if not isinstance(gate, dict):
                continue

            p1 = gate.get("p1")
            p2 = gate.get("p2")

            if not (isinstance(p1, list) and len(p1) == 3 and all(isinstance(c, (int, float)) for c in p1)):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="GATE_GEOMETRY",
                        message=f"{gate_name}.p1 must be a 3-element list of numbers",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
                continue

            if not (isinstance(p2, list) and len(p2) == 3 and all(isinstance(c, (int, float)) for c in p2)):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="GATE_GEOMETRY",
                        message=f"{gate_name}.p2 must be a 3-element list of numbers",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
                continue

            # Calculate gate width: Euclidean distance between p1 and p2
            width = math.sqrt(sum((c2 - c1) ** 2 for c1, c2 in zip(p1, p2)))

            # Blueprint Spec: Realistic track boundaries: 8.0m <= width <= 25.0m
            if width < 8.0:
                issues.append(
                    ValidationIssue(
                        severity="WARNING" if not self.strict else "ERROR",
                        category="GATE_WIDTH",
                        message=(
                            f"{gate_name} width ({width:.2f}m) is unusually narrow (< 8.0m). "
                            f"Vehicles may clip gate boundaries or fail detection."
                        ),
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
            elif width > 25.0:
                issues.append(
                    ValidationIssue(
                        severity="WARNING" if not self.strict else "ERROR",
                        category="GATE_WIDTH",
                        message=f"{gate_name} width ({width:.2f}m) exceeds standard track boundaries (> 25.0m).",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

    def _check_spawn_parameters(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        spawn = data.get("spawn", {})
        if not isinstance(spawn, dict):
            return

        test_id = data.get("test_id", "")
        fwd = spawn.get("forward_vector")
        if isinstance(fwd, list) and len(fwd) == 3 and all(isinstance(c, (int, float)) for c in fwd):
            length = math.sqrt(sum(c * c for c in fwd))
            if abs(length - 1.0) > 0.05:
                issues.append(
                    ValidationIssue(
                        severity="WARNING" if not self.strict else "ERROR",
                        category="SPAWN_VECTOR",
                        message=f"spawn.forward_vector is not normalized: length={length:.4f} (expected ~1.0)",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

        start_mode = data.get("start_mode")
        spd = spawn.get("initial_speed_kmh")
        if isinstance(spd, (int, float)):
            if start_mode == "STANDING" and spd > 0.1:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="START_MODE",
                        message=f"start_mode is 'STANDING' but initial_speed_kmh is {spd} (expected 0)",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
            elif start_mode in ("ROLLING", "FLYING_LAP") and spd < 1.0:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="START_MODE",
                        message=f"start_mode is '{start_mode}' but initial_speed_kmh is {spd} km/h (expected > 0)",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

    def _check_stop_box(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        timing = data.get("timing", {})
        fail_rules = data.get("fail_rules", {})
        if not isinstance(timing, dict) or not isinstance(fail_rules, dict):
            return

        stop_box = timing.get("stop_box")
        test_id = data.get("test_id", "")

        if stop_box is not None:
            overshoot_fail = fail_rules.get("stop_box_overshoot_fail", False)
            if not overshoot_fail:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="STOP_BOX",
                        message="timing.stop_box is defined, but fail_rules.stop_box_overshoot_fail is false",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

            size = stop_box.get("size")
            if isinstance(size, list) and len(size) == 3 and any(s <= 0 for s in size):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="STOP_BOX",
                        message=f"stop_box.size dimensions must be positive: {size}",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

    def _check_ac_content_exists(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        car_id = data.get("car_id")
        track_id = data.get("track_id")
        track_layout = data.get("track_layout", "")
        test_id = data.get("test_id", "")

        if not os.path.isdir(self.ac_root):
            return

        if car_id:
            if self._ac_cars_cache is not None:
                car_exists = car_id in self._ac_cars_cache
            else:
                car_exists = os.path.isdir(os.path.join(self.ac_root, "content", "cars", car_id))

            if not car_exists:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="AC_CONTENT_MISSING",
                        message=f"car_id '{car_id}' not found in {self.ac_root}\\content\\cars",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

        if track_id:
            if self._ac_tracks_cache is not None:
                track_exists = track_id in self._ac_tracks_cache
            else:
                track_exists = os.path.isdir(os.path.join(self.ac_root, "content", "tracks", track_id))

            if not track_exists:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="AC_CONTENT_MISSING",
                        message=f"track_id '{track_id}' not found in {self.ac_root}\\content\\tracks",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )
            elif track_layout:
                if self._ac_tracks_cache is not None and track_id in self._ac_tracks_cache:
                    layouts = self._ac_tracks_cache[track_id]
                    layout_exists = (track_layout in layouts) or len(layouts) == 0
                else:
                    layout_dir = os.path.join(self.ac_root, "content", "tracks", track_id, track_layout)
                    ui_layout = os.path.join(self.ac_root, "content", "tracks", track_id, "ui", track_layout)
                    layout_exists = os.path.isdir(layout_dir) or os.path.isdir(ui_layout)

                if not layout_exists:
                    issues.append(
                        ValidationIssue(
                            severity="WARNING" if not self.strict else "ERROR",
                            category="AC_CONTENT_MISSING",
                            message=f"track_layout '{track_layout}' not found under track '{track_id}'",
                            test_id=test_id,
                            file_path=filepath,
                        )
                    )
