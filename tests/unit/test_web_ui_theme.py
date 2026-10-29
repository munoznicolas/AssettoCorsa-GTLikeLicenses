#!/usr/bin/env python3
"""
test_web_ui_theme.py
Unit tests verifying theme synchronization and the theme switch button
in the Actions drawer across Web UI assets.
"""

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(REPO_ROOT, "tools", "web_ui", "static")


class TestWebUITheme(unittest.TestCase):
    """Test suite for theme configuration and Actions drawer theme button."""

    def test_index_html_theme_configuration(self):
        """Verify index.html includes theme button in actions drawer and syncs with browser preference."""
        index_path = os.path.join(STATIC_DIR, "index.html")
        self.assertTrue(os.path.isfile(index_path), f"File missing: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Theme toggle button exists inside actions drawer
        self.assertIn('id="btn-theme-toggle"', content)
        self.assertIn('id="theme-toggle-icon"', content)
        self.assertIn('id="theme-toggle-text"', content)

        # Meta color-scheme must declare support for light dark
        self.assertIn('<meta name="color-scheme" content="light dark"', content)

        # Inline head script must detect prefers-color-scheme or stored theme
        self.assertIn("prefers-color-scheme", content)
        self.assertIn("data-theme", content)

    def test_theme_js_synchronization_logic(self):
        """Verify theme.js supports detection, toggle and themechange event."""
        theme_path = os.path.join(STATIC_DIR, "js", "theme.js")
        self.assertTrue(os.path.isfile(theme_path), f"File missing: {theme_path}")
        with open(theme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must support browser preference detection & toggle
        self.assertIn("getBrowserTheme", content)
        self.assertIn("setTheme", content)
        self.assertIn("toggleTheme", content)
        self.assertIn("updateThemeToggleUI", content)
        self.assertIn("themechange", content)

    def test_style_css_theme_definitions(self):
        """Verify style.css declares color-scheme and contains theme palettes."""
        style_path = os.path.join(STATIC_DIR, "style.css")
        self.assertTrue(os.path.isfile(style_path), f"File missing: {style_path}")
        with open(style_path, "r", encoding="utf-8") as f:
            content = f.read()

        # color-scheme declarations
        self.assertIn("color-scheme: light dark;", content)
        self.assertIn(':root[data-theme="light"]', content)
        self.assertIn(':root[data-theme="dark"]', content)


if __name__ == "__main__":
    unittest.main()
