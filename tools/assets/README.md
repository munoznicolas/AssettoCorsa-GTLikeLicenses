# Feature: Media Assets & Procedural Generators (`tools/assets/`)

## Overview
This subsystem manages and procedurally synthesizes audio sound effects, UI texture badges, 3D gate ribbons, track/sector SVG maps, career preview miniatures, and inspects TrueType font typography for Assetto Corsa Custom Shaders Patch (CSP) DirectWrite rendering.

---

## Directory & File Structure
```
tools/assets/
├── audio_generator.py           # Synthesizes 16-bit 44.1kHz PCM mono WAV files
├── texture_generator.py         # Renders medal icons and neon 3D gate ribbons
├── create_app_icons.py          # Generates 128x128 RGBA icons for the AC Lua App
├── font_inspector.py            # Analyzes TTF font family, weights, and PostScript names
├── track_svg_generator.py       # Builds top-down vector SVG maps from AI splines
├── test_map_generator.py        # Builds per-test sector SVG maps (docs/test_maps/)
├── preview_generator.py         # Renders 1024x576 career event previews (preview.png)
└── README.md                    # This reference guide
```

---

## Quick Command Usage
```powershell
# Re-synthesize audio assets
python -m tools.assets.audio_generator

# Re-render PNG textures
python -m tools.assets.texture_generator

# Inspect TTF fonts and PostScript names
python -m tools.assets.font_inspector

# Regenerate test sector SVG maps and career previews
python -m tools.assets.test_map_generator
python -m tools.assets.preview_generator
```
