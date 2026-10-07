# Feature: Deployment, Build & Quality Assurance (`tools/deployment/`)

## Overview
This subsystem manages the synchronization of Lua scripts and game assets directly into the Assetto Corsa installation, packages distribution archives for Content Manager drag-and-drop installation, and performs static code analysis on Lua scripts and CSP SDK symbol usage.

---

## Directory & File Structure
```
tools/deployment/
├── sync.py                      # Live directory auto-sync tool to AC installation
├── packager.py                  # Release package builder (7z / zip) for Content Manager
├── api_auditor.py               # Audits Lua API calls against official CSP lib.lua SDK
├── lua_linter.py                # Bracket and control-flow static analysis linter
├── lua_syntax.py                # Regex syntax and string literal checker
└── README.md                    # This agent reference guide
```

---

## Deployment & Target Locations
When syncing to Assetto Corsa:
- Lua mode directory: `extension/lua/new-modes/gt-license/`
  - Engine scripts: `engine/*.lua`
  - UI scripts: `ui/*.lua`
  - Test JSONs: `data/tests/<tier>/*.json`
  - Assets & Fonts: `assets/...` and `fonts/*.ttf`
  - Scenario manifest: `manifest.ini`
  - Master entry point: `scenario.lua`
- Career series: `content/career/series_gt_license_<tier>/`

---

## Key Interfaces & Symbols

### `sync.py`
- `build_sync_mappings(repo_root, ac_root)`: Computes file-by-file source-to-destination mappings with mtime/size caching.

### `packager.py`
- `create_cm_archive(staging_dir, output_path)`: Creates structured 7z/ZIP file conforming to Content Manager specifications.
- `validate_build_artifacts(package_path)`: Verifies manifest and file presence inside release archive.

### `api_auditor.py`
- `load_sdk_symbols(sdk_path)`: Loads 1,166+ official CSP SDK API symbols from `lib.lua`.
- `scan_repo_lua_calls(repo_root)`: Identifies any calls to deprecated or unknown symbols.

### `lua_linter.py`
- `lint_lua(filepath)`: Verifies balanced block keywords (`if`, `function`, `for`, `do`, `end`) and parenthetical balance (`()`, `[]`, `{}`).

---

## Quick Command Usage
```powershell
# Synchronize repository directly to AC installation
python tools/sync_to_ac.py

# Audit all Lua API calls against CSP SDK
python tools/audit_csp_api.py

# Run Lua linter across all engine and UI modules
python tools/lint_lua.py

# Build Content Manager release package
python tools/build_cm_package.py
```

