# GT License HUD - Assetto Corsa Lua UI App

## Overview

`gt_license` is an Assetto Corsa Lua UI App providing customizable, movable Gran Turismo 7 replica HUD widgets for the GT-Like Licenses mod. It integrates natively with Assetto Corsa's app sidebar and window management system.

## Directory Structure

```
apps/lua/gt_license/
├── manifest.ini             # AC App manifest declaring all window IDs and callbacks
├── gt_license.lua           # Master app entry point
├── icon.png                 # Main app icon (128x128 RGBA)
├── icons/                   # Per-window sidebar icons (128x128 RGBA)
│   ├── timer.png            # Stopwatch window icon
│   ├── speedo.png           # Speedometer window icon
│   └── settings.png         # Configuration dialog icon
├── screens/                 # Modular screen window scripts
│   ├── theme.lua            # GT7 DirectWrite typography & color palettes
│   ├── settings.lua         # Persistent configuration manager (settings.ini)
│   ├── shared_state.lua     # Zero-copy inter-process shared state client
│   ├── timer_screen.lua     # Callback: script.timerHUD(dt)
│   ├── speedo_screen.lua    # Callback: script.speedoHUD(dt)
│   └── config_screen.lua    # Callback: script.configHUD(dt)
└── settings/                # Settings INI files
    ├── default_settings.ini # Factory defaults
    └── settings.ini         # User customized configuration
```

*(Note: TrueType fonts from `assets/fonts/` are bundled into `apps/lua/gt_license/fonts/` automatically during `sync_to_ac.py` and `build_cm_package.py`.)*

## Movable Windows & Individual Scaling

- **Native Movable Windows**:
  Each widget is rendered inside an independent native AC UI window. The user can drag and place each element anywhere on screen, and lock them in place with the window title bar's pin/lock icon.
- **Individual Widget Scaling**:
  Each widget features a resize handle in the bottom-right corner. Dragging the handle scales the widget's fonts, badges, and layout individually.
- **Authentic Gran Turismo Defaults**:
  Widgets initialize at default positions replicating Gran Turismo 7.

## Inter-Process Communication

The UI App communicates with the CSP New Mode simulation engine (`extension/lua/new-modes/gt-license/`) using CSP's high-speed typed memory block (`ac.connect` with key `app.GTLicense.sharedState`). When the app is active, it signals `uiAppActive = true`, allowing the New Mode engine to delegate in-race widget rendering to the movable app while retaining fullscreen event modals (Countdown, Disqualification, Results).
