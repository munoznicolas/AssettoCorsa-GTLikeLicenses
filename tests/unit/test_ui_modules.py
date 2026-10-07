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
        # 1. gt_license_hud.lua
        hud_path = REPO_ROOT / "lua" / "ui" / "gt_license_hud.lua"
        self.assertTrue(hud_path.is_file(), "Missing gt_license_hud.lua")
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
            "drawTopBanner",
            "drawStopwatchCluster",
            "drawGhostDelta",
            "drawCountdown",
            "drawDisqualifiedBanner",
            "drawResultsScreen",
            "DISQUALIFIED",
            "START!",
        ]:
            self.assertIn(req, hud_code, f"gt_license_hud.lua missing requirement: {req}")

        # 2. gt_render_gates.lua
        render_path = REPO_ROOT / "lua" / "ui" / "gt_render_gates.lua"
        self.assertTrue(render_path.is_file(), "Missing gt_render_gates.lua")
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
            self.assertIn(req, render_code, f"gt_render_gates.lua missing requirement: {req}")

        # 3. gt_audio_manager.lua
        audio_path = REPO_ROOT / "lua" / "ui" / "gt_audio_manager.lua"
        self.assertTrue(audio_path.is_file(), "Missing gt_audio_manager.lua")
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
            self.assertIn(req, audio_code, f"gt_audio_manager.lua missing requirement: {req}")

        # 4. gt_render_ghost.lua
        ghost_path = REPO_ROOT / "lua" / "ui" / "gt_render_ghost.lua"
        self.assertTrue(ghost_path.is_file(), "Missing gt_render_ghost.lua")
        ghost_code = ghost_path.read_text(encoding="utf-8")
        for req in [
            "GTRenderGhost.render",
            "GTRenderGhost.reset",
            "COLOR_BRAKE_ON",
            "COLOR_PACER_GOLD",
            "COLOR_TRAIL_RIBBON",
            "draw3DLine",
        ]:
            self.assertIn(req, ghost_code, f"gt_render_ghost.lua missing requirement: {req}")


if __name__ == "__main__":
    unittest.main()

