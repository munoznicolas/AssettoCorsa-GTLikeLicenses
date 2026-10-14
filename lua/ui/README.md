# CSP Lua UI & 3D Rendering Subsystem (`lua/ui/`)

## Overview
This subsystem handles all user-facing presentation inside Assetto Corsa via Custom Shaders Patch (CSP) `script.drawUI()` and `script.draw3D()` lifecycle hooks.

---

## Directory & File Structure
```
lua/ui/
├── license_hud.lua           # Master 2D ImGui/DWrite HUD, countdown, stopwatch, & results
├── render_gates.lua          # 3D ribbons for finish gates and stop box grid
├── audio_manager.lua         # Sound effects (beeps, buzzers, and brass victory fanfares)
├── common/
│   └── ui_theme.lua          # DirectWrite typography, paired outline fonts, and color palette
├── screens/
│   ├── timer_widget.lua      # Digital clock and live target delta widget
│   └── modal_overlays.lua    # Countdown, Disqualified banner, and Results screen
└── README.md                 # This agent reference guide
```

---

## UI Components & Rendering Hooks

### 1. `license_hud.lua` (`script.drawUI()`)
- **Stopwatch Cluster**: digital clock (`MM'SS.mmm`) tracking active run time since GO!
- **3-2-1-GO Graphics**: large centered countdown with sound synchronization.
- **Disqualification Banner**: red header with specific violation reason (e.g. `OFF-TRACK (3+ WHEELS OUTSIDE)`).
- **Results Modal**: final time, medal award graphic (Gold/Silver/Bronze), delta breakdown, and Retry/Exit buttons.

### 2. `render_gates.lua` (`script.draw3D()`)
- Renders 3D chequered finish arch ribbons via CSP `render.drawRibbon()` and `render.polyline()`.
- Renders 3D rectangular stop box outline on road surface with live OBB containment status.

### 3. `audio_manager.lua` (`ui.playSound()`)
- Procedural audio cues synchronized to countdown ticks and completion status.

