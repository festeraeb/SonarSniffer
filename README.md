# SonarSniffer v0.2.0 Beta

Advanced sonar data processing, visualization, and geospatial export for marine surveys.

## Overview

SonarSniffer is a desktop application for processing raw sonar files from various manufacturers (Garmin RSD, Klein SDF, Humminbird) and converting them into publication-ready visualizations and geospatial datasets.

## Key Features

- **Memory-Optimized Processing**: Auto-scales grid resolution for surveys from 1 km² to 10,000 km²
- **3D Visualization**: Export sonar data as KML with depth contours and bathymetric overlays
- **Geospatial Output**: Generate GeoTIFF, GeoJSON, and interactive HTML maps
- **CSV Export**: 17-column comprehensive data export with coordinate systems
- **Batch Processing**: Process multiple RSD files efficiently
- **Cross-Platform**: Windows, Linux, and macOS installers included
- **GPU Support**: Optional CUDA acceleration for video encoding

## Installation

### Windows
1. Download or clone the beta-clean branch
2. Run the installer:
   ```bash
   install_windows.bat
   ```
3. Launch the GUI:
   ```bash
   python sonar_gui.py
   ```

### Linux
1. Download or clone the beta-clean branch
2. Make the installer executable and run it:
   ```bash
   chmod +x install_linux.sh
   ./install_linux.sh
   ```
3. Launch the GUI:
   ```bash
   python sonar_gui.py
   ```

### macOS
1. Download or clone the beta-clean branch
2. Make the installer executable and run it:
   ```bash
   chmod +x install_macos.sh
   ./install_macos.sh
## System Requirements

### Minimum
- Python 3.10 or higher
- 4GB RAM
- 500MB free disk space
- Windows 10+, Ubuntu 20.04+, or macOS 10.15+

### Recommended
- Python 3.11+
- 8GB+ RAM (for processing 80,000+ record surveys)
- 2GB+ free disk space
- FFmpeg installed (auto-installed by installers)

## Supported File Formats

- **Garmin RSD**: Single/dual frequency, UHD2, Panoptix
- **Klein SDF**: SonarScan data files
- **Humminbird**: DAT files (experimental)

## Export Formats

- **3D KML**: Google Earth-compatible with bathymetric visualization
- **GeoTIFF**: Georeferenced raster imagery
- **GeoJSON**: Vector geospatial data
- **CSV**: 17-column comprehensive export
- **HTML**: Interactive web maps
- **Video**: MP4 encoding with optional GPU acceleration

## What's New in v0.2.0

### Memory Optimization
- Fixed 206 TiB memory allocation crash
- Auto-calculated grid resolution based on survey area
- Point decimation for surveys with 80,000+ records
- Conditional DEM generation to save memory

### Platform Support
- Windows installer with full environment setup
- Linux distro-aware installation (Ubuntu, Fedora, Arch, openSUSE)
- macOS installer with Homebrew integration

### Bug Fixes
- Fixed latitude/longitude coordinate mapping
- Fixed altitude conversion in 3D exports
- Enhanced CSV export (9 → 17 data columns)
- Improved HTML statistics validation

## Core Files

- **sonar_gui.py** (2,800+ lines): Main desktop GUI application
- **geospatial_exporter.py**: KML, GeoTIFF, and map generation
- **kml_3d_generator.py**: 3D bathymetric visualization
- **emit_parsed_csv.py**: Multi-column CSV export
- **requirements.txt**: 40+ Python packages organized by category

## Development

This is a **beta release** and may contain bugs. Please report issues on GitHub:
https://github.com/festeraeb/SonarSniffer

## License

See LICENSE.txt file for terms and conditions.

---

**Release**: v0.2.0 Beta  
**Updated**: November 21, 2025  
**Status**: Production Ready
````
- **Extending**: Add new parsers or integrations as modules and register in the server.

---

## License
See LICENSE file (if present) or contact the author.

---

## Last Updated
October 20, 2025
