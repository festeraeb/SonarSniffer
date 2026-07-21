# SonarSniffer

**Professional Sidescan Sonar Processing & Mosaic Engine**  
*NautiDog Sailing*

SonarSniffer parses Garmin RSD, Lowrance SL2/SL3, Humminbird DAT, XTF, JSF, and Cerulean sonar files. It produces geo-referenced mosaic imagery, enhanced video exports, MBTiles, KML/KMZ overlays, and ArcGIS-compatible outputs.

Video export uses a **built-in pure-Rust AV1/MP4 encoder** (`rav1e`). **GStreamer is not required** for normal use.

---

## Downloads

**Latest desktop (0.8.22):** [GitHub Release v0.8.22](https://github.com/festeraeb/SonarSniffer/releases/tag/v0.8.22) · mirror [cesarops.com/downloads/sonarsniffer](https://www.cesarops.com/downloads/sonarsniffer/)

Pre-built artifacts are published on [GitHub Releases](https://github.com/festeraeb/SonarSniffer/releases/latest) when you tag `v*` (CI builds automatically).

| Artifact | Platform | Use case |
|----------|----------|----------|
| `SonarSniffer-Setup.exe` | Windows | **Recommended** one-file installer (prereqs + MSI + CLIs) |
| `SonarSniffer_*_x64_en-US.msi` | Windows | Tauri desktop app (msiexec / Programs and Features) |
| `SonarSniffer_*_x64-setup.exe` | Windows | NSIS desktop installer (Tauri bundle) |
| `SonarSniffer.exe` | Windows | Portable desktop binary (no installer) |
| `SonarSniffer-Windows-CLI-x64.zip` | Windows | CLI only (`sonarsniffer-cli`, `parse_cli`, UI assets) |
| `SonarSniffer-macOS-CLI-x64.zip` | macOS | CLI only |
| `SonarSniffer_*.dmg` | macOS | Desktop app (Tauri) |

From 0.8.22 the desktop binary is **`SonarSniffer.exe`** (Tauri `mainBinaryName`). Prefer Start Menu / `%LOCALAPPDATA%\SonarSniffer\SonarSniffer.exe` over any stale portable under `%LOCALAPPDATA%\Programs\SonarSniffer\` (often old **0.77.5**).

---

## Installation

### Windows — `SonarSniffer-Setup.exe` (recommended)

1. Download `SonarSniffer-Setup.exe` from [Releases](https://github.com/festeraeb/SonarSniffer/releases/latest) (or [cesarops.com](https://www.cesarops.com/downloads/sonarsniffer/SonarSniffer-Setup.exe)).
2. Run as Administrator (UAC prompt).
3. The bootstrap installs WebView2 / VC++ if missing, then the MSI desktop app and CLI tools.
4. Launch from **Start Menu → SonarSniffer**, or `%LOCALAPPDATA%\SonarSniffer\SonarSniffer.exe`.

### Windows — MSI (`SonarSniffer_*_x64_en-US.msi`)

1. Download the MSI from Releases.
2. Double-click, or: `msiexec /i SonarSniffer_0.8.22_x64_en-US.msi`
3. Requires **WebView2** ([Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/)) — usually already on Windows 10/11.
4. App installs to `%LOCALAPPDATA%\SonarSniffer\` as `SonarSniffer.exe`. Exit code `3010` means success with a deferred reboot — the app is usable.

### Windows — NSIS (`SonarSniffer_*_x64-setup.exe`)

1. Download the NSIS setup from Releases (Tauri NSIS bundle).
2. Run the installer and follow the wizard.
3. Launch via Start Menu shortcut → `SonarSniffer.exe`.
4. Use this when you want the Tauri-native installer without the full Setup.exe prereq bootstrap.

### Windows — portable `SonarSniffer.exe`

1. Download `SonarSniffer.exe` from Releases (or the versioned folder on cesarops.com).
2. Place it in any folder (e.g. `C:\Tools\SonarSniffer\`) and run it.
3. Still needs **WebView2** on the machine. No Start Menu / uninstall entry.
4. Do **not** keep running an old copy under `%LOCALAPPDATA%\Programs\SonarSniffer\` if you also installed via Setup/MSI.

### Windows / macOS — CLI zip

**Windows**

1. Download `SonarSniffer-Windows-CLI-x64.zip` from [Releases](https://github.com/festeraeb/SonarSniffer/releases/latest).
2. Extract to a folder, e.g. `C:\SonarSniffer\`.
3. Open PowerShell or Command Prompt in that folder.

**macOS**

1. Download `SonarSniffer-macOS-CLI-x64.zip`.
2. Extract: `unzip SonarSniffer-macOS-CLI-x64.zip -d ~/SonarSniffer`
3. Make executable: `chmod +x ~/SonarSniffer/sonarsniffer-cli ~/SonarSniffer/parse_cli`
4. On first run, macOS may block the binary — System Settings → Privacy & Security → Allow.

No extra runtime is needed for `--video` (AV1 is built in).

### macOS — desktop DMG

1. Download `SonarSniffer_*.dmg` from Releases.
2. Open the DMG and drag SonarSniffer to Applications.
3. First launch: right-click → Open if Gatekeeper blocks the app.

---

## Usage

### Quick parse (inspect a sonar file)

```bash
parse_cli /path/to/file.RSD
```

Outputs: channel discovery, ping counts, firmware detection, GPS coverage.

### Full pipeline (mosaic + video + all outputs)

```bash
sonarsniffer-cli /path/to/file.RSD --video --mosaic --curvelet --colormap amber
```

### Options

| Flag | Description |
|------|-------------|
| `--video` | Export enhanced AV1/MP4 video (built-in encoder) |
| `--mosaic` | Generate geo-referenced mosaic PNGs |
| `--curvelet` | Apply curvelet denoising |
| `--soundtiles` | Run SoundTiles feature alignment |
| `--colormap <name>` | amber, sonar, viridis, magma, inferno, plasma, ocean, iron, jet, grayscale |
| `--output <dir>` | Override output directory |
| `--kml` | Export KML ground overlay |
| `--kmz` | Export KMZ package |
| `--mbtiles` | Export MBTiles tileset |
| `--arcgis` | Export ArcGIS-compatible GeoTIFF |

### Supported formats

- **Garmin RSD** — GT54, GT56, UHD, UHD2, Classic, LiveScope
- **Lowrance SL2/SL3** — Primary, Downscan, Sidescan
- **Humminbird DAT** — Side imaging, down imaging
- **XTF** — Extended Triton Format (survey-grade)
- **JSF** — EdgeTech JSF format
- **Cerulean** — Cerulean Sonar logs

---

## Build from source

### Prerequisites

- [Rust](https://rustup.rs) (stable)
- **CLI:** nothing else on Windows/macOS/Linux
- **Desktop (Tauri 2):**
  - `cargo install tauri-cli --version "^2.0"`
  - **Windows:** MSVC + WebView2 SDK (usually via Visual Studio Build Tools)
  - **macOS:** Xcode command-line tools
  - **Linux:** `libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, `libdbus-1-dev`, `pkg-config`

GStreamer is **optional** — only if you build with `--features video-gstreamer` for legacy H.264.

### CLI

Production flags are documented in [docs/BUILD_FLAGS.md](docs/BUILD_FLAGS.md)
(`--release --no-default-features`; optional Linux `--features jemalloc`).

```bash
git clone https://github.com/festeraeb/SonarSniffer.git
cd SonarSniffer
# preferred helper (sets CARGO_TARGET_DIR=/data/cargo-target when present):
bash tools/prod_cargo_build.sh
# or:
cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
# binaries: $CARGO_TARGET_DIR/release/sonarsniffer-cli, parse_cli
```

| Branch | Build |
|--------|--------|
| `master` | `tools/prod_cargo_build.sh` / release CI |
| `wasm` | `scripts/build_wasm.sh` (`wasm-pack --release --no-default-features`) |
| `ip` | same Cargo flags as master + packed InstallAssist (LLM/self-heal) |

### Desktop app

Sidecar binaries (`sonarsniffer-cli`, `parse_cli`, `soundtiles`) must be staged before `cargo tauri build`:

**Linux / macOS**

```bash
bash tools/stage_tauri_sidecars.sh
cd desktop/src-tauri
cargo tauri build --bundles dmg    # macOS
```

**Windows (PowerShell)**

```powershell
.\tools\publish.ps1 -Release
# or step-by-step:
.\tools\stage_tauri_sidecars.ps1
cd desktop\src-tauri
cargo tauri build --bundles msi,nsis
```

**Windows one-file installer**

After MSI/NSIS build:

```powershell
.\scripts\pack_sonarsniffer_windows_setup.ps1
# => dist\SonarSniffer-Setup.exe
```

### Release CI

Push a version tag to trigger the release workflow:

```bash
git tag v0.8.2
git push origin v0.8.2
```

CI builds CLI zips, Windows MSI/NSIS/Setup.exe, and macOS DMG, then attaches them to the GitHub Release.

---

## Desktop app features

- File browser and pipeline options
- Colormap picker with live previews
- Dependency checker (WebView2 on Windows; GStreamer optional legacy path)
- SoundTiles mosaic alignment (sidecar binary)
- License management

---

## License

Contact: nautik9@cesarops.com  
Website: https://cesarops.com
