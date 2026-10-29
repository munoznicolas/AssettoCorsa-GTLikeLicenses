#!/usr/bin/env python3
"""
test_web_ui_theme.py
Unit tests verifying browser preference theme synchronization and the ghost
utility theme toggle button in the Actions menu.
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(REPO_ROOT, "tools", "web_ui", "static")


class TestWebUITheme(unittest.TestCase):
    """Test suite for theme browser preference synchronization and menu utility integration."""

    def test_index_html_theme_configuration(self):
        """Verify index.html configures theme sync with browser preference and actions menu utility."""
        index_path = os.path.join(STATIC_DIR, "index.html")
        self.assertTrue(os.path.isfile(index_path), f"File missing: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Meta color-scheme must declare support for light dark
        self.assertIn('<meta name="color-scheme" content="light dark"', content)

        # Inline head script must detect prefers-color-scheme and apply data-theme without FOUC
        self.assertIn("prefers-color-scheme", content)
        self.assertIn("data-theme", content)

        # Theme toggle is positioned inside the actions menu as a ghost utility
        self.assertIn('id="btn-theme-toggle"', content)
        self.assertIn("btn-ghost", content)

    def test_dom_js_theme_toggle_elements(self):
        """Verify dom.js binds theme toggle elements."""
        dom_path = os.path.join(STATIC_DIR, "js", "dom.js")
        self.assertTrue(os.path.isfile(dom_path), f"File missing: {dom_path}")
        with open(dom_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("dom.btnThemeToggle", content)
        self.assertIn("dom.themeToggleIcon", content)
        self.assertIn("dom.themeToggleText", content)

    def test_theme_js_synchronization_logic(self):
        """Verify theme.js syncs with matchMedia and handles manual utility toggle."""
        theme_path = os.path.join(STATIC_DIR, "js", "theme.js")
        self.assertTrue(os.path.isfile(theme_path), f"File missing: {theme_path}")
        with open(theme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must support browser preference detection
        self.assertIn("getBrowserTheme", content)
        self.assertIn("syncThemeWithBrowser", content)
        self.assertIn("prefers-color-scheme", content)
        self.assertIn("themechange", content)
        self.assertIn("toggleTheme", content)

    def test_style_css_theme_definitions(self):
        """Verify style.css declares color-scheme and contains theme toggle styling."""
        style_path = os.path.join(STATIC_DIR, "style.css")
        self.assertTrue(os.path.isfile(style_path), f"File missing: {style_path}")
        with open(style_path, "r", encoding="utf-8") as f:
            content = f.read()

        # color-scheme declarations
        self.assertIn("color-scheme: light dark;", content)
        self.assertIn(':root[data-theme="light"]', content)
        self.assertIn(':root[data-theme="dark"]', content)

        # Ghost utility theme toggle styling
        self.assertIn(".theme-toggle-btn", content)


if __name__ == "__main__":
    unittest.main()
