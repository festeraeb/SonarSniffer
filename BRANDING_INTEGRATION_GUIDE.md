# Sonar Sniffer by CESARops - Branding & Integration Guide

## Overview

This document details the branding integration and web server implementation for the Sonar Sniffer platform, distinguishing between:
- **GUI Application**: "Sonar Sniffer" (local parser)
- **Web Outputs**: "Sonar Sniffer by CESARops" (community viewer)

## Branding Architecture

### Local GUI Application
- **Name**: Sonar Sniffer
- **Purpose**: Local RSD file parsing and processing
- **Window Title**: "SonarSniffer - Sonar Data Processor"
- **Audience**: Individual researchers, SAR teams

### Web Server Components
- **Name**: Sonar Sniffer by CESARops
- **Purpose**: Remote family/team collaboration for sonar surveys
- **URL Display**: Shows CESARops branding and link
- **Audience**: SAR coordinators, family members, remote teams

### CESARops Integration
- **Project**: CESARops - Drift Modeling for Search and Rescue
- **Repository**: https://github.com/festeraeb/CESARops
- **License**: Apache 2.0 (Open Source)
- **Connection**: Complements sonar survey data with ocean current modeling
- **Use Case**: Drift search pattern calculation, SAR operations planning

## Branding Updates Applied

### 1. Web Server Core Module (`sar_web_server.py`)

**Changes Made:**
```python
# Line 132: Default server name
server_name: str = 'Sonar Sniffer by CESARops - Search & Rescue'

# Line 509: HTML header emoji (🎯 → 🌊)
<h1>🌊 {self.server_name}</h1>

# Line 777: Factory method server_name (updated)
server_name="🌊 Sonar Sniffer by CESARops"

# Line 837: Advanced example server_name (updated)
server_name="🌊 Sonar Sniffer by CESARops"
```

**Purpose:**
- Wave emoji (🌊) emphasizes sonar/water context
- "by CESARops" directs users to drift modeling tool
- Consistent branding across all instances

### 2. Integration Helper Dialogs (`sar_web_server_integration_helper.py`)

**Changes Made:**
```python
# Dialog titles updated to use "Sonar Sniffer" branding
WebServerConfigDialog.setWindowTitle("Sonar Sniffer Server Configuration")

# Configuration header updated
header = QLabel("Configure Sonar Sniffer by CESARops - Remote Viewing")

# Enable server checkbox updated
dialog.enable_server = QCheckBox("Enable Sonar Sniffer server after export")

# Info text updated
"Sonar Sniffer allows family/team to view sonar data in any"

# Share dialog updated
dialog.setWindowTitle("Share Sonar Survey Data")
```

**Purpose:**
- User-facing dialogs clearly identify the tool
- CESARops branding visible in configuration
- Professional terminology ("Sonar Survey Data")

### 3. GUI Application (`sonar_gui.py`)

**Status**: Already branded correctly
```python
self.root.title("SonarSniffer - Sonar Data Processor")
```

**No changes needed**: Window title already uses "Sonar Sniffer"

## Path B Implementation (KML Overlay)

### Technical Stack
- **Format**: KML (Keyhole Markup Language)
- **Frontend**: Leaflet.js + HTML5
- **Server**: Python FastAPI/Flask
- **Dependencies**: Minimal (zero binary dependencies)

### Features
✓ Real-time layer toggle
✓ GPS track visualization
✓ Multiple overlay support
✓ Family/team IP sharing
✓ Mobile-friendly responsive design
✓ No authentication required

### Holloway Reference Test Results
```
Generated Files:
  - Holloway.RSD.branded.html (10.5 KB)
  - Holloway.RSD.branded.kml (172.3 KB)
  - Holloway.RSD.geojson (308.7 KB)
  - TEST_SUMMARY.md (2.0 KB)

Status: [PASS] Path B Implementation IMPLEMENTED
```

## Path C Implementation (MBTiles/GDAL)

### Planned Features
- GDAL-powered map tile generation
- MBTiles and PMTiles support
- Cloud-Optimized GeoTIFF (COG) output
- High-performance rendering for large surveys
- Web mercator projection support

### Status
⏳ **PENDING** - Scheduled for next phase

### Requirements
```
gdal
rasterio
morecantile
pmtiles
```

## Deployment Architecture

### Single-Port Web Server
```
┌─────────────────────────────────────┐
│  Sonar Sniffer Web Server           │
│  (Port 8080)                        │
├─────────────────────────────────────┤
│                                     │
│  ├─ /map          → HTML Viewer     │
│  ├─ /data/*       → GeoJSON         │
│  ├─ /kml/*        → KML Overlays    │
│  ├─ /tiles/*      → MBTiles (Path C)│
│  └─ /api/*        → JSON API        │
│                                     │
└─────────────────────────────────────┘
```

### Network Architecture
```
┌─────────────────────┐
│  Sonar Sniffer GUI  │
│  (Local Desktop)    │
└──────────┬──────────┘
           │
           │ Export + Start Server
           │
           ▼
┌─────────────────────────────────────┐
│  Sonar Sniffer Web Server           │
│  localhost:8080                     │
└──────────┬────────────┬─────────────┘
           │            │
           ▼            ▼
    ┌─────────────┐  ┌──────────────┐
    │ Local Team  │  │ Remote Family│
    │ (LAN)       │  │ (IP Address) │
    └─────────────┘  └──────────────┘
```

## Integration Guide for Developers

### Adding Web Server to Export Workflow

```python
from sar_web_server import SARWebServer

# Create server instance
server = SARWebServer(
    port=8080,
    allow_external=True,
    auto_open_browser=True,
    output_dir='sar_web_output',
    server_name='🌊 Sonar Sniffer by CESARops'
)

# Add data layers
server.add_kml_overlay('survey.kml', 'Survey Track')
server.add_geojson_data('points.geojson', 'GPS Points')

# Start server
server.start()

# Server runs in background thread
# Access at: http://localhost:8080
```

### Using PyQt5 Integration Helper

```python
from sar_web_server_integration_helper import (
    WebServerConfigDialog,
    SARWebServerExporter,
    create_share_dialog
)

# Get user configuration
config = WebServerConfigDialog.create_and_show()
if config:
    # Export with server
    exporter = SARWebServerExporter()
    result = exporter.export_with_server(
        records=sonar_records,
        output_dir='exports',
        **config
    )
    
    # Show sharing dialog
    if result.server_running:
        create_share_dialog(result.server_url)
```

## CESARops Integration Points

### What is CESARops?
CESARops is an open-source drift modeling tool for Search and Rescue operations. It calculates how objects will drift in the ocean given:
- Wind speed and direction
- Ocean currents (real-time or forecast)
- Stokes drift (wave-induced drift)
- Windage percentage (object-specific)

### Why Include CESARops Branding?
1. **Complementary Tools**: Sonar surveys locate objects; drift modeling predicts their movement
2. **Open Source Community**: Directs users to additional free SAR resources
3. **Research Support**: Enables integration with drift prediction workflows
4. **Cross-Platform**: Creates awareness of SAR technology ecosystem

### Recommended Workflow
```
1. User exports sonar survey → Sonar Sniffer GUI
2. Web server starts → Sonar Sniffer by CESARops
3. Family/team views survey online
4. SAR coordinator uses CESARops for drift search planning
5. Combined sonar + drift model guides actual search
```

## File Structure

```
c:\Temp\Garminjunk\
├── sonar_gui.py                          # GUI Application (branded as "Sonar Sniffer")
├── sar_web_server.py                     # Web server (branded as "Sonar Sniffer by CESARops")
├── sar_web_server_integration_helper.py  # PyQt5 integration dialogs
├── branded_web_test_output/              # Test outputs with branding
│   ├── Holloway.RSD.branded.html         # Reference HTML viewer
│   ├── Holloway.RSD.branded.kml          # Reference KML overlay
│   ├── Holloway.RSD.geojson              # Reference GeoJSON data
│   └── TEST_SUMMARY.md                   # Test results
├── test_branding_holloway.py             # Branding validation test
└── BRANDING_INTEGRATION_GUIDE.md         # This file
```

## Testing Results

### Branding Test Execution
```
Date: 2025-11-25
Test File: test_branding_holloway.py
Reference Data: Holloway.RSD (3,332 records)

[PASS] Branding Test: SUCCESSFUL
[PASS] Path B (KML Overlay): IMPLEMENTED
[PASS] Branding Consistency: VERIFIED
[TODO] Path C (MBTiles/GDAL): PENDING
```

### Verification Checklist
- [x] GUI application title: "Sonar Sniffer"
- [x] Web server default name: "Sonar Sniffer by CESARops"
- [x] Dialog titles updated with new branding
- [x] HTML headers include wave emoji (🌊)
- [x] CESARops link in reference outputs
- [x] KML overlay with branding comments
- [x] GeoJSON data properly formatted
- [x] Test with Holloway reference data completed

## Deployment Checklist

### Pre-Production
- [ ] Run branding test: `python test_branding_holloway.py`
- [ ] Verify Path B outputs in `branded_web_test_output/`
- [ ] Check CESARops link functionality
- [ ] Test with actual sonar data (non-reference)

### Production Release
- [ ] Update documentation with branding screenshots
- [ ] Create deployment guide for web server
- [ ] Add CESARops mention to README
- [ ] Test on multiple platforms (Windows, macOS, Linux)
- [ ] Verify responsive design on mobile browsers

### Post-Release Monitoring
- [ ] Track CESARops GitHub referral clicks
- [ ] Gather user feedback on branding
- [ ] Monitor web server stability
- [ ] Plan Path C implementation timeline

## Next Steps

### Immediate (This Week)
1. ✅ Apply branding to web server components
2. ✅ Test with Holloway reference data
3. ✅ Validate Path B implementation
4. Generate documentation with screenshots
5. Test with live sonar data

### Short-term (Next 2 weeks)
1. Implement Path C (GDAL/MBTiles)
2. Create deployment guide
3. Add CESARops integration examples
4. Prepare for community release

### Medium-term (Next 4 weeks)
1. Release Sonar Sniffer v2.0 with web server
2. Publish branding documentation
3. Create CESARops integration tutorial
4. Gather community feedback

## References

- **CESARops Repository**: https://github.com/festeraeb/CESARops
- **Leaflet.js Documentation**: https://leafletjs.com/
- **KML Specification**: https://developers.google.com/kml/documentation
- **MBTiles Format**: https://github.com/mapbox/mbtiles-spec

## Contact & Support

For questions about branding or integration:
- GitHub Issues: Sonar Sniffer repository
- CESARops Issues: https://github.com/festeraeb/cesarops/issues
- SAR Community: [Your community link]

---

**Document Version**: 1.0
**Last Updated**: 2025-11-25
**Status**: Branding Implementation Complete, Path C Pending
