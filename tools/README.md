# SonarSniffer repo tools

**Single source of truth:** all library and pipeline code lives in `src/` at the repo root.
The desktop app (`desktop/src-tauri/`) is a thin Tauri shell only — never copy or edit mirrored Rust sources there.

## Before every commit / release

```powershell
.\tools\publish.ps1
```

This verifies the repo layout, builds CLI + desktop, stages Tauri sidecars, and runs regression smoke tests.

## Scripts

| Script | Purpose |
|--------|---------|
| `publish.ps1` | Full pre-release gate (layout check, build, stage, regression) |
| `verify_no_mirror.ps1` | Fail if duplicated library `.rs` files appear under `desktop/src-tauri/src/` |
| `stage_tauri_sidecars.ps1` | Copy `parse_cli` + `sonarsniffer-cli` into Tauri `binaries/` |
| `stage_tauri_sidecars.sh` | Same for Linux/macOS CI |
| `regression_smoke.ps1` | Millers / Holloway / Sonar010 mosaic smoke test (`-Fast` for host-tuned quick run) |

## Build output directory

Network shares may deny writes to `target/`. All tools set:

```powershell
$env:CARGO_TARGET_DIR = "$env:LOCALAPPDATA\SonarSniffer-build\target"
```

## Editing rules

1. Change parsers, mosaic, outputs, video → **`src/` only**
2. Change desktop UI → **`desktop/ui/`**
3. Change Tauri IPC / file dialogs → **`desktop/src-tauri/src/commands.rs`**
4. Never run `robocopy src desktop\src-tauri\src` — that workflow is removed.
