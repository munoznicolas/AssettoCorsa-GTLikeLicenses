#!/usr/bin/env python3
"""
Unit Test & Integrity Suite for UI, 3D Rendering & Audio Layer
Validates lua/ui/ modules and assets/ directories.
"""

import os
import sys
import unittest
import wave
from pathlib import Path
from PIL import Image

UNIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = UNIT_DIR.parent.parent


class TestUIModules(unittest.TestCase):
    """Integrity and contract tests for UI, audio, and texture assets."""

    def test_audio_assets(self):
        audio_dir = REPO_ROOT / "assets" / "audio"
        required_wavs = [
            "countdown_beep.wav",
            "countdown_go.wav",
            "fail_buzzer.wav",
            "pass_fanfare.wav",
            "gold_fanfare.wav",
        ]
        for wav_name in required_wavs:
            p = audio_dir / wav_name
            self.assertTrue(p.is_file(), f"Missing audio asset: {p}")
            with wave.open(str(p), "r") as wf:
                self.assertIn(wf.getnchannels(), (1, 2), f"{wav_name}: invalid channels")
                self.assertEqual(wf.getsampwidth(), 2, f"{wav_name}: not 16-bit PCM")
                self.assertEqual(wf.getframerate(), 44100, f"{wav_name}: sample rate != 44100")
                duration = wf.getnframes() / wf.getframerate()
                self.assertGreater(duration, 0.05, f"{wav_name}: duration too short ({duration}s)")

    def test_texture_assets(self):
        tex_dir = REPO_ROOT / "assets" / "textures"
        required_pngs = [
            "medal_gold.png",
            "medal_silver.png",
            "medal_bronze.png",
            "ribbon_start.png",
            "ribbon_finish.png",
        ]
        for png_name in required_pngs:
            p = tex_dir / png_name
            self.assertTrue(p.is_file(), f"Missing texture asset: {p}")
            with Image.open(str(p)) as im:
                self.assertEqual(im.format, "PNG", f"{png_name}: not PNG")
                self.assertEqual(im.mode, "RGBA", f"{png_name}: not RGBA")
                w, h = im.size
                self.assertTrue(w >= 128 and h >= 64, f"{png_name}: dimensions too small ({w}x{h})")

    def test_lua_module_contracts(self):
        # 1. license_hud.lua
        hud_path = REPO_ROOT / "lua" / "ui" / "license_hud.lua"
        self.assertTrue(hud_path.is_file(), "Missing license_hud.lua")
        hud_code = hud_path.read_text(encoding="utf-8")
        for req in [
            "GTLicenseHUD.STATE",
            "GTLicenseHUD.init",
            "GTLicenseHUD.reset",
            "GTLicenseHUD.update",
            "GTLicenseHUD.draw",
            "GTLicenseHUD.drawHUD",
            "GTLicenseHUD.evaluateMedal",
            "ui.beginTransparentWindow",
            "ui.endTransparentWindow",
            "drawStopwatchCluster",
            "drawCountdown",
            "drawDisqualifiedBanner",
            "drawResultsScreen",
            "DISQUALIFIED",
            "START!",
        ]:
            self.assertIn(req, hud_code, f"license_hud.lua missing requirement: {req}")

        # 2. render_gates.lua
        render_path = REPO_ROOT / "lua" / "ui" / "render_gates.lua"
        self.assertTrue(render_path.is_file(), "Missing render_gates.lua")
        render_code = render_path.read_text(encoding="utf-8")
        for req in [
            "render.drawRibbon",
            "render.polyline",
            "GTRenderGates.init",
            "GTRenderGates.draw3D",
            "GTRenderGates.drawStartGate",
            "GTRenderGates.drawFinishGate",
            "GTRenderGates.drawStopBox",
            "GTRenderGates.drawGuideLine",
            "computeStopBoxCorners",
        ]:
            self.assertIn(req, render_code, f"render_gates.lua missing requirement: {req}")

        # 3. audio_manager.lua
        audio_path = REPO_ROOT / "lua" / "ui" / "audio_manager.lua"
        self.assertTrue(audio_path.is_file(), "Missing audio_manager.lua")
        audio_code = audio_path.read_text(encoding="utf-8")
        for req in [
            "GTAudioManager.SOUNDS",
            "GTAudioManager.init",
            "GTAudioManager.reset",
            "GTAudioManager.playCountdownBeep",
            "GTAudioManager.playCountdownGo",
            "GTAudioManager.playFailBuzzer",
            "GTAudioManager.playPassFanfare",
            "GTAudioManager.playGoldFanfare",
            "GTAudioManager.update",
            "ui.playSound",
            "countdown_beep.wav",
            "countdown_go.wav",
            "fail_buzzer.wav",
            "pass_fanfare.wav",
            "gold_fanfare.wav",
        ]:
            self.assertIn(req, audio_code, f"audio_manager.lua missing requirement: {req}")

    def test_ui_screens_modular_contracts(self):
        """Verifies modular widget contracts in lua/ui/screens and common."""
        screens_dir = REPO_ROOT / "lua" / "ui" / "screens"
        self.assertTrue((screens_dir / "timer_widget.lua").is_file())
        self.assertFalse((screens_dir / "gt_banner_widget.lua").exists())
        self.assertFalse((screens_dir / "gt_ghost_widget.lua").exists())
        self.assertTrue((screens_dir / "modal_overlays.lua").is_file())

        overlay_file = screens_dir / "modal_overlays.lua"
        overlay_code = overlay_file.read_text(encoding="utf-8")
        self.assertIn("RESTART (R)", overlay_code)
        self.assertIn("EXIT (ESC)", overlay_code)
        self.assertNotIn("NEXT EVENT", overlay_code)

        theme_file = REPO_ROOT / "lua" / "ui" / "common" / "ui_theme.lua"
        self.assertTrue(theme_file.is_file())
        theme_code = theme_file.read_text(encoding="utf-8")
        for req in ["GTTheme.COLORS", "GTTheme.formatTime", "GTTheme.formatDelta", "GTTheme.evaluateMedal", "GTTheme.getTargetDisplay"]:
            self.assertIn(req, theme_code)

    def test_ui_app_structure(self):
        """Verifies integrity of AC Lua App directory apps/lua/gt_license/."""
        app_dir = REPO_ROOT / "apps" / "lua" / "gt_license"
        self.assertTrue(app_dir.is_dir(), "apps/lua/gt_license directory does not exist")

        # Manifest
        manifest_path = app_dir / "manifest.ini"
        self.assertTrue(manifest_path.is_file(), "manifest.ini missing in gt_license app")
        manifest_text = manifest_path.read_text(encoding="utf-8")
        for req in [
            "[ABOUT]",
            "NAME = GT License HUD",
            "[WINDOW_...]",
            "ID = config",
            "FUNCTION_MAIN = configHUD",
            "ID = timer",
            "FUNCTION_MAIN = timerHUD",
        ]:
            self.assertIn(req, manifest_text)
        self.assertNotIn("ID = banner", manifest_text)
        self.assertNotIn("ID = ghost", manifest_text)

        # Screens
        screens_dir = app_dir / "screens"
        self.assertTrue(screens_dir.is_dir(), "screens directory missing in gt_license app")
        required_screens = [
            "timer_screen.lua",
            "config_screen.lua",
            "settings.lua",
            "shared_state.lua",
            "theme.lua",
        ]
        for s in required_screens:
            self.assertTrue((screens_dir / s).is_file(), f"Missing app screen: {s}")
        self.assertFalse((screens_dir / "banner_screen.lua").exists())
        self.assertFalse((screens_dir / "ghost_screen.lua").exists())

        # Icons
        icons_dir = app_dir / "icons"
        self.assertTrue(icons_dir.is_dir(), "icons directory missing in gt_license app")
        for icon in ["timer.png", "ghost.png", "settings.png"]:
            p = icons_dir / icon
            self.assertTrue(p.is_file(), f"Missing icon: {icon}")
            with Image.open(str(p)) as im:
                self.assertEqual(im.format, "PNG")
                self.assertEqual(im.size, (128, 128))
        self.assertFalse((icons_dir / "banner.png").exists())


if __name__ == "__main__":
    unittest.main()


