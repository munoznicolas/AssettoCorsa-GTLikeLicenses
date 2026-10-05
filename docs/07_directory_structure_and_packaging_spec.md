# Directory Structure & Packaging Specification

## 1. Overview

This document specifies the complete file and directory topology for the **Assetto Corsa GT-Like Licenses Mod**. It defines three distinct topologies:
1. **Repository Source Topology**: The structure of this development repository.
2. **Assetto Corsa Runtime Deployment Topology**: The exact locations where mod files are installed inside the Assetto Corsa root directory (`D:\SteamLibrary\steamapps\common\assettocorsa`).
3. **Content Manager (CM) Distribution Package Topology**: The format of the downloadable release `.zip` archive for one-click drag-and-drop installation via Content Manager.

---

## 2. Development Repository Topology

This is the file tree maintained in the Git repository:

```
d:\Repositories\AssettoCorsa-GTLikeLicenses\
├── .git/                                   # Git revision control database
├── docs/                                   # Architectural & design documentation
│   ├── 01_gran_turismo_licenses_reference.md
│   ├── 02_assetto_corsa_modding_capabilities.md
│   ├── 03_kunos_official_resources_catalog.md
│   ├── 04_kunos_licenses_proposal.md
│   ├── 05_ai_agent_development_blueprint.md
│   ├── 06_multi_agent_parallel_strategy.md
│   └── 07_directory_structure_and_packaging_spec.md
│
├── schema/                                 # Machine-readable validation contracts
│   ├── test_definition.schema.json         # JSON Schema for all 58 test definitions
│   └── career_manifest.schema.json         # JSON Schema for series metadata
│
├── tools/                                  # Automation, calibration & build scripts
│   ├── extract_spline_coords.py            # Python extractor for AC .ai spline files
│   ├── validate_curriculum.py              # Repository linter & test validator
│   ├── build_cm_package.py                 # Bundles source into Content Manager zip
│   └── test_calibration_tool.py            # Interactive developer calibration script
│
├── lua/                                    # Custom Shaders Patch (CSP) Lua Source
│   ├── engine/                             # Core simulation & lifecycle engine
│   │   ├── gt_license_engine.lua           # Master Scenario entry point
│   │   ├── gt_physics_hooks.lua            # Rolling velocity & teleportation
│   │   ├── gt_adjudicator.lua              # Off-track, collision & stop-box tripwires
│   │   └── gt_session_reset.lua            # In-memory instant reset controller
│   │
│   └── ui/                                 # Vector HUD, 3D Rendering & Audio
│       ├── gt_license_hud.lua              # GT-style canvas vector HUD & banners
│       ├── gt_render_gates.lua             # 3D ribbons for start/finish & apex lines
│       └── gt_audio_manager.lua            # Sound event player (beeps, buzzers, jingles)
│
├── assets/                                 # Media assets & UI artwork
│   ├── audio/                              # Sound FX (WAV / OGG / FMOD banks)
│   │   ├── countdown_beep.wav              # 3-2-1 countdown cue
│   │   ├── countdown_go.wav                # High pitch GO chime
│   │   ├── fail_buzzer.wav                 # Off-track / barrier contact fail sound
│   │   ├── pass_fanfare.wav                # Test passed fanfare
│   │   └── gold_fanfare.wav                # Gold medal victory jingle
│   │
│   ├── textures/                           # Vector textures & icons
│   │   ├── medal_gold.png
│   │   ├── medal_silver.png
│   │   ├── medal_bronze.png
│   │   ├── ribbon_start.png
│   │   └── ribbon_finish.png
│   │
│   └── career_ui/                          # Content Manager series thumbnail previews
│       ├── series_b_badge.png
│       ├── series_a_badge.png
│       ├── series_ib_badge.png
│       ├── series_ia_badge.png
│       └── series_s_badge.png
│
├── content/                                # Declarative Mod Content
│   ├── tests/                              # The 58 Test Data Definitions (JSON)
│   │   ├── national_b/                     # Tests B-01 to B-12
│   │   │   ├── test_b01.json
│   │   │   └── ...
│   │   ├── national_a/                     # Tests A-01 to A-12
│   │   │   ├── test_a01.json
│   │   │   └── ...
│   │   ├── international_b/                # Tests IB-01 to IB-12
│   │   │   ├── test_ib01.json
│   │   │   └── ...
│   │   ├── international_a/                # Tests IA-01 to IA-12
│   │   │   ├── test_ia01.json
│   │   │   └── ...
│   │   └── super_license/                  # Tests S-01 to S-10
│   │       ├── test_s01.json
│   │       └── ...
│   │
│   └── career/                             # Content Manager Career Package Files
│       ├── series_gt_b/                    # National B Series folder
│       │   ├── series.ini                  # Series config & requirements
│       │   ├── preview.png                 # CM Series card image
│       │   ├── event1/                     # Event 1 folder
│       │   │   └── event.ini
│       │   └── ...
│       ├── series_gt_a/                    # REQUIRES=GT_B
│       ├── series_gt_ib/                   # REQUIRES=GT_A
│       ├── series_gt_ia/                   # REQUIRES=GT_IB
│       └── series_gt_s/                    # REQUIRES=GT_IA
│
└── README.md                               # Root project overview & navigation
```

---

## 3. Assetto Corsa Runtime Deployment Topology

When the mod is installed into the user's Assetto Corsa directory (`<AC_ROOT>`), the files map to the following locations:

```
<AC_ROOT>/ (e.g. D:\SteamLibrary\steamapps\common\assettocorsa\)
│
├── extension/
│   └── lua/
│       └── new-modes/
│           └── gt-license/                         # CSP New-Mode Scenario Hook
│               ├── manifest.ini                    # Mode declaration for CSP
│               ├── scenario.lua                    # Entry point pointing to engine
│               ├── engine/
│               │   ├── gt_license_engine.lua
│               │   ├── gt_physics_hooks.lua
│               │   ├── gt_adjudicator.lua
│               │   └── gt_session_reset.lua
│               ├── ui/
│               │   ├── gt_license_hud.lua
│               │   ├── gt_render_gates.lua
│               │   └── gt_audio_manager.lua
│               ├── data/
│               │   └── tests/                      # All 58 test JSON configs
│               │       ├── national_b/
│               │       ├── national_a/
│               │       ├── international_b/
│               │       ├── international_a/
│               │       └── super_license/
│               └── assets/
│                   ├── audio/                      # Audio SFX
│                   └── textures/                   # Ribbons & medals
│
└── content/
    └── career/                                     # Content Manager Custom Career Series
        ├── series_gt_license_b/
        │   ├── series.ini
        │   ├── preview.png
        │   ├── event1/event.ini
        │   └── ... (event1 through event12)
        ├── series_gt_license_a/
        │   ├── series.ini                          # REQUIRES=GT_LIC_B
        │   ├── preview.png
        │   └── ... (event1 through event12)
        ├── series_gt_license_ib/
        │   ├── series.ini                          # REQUIRES=GT_LIC_A
        │   └── ...
        ├── series_gt_license_ia/
        │   ├── series.ini                          # REQUIRES=GT_LIC_IB
        │   └── ...
        └── series_gt_license_s/
            ├── series.ini                          # REQUIRES=GT_LIC_IA
            └── ... (event1 through event10)
```

---

## 4. Content Manager (CM) Distribution Package Topology

Content Manager supports automated installation when a `.zip` archive follows AC root-relative folder paths. The distributed archive is structured as follows:

### Archive Name: `AssettoCorsa_GT_Licenses_v1.0.zip`

```
AssettoCorsa_GT_Licenses_v1.0.zip
│
├── extension/
│   └── lua/
│       └── new-modes/
│           └── gt-license/
│               ├── manifest.ini
│               ├── scenario.lua
│               ├── engine/
│               ├── ui/
│               ├── data/
│               └── assets/
│
└── content/
    └── career/
        ├── series_gt_license_b/
        ├── series_gt_license_a/
        ├── series_gt_license_ib/
        ├── series_gt_license_ia/
        └── series_gt_license_s/
```

### Installation Behavior:
When a user drags `AssettoCorsa_GT_Licenses_v1.0.zip` into Content Manager:
1. Content Manager detects both `extension/lua/new-modes/` and `content/career/`.
2. It prompts: *"Install Custom Game Mode & Career Series: Gran Turismo Licenses"*.
3. Upon clicking **Install**, CM extracts the files directly to the respective game paths.
4. The custom licenses immediately appear under **Content Manager $\rightarrow$ Career $\rightarrow$ Gran Turismo Licenses**.

---

## 5. File Naming Conventions & Formats

To ensure automated tools and AI subagents parse data without exceptions, all files adhere to strict naming conventions:

### 5.1 Test Definition Files
* **Path**: `content/tests/<tier>/test_<tier_code><number>.json`
* **Format**: Pure UTF-8 JSON conforming to `test_definition.schema.json`.
* **Examples**:
  * `test_b01.json` through `test_b12.json`
  * `test_a01.json` through `test_a12.json`
  * `test_ib01.json` through `test_ib12.json`
  * `test_ia01.json` through `test_ia12.json`
  * `test_s01.json` through `test_s10.json`

### 5.2 Content Manager Career Files
* **Series Identifier**: Unique code defined in `series.ini`:
  * `CODE=GT_LIC_B`
  * `CODE=GT_LIC_A` (with `REQUIRES=GT_LIC_B`)
  * `CODE=GT_LIC_IB` (with `REQUIRES=GT_LIC_A`)
  * `CODE=GT_LIC_IA` (with `REQUIRES=GT_LIC_IB`)
  * `CODE=GT_LIC_S` (with `REQUIRES=GT_LIC_IA`)
* **Event Folder Names**: `event1`, `event2`, ..., `event12` (lowercase, sequential numbers).
* **Configuration File**: `event.ini` inside each event folder.
* **Preview Artwork**:
  * `preview.png`: $1920 \times 1080$ or $1024 \times 576$ PNG for series banners.

### 5.3 Audio Files
* **Format**: 16-bit PCM WAV or OGG Vorbis, $44.1\text{ kHz}$ Stereo.
* **Max Latency**: Uncompressed WAV preferred for countdown beeps and fail buzzers to ensure zero playback latency.

---

## 6. Subagent Directory Ownership & Write Boundaries

Under the multi-agent parallelization model, each subagent is granted exclusive write access to specific subtrees:

| Subagent Role | Exclusive Write Paths | Read-Only Access Paths |
| :--- | :--- | :--- |
| **Tooling Specialist** | `tools/` | `schema/`, `<AC_ROOT>/` |
| **Engine Specialist** | `lua/engine/` | `schema/`, `tools/` |
| **HUD & Audio Specialist**| `lua/ui/`, `assets/` | `schema/` |
| **Author: National B** | `content/tests/national_b/` | `tools/`, `schema/`, `<AC_ROOT>/` |
| **Author: National A** | `content/tests/national_a/` | `tools/`, `schema/`, `<AC_ROOT>/` |
| **Author: Internat. B** | `content/tests/international_b/`| `tools/`, `schema/`, `<AC_ROOT>/` |
| **Author: Internat. A** | `content/tests/international_a/`| `tools/`, `schema/`, `<AC_ROOT>/` |
| **Author: Super Lic.** | `content/tests/super_license/` | `tools/`, `schema/`, `<AC_ROOT>/` |
| **Packaging Specialist** | `content/career/` | `content/tests/` |
| **QA Specialist** | `release/` | Repository-wide |
