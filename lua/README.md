# CSP Lua New Modes Architecture (`lua/`)

## Overview
Assetto Corsa GT-Like Licenses executes within the Custom Shaders Patch (CSP) **New Modes** subsystem under `extension/lua/new-modes/gt-license/`.

---

## Architecture Breakdown
```
lua/
├── engine/                      # Core simulation, physics, and adjudication
│   ├── license_engine.lua       # Master scenario coordinator
│   ├── engine_runtime.lua       # Frame update, HUD delegation, & lifecycle hooks
│   ├── config_loader.lua        # Dynamic test JSON & race.ini loader
│   ├── results.lua              # Results compilation & medal evaluation
│   ├── physics_hooks.lua        # Authoritative CSP physics integration
│   ├── rolling_start.lua        # Rolling start & countdown controller
│   ├── adjudicator.lua          # Gate crossing, stop box, & track limits
│   ├── ai_coordinator.lua       # AI autopilot coordinator
│   ├── session_reset.lua        # Session restart & debounce
│   ├── shared_state.lua         # Inter-process shared state broadcaster
│   ├── telemetry_logger.lua     # In-engine evaluation telemetry logger
│   ├── utils.lua                # Math, vector, and CSP helpers
│   └── README.md
├── ui/                          # Presentation & 3D rendering
│   ├── license_hud.lua          # 2D HUD, stopwatch, banners, & results modal
│   ├── render_gates.lua         # 3D ribbons, stop box, & gate markers
│   ├── audio_manager.lua        # Sound effects & fanfares
│   ├── common/                  # Shared theme & typography
│   ├── screens/                 # Modular widgets & modal overlays
│   └── README.md
└── README.md                    # This runtime overview
```

---

## Lifecycle Hooks Invoked by CSP
CSP New Modes calls the following 4 lifecycle hooks in `scenario.lua`:
- `script.prepare(dt)`: Session preparation stage.
- `script.update(dt)`: Primary 60 Hz physics update loop (calls `engine:update(dt)`).
- `script.draw3D(dt)`: 3D world rendering (calls `engine:draw3D(dt)` $\rightarrow$ gates and stop boxes).
- `script.drawUI()`: 2D ImGui/DWrite rendering (calls `engine:drawUI()` $\rightarrow$ HUD and results).

> [!IMPORTANT]
> CSP New Modes **never calls `script.init()`**. Top-level engines are instantiated at require time.
