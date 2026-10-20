# UI Screens & Widgets Subsystem (`lua/ui/screens/`)

## Overview

This directory contains modular screen widgets for the CSP New Mode HUD. Each module encapsulates independent DirectWrite/ImGui drawing logic.

## Module Catalog

| Script                                       | Module            | Description                                                                                          |
| :------------------------------------------- | :---------------- | :--------------------------------------------------------------------------------------------------- |
| [`timer_widget.lua`](timer_widget.lua)       | `GTTimerWidget`   | High-precision digital stopwatch typography (`TIME MM'SS.mmm`) and live target delta indicator.     |
| [`modal_overlays.lua`](modal_overlays.lua)   | `GTModalOverlays` | Fullscreen event overlays (3-2-1-START countdown, crimson Disqualification banner, Results card).    |
