# SonarSniffer changelog

## 0.8.20 — 2026-07-11

### Standalone product scope

- Add `tools/verify_standalone_repo.sh` and `docs/REPO_SCOPE.md` — SonarSniffer + SoundTiles only; no monorepo pollution.
- Remove legacy `rust-garmin-rsd-cli/` duplicate tree (parser lives in `src/`).
- Decouple installer from hardcoded CesarOps/nautivecs endpoints (opt-in via env vars).
- Optional local Ollama install assist (`SONARSNIFFER_INSTALL_ASSIST=1`); no cloud tunnel or remote PowerShell.
- WASM build prep: `wasm32` cfg gates, `scripts/build_wasm.sh`, `src/wasm_api.rs`.
- CI release workflow runs standalone layout verification before desktop build.
- Branches: `master` (release), `wasm` (experimental), `ip` (local install assist).

## 0.8.19 — 2026-06-24

### Windows setup bootstrap

- Fix Rust `format!` escaping in the elevated PowerShell launcher (`${timeoutSec}`).
- Declare `embed_payload` cfg in setup-bootstrap `build.rs` for current Rust check-cfg.
- Tag `v0.8.19` triggers the release rebuild.

## 0.8.18 — 2026-06-24

### Release CI / standalone packaging

- Retry transient Windows CLI cargo dependency downloads in release CI.
- Make `pack_sonarsniffer_windows_setup.ps1` work in the standalone SonarSniffer repo as well as the legacy monorepo layout.
- Tag `v0.8.18` triggers the cleaned GitHub Actions Windows/macOS release build.

## 0.8.17 — 2026-06-24

### Repository cleanup / release rebuild

- Remove accidentally committed setup-bootstrap build artifacts from the release branch.
- Align Cargo/Tauri package versions and lockfile state for the cleaned GitHub Actions release.
- Tag `v0.8.17` triggers GitHub Actions Windows/macOS release build.

## 0.8.16 — 2026-06-14

### Windows installer (winget / WebView2 hardening)

- **Registry-first prereqs** — skip winget when VC++ 2015–2022, WebView2, or GStreamer already present (`Test-VCRedistRobust`, `Test-WebView2Robust`, `Test-GStreamerRobust`).
- **`Install-WingetRobust`** — `winget list` skip-if-installed, 90–120s job timeout, `--disable-interactivity`, optional `--silent`.
- **Kit bundles `lib/SonarSniffer.Install.psm1`** — fixes laptop installs that hung on winget WebView2 re-check.
- **UAC reprompt** — 90s timeout, 3 attempts, visible “look for UAC behind other windows” message.
- **`Write-NautivecsInstallError`** — POST common failure codes to fleet nautivecs when reachable.
- **Rust bootstrap** — WebView2 preflight (registry + exe `--version` + folder fallback); passes `-StrictSilent` to install script.
- Switches: `-SkipWinget`, `-StrictSilent` on `install_sonarsniffer_full.ps1`.

### Build

- Tag `sonarsniffer-v0.8.16` triggers GitHub Actions Windows build → `SonarSniffer-Setup.exe` release artifact.

## 0.8.15

- Prior Tauri desktop + setup bootstrap baseline.
