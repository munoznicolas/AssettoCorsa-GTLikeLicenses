# Developer Tooling & Verification Suite (`tools/`)

## Architecture Overview
The `tools/` directory contains all Python-based automation, procedural asset synthesis, track kinematics analysis, curriculum validation, headless simulation, and in-engine launch testing.

Tooling is organized by feature domains into dedicated subpackages, with backward-compatible CLI forwarders preserved at the root.

```
tools/
├── content/                     # Curriculum catalog, generation, and validation
│   ├── catalog/                 # 58 modular test definitions by tier
│   ├── generator.py             # Content generator (tests & CM career series)
│   ├── validator.py             # Schema & geometry validator
│   ├── simulator.py             # Headless kinematic simulator
│   └── README.md
├── spline/                      # Spline decoding & rolling start circuit mapper
│   ├── parser.py                # Binary fast_lane.ai reader
│   ├── straight_analyzer.py     # Kinematic steering angle analyzer
│   ├── circuit_mapper.py        # Interactive HTML circuit visualizer
│   ├── templates/               # Standalone interactive HTML/JS templates
│   └── README.md
├── telemetry/                   # AI recording & ghost pacer trajectory engine
│   ├── recorder.py              # Shared memory 60Hz telemetry logger
│   ├── ghost_generator.py       # Gold ghost 2-pass kinematic trajectory builder
│   └── README.md
├── assets/                      # Media synthesis & font inspection
│   ├── audio_generator.py       # 16-bit 44.1kHz PCM WAV procedural synthesizer
│   ├── texture_generator.py     # Ribbon & medal RGBA PNG generator
│   ├── font_inspector.py        # DirectWrite TTF font inspector
│   └── README.md
├── testing/                     # AC in-engine launch & simulation harness
│   ├── ac_launcher.py           # race.ini generator & acs.exe process orchestrator
│   ├── eval_loop.py             # Automated test-and-eval loop
│   ├── suite_runner.py          # Master 7-stage verification runner
│   └── README.md
├── deployment/                  # Sync, packaging & code quality
│   ├── sync.py                  # Live sync to AC installation directory
│   ├── packager.py              # Content Manager package builder
│   ├── api_auditor.py           # CSP Lua SDK symbol auditor
│   ├── lua_linter.py            # Lua block & bracket balance linter
│   ├── lua_syntax.py            # Lua syntax checker
│   └── README.md
└── README.md                    # This master tooling index
```

---

## Canonical Developer Workflow
Always use these commands to develop and verify changes:

```powershell
# 1. Regenerate content (JSON tests + CM career series)
python tools/generate_all_content.py

# 2. Live sync to Assetto Corsa installation
python tools/sync_to_ac.py

# 3. Validate curriculum schema and gate geometry
python tools/validate_curriculum.py --all

# 4. Run headless 60Hz kinematic simulation (348 scenarios)
python tools/simulate_all_tests.py

# 5. Run full verification suite (all 7 stages)
python tools/run_full_validation_suite.py
```

