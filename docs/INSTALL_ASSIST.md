# Installer with local LLM assist + self-heal (experimental)

The `ip` branch ships the same SonarSniffer + SoundTiles product as `master`, plus an
**optional** local troubleshooting helper packed into `SonarSniffer-Setup.exe`
(`scripts/lib/SonarSniffer.InstallAssist.psm1`).

## Cargo / build flags

Same production native flags as `master` — see [BUILD_FLAGS.md](BUILD_FLAGS.md):

```bash
cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
# or: bash tools/prod_cargo_build.sh
```

Do **not** enable `video-gstreamer` for the assist SKU unless intentionally shipping legacy H.264.

## Enable assist

Before or during install:

```powershell
$env:SONARSNIFFER_INSTALL_ASSIST = '1'
# optional:
$env:SONARSNIFFER_OLLAMA_URL = 'http://127.0.0.1:11434'
$env:SONARSNIFFER_OLLAMA_MODEL = 'tinyllama'
```

When enabled, the assist module:

1. Emits **deterministic self-heal hints** from the install log (WebView2, VC++, UAC, winget, MSI).
2. Optionally asks local [Ollama](https://ollama.com/) for a short narrative if reachable.

It does **not**:

- Call CesarOps / cloud agents
- Execute remote PowerShell payloads
- Bundle any monorepo code
- Change Cargo feature selection

## Primary release line

Use **`master`** for production `SonarSniffer-Setup.exe` releases unless you are testing assist.
Pack with `scripts/pack_sonarsniffer_windows_setup.ps1` after a production-flagged desktop build.
