# Developer Tooling & Verification Suite (`tools/`)

## Architecture Overview
The `tools/` directory contains all Python-based automation, procedural asset synthesis, track kinematics analysis, curriculum validation, headless simulation, in-engine launch testing, and the interactive License Test Designer Web UI.

Tooling is organized by feature domains into dedicated subpackages, with top-level CLI entry points for primary developer workflows:

```
tools/
├── content/                     # Curriculum catalog, generation, and validation
│   ├── catalog/                 # Modular test definitions by tier
│   ├── generator.py             # Content generator (tests & CM career series)
│   ├── validator.py             # Schema & geometry validator
│   ├── validation_rules.py      # Validation rules & reporting models
│   ├── simulator.py             # Headless 60Hz kinematic simulator
│   └── README.md
├── spline/                      # Spline decoding & rolling start circuit mapper
│   ├── models.py                # Shared spline & gate data models
│   ├── parser.py                # Binary fast_lane.ai reader
│   ├── straight_analyzer.py     # Kinematic steering angle analyzer
│   ├── circuit_mapper.py        # Interactive HTML circuit visualizer
│   ├── templates/               # Standalone interactive HTML/JS templates
│   └── README.md
├── telemetry/                   # AI telemetry recording & spline profiling
│   ├── profile.py               # Telemetry data models & spline calibration
│   ├── recorder.py              # Shared memory 60Hz telemetry logger
│   └── README.md
├── assets/                      # Media synthesis, map SVGs, & font inspection
│   ├── audio_generator.py       # 16-bit 44.1kHz PCM WAV procedural synthesizer
│   ├── texture_generator.py     # Ribbon & medal RGBA PNG generator
│   ├── create_app_icons.py      # HUD app icon generator
│   ├── font_inspector.py        # DirectWrite TTF font inspector
│   ├── track_svg_generator.py   # Top-down vector track SVG builder
│   ├── test_map_generator.py    # Per-test highlighted sector SVG builder
│   ├── preview_generator.py     # Zoomed 1024x576 career event preview builder
│   └── README.md
├── testing/                     # AC in-engine launch & simulation harness
│   ├── ac_launcher.py           # race.ini generator & acs.exe process orchestrator
│   ├── log_auditor.py           # Game log & crash signature auditor
│   ├── eval_loop.py             # Automated sync -> launch -> eval loop
│   ├── restart_telemetry.py     # In-engine session restart telemetry evaluator
│   ├── record_ai_times.py       # Automated AI lap/sector time recorder
│   ├── suite_runner.py          # Master multi-stage verification runner
│   └── README.md
├── deployment/                  # Sync, packaging & code quality
│   ├── sync.py                  # Live sync to AC installation directory
│   ├── packager.py              # Content Manager package builder
│   ├── api_auditor.py           # CSP Lua SDK symbol auditor
│   ├── lua_linter.py            # Lua block & bracket balance linter
│   ├── lua_syntax.py            # Lua syntax checker
│   └── README.md
├── web_ui/                      # Interactive License Test Designer Web UI
│   ├── server.py                # Local HTTP server & security middleware
│   ├── api_handlers.py          # REST API endpoints
│   ├── catalog_manager.py       # Catalog persistence & CRUD operations
│   ├── ac_discovery.py          # Track, layout, & car discovery
│   ├── physics_calculator.py    # Instant target & physics calculation
│   ├── runner.py                # Asynchronous job queue runner
│   └── static/                  # Frontend HTML/CSS/JS application
└── README.md                    # This master tooling index
```

---

## Canonical Developer Workflow
Use these top-level CLI entry points to develop and verify changes:

```powershell
# 1. Regenerate content (JSON tests + CM career series + previews/maps)
python tools/generate_all_content.py

# 2. Live sync to Assetto Corsa installation
python tools/sync_to_ac.py

# 3. Validate curriculum schema and gate geometry
python tools/validate_curriculum.py --all

# 4. Run headless 60Hz kinematic simulation
python tools/simulate_all_tests.py

# 5. Run full verification suite
python tools/run_full_validation_suite.py

# 6. Build Content Manager distribution package
python tools/build_cm_package.py --validate

# 7. Launch License Test Designer Web UI
python tools/designer.py
```
