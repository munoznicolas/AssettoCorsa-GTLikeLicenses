import os
import sys
import re
import math

REPO_ROOT = os.path.abspath('.')
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools'))

from tools.content.catalog import TEST_CATALOG
from tools.extract_spline_coords import SplineParser, find_spline_file, DEFAULT_AC_ROOT
from tools.apply_rolling_start_calibrations import CONFIG_40

def compute_steer(radius, wheelbase=2.5, steer_ratio=14.5):
    if radius <= 0.1 or math.isinf(radius) or math.isnan(radius):
        return 0.0
    return math.atan2(wheelbase, radius) * steer_ratio * (180.0 / math.pi)

def get_tier_file(test_id):
    prefix = test_id.split("-")[0]
    mapping = {"B": "national_b.py", "A": "national_a.py", "IB": "international_b.py", "IA": "international_a.py", "S": "super_license.py"}
    return os.path.join(REPO_ROOT, "tools", "content", "catalog", mapping.get(prefix, "national_b.py"))

parsers = {}
new_finishes = {}

for tdef in TEST_CATALOG:
    if tdef.get('with_stop_box', False) or tdef['start_mode'] == 'FLYING_LAP':
        continue
        
    t_id = tdef['test_id']
    track_id = tdef['track_id']
    layout = tdef['track_layout']
    key = f"{track_id}::{layout}"
    
    if key not in parsers:
        spline_file = find_spline_file(track_id, layout, DEFAULT_AC_ROOT)
        if spline_file:
            parsers[key] = SplineParser(spline_file)
        else:
            continue
            
    parser = parsers[key]
    tot_len = parser.total_length
    
    if t_id in CONFIG_40:
        fin_s = CONFIG_40[t_id]['finish_s']
    else:
        fin_s = tdef['finish_s']
        
    fin_dist = fin_s * tot_len
    
    def get_steer_at_dist(dist):
        wp = min(parser.waypoints, key=lambda w: abs((w.distance % tot_len) - (dist % tot_len)))
        return compute_steer(wp.radius)
        
    curr_steer = get_steer_at_dist(fin_dist)
    if curr_steer > 5.0:
        step = 1.0
        search_dist = fin_dist
        consecutive_straight = 0
        while True:
            search_dist = (search_dist + step) % tot_len
            st = get_steer_at_dist(search_dist)
            if st <= 5.0:
                consecutive_straight += step
            else:
                consecutive_straight = 0
                
            if consecutive_straight >= 20.0:
                break
                
            if (search_dist - fin_dist) % tot_len > 1500:
                break # safeguard
        
        new_fin_dist = (search_dist - 10.0) % tot_len
        new_fin_s = round(new_fin_dist / tot_len, 4)
        new_finishes[t_id] = new_fin_s
        print(f"{t_id}: {fin_s} -> {new_fin_s}")

# 1. Update CONFIG_40 in tools/apply_rolling_start_calibrations.py
calib_file = os.path.join(REPO_ROOT, "tools", "apply_rolling_start_calibrations.py")
with open(calib_file, "r", encoding="utf-8") as f:
    calib_content = f.read()

for t_id, new_fin_s in new_finishes.items():
    if t_id in CONFIG_40:
        pattern = rf'("{t_id}":\s*{{.*?)"finish_s":\s*[\d\.]+'
        calib_content = re.sub(pattern, rf'\g<1>"finish_s": {new_fin_s}', calib_content)

with open(calib_file, "w", encoding="utf-8") as f:
    f.write(calib_content)

# 2. Update directly in catalog files for those NOT in CONFIG_40
for t_id, new_fin_s in new_finishes.items():
    if t_id not in CONFIG_40:
        fpath = get_tier_file(t_id)
        with open(fpath, "r", encoding="utf-8") as f:
            c_content = f.read()
        pattern = rf'({{\s*"test_id":\s*"{re.escape(t_id)}",.*?}})'
        match = re.search(pattern, c_content, re.DOTALL)
        if match:
            block = match.group(1)
            block = re.sub(r'"finish_s":\s*[\d\.]+', f'"finish_s": {new_fin_s}', block)
            c_content = c_content[:match.start(1)] + block + c_content[match.end(1):]
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(c_content)

print("Done updating sources.")
