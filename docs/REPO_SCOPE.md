# SonarSniffer repository scope

This repository contains **only** the SonarSniffer product:

| Component | Purpose |
|-----------|---------|
| `src/` | Core library + `sonarsniffer-cli` + `parse_cli` |
| `soundtiles/` | SoundTiles alignment sidecar (bundled with desktop) |
| `nauticuvs/` | Vendored curvelet/FDCT dependency (path crate) |
| `desktop/` | Tauri 2 desktop shell + `ui/` |
| `setup-bootstrap/` | Windows one-file `SonarSniffer-Setup.exe` launcher |
| `scripts/` | Installers and release helpers |
| `tools/` | Build verification and sidecar staging |
| `testdata/` | Small fixtures for CI/smoke tests |

## Not in scope

Do **not** add or sync from the CesarOps / wreckhunter monorepo:

- `var/`, `systemd/`, `wrecks_api/`, `tauri/dist-web/`, forge missions, fleet scripts
- `rust-garmin-rsd-cli/` (legacy duplicate; parser lives in `src/garmin_rsd_parser.rs`)
- Cloud diagnostic tunnels or remote PowerShell execution in installers

## Branches

| Branch | Purpose |
|--------|---------|
| `master` | Native desktop + CLI installers (primary release line) |
| `wasm` | Browser WASM build (`wasm-pack`) — experimental |
| `ip` | Installer with optional **local** Ollama assist — experimental |

Run `tools/verify_standalone_repo.sh` before tagging a release.
