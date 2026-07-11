# Installer with local LLM assist (experimental)

The `ip` branch ships the same SonarSniffer + SoundTiles product as `master`, plus an **optional**
local troubleshooting helper during Windows install.

## Enable

Before or during install:

```powershell
$env:SONARSNIFFER_INSTALL_ASSIST = '1'
# optional:
$env:SONARSNIFFER_OLLAMA_URL = 'http://127.0.0.1:11434'
$env:SONARSNIFFER_OLLAMA_MODEL = 'tinyllama'
```

Requires [Ollama](https://ollama.com/) running locally. The assist module **only reads the local install log**
and suggests next steps. It does **not**:

- Call CesarOps / cloud agents
- Execute remote PowerShell payloads
- Bundle any monorepo code

## Primary release line

Use **`master`** for production `SonarSniffer-Setup.exe` releases unless you are testing assist.
