# SonarSniffer

**Professional Sidescan Sonar Processing & Mosaic Engine**  
*NautiDog Sailing*

SonarSniffer parses Garmin RSD, Lowrance SL2/SL3, Humminbird DAT, XTF, JSF, and Cerulean sonar files. It produces geo-referenced mosaic imagery, enhanced video exports, MBTiles, KML/KMZ overlays, and ArcGIS-compatible outputs.

Video export uses a **built-in pure-Rust AV1/MP4 encoder** (`rav1e`). **GStreamer is not required** for normal use.

---

## Downloads

Pre-built artifacts are published on [GitHub Releases](https://github.com/festeraeb/SonarSniffer/releases/latest) when you tag `v*` (CI builds automatically).

| Artifact | Platform | Use case |
|----------|----------|----------|
| `SonarSniffer-Windows-CLI-x64.zip` | Windows | CLI only (`sonarsniffer-cli`, `parse_cli`, UI assets) |
| `SonarSniffer-macOS-CLI-x64.zip` | macOS | CLI only |
| `SonarSniffer-Setup.exe` | Windows | One-click installer (WebView2 + MSI + CLIs) |
| `SonarSniffer_*.msi` | Windows | Desktop app (Tauri) |
| `SonarSniffer_*.dmg` | macOS | Desktop app (Tauri) |

Legacy CLI zip names (`SonarSniffer-Windows-x64.zip`) may appear on older releases.

---

## Installation

### Option A — CLI only (Windows / macOS)

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

### Option B — Desktop app (Windows)

**Easiest:** download `SonarSniffer-Setup.exe` from Releases and run as Administrator. It installs WebView2 (if missing), the MSI desktop app, and CLI tools.

**Manual MSI:** download `SonarSniffer_*.msi`, double-click to install. Requires **WebView2** ([Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/)) — usually already present on Windows 10/11.

### Option C — Desktop app (macOS)

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

```bash
git clone https://github.com/festeraeb/SonarSniffer.git
cd SonarSniffer
cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
# binaries: target/release/sonarsniffer-cli, target/release/parse_cli
```

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
