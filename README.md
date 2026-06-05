# SonarSniffer

**Professional Sidescan Sonar Processing & Mosaic Engine**  
*NautiDog Sailing*

SonarSniffer parses Garmin RSD, Lowrance SL2/SL3, Humminbird DAT, XTF, JSF, and Cerulean sonar files. It produces geo-referenced mosaic imagery, enhanced video exports, MBTiles, KML/KMZ overlays, and ArcGIS-compatible outputs.

---

## Downloads

| Platform | Link |
|----------|------|
| Windows x64 | [SonarSniffer-Windows-x64.zip](https://github.com/festeraeb/SonarSniffer/releases/latest/download/SonarSniffer-Windows-x64.zip) |
| macOS x64 | [SonarSniffer-macOS-x64.zip](https://github.com/festeraeb/SonarSniffer/releases/latest/download/SonarSniffer-macOS-x64.zip) |

---

## Installation

### Windows

1. Download `SonarSniffer-Windows-x64.zip` from the link above
2. Extract to a folder (e.g. `C:\SonarSniffer\`)
3. **Install GStreamer** (required for video export):
   - Download from https://gstreamer.freedesktop.org/download/
   - Install the **MSVC 64-bit** runtime package
   - Ensure `C:\gstreamer\1.0\msvc_x86_64\bin` is in your PATH
4. Run `sonarsniffer-cli.exe` from the command line or use the Tauri desktop app

### macOS

1. Download `SonarSniffer-macOS-x64.zip` from the link above
2. Extract: `unzip SonarSniffer-macOS-x64.zip -d ~/SonarSniffer`
3. **Install GStreamer** (required for video export):
   ```bash
   brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad
   ```
4. Make executable: `chmod +x ~/SonarSniffer/sonarsniffer-cli ~/SonarSniffer/parse_cli`
5. On first run, macOS may block it — go to System Settings → Privacy & Security → Allow

---

## Usage

### Quick Parse (inspect a sonar file)

```bash
parse_cli /path/to/file.RSD
```

Outputs: channel discovery, ping counts, firmware detection, GPS coverage.

### Full Pipeline (mosaic + video + all outputs)

```bash
sonarsniffer-cli /path/to/file.RSD --video --mosaic --curvelet --colormap amber
```

### Options

| Flag | Description |
|------|-------------|
| `--video` | Export enhanced GStreamer video |
| `--mosaic` | Generate geo-referenced mosaic PNGs |
| `--curvelet` | Apply curvelet denoising |
| `--soundtiles` | Run SoundTiles feature alignment |
| `--colormap <name>` | amber, sonar, viridis, magma, inferno, plasma, ocean, iron, jet, grayscale |
| `--output <dir>` | Override output directory |
| `--kml` | Export KML ground overlay |
| `--kmz` | Export KMZ package |
| `--mbtiles` | Export MBTiles tileset |
| `--arcgis` | Export ArcGIS-compatible GeoTIFF |

### Supported Formats

- **Garmin RSD** — All generations (GT54, GT56, UHD, UHD2, Classic, LiveScope)
- **Lowrance SL2/SL3** — Primary, Downscan, Sidescan channels
- **Humminbird DAT** — Side imaging, down imaging
- **XTF** — Extended Triton Format (survey-grade)
- **JSF** — EdgeTech JSF format
- **Cerulean** — Cerulean Sonar logs

---

## Desktop App (Tauri)

The desktop app provides a GUI launcher with:
- File browser and pipeline options
- Colormap picker with live previews
- Dependency checker (GStreamer auto-install on Windows)
- SoundTiles standalone mosaic tool
- License management

To build the desktop app from source:
```bash
cd desktop/src-tauri
cargo tauri build
```

Requires: Rust, Tauri CLI (`cargo install tauri-cli`), platform SDK (MSVC on Windows, Xcode on macOS).

---

## License

Contact: cesarops@cesarops.com  
Website: https://cesarops.com

