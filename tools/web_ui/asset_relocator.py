"""
asset_relocator.py
Asset relocation and stale artifact cleanup utilities when license tests are renumbered,
reordered, or deleted in the Web UI catalog.
"""

import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from tools.content.catalog import SERIES_METADATA, TIER_FOLDER_MAP
from tools.spline.parser import DEFAULT_AC_ROOT


def _test_identity_signature(t: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        str(t.get("title", "")).strip(),
        str(t.get("track_id", "")).strip(),
        str(t.get("track_layout", "")).strip(),
        str(t.get("car_id", "")).strip(),
        round(float(t.get("start_s", 0.0)), 4),
        round(float(t.get("finish_s", 1.0)), 4),
        str(t.get("start_mode", "STANDING")).strip().upper(),
    )


def _parse_test_number(test_id: Optional[str], prefix: str) -> Optional[int]:
    if not test_id or not isinstance(test_id, str) or not test_id.startswith(prefix):
        return None
    try:
        num = int(test_id[len(prefix):])
        return num if num > 0 else None
    except ValueError:
        return None


def _resolve_previous_test_ids(
    tests: List[Dict[str, Any]],
    old_tests: List[Dict[str, Any]],
    prefix: str,
) -> List[Optional[str]]:
    has_explicit_prev = any(bool(t.get("previous_test_id")) for t in tests)
    has_unrenumbered_ids = any(
        str(t.get("test_id", "")).strip() != f"{prefix}{idx}"
        for idx, t in enumerate(tests, start=1)
    )
    if has_explicit_prev or has_unrenumbered_ids:
        resolved: List[Optional[str]] = []
        for t in tests:
            raw_prev = str(t.get("previous_test_id") or t.get("test_id") or "").strip()
            resolved.append(raw_prev if _parse_test_number(raw_prev, prefix) is not None else None)
        return resolved

    old_sigs = [_test_identity_signature(ot) for ot in old_tests]
    used_old: Set[int] = set()
    resolved = []
    for t in tests:
        sig = _test_identity_signature(t)
        matched_id: Optional[str] = None
        for old_idx, old_sig in enumerate(old_sigs):
            if old_idx not in used_old and old_sig == sig:
                used_old.add(old_idx)
                matched_id = str(old_tests[old_idx].get("test_id", "")).strip() or f"{prefix}{old_idx + 1}"
                break
        resolved.append(matched_id)
    return resolved


def _read_binary_if_exists(path: str) -> Optional[bytes]:
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return None
    return None


def _read_test_asset_bundle(
    series_folder: str,
    tier_folder: str,
    prefix_clean: str,
    old_id: Optional[str],
    old_num: Optional[int],
) -> Dict[str, Any]:
    if not old_id or old_num is None:
        return {
            "preview_bytes": None,
            "alt_preview_bytes": None,
            "svg_text": None,
            "test_json": None,
        }

    career_preview = os.path.join(REPO_ROOT, "content", "career", series_folder, f"event{old_num}", "preview.png")
    alt_preview = os.path.join(REPO_ROOT, "assets", "previews", "tests", f"{old_id}.png")
    svg_path = os.path.join(REPO_ROOT, "docs", "test_maps", f"{old_id}.svg")
    test_json_path = os.path.join(REPO_ROOT, "content", "tests", tier_folder, f"test_{prefix_clean}{old_num:02d}.json")

    svg_text = None
    if os.path.isfile(svg_path):
        try:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_text = f.read()
        except OSError:
            svg_text = None

    test_json = None
    if os.path.isfile(test_json_path):
        try:
            with open(test_json_path, "r", encoding="utf-8") as f:
                test_json = json.load(f)
        except Exception:
            test_json = None

    return {
        "preview_bytes": _read_binary_if_exists(career_preview),
        "alt_preview_bytes": _read_binary_if_exists(alt_preview),
        "svg_text": svg_text,
        "test_json": test_json,
    }


def _remove_slot_assets(
    series_folder: str,
    tier_folder: str,
    prefix: str,
    prefix_clean: str,
    num: int,
) -> None:
    test_id = f"{prefix}{num}"
    paths = [
        os.path.join(REPO_ROOT, "content", "career", series_folder, f"event{num}", "preview.png"),
        os.path.join(REPO_ROOT, "assets", "previews", "tests", f"{test_id}.png"),
        os.path.join(REPO_ROOT, "docs", "test_maps", f"{test_id}.svg"),
        os.path.join(REPO_ROOT, "content", "tests", tier_folder, f"test_{prefix_clean}{num:02d}.json"),
    ]
    for p in paths:
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass


def _mirror_file_to_ac_if_present(repo_file: str, ac_root: str = DEFAULT_AC_ROOT) -> None:
    if not ac_root or not os.path.isdir(ac_root) or not os.path.isfile(repo_file):
        return
    try:
        rel_path = os.path.relpath(repo_file, REPO_ROOT)
        ac_dest = os.path.realpath(os.path.join(ac_root, rel_path))
        real_ac_root = os.path.realpath(ac_root)
        if os.path.commonpath([real_ac_root, ac_dest]) == real_ac_root and os.path.isdir(os.path.dirname(ac_dest)):
            import shutil
            shutil.copyfile(repo_file, ac_dest)
    except Exception:
        pass


def _write_relocated_test_assets(
    series_folder: str,
    tier_folder: str,
    prefix_clean: str,
    new_id: str,
    new_num: int,
    old_id: Optional[str],
    t: Dict[str, Any],
    bundle: Dict[str, Any],
    ac_root: str = DEFAULT_AC_ROOT,
) -> None:
    from tools.content.generator import generate_single_career_event, generate_single_test_json
    from tools.assets.test_map_generator import generate_single_map
    from tools.assets.preview_generator import generate_single_preview

    # 1. Career preview.png
    dest_preview = os.path.join(REPO_ROOT, "content", "career", series_folder, f"event{new_num}", "preview.png")
    if bundle["preview_bytes"] is not None:
        os.makedirs(os.path.dirname(dest_preview), exist_ok=True)
        with open(dest_preview, "wb") as f:
            f.write(bundle["preview_bytes"])
        _mirror_file_to_ac_if_present(dest_preview, ac_root=ac_root)
    else:
        try:
            generate_single_preview(new_id, test_data=t, ac_root=ac_root)
        except Exception:
            pass

    # 2. Optional assets/previews/tests/<ID>.png
    if bundle["alt_preview_bytes"] is not None:
        alt_dir = os.path.join(REPO_ROOT, "assets", "previews", "tests")
        if os.path.isdir(alt_dir):
            with open(os.path.join(alt_dir, f"{new_id}.png"), "wb") as f:
                f.write(bundle["alt_preview_bytes"])

    # 3. Vector Map SVG
    dest_svg = os.path.join(REPO_ROOT, "docs", "test_maps", f"{new_id}.svg")
    if bundle["svg_text"] is not None:
        os.makedirs(os.path.dirname(dest_svg), exist_ok=True)
        svg_text = bundle["svg_text"]
        if old_id:
            svg_text = svg_text.replace(f"<title>{old_id}:", f"<title>{new_id}:", 1)
        with open(dest_svg, "w", encoding="utf-8") as f:
            f.write(svg_text)
    else:
        try:
            generate_single_map(new_id, test_data=t, ac_root=ac_root)
        except Exception:
            pass

    # 4. Test JSON
    dest_test_json = os.path.join(REPO_ROOT, "content", "tests", tier_folder, f"test_{prefix_clean}{new_num:02d}.json")
    if isinstance(bundle["test_json"], dict):
        os.makedirs(os.path.dirname(dest_test_json), exist_ok=True)
        updated_json = dict(bundle["test_json"])
        updated_json["test_id"] = new_id
        with open(dest_test_json, "w", encoding="utf-8") as f:
            json.dump(updated_json, f, indent=2)
    else:
        try:
            generate_single_test_json(t, ac_root=ac_root)
        except Exception:
            pass

    # 5. Career event.ini
    try:
        event_ini = generate_single_career_event(t)
        if event_ini:
            _mirror_file_to_ac_if_present(event_ini, ac_root=ac_root)
    except Exception:
        pass


def _relocate_tier_test_assets(
    tier_name: str,
    tests: List[Dict[str, Any]],
    old_test_ids: List[Optional[str]],
    old_count: int,
) -> None:
    meta = next((s for s in SERIES_METADATA if s["tier_name"] == tier_name), None)
    if not meta:
        return
    prefix = meta["test_prefix"]
    prefix_clean = prefix.rstrip("-").lower()
    series_folder = meta["folder"]
    tier_folder = TIER_FOLDER_MAP[tier_name]

    moved_entries: List[Tuple[int, str, Optional[int], Optional[str], Dict[str, Any], Dict[str, Any]]] = []
    affected_slots: Set[int] = set()

    for idx, t in enumerate(tests, start=1):
        new_id = f"{prefix}{idx}"
        old_id = old_test_ids[idx - 1] if idx - 1 < len(old_test_ids) else None
        old_num = _parse_test_number(old_id, prefix)
        if old_num == idx:
            continue
        bundle = _read_test_asset_bundle(series_folder, tier_folder, prefix_clean, old_id, old_num)
        moved_entries.append((idx, new_id, old_num, old_id, t, bundle))
        affected_slots.add(idx)
        if old_num is not None and 1 <= old_num <= len(tests):
            affected_slots.add(old_num)

    if moved_entries:
        for slot_num in sorted(affected_slots):
            _remove_slot_assets(series_folder, tier_folder, prefix, prefix_clean, slot_num)

        for new_num, new_id, _old_num, old_id, t, bundle in moved_entries:
            _write_relocated_test_assets(
                series_folder=series_folder,
                tier_folder=tier_folder,
                prefix_clean=prefix_clean,
                new_id=new_id,
                new_num=new_num,
                old_id=old_id,
                t=t,
                bundle=bundle,
            )

    if len(tests) < old_count:
        clean_stale_tests()


def _clean_stale_json_files(test_catalog: List[Dict[str, Any]]) -> None:
    valid_files = set()
    for tdef in test_catalog:
        tier_dir = os.path.join(REPO_ROOT, "content", "tests", TIER_FOLDER_MAP[tdef["tier"]])
        prefix, num_str = tdef["test_id"].split("-")
        num = int(num_str)
        valid_files.add(os.path.normpath(os.path.join(tier_dir, f"test_{prefix.lower()}{num:02d}.json")))

    tests_root = os.path.join(REPO_ROOT, "content", "tests")
    for t_folder in TIER_FOLDER_MAP.values():
        dir_path = os.path.join(tests_root, t_folder)
        if not os.path.isdir(dir_path):
            continue
        for f in glob.glob(os.path.join(dir_path, "*.json")):
            if os.path.normpath(f) not in valid_files:
                try:
                    os.remove(f)
                except OSError:
                    pass


def _clean_stale_career_events(test_catalog: List[Dict[str, Any]]) -> None:
    import shutil
    career_root = os.path.join(REPO_ROOT, "content", "career")
    for s_meta in SERIES_METADATA:
        series_dir = os.path.join(career_root, s_meta["folder"])
        if not os.path.isdir(series_dir):
            continue
        tier_tests = [t for t in test_catalog if t["tier"] == s_meta["tier_name"]]
        max_events = len(tier_tests)
        for event_dir in glob.glob(os.path.join(series_dir, "event*")):
            m = re.match(r"event(\d+)$", os.path.basename(event_dir))
            if m and int(m.group(1)) > max_events:
                try:
                    shutil.rmtree(event_dir)
                except OSError:
                    pass


def _clean_stale_svg_maps(valid_test_ids: set) -> None:
    maps_dir = os.path.join(REPO_ROOT, "docs", "test_maps")
    if not os.path.isdir(maps_dir):
        return
    for svg_file in glob.glob(os.path.join(maps_dir, "*.svg")):
        tid = os.path.splitext(os.path.basename(svg_file))[0]
        if tid not in valid_test_ids:
            try:
                os.remove(svg_file)
            except OSError:
                pass


def clean_stale_tests() -> None:
    """Removes any generated test JSONs that are no longer in the catalog."""
    from tools.content.catalog import TEST_CATALOG

    _clean_stale_json_files(TEST_CATALOG)
    _clean_stale_career_events(TEST_CATALOG)
    _clean_stale_svg_maps({tdef["test_id"] for tdef in TEST_CATALOG})
