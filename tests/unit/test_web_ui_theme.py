#!/usr/bin/env python3
"""
test_web_ui_theme.py
Unit tests verifying browser preference theme synchronization and the complete removal
of the manual light/dark theme switch toggle button across Web UI assets.
"""

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(REPO_ROOT, "tools", "web_ui", "static")


class TestWebUITheme(unittest.TestCase):
    """Test suite for theme browser preference synchronization."""

    def test_index_html_theme_configuration(self):
        """Verify index.html removes toggle button and syncs with browser preference."""
        index_path = os.path.join(STATIC_DIR, "index.html")
        self.assertTrue(os.path.isfile(index_path), f"File missing: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Theme toggle button must be completely removed
        self.assertNotIn('id="btn-theme-toggle"', content)
        self.assertNotIn('id="theme-toggle-icon"', content)
        self.assertNotIn("theme-toggle-btn", content)

        # Meta color-scheme must declare support for light dark
        self.assertIn('<meta name="color-scheme" content="light dark"', content)

        # Inline head script must detect prefers-color-scheme and apply data-theme without FOUC
        self.assertIn("prefers-color-scheme", content)
        self.assertIn("data-theme", content)
        # Must not rely on localStorage to override browser theme
        self.assertNotIn('localStorage.getItem("theme")', content)

    def test_dom_js_removes_theme_toggle_elements(self):
        """Verify dom.js does not attempt to bind the removed theme toggle button."""
        dom_path = os.path.join(STATIC_DIR, "js", "dom.js")
        self.assertTrue(os.path.isfile(dom_path), f"File missing: {dom_path}")
        with open(dom_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("dom.btnThemeToggle", content)
        self.assertNotIn("dom.themeToggleIcon", content)
        self.assertNotIn("btn-theme-toggle", content)
        self.assertNotIn("theme-toggle-icon", content)

    def test_theme_js_synchronization_logic(self):
        """Verify theme.js syncs with matchMedia and removes manual button handlers."""
        theme_path = os.path.join(STATIC_DIR, "js", "theme.js")
        self.assertTrue(os.path.isfile(theme_path), f"File missing: {theme_path}")
        with open(theme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must support browser preference detection
        self.assertIn("getBrowserTheme", content)
        self.assertIn("syncThemeWithBrowser", content)
        self.assertIn("prefers-color-scheme", content)
        self.assertIn("themechange", content)

        # Must not have button event listeners or button UI bindings
        self.assertNotIn("dom.btnThemeToggle", content)
        self.assertNotIn("addEventListener(\"click\"", content)

        # Must clean up any legacy localStorage preference
        self.assertIn('localStorage.removeItem', content)

    def test_style_css_theme_definitions(self):
        """Verify style.css declares color-scheme and contains no theme toggle button styles."""
        style_path = os.path.join(STATIC_DIR, "style.css")
        self.assertTrue(os.path.isfile(style_path), f"File missing: {style_path}")
        with open(style_path, "r", encoding="utf-8") as f:
            content = f.read()

        # color-scheme declarations
        self.assertIn("color-scheme: light dark;", content)
        self.assertIn(':root[data-theme="light"]', content)
        self.assertIn(':root[data-theme="dark"]', content)

        # Removed theme toggle styles
        self.assertNotIn(".theme-toggle-btn", content)
        self.assertNotIn("#theme-toggle-icon", content)


if __name__ == "__main__":
    unittest.main()
