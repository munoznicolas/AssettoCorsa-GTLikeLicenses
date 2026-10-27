import os
import json
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.web_ui.catalog_manager import get_track_spline_data, get_available_tracks

def generate_all_splines(out_dir: str = None) -> int:
    if out_dir is None:
        out_dir = os.path.join(REPO_ROOT, "data", "splines")
    os.makedirs(out_dir, exist_ok=True)

    tracks = get_available_tracks()
    generated_count = 0

    for t in tracks:
        t_id = t["track_id"]
        layouts = t.get("layouts", [])

        # Default track spline
        s_def = get_track_spline_data(t_id, "")
        if not s_def and layouts:
            s_def = get_track_spline_data(t_id, layouts[0]["layout_id"])

        if s_def and not s_def.get("error"):
            target_path = os.path.join(out_dir, f"{t_id}.json")
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump({"success": True, "spline": s_def}, f, separators=(',', ':'))
            generated_count += 1

        # Specific layouts
        for lay in layouts:
            lay_id = lay["layout_id"]
            if lay_id:
                s_lay = get_track_spline_data(t_id, lay_id)
                if s_lay and not s_lay.get("error"):
                    target_path = os.path.join(out_dir, f"{t_id}__{lay_id}.json")
                    with open(target_path, "w", encoding="utf-8") as f:
                        json.dump({"success": True, "spline": s_lay}, f, separators=(',', ':'))
                    generated_count += 1

    print(f"Generated {generated_count} pre-rendered spline files in {out_dir}")
    return generated_count

if __name__ == "__main__":
    generate_all_splines()
