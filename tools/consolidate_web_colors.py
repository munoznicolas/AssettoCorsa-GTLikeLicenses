#!/usr/bin/env python3
"""
tools/consolidate_web_colors.py
Automated Design System Color Consolidation for AC License Center.
Consolidates 164 fragmented, hardcoded color codes into a 24-token design system.
"""

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(REPO_ROOT, "tools", "web_ui", "static")

def consolidate_style_css():
    css_path = os.path.join(STATIC_DIR, "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. New Token Architecture in :root
    new_root = """/* style.css - Gran Turismo Aesthetic for License Test Designer */

:root {
  color-scheme: dark;

  /* 1. Surfaces & Backgrounds */
  --bg-main: #0c0f14;
  --bg-panel: #13171e;
  --bg-card: #191f28;
  --bg-input: #10141a;

  /* 2. Borders & Outlines */
  --border-color: #262e3b;
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-focus: #38bdf8;

  /* 3. Typography */
  --text-main: #f3f4f6;
  --text-muted: #8b9bb4;
  --text-dim: #5c687a;

  /* 4. Brand Accents */
  --gt-red: #e11d48;
  --gt-blue: #2563eb;
  --accent-sky: #38bdf8;

  /* 5. Medals & License Tiers */
  --accent-gold: #f59e0b;
  --accent-silver: #94a3b8;
  --accent-bronze: #d97706;
  --tier-super: #8b5cf6;

  /* 6. Status Semantics */
  --accent-green: #10b981;
  --accent-danger: #ef4444;
  --accent-warning: #f59e0b;

  /* 7. Standardized Alpha Overlays & Glows */
  --accent-sky-bg: rgba(56, 189, 248, 0.12);
  --accent-sky-border: rgba(56, 189, 248, 0.35);
  --accent-sky-glow: rgba(56, 189, 248, 0.25);

  --accent-green-bg: rgba(16, 185, 129, 0.15);
  --accent-green-border: rgba(16, 185, 129, 0.35);

  --accent-danger-bg: rgba(239, 68, 68, 0.15);
  --accent-danger-border: rgba(239, 68, 68, 0.35);

  --accent-gold-bg: rgba(245, 158, 11, 0.15);
  --accent-gold-border: rgba(245, 158, 11, 0.35);

  /* 8. Telemetry Data Series */
  --chart-speed: #38bdf8;
  --chart-throttle: #10b981;
  --chart-brake: #ef4444;
  --chart-rpm: #f59e0b;
  --chart-steer: #06b6d4;
  --chart-gear: #8b5cf6;
  --chart-latg: #f43f5e;

  --font-display: "Chakra Petch", sans-serif;
  --font-body: "Inter", sans-serif;
  --font-mono: "JetBrains Mono", monospace;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}"""

    content = re.sub(
        r'/\* style\.css - Gran Turismo Aesthetic for License Test Designer \*/\s*:root\s*\{[^}]+\}',
        new_root,
        content
    )

    # 2. Add Reusable Badges, Banners & Dropzone Classes right after .badge definitions
    badge_utilities = """.badge-success {
  background-color: var(--accent-green-bg);
  color: var(--accent-green);
  border: 1px solid var(--accent-green-border);
}

.badge-sky {
  background-color: var(--accent-sky-bg);
  color: var(--accent-sky);
  border: 1px solid var(--accent-sky-border);
}

.badge-danger {
  background-color: var(--accent-danger-bg);
  color: var(--accent-danger);
  border: 1px solid var(--accent-danger-border);
}

.badge-gold,
.badge-warning {
  background-color: var(--accent-gold-bg);
  color: var(--accent-gold);
  border: 1px solid var(--accent-gold-border);
}

.badge-neutral {
  background-color: rgba(148, 163, 184, 0.15);
  color: var(--text-muted);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

/* Info & Status Banners */
.info-banner-sky {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--accent-sky-bg);
  border: 1px solid var(--accent-sky-border);
}

.info-banner-warning {
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--accent-gold-bg);
  border: 1px solid var(--accent-gold-border);
}

.info-banner-success {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--accent-green-bg);
  border: 1px solid var(--accent-green-border);
}

.info-banner-danger {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--accent-danger-bg);
  border: 1px solid var(--accent-danger);
  color: #ffffff;
}

/* Reusable Dashed Telemetry Dropzone */
.dropzone-dashed {
  border: 2px dashed var(--accent-sky-border);
  border-radius: var(--radius-md);
  background: rgba(16, 20, 26, 0.5);
  transition: all 0.2s ease;
}

.dropzone-dashed:hover,
.dropzone-dashed.dragover {
  border-color: var(--accent-sky);
  background: var(--accent-sky-bg);
}
"""
    if ".badge-success {" not in content:
        content = content.replace("/* Badges */\n.badge {", f"{badge_utilities}\n/* Badges */\n.badge {{")

    # 3. Consolidate specific hardcoded rules in style.css:
    replacements = [
        # Navbar logo gradient
        ('background: linear-gradient(135deg, #1e222d, #0a0c10);', 'background: linear-gradient(135deg, var(--bg-card), var(--bg-main));'),
        ('border: 2px solid #ef4444;', 'border: 2px solid var(--accent-danger);'),
        ('box-shadow: 0 0 10px rgba(239, 68, 68, 0.45);', 'box-shadow: 0 0 10px var(--accent-danger-border);'),
        ('color: #fff;', 'color: var(--text-main);'),
        ('color: #ffffff;', 'color: var(--text-main);'),

        # License nav background
        ('.license-nav {\n  background-color: #10141a;', '.license-nav {\n  background-color: var(--bg-input);'),

        # Reference tabs
        ('.reference-tab {\n  color: #38bdf8;', '.reference-tab {\n  color: var(--accent-sky);'),
        ('.reference-tab:hover {\n  color: #7dd3fc;\n  background-color: #16242f;', '.reference-tab:hover {\n  color: var(--accent-sky);\n  background-color: var(--accent-sky-bg);'),
        ('.reference-tab.active {\n  color: #38bdf8;\n  border-bottom-color: #38bdf8;\n  background-color: #172b38;', '.reference-tab.active {\n  color: var(--accent-sky);\n  border-bottom-color: var(--accent-sky);\n  background-color: var(--accent-sky-bg);'),
        ('.license-tab:hover {\n  color: var(--text-main);\n  background-color: #1a1e25;', '.license-tab:hover {\n  color: var(--text-main);\n  background-color: var(--bg-card);'),
        ('.license-tab.active {\n  color: var(--text-main);\n  border-bottom-color: var(--gt-red);\n  background-color: #2e1a24;', '.license-tab.active {\n  color: var(--text-main);\n  border-bottom-color: var(--gt-red);\n  background-color: var(--accent-danger-bg);'),

        # Test item states
        ('.test-item:hover {\n  border-color: #3f4d61;', '.test-item:hover {\n  border-color: var(--border-color);'),
        ('.test-item.active {\n  border-color: var(--gt-red);\n  background-color: #202733;\n  box-shadow: 0 0 10px rgba(225, 29, 72, 0.15);', '.test-item.active {\n  border-color: var(--gt-red);\n  background-color: var(--bg-card);\n  box-shadow: 0 0 10px var(--accent-danger-border);'),
        ('background-color: #1a1a1a;', 'background-color: var(--bg-main);'),
        ('background: rgba(10, 15, 25, 0.88);', 'background: var(--bg-input);'),
        ('background-color: #283241;', 'background-color: var(--bg-card);'),
        ('.test-item-mode.rolling {\n  color: #60a5fa;\n  border: 1px solid rgba(96, 165, 250, 0.3);', '.test-item-mode.rolling {\n  color: var(--accent-sky);\n  border: 1px solid var(--accent-sky-border);\n  background-color: var(--accent-sky-bg);'),
        ('.test-item-mode.standing {\n  color: #f87171;\n  border: 1px solid rgba(248, 113, 113, 0.3);', '.test-item-mode.standing {\n  color: var(--accent-danger);\n  border: 1px solid var(--accent-danger-border);\n  background-color: var(--accent-danger-bg);'),
        ('.test-item-mode.flying_lap {\n  color: #34d399;\n  border: 1px solid rgba(52, 211, 153, 0.3);', '.test-item-mode.flying_lap {\n  color: var(--accent-green);\n  border: 1px solid var(--accent-green-border);\n  background-color: var(--accent-green-bg);'),

        # Filter count badges
        ('.filter-count-badge {\n  font-family: var(--font-mono);\n  font-size: 10px;\n  color: var(--accent-gold);\n  background-color: rgba(245, 158, 11, 0.12);\n  padding: 1px 6px;\n  border-radius: var(--radius-sm);\n  border: 1px solid rgba(245, 158, 11, 0.25);', '.filter-count-badge {\n  font-family: var(--font-mono);\n  font-size: 10px;\n  color: var(--accent-gold);\n  background-color: var(--accent-gold-bg);\n  padding: 1px 6px;\n  border-radius: var(--radius-sm);\n  border: 1px solid var(--accent-gold-border);'),
        ('.filter-count-badge.empty {\n  color: var(--accent-danger);\n  background-color: rgba(239, 68, 68, 0.12);\n  border-color: rgba(239, 68, 68, 0.3);', '.filter-count-badge.empty {\n  color: var(--accent-danger);\n  background-color: var(--accent-danger-bg);\n  border-color: var(--accent-danger-border);'),
        ('background-color: rgba(16, 20, 26, 0.85);\n  border-color: rgba(38, 46, 59, 0.85);', 'background-color: var(--bg-input);\n  border-color: var(--border-color);'),
        ('background-color: #34373d;', 'background-color: var(--border-color);'),

        # Buttons
        ('.btn-primary:hover {\n  background-color: #f43f5e;', '.btn-primary:hover {\n  filter: brightness(1.15);'),
        ('.btn-secondary {\n  background-color: #263242;\n  color: var(--text-main);\n  border: 1px solid #3c4b5e;', '.btn-secondary {\n  background-color: var(--bg-card);\n  color: var(--text-main);\n  border: 1px solid var(--border-color);'),
        ('.btn-secondary:hover {\n  background-color: #324256;', '.btn-secondary:hover {\n  background-color: var(--border-color);'),
        ('.btn-accent:hover {\n  background-color: #fbbf24;', '.btn-accent:hover {\n  filter: brightness(1.1);'),
        ('.btn-success:hover {\n  background-color: #34d399;', '.btn-success:hover {\n  filter: brightness(1.1);'),
        ('.btn-danger {\n  background-color: #450a0a;\n  color: #fca5a5;\n  border: 1px solid #991b1b;', '.btn-danger {\n  background-color: var(--accent-danger-bg);\n  color: var(--accent-danger);\n  border: 1px solid var(--accent-danger-border);'),
        ('.btn-danger:hover {\n  background-color: #7f1d1d;\n  color: var(--text-main);', '.btn-danger:hover {\n  background-color: var(--accent-danger);\n  color: #ffffff;'),
        ('.btn-warning {\n  background-color: #451a03;\n  color: #fef3c7;\n  border: 1px solid #b45309;', '.btn-warning {\n  background-color: var(--accent-gold-bg);\n  color: var(--accent-gold);\n  border: 1px solid var(--accent-gold-border);'),
        ('.btn-warning:hover {\n  background-color: #78350f;\n  color: #ffffff;\n  border-color: #d97706;', '.btn-warning:hover {\n  background-color: var(--accent-gold);\n  color: #000000;\n  border-color: var(--accent-gold);'),

        # Badges default background
        ('background-color: #232c38;\n  color: var(--accent-gold);', 'background-color: var(--bg-input);\n  color: var(--accent-gold);\n  border: 1px solid var(--border-color);'),

        # Mode cards
        ('.mode-card:hover {\n  border-color: #3f4d61;', '.mode-card:hover {\n  border-color: var(--border-focus);'),
        ('background-color: rgba(245, 158, 11, 0.08);\n  box-shadow: 0 0 10px rgba(245, 158, 11, 0.2);', 'background-color: var(--accent-gold-bg);\n  box-shadow: 0 0 10px var(--accent-gold-border);'),

        # Canvas container & range slider
        ('background: radial-gradient(circle at center, #151a21 0%, #0c0f14 100%);', 'background: radial-gradient(circle at center, var(--bg-card) 0%, var(--bg-main) 100%);'),
        ('background: #252e3b;', 'background: var(--border-color);'),
        ('background-color: #2b3543;', 'background-color: var(--border-color);'),

        # Target validation error
        ('.target-validation-error {\n  margin-top: 10px;\n  padding: 8px 12px;\n  background-color: #450a0a;\n  border: 1px solid #991b1b;\n  border-radius: var(--radius-sm);\n  color: #fca5a5;', '.target-validation-error {\n  margin-top: 10px;\n  padding: 8px 12px;\n  background-color: var(--accent-danger-bg);\n  border: 1px solid var(--accent-danger-border);\n  border-radius: var(--radius-sm);\n  color: var(--accent-danger);'),

        # Toast
        ('.toast {\n  position: fixed;\n  bottom: 24px;\n  right: 24px;\n  background-color: #1e293b;\n  border: 1px solid #475569;\n  border-radius: var(--radius-md);\n  padding: 12px 20px;\n  color: var(--text-main);', '.toast {\n  position: fixed;\n  bottom: 24px;\n  right: 24px;\n  background-color: var(--bg-card);\n  border: 1px solid var(--border-color);\n  border-radius: var(--radius-md);\n  padding: 12px 20px;\n  color: var(--text-main);'),
        ('.toast.success {\n  border-color: var(--accent-green);\n  background-color: #064e3b;', '.toast.success {\n  border-color: var(--accent-green-border);\n  background-color: var(--accent-green-bg);\n  color: var(--accent-green);'),
        ('.toast.error {\n  border-color: var(--accent-danger);\n  background-color: #7f1d1d;', '.toast.error {\n  border-color: var(--accent-danger-border);\n  background-color: var(--accent-danger-bg);\n  color: var(--accent-danger);'),

        # Pills
        ('.pill-btn:hover {\n  color: var(--text-main);\n  border-color: #475569;\n  background-color: #1e293b;', '.pill-btn:hover {\n  color: var(--text-main);\n  border-color: var(--border-color);\n  background-color: var(--bg-card);'),
        ('.pill-btn.active {\n  background-color: #0369a1;\n  border-color: #38bdf8;\n  color: var(--text-main);\n  box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);', '.pill-btn.active {\n  background-color: var(--accent-sky-bg);\n  border-color: var(--accent-sky);\n  color: var(--accent-sky);\n  box-shadow: 0 0 10px var(--accent-sky-glow);'),
        ('.pill-btn-ac {\n  border-color: rgba(225, 29, 72, 0.4);\n  color: #fca5a5;', '.pill-btn-ac {\n  border-color: var(--accent-danger-border);\n  color: var(--accent-danger);'),
        ('.pill-btn-ac:hover {\n  border-color: #ef4444;\n  color: var(--text-main);\n  background-color: rgba(225, 29, 72, 0.15);', '.pill-btn-ac:hover {\n  border-color: var(--gt-red);\n  color: var(--text-main);\n  background-color: var(--accent-danger-bg);'),
        ('.pill-btn-ac.active {\n  background-color: #e11d48;\n  border-color: #fb7185;\n  color: var(--text-main);\n  box-shadow: 0 0 12px rgba(225, 29, 72, 0.45);', '.pill-btn-ac.active {\n  background-color: var(--gt-red);\n  border-color: var(--accent-danger);\n  color: var(--text-main);\n  box-shadow: 0 0 12px var(--accent-danger-border);'),

        # Chart dots & text
        ('.chart-dot.hp {\n  background-color: #ef4444;\n  box-shadow: 0 0 8px #ef4444;', '.chart-dot.hp {\n  background-color: var(--accent-danger);\n  box-shadow: 0 0 8px var(--accent-danger);'),
        ('.chart-dot.pw {\n  background-color: #f59e0b;\n  box-shadow: 0 0 8px #f59e0b;', '.chart-dot.pw {\n  background-color: var(--accent-gold);\n  box-shadow: 0 0 8px var(--accent-gold);'),
        ('.chart-dot.gold {\n  background-color: #10b981;\n  box-shadow: 0 0 8px #10b981;', '.chart-dot.gold {\n  background-color: var(--accent-green);\n  box-shadow: 0 0 8px var(--accent-green);'),
        ('.chart-dot.dist {\n  background-color: #06b6d4;\n  box-shadow: 0 0 8px #06b6d4;', '.chart-dot.dist {\n  background-color: var(--accent-sky);\n  box-shadow: 0 0 8px var(--accent-sky);'),
        ('.chart-dot.drivetrain {\n  background-color: #8b5cf6;\n  box-shadow: 0 0 8px #8b5cf6;', '.chart-dot.drivetrain {\n  background-color: var(--tier-super);\n  box-shadow: 0 0 8px var(--tier-super);'),
        ('color: #f87171;', 'color: var(--accent-danger);'),
        ('color: #fbbf24;', 'color: var(--accent-gold);'),
        ('color: #f43f5e;', 'color: var(--gt-red);'),
        ('color: #22d3ee;', 'color: var(--accent-sky);'),
        ('color: #38bdf8;', 'color: var(--accent-sky);'),

        # Reference table tags
        ('.ref-data-table th {\n  position: sticky;\n  top: 0;\n  background-color: #131822;', '.ref-data-table th {\n  position: sticky;\n  top: 0;\n  background-color: var(--bg-panel);'),
        ('background-color: #1e293b;', 'background-color: var(--border-color);'),
        ('.ref-data-table .tag-game-ac {\n  color: #fecdd3;\n  background-color: #4c0519;', '.ref-data-table .tag-game-ac {\n  color: var(--accent-danger);\n  background-color: var(--accent-danger-bg);'),

        # Driver.js Cyber GT Theme
        ('background-color: #131722 !important;', 'background-color: var(--bg-card) !important;'),
        ('border: 1px solid rgba(56, 189, 248, 0.45) !important;', 'border: 1px solid var(--accent-sky-border) !important;'),
        ('box-shadow: 0 12px 36px rgba(0, 0, 0, 0.85), 0 0 24px rgba(56, 189, 248, 0.2) !important;', 'box-shadow: 0 12px 36px rgba(0, 0, 0, 0.85), 0 0 24px var(--accent-sky-glow) !important;'),
        ('color: #f1f5f9 !important;', 'color: var(--text-main) !important;'),
        ('color: #38bdf8 !important;', 'color: var(--accent-sky) !important;'),
        ('color: #cbd5e1 !important;', 'color: var(--text-muted) !important;'),
        ('color: #94a3b8 !important;', 'color: var(--text-dim) !important;'),
        ('color: #ef4444 !important;', 'color: var(--accent-danger) !important;'),
        ('background: rgba(239, 68, 68, 0.15) !important;', 'background: var(--accent-danger-bg) !important;'),
        ('background-color: #1e293b !important;\n  border: 1px solid #334155 !important;', 'background-color: var(--bg-panel) !important;\n  border: 1px solid var(--border-color) !important;'),
        ('background-color: rgba(56, 189, 248, 0.2) !important;\n  border-color: #38bdf8 !important;\n  color: #38bdf8 !important;', 'background-color: var(--accent-sky-bg) !important;\n  border-color: var(--accent-sky) !important;\n  color: var(--accent-sky) !important;'),
        ('background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;\n  border-color: #3b82f6 !important;', 'background: linear-gradient(135deg, var(--gt-blue), #1d4ed8) !important;\n  border-color: var(--border-focus) !important;'),
        ('border-left-color: #131722 !important;', 'border-left-color: var(--bg-card) !important;'),
        ('border-right-color: #131722 !important;', 'border-right-color: var(--bg-card) !important;'),
        ('border-top-color: #131722 !important;', 'border-top-color: var(--bg-card) !important;'),
        ('border-bottom-color: #131722 !important;', 'border-bottom-color: var(--bg-card) !important;'),
        ('background: rgba(30, 41, 59, 0.6);', 'background: var(--bg-card);'),
        ('border: 1px solid rgba(56, 189, 248, 0.35);', 'border: 1px solid var(--accent-sky-border);'),
        ('border-color: rgba(56, 189, 248, 0.75);\n  background: rgba(56, 189, 248, 0.08);\n  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 12px rgba(56, 189, 248, 0.15);', 'border-color: var(--accent-sky);\n  background: var(--accent-sky-bg);\n  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 12px var(--accent-sky-glow);'),
        ('outline: 2px solid #38bdf8;', 'outline: 2px solid var(--accent-sky);'),
        ('border: 1px solid rgba(245, 158, 11, 0.35);', 'border: 1px solid var(--accent-gold-border);'),
        ('border-color: rgba(245, 158, 11, 0.75);\n  background: rgba(245, 158, 11, 0.08);\n  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 12px rgba(245, 158, 11, 0.15);', 'border-color: var(--accent-gold);\n  background: var(--accent-gold-bg);\n  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 0 12px var(--accent-gold-border);'),
        ('outline: 2px solid #fbbf24;', 'outline: 2px solid var(--accent-gold);'),
        ('.flow1-title {\n  color: #38bdf8;', '.flow1-title {\n  color: var(--accent-sky);'),
        ('.flow2-title {\n  color: #fbbf24;', '.flow2-title {\n  color: var(--accent-gold);'),
        ('color: #cbd5e1;', 'color: var(--text-muted);'),
    ]

    for old_str, new_str in replacements:
        content = content.replace(old_str, new_str)

    with open(css_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Consolidated {css_path}")


def consolidate_index_html():
    html_path = os.path.join(STATIC_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    replacements = [
        # Stop AC button
        ('style="display: none; background: #dc2626; color: #fff; border: 1px solid #ef4444;"',
         'class="btn btn-danger" style="display: none;"'),

        # Submit PR button in navbar
        ('style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);"',
         'class="btn btn-success"'),

        # AI Speed status badge
        ('style="display: none; font-size: 11px; padding: 4px 8px; border-radius: 4px; background: #451a03; border: 1px solid #d97706; color: #fef3c7;"',
         'class="badge badge-gold mt-2" style="display: none;"'),

        # Export single telemetry script button
        ('style="display: none; font-size: 11px; padding: 3px 8px; border-color: #38bdf8; color: #38bdf8; gap: 4px; align-items: center;"',
         'style="display: none; font-size: 11px; padding: 3px 8px; border-color: var(--accent-sky); color: var(--accent-sky); gap: 4px; align-items: center;"'),

        # Missing telemetry card
        ('style="display: none; padding: 12px; border-radius: 6px; background: rgba(245, 158, 11, 0.1); border: 1px dashed rgba(245, 158, 11, 0.4);"',
         'class="info-banner-warning mt-2" style="display: none;"'),
        ('style="border: 1px dashed rgba(255,255,255,0.25); border-radius: 4px; padding: 10px; text-align: center; cursor: pointer; background: rgba(0,0,0,0.25); transition: border-color 0.2s;"',
         'class="dropzone-dashed" style="padding: 10px; text-align: center; cursor: pointer; margin-top: 8px;"'),

        # Summary banner in modal
        ('style="padding: 10px 14px; border-radius: 6px; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); margin-bottom: 14px; font-size: 13px;"',
         'class="info-banner-sky" style="margin-bottom: 14px; font-size: 13px;"'),

        # Local runner script button
        ('style="border-color: #38bdf8; color: #38bdf8;"',
         'style="border-color: var(--accent-sky); color: var(--accent-sky);"'),

        # Run telemetry enqueue button
        ('style="background: #f59e0b; border-color: #d97706; color: #000; font-weight: 600;"',
         'class="btn btn-accent" style="color: #000000; font-weight: 600;"'),

        # Contributor identity label
        ('color: #f8fafc;', 'color: var(--text-main);'),

        # Telemetry dropzone in modal
        ('style="border: 2px dashed rgba(56, 189, 248, 0.35); border-radius: 8px; padding: 24px 16px; text-align: center; cursor: pointer; transition: all 0.2s; background: rgba(15, 23, 42, 0.4);"',
         'class="dropzone-dashed" style="padding: 24px 16px; text-align: center; cursor: pointer;"'),
        ('color: #64748b;', 'color: var(--text-dim);'),

        # Success card in PR modal
        ('style="display: none; padding: 16px; border-radius: 8px; background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); text-align: center;"',
         'class="info-banner-success" style="display: none; text-align: center;"'),

        # PR link & submit buttons
        ('style="background: #22c55e; border-color: #16a34a; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;"',
         'class="btn btn-success" style="font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px;"'),
        ('style="background: #22c55e; border-color: #16a34a; font-weight: 600;"',
         'class="btn btn-success" style="font-weight: 600;"'),
    ]

    for old_str, new_str in replacements:
        content = content.replace(old_str, new_str)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Consolidated {html_path}")


def consolidate_js_files():
    # 1. queue-runner.js
    qr_path = os.path.join(STATIC_DIR, "js", "queue-runner.js")
    with open(qr_path, "r", encoding="utf-8") as f:
        qr = f.read()

    qr_replacements = [
        ('return `<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);">PASSED</span>`;',
         'return `<span class="badge badge-success">PASSED</span>`;'),
        ('return `<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);">RUNNING</span>`;',
         'return `<span class="badge badge-sky">RUNNING</span>`;'),
        ('return `<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);">AUDITING</span>`;',
         'return `<span class="badge badge-sky">AUDITING</span>`;'),
        ('return `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);">QUEUED</span>`;',
         'return `<span class="badge badge-gold">QUEUED</span>`;'),
        ('return `<span class="badge" style="background: rgba(255, 255, 255, 0.08); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.12);">PENDING</span>`;',
         'return `<span class="badge badge-neutral">PENDING</span>`;'),
        ('return `<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4);">${job.status.toUpperCase()}</span>`;',
         'return `<span class="badge badge-danger">${job.status.toUpperCase()}</span>`;'),
    ]
    for old_str, new_str in qr_replacements:
        qr = qr.replace(old_str, new_str)
    with open(qr_path, "w", encoding="utf-8") as f:
        f.write(qr)
    print(f"[OK] Consolidated {qr_path}")

    # 2. telemetry-submitter.js
    ts_path = os.path.join(STATIC_DIR, "js", "telemetry-submitter.js")
    with open(ts_path, "r", encoding="utf-8") as f:
        ts = f.read()

    ts = ts.replace('dropzone.style.borderColor = "#38bdf8";\n      dropzone.style.background = "rgba(56, 189, 248, 0.1)";',
                    'dropzone.classList.add("dragover");')
    ts = ts.replace('dropzone.style.borderColor = "rgba(56, 189, 248, 0.35)";\n      dropzone.style.background = "rgba(15, 23, 42, 0.4)";',
                    'dropzone.classList.remove("dragover");')
    ts = ts.replace('authStatus.style.background = "rgba(34, 197, 94, 0.2)";\n    authStatus.style.color = "#4ade80";\n    authStatus.style.borderColor = "rgba(34, 197, 94, 0.4)";',
                    'authStatus.className = "badge badge-success";')
    ts = ts.replace('authStatus.style.background = "rgba(148, 163, 184, 0.2)";\n    authStatus.style.color = "#94a3b8";\n    authStatus.style.borderColor = "rgba(148, 163, 184, 0.3)";',
                    'authStatus.className = "badge badge-neutral";')

    with open(ts_path, "w", encoding="utf-8") as f:
        f.write(ts)
    print(f"[OK] Consolidated {ts_path}")

    # 3. test-editor.js
    te_path = os.path.join(STATIC_DIR, "js", "test-editor.js")
    with open(te_path, "r", encoding="utf-8") as f:
        te = f.read()

    te = te.replace('dom.telemetryDropzoneEditor.style.borderColor = "#38bdf8";\n      dom.telemetryDropzoneEditor.style.background = "rgba(56, 189, 248, 0.15)";',
                    'dom.telemetryDropzoneEditor.classList.add("dragover");')
    te = te.replace('dom.telemetryDropzoneEditor.style.borderColor = "rgba(255, 255, 255, 0.25)";\n      dom.telemetryDropzoneEditor.style.background = "rgba(0, 0, 0, 0.25)";',
                    'dom.telemetryDropzoneEditor.classList.remove("dragover");')

    with open(te_path, "w", encoding="utf-8") as f:
        f.write(te)
    print(f"[OK] Consolidated {te_path}")

    # 4. track-canvas.js
    tc_path = os.path.join(STATIC_DIR, "js", "track-canvas.js")
    with open(tc_path, "r", encoding="utf-8") as f:
        tc = f.read()

    tc = tc.replace('ctx.fillStyle = "#161b22";', 'ctx.fillStyle = "#0c0f14";') # --bg-main
    tc = tc.replace('ctx.fillStyle = "#48566a";', 'ctx.fillStyle = "#262e3b";') # --border-color grid
    tc = tc.replace('ctx.strokeStyle = "#27313f";', 'ctx.strokeStyle = "#262e3b";') # --border-color centerline
    tc = tc.replace('ctx.shadowColor = "rgba(245, 158, 11, 0.6)";', 'ctx.shadowColor = "rgba(245, 158, 11, 0.35)";')

    with open(tc_path, "w", encoding="utf-8") as f:
        f.write(tc)
    print(f"[OK] Consolidated {tc_path}")

    # 5. miniature-builder.js
    mb_path = os.path.join(STATIC_DIR, "js", "miniature-builder.js")
    with open(mb_path, "r", encoding="utf-8") as f:
        mb = f.read()

    mb = mb.replace('bgGrad.addColorStop(0, "#0b0f19");', 'bgGrad.addColorStop(0, "#0c0f14");') # --bg-main
    mb = mb.replace('bgGrad.addColorStop(1, "#111827");', 'bgGrad.addColorStop(1, "#13171e");') # --bg-panel
    mb = mb.replace('ctx.strokeStyle = "#334155";', 'ctx.strokeStyle = "#262e3b";') # --border-color
    mb = mb.replace('ctx.fillStyle = "#64748b";', 'ctx.fillStyle = "#5c687a";') # --text-dim

    with open(mb_path, "w", encoding="utf-8") as f:
        f.write(mb)
    print(f"[OK] Consolidated {mb_path}")

    # 6. reference-view.js
    rv_path = os.path.join(STATIC_DIR, "js", "reference-view.js")
    with open(rv_path, "r", encoding="utf-8") as f:
        rv = f.read()

    rv = rv.replace('backgroundColor: "#1e293b",\n          titleColor: "#fff",\n          bodyColor: "#cbd5e1",\n          borderColor: "#334155",',
                    'backgroundColor: "#13171e",\n          titleColor: "#f3f4f6",\n          bodyColor: "#8b9bb4",\n          borderColor: "#262e3b",')
    rv = rv.replace('color: "#64748b",', 'color: "#5c687a",')
    rv = rv.replace('color: "#94a3b8",', 'color: "#8b9bb4",')
    rv = rv.replace('ctx.fillStyle = "rgba(15, 23, 42, 0.9)";', 'ctx.fillStyle = "rgba(19, 23, 30, 0.9)";')

    with open(rv_path, "w", encoding="utf-8") as f:
        f.write(rv)
    print(f"[OK] Consolidated {rv_path}")


if __name__ == "__main__":
    print("Beginning automated color consolidation...")
    consolidate_style_css()
    consolidate_index_html()
    consolidate_js_files()
    print("\nColor consolidation completed successfully!")
