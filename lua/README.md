# CSP Lua New Modes Architecture (`lua/`)

## Overview
Assetto Corsa GT-Like Licenses executes within the Custom Shaders Patch (CSP) **New Modes** subsystem under `extension/lua/new-modes/gt-license/`.

---

## Architecture Breakdown
```
lua/
├── engine/                      # Core simulation, physics, and adjudication
│   ├── gt_license_engine.lua    # Master scenario coordinator
│   ├── gt_config_loader.lua     # Dynamic test JSON & race.ini loader
│   ├── gt_results.lua           # Results compilation & medal evaluation
│   ├── gt_physics_hooks.lua     # Authoritative CSP physics integration
│   ├── gt_adjudicator.lua       # Gate crossing & track limits
│   ├── gt_ghost_manager.lua     # Ghost telemetry playback
│   ├── gt_ai_coordinator.lua    # AI autopilot coordinator
│   ├── gt_session_reset.lua     # Session restart & debounce
│   ├── gt_utils.lua             # Math, vector, and CSP helpers
│   └── README.md
├── ui/                          # Presentation & 3D rendering
│   ├── gt_license_hud.lua       # 2D HUD, stopwatch, banners, & results modal
│   ├── gt_render_gates.lua      # 3D ribbons & gate markers
│   ├── gt_render_ghost.lua      # 3D ghost ribbon & pacer visualization
│   ├── gt_audio_manager.lua     # Sound effects & fanfares
│   └── README.md
└── README.md                    # This runtime overview
```

---

## Lifecycle Hooks Invoked by CSP
CSP New Modes calls the following 4 lifecycle hooks in `scenario.lua`:
- `script.prepare(dt)`: Session preparation stage.
- `script.update(dt)`: Primary 60 Hz physics update loop (calls `engine:update(dt)`).
- `script.draw3D(dt)`: 3D world rendering (calls `engine:draw3D(dt)` $\rightarrow$ gates and ghost ribbons).
- `script.drawUI()`: 2D ImGui/DWrite rendering (calls `engine:drawUI()` $\rightarrow$ HUD and results).

> [!IMPORTANT]
> CSP New Modes **never calls `script.init()`**. Top-level engines are instantiated at require time.

