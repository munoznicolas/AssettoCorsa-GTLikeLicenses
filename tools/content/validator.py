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
import os
import sys
from typing import Any, Dict, List, Optional, Set

try:
    import jsonschema
except ImportError:
    print("[ERROR] jsonschema package is required. Install via: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

from tools.content.validation_rules import (
    TIER_FOLDER_NAMES,
    TIER_MAP,
    TIER_ORDER,
    TIER_PREFIX,
    ValidationIssue,
    ValidationReport,
    ValidationRulesMixin,
)

# Default paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SCHEMA_PATH = os.path.join(REPO_ROOT, "schema", "test_definition.schema.json")
DEFAULT_TESTS_DIR = os.path.join(REPO_ROOT, "content", "tests")
DEFAULT_CAREER_DIR = os.path.join(REPO_ROOT, "content", "career")
DEFAULT_AC_ROOT = os.environ.get(
    "AC_ROOT",
    r"D:\SteamLibrary\steamapps\common\assettocorsa",
)


class CurriculumValidator(ValidationRulesMixin):
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
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="FILE_IO",
                    message=f"Test file not found: {filepath}",
                    file_path=filepath,
                )
            )
            return issues

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    category="JSON_SYNTAX",
                    message=f"Malformed JSON: {exc}",
                    file_path=filepath,
                )
            )
            return issues

        test_id = data.get("test_id", "UNKNOWN")

        # 1. JSON Schema Validation
        if self.validator:
            schema_errors = list(self.validator.iter_errors(data))
            for err in schema_errors:
                path_desc = ".".join(str(p) for p in err.absolute_path) or "root"
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="SCHEMA",
                        message=f"Field '{path_desc}': {err.message}",
                        test_id=test_id,
                        file_path=filepath,
                    )
                )

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

    def validate_career_series(self, career_dir: str = DEFAULT_CAREER_DIR) -> List[ValidationIssue]:
        """Validates Content Manager career prerequisite chains and series.ini configurations."""
        issues: List[ValidationIssue] = []
        if not os.path.isdir(career_dir):
            return issues

        series_folders = [
            f
            for f in os.listdir(career_dir)
            if os.path.isdir(os.path.join(career_dir, f)) and f.startswith("series_")
        ]

        series_codes: Dict[str, str] = {}  # code -> folder
        requires_map: Dict[str, Optional[str]] = {}  # folder -> required_code

        for folder in series_folders:
            ini_path = os.path.join(career_dir, folder, "series.ini")
            if not os.path.isfile(ini_path):
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="CAREER",
                        message=f"Missing series.ini in career folder '{folder}'",
                        file_path=ini_path,
                    )
                )
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
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="CAREER",
                        message=f"Error reading {ini_path}: {e}",
                        file_path=ini_path,
                    )
                )

        # Check prerequisite link integrity
        for folder, req_code in requires_map.items():
            if req_code and req_code not in series_codes:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="CAREER_PREREQUISITE",
                        message=f"Series in '{folder}' requires unknown prerequisite code '{req_code}'",
                        file_path=os.path.join(career_dir, folder, "series.ini"),
                    )
                )

        return issues


def validate_career_series(career_dir: str = DEFAULT_CAREER_DIR) -> List[ValidationIssue]:
    """Standalone helper for career series validation."""
    validator = CurriculumValidator(skip_ac_check=True)
    return validator.validate_career_series(career_dir)


def discover_test_files(
    tests_dir: str = DEFAULT_TESTS_DIR, tier_filter: Optional[str] = None
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
    parser.add_argument("--all", action="store_true", help="Validate all tests across all curriculum tiers")
    parser.add_argument(
        "--tier", "-t", type=str,
        help="Filter validation by tier (e.g. national_b, national_a, international_b, super_license)",
    )
    parser.add_argument(
        "--test", "--file", "-f", dest="test_file", type=str,
        help="Validate a single specific test JSON file",
    )
    parser.add_argument(
        "--ac-root", type=str, default=DEFAULT_AC_ROOT,
        help=f"Assetto Corsa installation root (default: {DEFAULT_AC_ROOT})",
    )
    parser.add_argument(
        "--schema", type=str, default=DEFAULT_SCHEMA_PATH,
        help=f"Path to test_definition.schema.json (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--tests-dir", type=str, default=DEFAULT_TESTS_DIR,
        help=f"Path to tests directory (default: {DEFAULT_TESTS_DIR})",
    )
    parser.add_argument(
        "--career-dir", type=str, default=DEFAULT_CAREER_DIR,
        help=f"Path to career directory (default: {DEFAULT_CAREER_DIR})",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument(
        "--skip-ac-check", action="store_true",
        help="Skip verification of car and track existence against AC installation",
    )
    parser.add_argument("--json", action="store_true", help="Output results as machine-readable JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable detailed diagnostic messages")

    args = parser.parse_args()

    if args.test_file:
        test_files = [os.path.abspath(args.test_file)]
    else:
        tier_arg = args.tier if args.tier else None
        test_files = discover_test_files(args.tests_dir, tier_arg)

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

    report = ValidationReport(total_files_checked=len(test_files))

    for fpath in test_files:
        issues = validator.validate_test_file(fpath)
        if any(i.severity == "ERROR" for i in issues):
            report.failed_files += 1
        else:
            report.passed_files += 1
        report.issues.extend(issues)

    report.issues.extend(validator.validate_career_series(args.career_dir))

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
            ],
        }
        print(json.dumps(out_dict, indent=2))
    else:
        print_report(report, verbose=args.verbose)

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
