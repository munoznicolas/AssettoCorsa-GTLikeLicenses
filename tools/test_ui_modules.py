"""
Unit Test & Integrity Suite for UI, 3D Rendering & Audio Layer
Validates lua/ui/ modules and assets/ directories.
"""

import os
import wave
from pathlib import Path
from PIL import Image

def test_audio_assets():
    audio_dir = Path("assets/audio")
    required_wavs = [
        "countdown_beep.wav",
        "countdown_go.wav",
        "fail_buzzer.wav",
        "pass_fanfare.wav",
        "gold_fanfare.wav",
    ]
    for wav_name in required_wavs:
        p = audio_dir / wav_name
        assert p.is_file(), f"Missing audio asset: {p}"
        with wave.open(str(p), "r") as wf:
            assert wf.getnchannels() in (1, 2), f"{wav_name}: invalid channels"
            assert wf.getsampwidth() == 2, f"{wav_name}: not 16-bit PCM"
            assert wf.getframerate() == 44100, f"{wav_name}: sample rate != 44100"
            duration = wf.getnframes() / wf.getframerate()
            assert duration > 0.05, f"{wav_name}: duration too short ({duration}s)"
    print("[OK] All 5 WAV audio assets are valid 16-bit 44.1kHz PCM files.")

def test_texture_assets():
    tex_dir = Path("assets/textures")
    required_pngs = [
        "medal_gold.png",
        "medal_silver.png",
        "medal_bronze.png",
        "ribbon_start.png",
        "ribbon_finish.png",
    ]
    for png_name in required_pngs:
        p = tex_dir / png_name
        assert p.is_file(), f"Missing texture asset: {p}"
        with Image.open(str(p)) as im:
            assert im.format == "PNG", f"{png_name}: not PNG"
            assert im.mode == "RGBA", f"{png_name}: not RGBA"
            w, h = im.size
            assert w >= 128 and h >= 64, f"{png_name}: dimensions too small ({w}x{h})"
    print("[OK] All 5 PNG texture assets are valid RGBA images.")

def test_lua_module_contracts():
    # 1. gt_license_hud.lua
    hud_path = Path("lua/ui/gt_license_hud.lua")
    assert hud_path.is_file(), "Missing gt_license_hud.lua"
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
        "drawSpeedIndicator",
        "drawCountdown",
        "drawDisqualifiedBanner",
        "drawResultsScreen",
        "DISQUALIFIED",
        "START!",
    ]:
        assert req in hud_code, f"gt_license_hud.lua missing requirement: {req}"
    print("[OK] gt_license_hud.lua satisfies all interface and rendering contracts.")

    # 2. gt_render_gates.lua
    render_path = Path("lua/ui/gt_render_gates.lua")
    assert render_path.is_file(), "Missing gt_render_gates.lua"
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
        assert req in render_code, f"gt_render_gates.lua missing requirement: {req}"
    print("[OK] gt_render_gates.lua satisfies all 3D ribbons & gate rendering contracts.")

    # 3. gt_audio_manager.lua
    audio_path = Path("lua/ui/gt_audio_manager.lua")
    assert audio_path.is_file(), "Missing gt_audio_manager.lua"
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
        assert req in audio_code, f"gt_audio_manager.lua missing requirement: {req}"
    print("[OK] gt_audio_manager.lua satisfies all audio triggering contracts.")

    # 4. gt_render_ghost.lua
    ghost_path = Path("lua/ui/gt_render_ghost.lua")
    assert ghost_path.is_file(), "Missing gt_render_ghost.lua"
    ghost_code = ghost_path.read_text(encoding="utf-8")
    for req in [
        "GTRenderGhost.render",
        "GTRenderGhost.reset",
        "COLOR_BRAKE_ON",
        "COLOR_PACER_GOLD",
        "COLOR_TRAIL_RIBBON",
        "draw3DLine",
    ]:
        assert req in ghost_code, f"gt_render_ghost.lua missing requirement: {req}"
    print("[OK] gt_render_ghost.lua satisfies all 3D hologram & pacer rendering contracts.")

def main():
    test_audio_assets()
    test_texture_assets()
    test_lua_module_contracts()
    print("\nALL UI LAYER TESTS AND VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
