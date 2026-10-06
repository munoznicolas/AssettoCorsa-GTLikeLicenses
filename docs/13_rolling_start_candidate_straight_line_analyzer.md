# Document 13: Rolling Start Candidate Straight-Line Analyzer

## 1. Overview & Problem Definition

In Assetto Corsa Gran Turismo-style license tests, rolling starts require handing vehicle control over to the player at highway speeds (e.g. 70 to 120 km/h) precisely when the countdown reaches **"GO!"**.

If a rolling start countdown occurs in a turn or curved section:
1. The native AI autopilot must hold a non-zero steering angle.
2. The vehicle is under lateral cornering load and lateral tire slip.
3. At the instant of handover, the player's physical steering wheel is likely centered at $0^\circ$, causing an instant divergence from the AI's line, sudden weight transfer snap, or immediate spin.

To ensure **100% fair, predictable handovers**, rolling starts must be placed on track segments where the official AI spline travels in **almost a straight line**, allowing the player to begin with their steering wheel centered at $0^\circ$.

---

## 2. Kinematic Bicycle Model & Deviation Parameter

Assetto Corsa's binary AI splines (`fast_lane.ai`) record the horizontal curve radius $R$ (in meters) for each waypoint. The tool translates track curvature into physical steering wheel deflection angle:

$$\delta_{\text{road}} = \arctan\left(\frac{L}{R}\right) \approx \frac{L}{R} \quad \text{(radians)}$$

$$\delta_{\text{wheel}} = \delta_{\text{road}} \times r_{\text{steer}} \times \left(\frac{180^\circ}{\pi}\right) \quad \text{(degrees)}$$

### Standard Parameters:
- **Vehicle Wheelbase ($L$)**: $2.5\,\text{m}$ (representing common sports cars: Mazda Miata, Toyota AE86, Alfa Giulietta).
- **Steering Rack Ratio ($r_{\text{steer}}$)**: $14.5:1$.
- **Main Deviation Parameter ($\delta_{\max}$)**: Maximum allowable steering wheel deflection error from zero (default: $\pm 2.0^\circ$, adjustable in real time).

### Reference Table:
| Curvature Radius ($R$) | Physical Wheel Angle ($\delta_{\text{wheel}}$) | Classification |
| :--- | :--- | :--- |
| $> 10,000\,\text{m}$ | $< \pm 0.2^\circ$ | Dead straight |
| $2,500\,\text{m} - 10,000\,\text{m}$ | $\pm 0.2^\circ - \pm 0.8^\circ$ | High-speed straight |
| $1,000\,\text{m} - 2,500\,\text{m}$ | $\pm 0.8^\circ - \pm 2.1^\circ$ | Gentle straight / viable rolling zone |
| $500\,\text{m} - 1,000\,\text{m}$ | $\pm 2.1^\circ - \pm 4.2^\circ$ | Sweeper / gentle kink |
| $< 300\,\text{m}$ | $> \pm 7.0^\circ$ | Definite corner |

---

## 3. Tool Architecture

```
tools/
├── extract_spline_coords.py      # Binary Assetto Corsa AI spline reader
├── record_ai_telemetry.py        # 95% AI Telemetry Profiler (Shared memory 60Hz or spline calibrated)
├── track_straight_analyzer.py    # Kinematic straight detection & scoring engine with backward integration
└── rolling_start_mapper.py       # CLI runner & interactive HTML circuit mapper
```

### 3.1 Proficient 95% AI Telemetry Grounding
Rather than assuming an arbitrary user-chosen rolling speed, speed is grounded in the **exact speed of a proficient 95% AI driver** (`ai_level = 95`):
- **Dynamic Speed Profile**: Handover speed ($v_{\text{gate}}$), countdown spawn speed ($v_{\text{spawn}}$), engaged transmission gear, and engine RPM are evaluated directly from the 95% AI profile.
- **Backward Velocity Integration**: Run-up distance ($d_{\text{countdown}} = \int_0^{t_{\text{cd}}} v(t) dt$) and post-"GO!" reaction distance ($d_{\text{post\_go}} = \int_0^{t_{\text{margin}}} v(t) dt$) are computed by numerically integrating backward along the vehicle's true speed curve.
- **Non-Modifiable Speed Policy**: Speed is an authoritative property of the circuit sector and car, not a synthetic player slider.

### 3.2 Key Engineering Features:
1. **Circular Track Loop Wrap-Around**: Detects and merges straight sections that cross the start/finish line ($s = L_{\text{track}} \to s = 0$) into one continuous straight segment (e.g., Vallelunga and Monza main straights).
2. **Micro-Gap Bridging**: Merges discrete curb-hop spline noise ($\le 12\,\text{m}$) when heading is consistent.
3. **Circular Median Heading**: Uses robust waypoint forward vector statistics to prevent inverted coordinate glitch artifacts.
4. **Candidate Scoring**: Evaluates candidate locations based on straightness, run-up distance ($v \times t$), and post-"GO!" reaction margin before the next corner.

---

## 4. Usage Instructions

### 4.1 CLI Single Track Inspection
```powershell
python tools/rolling_start_mapper.py --track ks_vallelunga --layout club_circuit
```

### 4.2 Inspect All 27 Curriculum Tracks (Recommended)
Generates the self-contained interactive circuit map containing all 27 tracks used in the 58 license tests:
```powershell
python tools/rolling_start_mapper.py --curriculum --output-html output/curriculum_rolling_map.html
```

### 4.3 Batch Scan All 54 Official Kunos Configurations
```powershell
python tools/rolling_start_mapper.py --all-kunos --output-html output/kunos_rolling_starts_master.html --output-json output/kunos_rolling_candidates.json
```

### 4.4 Automatically Open in Web Browser
Add `--open` to view immediately:
```powershell
python tools/rolling_start_mapper.py --track monza --open
```

---

## 5. Live Interactive UI Controls

The generated HTML map (`output/curriculum_rolling_map.html`) features real-time client-side controls that update at 60 FPS without server roundtrips:

1. **Max Steering Wheel Error ($\delta$) Slider**: $\pm 0.5^\circ$ to $\pm 5.0^\circ$ (default: $\pm 2.0^\circ$).
2. **Min Straight Length Slider**: $20\,\text{m}$ to $300\,\text{m}$ (default: $60\,\text{m}$).
3. **Proficient 95% AI Grounding Card**: Displays vehicle model, AI skill level (95%), flying lap time, and cache source. Target speed, gear, and RPM are locked to ground truth.
4. **Countdown Duration Slider**: $1.0\,\text{s}$ to $5.0\,\text{s}$ (default: $3.0\,\text{s}$).
5. **Post-"GO!" Straight Time Slider**: $0.5\,\text{s}$ to $5.0\,\text{s}$ (default: $1.5\,\text{s}$). Measures the player's straight-line reaction time before the next corner.
6. **Track Selector Dropdown**: Switch between circuits instantly.
7. **Interactive SVG Map**:
   - Glowing emerald green straights vs dark gray curves.
   - Click any candidate card to pan/zoom, revealing the 🚗 Spawn Point, ⏱️ Dashed Countdown vector, and 🏁 Start Gate perpendicular line.
8. **Curriculum Snippet Generator**: Copy-paste ready JSON snippet matching `TEST_CATALOG` in `tools/generate_all_content.py`, complete with `speed`, `gear`, and `rpm`.

