"""
tiers.py
Career series metadata and tier folder mappings for Assetto Corsa GT Licenses.
"""

SERIES_METADATA = [
    {
        "folder": "series_gt_license_b",
        "code": "GT_LIC_B",
        "requires": None,
        "tier_name": "National B",
        "name": "Gran Turismo National B License",
        "description": "Fundamentals of vehicle dynamics: longitudinal braking threshold, out-in-out trajectory, weight transfer, and low-power roadster handling.",
        "badge_asset": "series_b_badge.png",
        "test_prefix": "B-",
    },
    {
        "folder": "series_gt_license_a",
        "code": "GT_LIC_A",
        "requires": "GT_LIC_B",
        "tier_name": "National A",
        "name": "Gran Turismo National A License",
        "description": "Intermediate sports car dynamics: high-speed chicanes, blind off-camber drops, mid-engine balance, and turbo torque delivery.",
        "badge_asset": "series_a_badge.png",
        "test_prefix": "A-",
    },
    {
        "folder": "series_gt_license_ib",
        "code": "GT_LIC_IB",
        "requires": "GT_LIC_A",
        "tier_name": "International B",
        "name": "Gran Turismo International B License",
        "description": "High performance & downforce commitment: modern supercars, slipstream overtaking, low-grip control, and high-speed chicanes.",
        "badge_asset": "series_ib_badge.png",
        "test_prefix": "IB-",
    },
    {
        "folder": "series_gt_license_ia",
        "code": "GT_LIC_IA",
        "requires": "GT_LIC_IB",
        "tier_name": "International A",
        "name": "Gran Turismo International A License",
        "description": "Professional motorsport racecraft: GT3, GT4, and DTM race machinery. Full slick tires, racing ABS/TC, high-downforce, and curb discipline.",
        "badge_asset": "series_ia_badge.png",
        "test_prefix": "IA-",
    },
    {
        "folder": "series_gt_license_s",
        "code": "GT_LIC_S",
        "requires": "GT_LIC_IA",
        "tier_name": "Super License",
        "name": "Gran Turismo Super License",
        "description": "The ultimate test of speed and discipline: full timed laps with zero room for error in Hypercars, Group C legends, LMP1, and Formula 1.",
        "badge_asset": "series_s_badge.png",
        "test_prefix": "S-",
    },
]

TIER_FOLDER_MAP = {
    "National B": "national_b",
    "National A": "national_a",
    "International B": "international_b",
    "International A": "international_a",
    "Super License": "super_license",
}
