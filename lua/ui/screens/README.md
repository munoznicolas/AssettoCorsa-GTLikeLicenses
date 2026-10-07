# UI Screens & Widgets Subsystem (`lua/ui/screens/`)

## Overview

This directory contains modular screen widgets for both the CSP New Mode HUD and the movable Assetto Corsa Lua App (`gt_license`). Each module encapsulates independent DirectWrite/ImGui drawing logic.

## Module Catalog

| Script                                                                                                              | Module            | Description                                                                                          |
| :------------------------------------------------------------------------------------------------------------------ | :---------------- | :--------------------------------------------------------------------------------------------------- |
| [`gt_timer_widget.lua`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/lua/ui/screens/gt_timer_widget.lua)     | `GTTimerWidget`   | Digital stopwatch typography and live medal target delta comparison (`GOLD +0.320`, `LIMIT -0.150`). |
| [`gt_ghost_widget.lua`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/lua/ui/screens/gt_ghost_widget.lua)     | `GTGhostWidget`   | Ghost / Pace Car delta readout and hotkey OSD notification banner.                                   |
| [`gt_modal_overlays.lua`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/lua/ui/screens/gt_modal_overlays.lua) | `GTModalOverlays` | Fullscreen event overlays (3-2-1-START countdown, crimson Disqualification banner, Results card).    |
