# CSP Lua UI & 3D Rendering Subsystem (`lua/ui/`)

## Overview
This subsystem handles all user-facing presentation inside Assetto Corsa via Custom Shaders Patch (CSP) `script.drawUI()` and `script.draw3D()` lifecycle hooks.

---

## Directory & File Structure
```
lua/ui/
├── gt_license_hud.lua           # Master 2D ImGui/DWrite HUD, countdown, stopwatch, & results
├── gt_render_gates.lua          # 3D ribbons for start/finish gates and stop box grid
├── gt_render_ghost.lua          # 3D semi-transparent ghost vehicle ribbon and trajectory line
├── gt_audio_manager.lua         # Sound effects (beeps, buzzers, and brass victory fanfares)
└── README.md                    # This agent reference guide
```

---

## UI Components & Rendering Hooks

### 1. `gt_license_hud.lua` (`script.drawUI()`)
- **Stopwatch Cluster**: digital clock (`MM:SS.mmm`) tracking active run time since GO!
- **Ghost Delta & OSD**: real-time lead/lag distance widget and hotkey display (`[G] Toggle Ghost`, `[O] Cycle Mode`).
- **3-2-1-GO Graphics**: large centered countdown with sound synchronization.
- **Disqualification Banner**: red header with specific violation reason (e.g. `OFF-TRACK (3+ WHEELS OUTSIDE)`).
- **Results Modal**: final time, medal award graphic (Gold/Silver/Bronze), delta breakdown, and Retry/Next buttons.

### 2. `gt_render_gates.lua` (`script.draw3D()`)
- Renders 3D start/finish arch ribbons via CSP `render.drawRibbon()` and `render.polyline()`.
- Renders 3D rectangular stop box outline on road surface.

### 3. `gt_render_ghost.lua` (`script.draw3D()`)
- Visualizes ghost trajectory ribbon with brake zone highlighting (red when braking, gold when accelerating).

### 4. `gt_audio_manager.lua` (`ui.playSound()`)
- Procedural audio cues synchronized to countdown ticks and completion status.

