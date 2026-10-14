# UI Screens & Widgets Subsystem (`lua/ui/screens/`)

## Overview

This directory contains modular screen widgets for both the CSP New Mode HUD and the movable Assetto Corsa Lua App (`gt_license`). Each module encapsulates independent DirectWrite/ImGui drawing logic.

## Module Catalog

| Script                                                                                                          | Module            | Description                                                                                          |
| :-------------------------------------------------------------------------------------------------------------- | :---------------- | :--------------------------------------------------------------------------------------------------- |
| [`timer_widget.lua`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/lua/ui/screens/timer_widget.lua)       | `GTTimerWidget`   | High-precision digital stopwatch typography (`TIME MM'SS.mmm`) and live target delta indicator.     |
| [`modal_overlays.lua`](file:///d:/Repositories/AssettoCorsa-GTLikeLicenses/lua/ui/screens/modal_overlays.lua)   | `GTModalOverlays` | Fullscreen event overlays (3-2-1-START countdown, crimson Disqualification banner, Results card).    |
