# Content Manager Career Mode Integration (`content/career/`)

## Overview
Stores the 5 career series packages recognized by Content Manager.

---

## Structure
Each series folder contains:
- `series.ini`: Series code, name, description, prerequisites (`REQUIRES`), and goal requirements.
- `preview.png`: High-resolution tier badge banner displayed in Content Manager Career selector.
- `event1/event.ini` .. `event12/event.ini`: Individual test event configurations containing:
  - `[EVENT]`: Name & lesson objective description.
  - `[RACE]`: Track, car, penalties, and `__CM_CUSTOM_MODE=gt-license`.
  - `[CONDITION_0..2]`: Bronze, Silver, Gold target times in milliseconds.

## Progression Chain
$$\text{National B} \longrightarrow \text{National A} \longrightarrow \text{International B} \longrightarrow \text{International A} \longrightarrow \text{Super License}$$

