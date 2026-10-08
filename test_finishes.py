import os
import sys
import math

REPO_ROOT = os.path.dirname(os.path.abspath('.'))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools'))

from tools.content.catalog import TEST_CATALOG
from tools.extract_spline_coords import SplineParser, find_spline_file, DEFAULT_AC_ROOT

def compute_steer(radius, wheelbase=2.5, steer_ratio=14.5):
    if radius <= 0.1 or math.isinf(radius) or math.isnan(radius):
        return 0.0
    return math.atan2(wheelbase, radius) * steer_ratio * (180.0 / math.pi)

parsers = {}
for tdef in TEST_CATALOG:
    if tdef.get('with_stop_box', False):
        continue  # skip stop box tests? The prompt just said "tests ending positions"

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
    fin_dist = tdef['finish_s'] * tot_len
    
    # find waypoint at fin_dist
    wp = min(parser.waypoints, key=lambda w: abs((w.distance % tot_len) - (fin_dist % tot_len)))
    steer = compute_steer(wp.radius)
    
    if steer > 5.0:
        print(f"Test {tdef['test_id']} ends at corner: {steer:.1f} deg steer. dist={fin_dist:.1f}")

