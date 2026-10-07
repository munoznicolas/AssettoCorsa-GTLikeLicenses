# Assetto Corsa UI Apps (`apps/`)

## Overview

This directory houses native Assetto Corsa UI applications implemented via Custom Shaders Patch (CSP) Lua App subsystem. Unlike New Mode scripts (which control the session lifecycle and 3D world hooks), Lua Apps appear in Assetto Corsa's in-game taskbar and can be dragged, customized, and positioned freely on screen by the user.

## App Catalog

| Application        | Path                                                                                                       | Description                                                                                     |
| :----------------- | :--------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------- |
| **GT License HUD** | [`apps/lua/gt_license`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/apps/lua/gt_license/README.md) | Gran Turismo 7 replica HUD widgets (Stopwatch, Target Deltas, Top Banner, Ghost Delta, Config). |

## Integration with CSP New Modes

- Modes declare their companion app via `[TWEAKS] ASSOCIATED_APPS = gt_license` in `manifest.ini`.
- High-speed zero-copy memory blocks (`ac.connect`) synchronize live telemetry between simulation engine and UI App.
