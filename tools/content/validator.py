#!/usr/bin/env python3
"""
validate_curriculum.py
Gran Turismo License Mod - Curriculum & Test Definition Linter

Performs comprehensive validation of license test definitions:
  1. JSON Schema Conformance against schema/test_definition.schema.json
  2. Assetto Corsa Content Existence (car_id and track_id in AC installation)
  3. Logical Consistency of Target Times (gold_seconds < silver_seconds < bronze_seconds)
  4. 3D Gate Vector Geometry & Realistic Track Limits (8.0m <= gate_width <= 25.0m)
  5. Vehicle Spawn Vector Integrity (normalized heading, initial speed vs mode)
  6. Stop Box Consistency (stop_box vs stop_box_overshoot_fail)
  7. Content Manager Career Progression Chains (if career configs are present)

Usage:
  python tools/validate_curriculum.py --all
  python tools/validate_curriculum.py --tier national_b
  python tools/validate_curriculum.py --tier "National A"
  python tools/validate_curriculum.py --test content/tests/national_b/test_b01.json
"""

import argparse
import configparser
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import jsonschema
except ImportError:
    print("[ERROR] jsonschema package is required. Install via: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

# Default paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SCHEMA_PATH = os.path.join(REPO_ROOT, "schema", "test_definition.schema.json")
DEFAULT_TESTS_DIR = os.path.join(REPO_ROOT, "content", "tests")
DEFAULT_CAREER_DIR = os.path.join(REPO_ROOT, "content", "career")
DEFAULT_AC_ROOT = os.environ.get(
    "AC_ROOT",
    r"D:\SteamLibrary\steamapps\common\assettocorsa"
)

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


class CurriculumValidator:
    """Validator engine for Assetto Corsa License Tests."""

    def __init__(
        self,
        schema_path: str = DEFAULT_SCHEMA_PATH,
        ac_root: str = DEFAULT_AC_ROOT,
        strict: bool = False,
        skip_ac_check: bool = False,
    ):
        self.schema_path = schema_path
        self.ac_root = ac_root
        self.strict = strict
        self.skip_ac_check = skip_ac_check
        self.schema: Dict[str, Any] = {}
        self.validator: Optional[jsonschema.Draft7Validator] = None
        self._load_schema()

        # Cache for AC car/track folders to avoid redundant disk I/O
        self._ac_cars_cache: Optional[Set[str]] = None
        self._ac_tracks_cache: Optional[Dict[str, Set[str]]] = None
        if not self.skip_ac_check and os.path.isdir(self.ac_root):
            self._scan_ac_installation()

    def _load_schema(self) -> None:
        if not os.path.isfile(self.schema_path):
            raise FileNotFoundError(f"JSON Schema not found: {self.schema_path}")
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
        self.validator = jsonschema.Draft7Validator(self.schema)

    def _scan_ac_installation(self) -> None:
        cars_dir = os.path.join(self.ac_root, "content", "cars")
        if os.path.isdir(cars_dir):
            try:
                self._ac_cars_cache = set(os.listdir(cars_dir))
            except Exception:
                self._ac_cars_cache = None

        tracks_dir = os.path.join(self.ac_root, "content", "tracks")
        if os.path.isdir(tracks_dir):
            try:
                self._ac_tracks_cache = {}
                for track_name in os.listdir(tracks_dir):
                    track_full = os.path.join(tracks_dir, track_name)
                    if os.path.isdir(track_full):
                        layouts = set()
                        # Inspect subfolders for layouts (ui/ or subdirectories containing data/ or models*.ini)
                        ui_dir = os.path.join(track_full, "ui")
                        if os.path.isdir(ui_dir):
                            for item in os.listdir(ui_dir):
                                if os.path.isdir(os.path.join(ui_dir, item)):
                                    layouts.add(item)
                        for item in os.listdir(track_full):
                            sub = os.path.join(track_full, item)
                            if os.path.isdir(sub) and item not in ("ui", "data", "ai", "skins"):
                                layouts.add(item)
                        self._ac_tracks_cache[track_name] = layouts
            except Exception:
                self._ac_tracks_cache = None

    def validate_test_file(self, filepath: str) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        if not os.path.isfile(filepath):
            issues.append(ValidationIssue(
                severity="ERROR",
                category="FILE_IO",
                message=f"Test file not found: {filepath}",
                file_path=filepath
            ))
            return issues

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(
                severity="ERROR",
                category="JSON_SYNTAX",
                message=f"Malformed JSON: {exc}",
                file_path=filepath
            ))
            return issues

        test_id = data.get("test_id", "UNKNOWN")

        # 1. JSON Schema Validation
        if self.validator:
            schema_errors = list(self.validator.iter_errors(data))
            for err in schema_errors:
                path_desc = ".".join(str(p) for p in err.absolute_path) or "root"
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="SCHEMA",
                    message=f"Field '{path_desc}': {err.message}",
                    test_id=test_id,
                    file_path=filepath
                ))

        # 2. Test ID & Directory Hierarchy Consistency
        self._check_test_id_conformance(data, filepath, issues)

        # 3. Target Times Logical Integrity
        self._check_target_times(data, filepath, issues)

        # 4. Gate Vector Geometry & Realistic Track Limits
        self._check_gate_geometry(data, filepath, issues)

        # 5. Spawn Physics & Start Mode Alignment
        self._check_spawn_parameters(data, filepath, issues)

        # 6. Stop Box Adjudication Rules
        self._check_stop_box(data, filepath, issues)

        # 7. Assetto Corsa Installation Content Verification
        if not self.skip_ac_check:
            self._check_ac_content_exists(data, filepath, issues)

        return issues

    def _check_test_id_conformance(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        test_id = str(data.get("test_id", ""))
        tier = str(data.get("tier", ""))
        filename = os.path.basename(filepath)

        # Regex validation: B-1, A-12, IB-5, IA-8, S-10
        m = re.match(r"^(B|A|IB|IA|S)-([0-9]{1,2})$", test_id)
        if not m:
            issues.append(ValidationIssue(
                severity="ERROR",
                category="TEST_ID",
                message=f"test_id '{test_id}' does not match standard pattern (e.g. B-1, A-12, IB-3, IA-7, S-10)",
                test_id=test_id,
                file_path=filepath
            ))
            return

        prefix, num_str = m.groups()
        num = int(num_str)

        # Check expected tier match
        expected_prefixes = {
            "National B": "B",
            "National A": "A",
            "International B": "IB",
            "International A": "IA",
            "Super License": "S",
        }
        if tier in expected_prefixes and expected_prefixes[tier] != prefix:
            issues.append(ValidationIssue(
                severity="ERROR",
                category="TIER_MISMATCH",
                message=f"test_id '{test_id}' has prefix '{prefix}', but tier is '{tier}' (expected '{expected_prefixes[tier]}')",
                test_id=test_id,
                file_path=filepath
            ))

        # Check test number range based on active catalog tier capacity
        from tools.content.catalog import TESTS_BY_TIER
        max_num = len(TESTS_BY_TIER.get(tier, [])) or (15 if tier == "Super License" else 17)
        if num < 1 or num > max_num:
            issues.append(ValidationIssue(
                severity="ERROR",
                category="TEST_NUMBER",
                message=f"Test number {num} out of bounds for {tier} (valid: 1-{max_num})",
                test_id=test_id,
                file_path=filepath
            ))

        # Check filename consistency (e.g. test_b01.json or test_b1.json)
        expected_filename_stem = f"test_{prefix.lower()}{num:02d}"
        expected_filename_stem_short = f"test_{prefix.lower()}{num}"
        current_stem = os.path.splitext(filename)[0].lower()
        if current_stem not in (expected_filename_stem, expected_filename_stem_short):
            issues.append(ValidationIssue(
                severity="WARNING" if not self.strict else "ERROR",
                category="FILENAME",
                message=f"File name '{filename}' does not follow convention '{expected_filename_stem}.json'",
                test_id=test_id,
                file_path=filepath
            ))

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
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="TARGET_TIMES",
                    message=f"{name}_seconds ({val}) must be a positive number",
                    test_id=test_id,
                    file_path=filepath
                ))
                return

        # Crucial Rule: gold < silver < bronze
        if not (gold < silver < bronze):
            issues.append(ValidationIssue(
                severity="ERROR",
                category="TARGET_TIMES",
                message=(
                    f"Target times must strictly satisfy gold < silver < bronze. "
                    f"Received: Gold={gold:.3f}s, Silver={silver:.3f}s, Bronze={bronze:.3f}s"
                ),
                test_id=test_id,
                file_path=filepath
            ))

        # Plausibility gap check
        if silver - gold < 0.1:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="TARGET_TIMES",
                message=f"Silver target ({silver:.2f}s) is suspiciously close to Gold ({gold:.2f}s) (delta < 0.1s)",
                test_id=test_id,
                file_path=filepath
            ))
        if bronze - silver < 0.1:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="TARGET_TIMES",
                message=f"Bronze target ({bronze:.2f}s) is suspiciously close to Silver ({silver:.2f}s) (delta < 0.1s)",
                test_id=test_id,
                file_path=filepath
            ))

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
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="GATE_GEOMETRY",
                    message=f"{gate_name}.p1 must be a 3-element list of numbers",
                    test_id=test_id,
                    file_path=filepath
                ))
                continue

            if not (isinstance(p2, list) and len(p2) == 3 and all(isinstance(c, (int, float)) for c in p2)):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="GATE_GEOMETRY",
                    message=f"{gate_name}.p2 must be a 3-element list of numbers",
                    test_id=test_id,
                    file_path=filepath
                ))
                continue

            # Calculate gate width: Euclidean distance between p1 and p2
            width = math.sqrt(sum((c2 - c1) ** 2 for c1, c2 in zip(p1, p2)))

            # Blueprint Spec: Realistic track boundaries: 8.0m <= width <= 25.0m
            if width < 8.0:
                issues.append(ValidationIssue(
                    severity="WARNING" if not self.strict else "ERROR",
                    category="GATE_WIDTH",
                    message=(
                        f"{gate_name} width ({width:.2f}m) is unusually narrow (< 8.0m). "
                        f"Vehicles may clip gate boundaries or fail detection."
                    ),
                    test_id=test_id,
                    file_path=filepath
                ))
            elif width > 25.0:
                issues.append(ValidationIssue(
                    severity="WARNING" if not self.strict else "ERROR",
                    category="GATE_WIDTH",
                    message=(
                        f"{gate_name} width ({width:.2f}m) exceeds standard track boundaries (> 25.0m)."
                    ),
                    test_id=test_id,
                    file_path=filepath
                ))

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
                issues.append(ValidationIssue(
                    severity="WARNING" if not self.strict else "ERROR",
                    category="SPAWN_VECTOR",
                    message=f"spawn.forward_vector is not normalized: length={length:.4f} (expected ~1.0)",
                    test_id=test_id,
                    file_path=filepath
                ))

        start_mode = data.get("start_mode")
        spd = spawn.get("initial_speed_kmh")
        if isinstance(spd, (int, float)):
            if start_mode == "STANDING" and spd > 0.1:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="START_MODE",
                    message=f"start_mode is 'STANDING' but initial_speed_kmh is {spd} (expected 0)",
                    test_id=test_id,
                    file_path=filepath
                ))
            elif start_mode in ("ROLLING", "FLYING_LAP") and spd < 1.0:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="START_MODE",
                    message=f"start_mode is '{start_mode}' but initial_speed_kmh is {spd} km/h (expected > 0)",
                    test_id=test_id,
                    file_path=filepath
                ))

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
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="STOP_BOX",
                    message="timing.stop_box is defined, but fail_rules.stop_box_overshoot_fail is false",
                    test_id=test_id,
                    file_path=filepath
                ))

            center = stop_box.get("center")
            size = stop_box.get("size")
            if isinstance(size, list) and len(size) == 3:
                if any(s <= 0 for s in size):
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        category="STOP_BOX",
                        message=f"stop_box.size dimensions must be positive: {size}",
                        test_id=test_id,
                        file_path=filepath
                    ))

    def _check_ac_content_exists(
        self, data: Dict[str, Any], filepath: str, issues: List[ValidationIssue]
    ) -> None:
        car_id = data.get("car_id")
        track_id = data.get("track_id")
        track_layout = data.get("track_layout", "")
        test_id = data.get("test_id", "")

        if not os.path.isdir(self.ac_root):
            # If AC root does not exist on disk, warn once per batch
            return

        # Check Car
        if car_id:
            car_exists = False
            if self._ac_cars_cache is not None:
                car_exists = car_id in self._ac_cars_cache
            else:
                car_path = os.path.join(self.ac_root, "content", "cars", car_id)
                car_exists = os.path.isdir(car_path)

            if not car_exists:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="AC_CONTENT_MISSING",
                    message=f"car_id '{car_id}' not found in {self.ac_root}\\content\\cars",
                    test_id=test_id,
                    file_path=filepath
                ))

        # Check Track
        if track_id:
            track_exists = False
            if self._ac_tracks_cache is not None:
                track_exists = track_id in self._ac_tracks_cache
            else:
                track_path = os.path.join(self.ac_root, "content", "tracks", track_id)
                track_exists = os.path.isdir(track_path)

            if not track_exists:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="AC_CONTENT_MISSING",
                    message=f"track_id '{track_id}' not found in {self.ac_root}\\content\\tracks",
                    test_id=test_id,
                    file_path=filepath
                ))
            elif track_layout:
                # Check layout
                layout_exists = False
                if self._ac_tracks_cache is not None and track_id in self._ac_tracks_cache:
                    layouts = self._ac_tracks_cache[track_id]
                    layout_exists = (track_layout in layouts) or len(layouts) == 0
                else:
                    layout_dir = os.path.join(self.ac_root, "content", "tracks", track_id, track_layout)
                    ui_layout = os.path.join(self.ac_root, "content", "tracks", track_id, "ui", track_layout)
                    layout_exists = os.path.isdir(layout_dir) or os.path.isdir(ui_layout)

                if not layout_exists:
                    issues.append(ValidationIssue(
                        severity="WARNING" if not self.strict else "ERROR",
                        category="AC_CONTENT_MISSING",
                        message=f"track_layout '{track_layout}' not found under track '{track_id}'",
                        test_id=test_id,
                        file_path=filepath
                    ))

    def validate_career_series(self, career_dir: str = DEFAULT_CAREER_DIR) -> List[ValidationIssue]:
        """Validates Content Manager career prerequisite chains and series.ini configurations."""
        issues: List[ValidationIssue] = []
        if not os.path.isdir(career_dir):
            return issues

        series_folders = [
            f for f in os.listdir(career_dir)
            if os.path.isdir(os.path.join(career_dir, f)) and f.startswith("series_")
        ]

        series_codes: Dict[str, str] = {}  # code -> folder
        requires_map: Dict[str, Optional[str]] = {}  # folder -> required_code

        for folder in series_folders:
            ini_path = os.path.join(career_dir, folder, "series.ini")
            if not os.path.isfile(ini_path):
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="CAREER",
                    message=f"Missing series.ini in career folder '{folder}'",
                    file_path=ini_path
                ))
                continue

            cp = configparser.ConfigParser(interpolation=None)
            try:
                cp.read(ini_path, encoding="utf-8")
                code = cp.get("SERIES", "CODE", fallback="").strip()
                req = cp.get("SERIES", "REQUIRES", fallback=None)
                if code:
                    series_codes[code] = folder
                requires_map[folder] = req.strip() if req else None
            except Exception as e:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="CAREER",
                    message=f"Error reading {ini_path}: {e}",
                    file_path=ini_path
                ))

        # Check prerequisite link integrity
        for folder, req_code in requires_map.items():
            if req_code and req_code not in series_codes:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="CAREER_PREREQUISITE",
                    message=f"Series in '{folder}' requires unknown prerequisite code '{req_code}'",
                    file_path=os.path.join(career_dir, folder, "series.ini")
                ))

        return issues


def discover_test_files(
    tests_dir: str = DEFAULT_TESTS_DIR,
    tier_filter: Optional[str] = None
) -> List[str]:
    """Finds test JSON files filtered by tier or across all tiers."""
    if not os.path.isdir(tests_dir):
        return []

    target_subfolders: Optional[List[str]] = None
    if tier_filter:
        norm_key = tier_filter.strip().lower().replace(" ", "_")
        if norm_key in TIER_MAP:
            display_name, _ = TIER_MAP[norm_key]
            folder_name = TIER_FOLDER_NAMES[display_name]
            target_subfolders = [folder_name]
        else:
            # Match directly against folder name
            target_subfolders = [tier_filter]

    files: List[str] = []
    for root, _, filenames in os.walk(tests_dir):
        rel = os.path.relpath(root, tests_dir)
        top_sub = rel.split(os.sep)[0] if rel != "." else ""

        if target_subfolders and top_sub not in target_subfolders and rel != ".":
            continue

        for fname in sorted(filenames):
            if fname.endswith(".json") and fname.startswith("test_"):
                files.append(os.path.join(root, fname))

    return sorted(files)


def print_report(report: ValidationReport, verbose: bool = False) -> None:
    """Renders formatted console output for the validation report."""
    print("=" * 80)
    print(" ASSETTO CORSA GT LICENSES - CURRICULUM VALIDATION REPORT")
    print("=" * 80)
    print(f"Total Test Definitions Audited: {report.total_files_checked}")
    print(f"Tests Passed:                   {report.passed_files}")
    print(f"Tests Failed:                   {report.failed_files}")
    print(f"Total Errors:                   {report.error_count}")
    print(f"Total Warnings:                 {report.warning_count}")
    print("-" * 80)

    if not report.issues:
        print("[STATUS] ALL CHECKS PASSED PERFECTLY - ZERO ERRORS DETECTED.")
        print("=" * 80)
        return

    # Group issues by test/file
    grouped: Dict[str, List[ValidationIssue]] = {}
    for issue in report.issues:
        key = issue.test_id or (os.path.basename(issue.file_path) if issue.file_path else "GENERAL")
        grouped.setdefault(key, []).append(issue)

    for key, item_issues in sorted(grouped.items()):
        has_err = any(i.severity == "ERROR" for i in item_issues)
        status_tag = "[FAIL]" if has_err else "[WARN]"
        print(f"\n{status_tag} {key}:")
        for i in item_issues:
            prefix = "  [ERROR]" if i.severity == "ERROR" else "  [WARN] "
            print(f"{prefix} ({i.category}): {i.message}")

    print("\n" + "=" * 80)
    if report.has_errors:
        print(f"[STATUS] VALIDATION FAILED with {report.error_count} error(s).")
    else:
        print("[STATUS] VALIDATION PASSED with warnings.")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assetto Corsa GT Licenses - Curriculum Validator & Linter"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all tests across all curriculum tiers"
    )
    parser.add_argument(
        "--tier", "-t",
        type=str,
        help="Filter validation by tier (e.g. national_b, national_a, international_b, super_license)"
    )
    parser.add_argument(
        "--test", "--file", "-f",
        dest="test_file",
        type=str,
        help="Validate a single specific test JSON file"
    )
    parser.add_argument(
        "--ac-root",
        type=str,
        default=DEFAULT_AC_ROOT,
        help=f"Assetto Corsa installation root (default: {DEFAULT_AC_ROOT})"
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to test_definition.schema.json (default: {DEFAULT_SCHEMA_PATH})"
    )
    parser.add_argument(
        "--tests-dir",
        type=str,
        default=DEFAULT_TESTS_DIR,
        help=f"Path to tests directory (default: {DEFAULT_TESTS_DIR})"
    )
    parser.add_argument(
        "--career-dir",
        type=str,
        default=DEFAULT_CAREER_DIR,
        help=f"Path to career directory (default: {DEFAULT_CAREER_DIR})"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--skip-ac-check",
        action="store_true",
        help="Skip verification of car and track existence against AC installation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as machine-readable JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed diagnostic messages"
    )

    args = parser.parse_args()

    # Determine files to validate
    test_files: List[str] = []
    if args.test_file:
        test_files = [os.path.abspath(args.test_file)]
    else:
        tier_arg = args.tier if args.tier else None
        test_files = discover_test_files(args.tests_dir, tier_arg)

    # Initialize validator
    try:
        validator = CurriculumValidator(
            schema_path=args.schema,
            ac_root=args.ac_root,
            strict=args.strict,
            skip_ac_check=args.skip_ac_check,
        )
    except Exception as exc:
        print(f"[FATAL ERROR] Failed to initialize validator: {exc}", file=sys.stderr)
        return 2

    report = ValidationReport()
    report.total_files_checked = len(test_files)

    for fpath in test_files:
        issues = validator.validate_test_file(fpath)
        has_error = any(i.severity == "ERROR" for i in issues)
        if has_error:
            report.failed_files += 1
        else:
            report.passed_files += 1
        report.issues.extend(issues)

    # Validate career files if present
    career_issues = validator.validate_career_series(args.career_dir)
    report.issues.extend(career_issues)

    if args.json:
        out_dict = {
            "total_files_checked": report.total_files_checked,
            "passed_files": report.passed_files,
            "failed_files": report.failed_files,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "has_errors": report.has_errors,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "test_id": i.test_id,
                    "file_path": i.file_path,
                }
                for i in report.issues
            ]
        }
        print(json.dumps(out_dict, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
