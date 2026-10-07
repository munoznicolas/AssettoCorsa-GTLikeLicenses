# Feature: Media Assets & Procedural Generators (`tools/assets/`)

## Overview
This subsystem manages and procedurally synthesizes audio sound effects, UI texture badges, 3D gate ribbons, and inspects TrueType font typography for Assetto Corsa Custom Shaders Patch (CSP) DirectWrite rendering.

---

## Directory & File Structure
```
tools/assets/
├── audio_generator.py           # Synthesizes 16-bit 44.1kHz PCM mono WAV files
├── texture_generator.py         # Renders medal icons and neon 3D gate ribbons
├── font_inspector.py            # Analyzes TTF font family, weights, and PostScript names
└── README.md                    # This agent reference guide
```

---

## Asset Specifications

### Audio Assets (`assets/audio/`)
- Format: Pure 16-bit PCM WAV, 44,100 Hz, Mono
- Files:
  - `countdown_beep.wav`: 880 Hz beep with sharp attack (150ms)
  - `countdown_go.wav`: 1760 Hz high chime (400ms)
  - `fail_buzzer.wav`: 110 Hz / 116.5 Hz harsh acoustic dissonance (600ms)
  - `pass_fanfare.wav`: C5 $\rightarrow$ E5 $\rightarrow$ G5 $\rightarrow$ C6 brass triad (1.2s)
  - `gold_fanfare.wav`: Ascending celebratory arpeggio (2.0s)

### Textures & Ribbons (`assets/textures/`)
- Format: 32-bit RGBA PNG
- Files:
  - `medal_gold.png`, `medal_silver.png`, `medal_bronze.png`: $256 \times 256$ vector laurels
  - `ribbon_start.png`: $512 \times 128$ glowing neon cyan gradient
  - `ribbon_finish.png`: $512 \times 128$ chequered racing flag pattern

### Typography & Fonts (`assets/fonts/`)
- DirectWrite custom fonts loaded by CSP Lua:
  - `Polymath-Regular.ttf` / `Polymath-Bold.ttf`
  - `GranTurismo-Bold.ttf` / `GranTurismo-Italic.ttf`

---

## Quick Command Usage
```powershell
# Re-synthesize audio assets
python tools/generate_audio_assets.py

# Re-render PNG textures
python tools/generate_texture_assets.py

# Inspect TTF fonts and PostScript names
python tools/inspect_fonts.py
```

