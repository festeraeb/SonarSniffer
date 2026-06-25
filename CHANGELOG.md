# SonarSniffer changelog

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
