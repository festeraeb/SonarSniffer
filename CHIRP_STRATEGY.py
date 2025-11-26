#!/usr/bin/env python3
"""
CHIRP/ClearVue Data Analysis & Utilization Strategy

CV-54-UHD.RSD Analysis
=====================

WHAT WE FOUND:
- 61,123 raw sonar frames (frame type 0x06)
- NOT a standard RSD wrapper format
- Streaming format from device (likely HDMI capture or memory dump)
- Mixed metadata frames (1-10 bytes) and data frames (up to 19KB)
- GT54 transducer chirp data

WHAT WE KNOW FROM FIRMWARE ANALYSIS:
- CV = CHIRP/ClearVue units (frequency: 24.72)
- Multiple frequency channels: 6, 7, 8, 9, 10
- echoMAP CHIRP series: 53cv, 54cv, 55cv, 73cv, 74cv, 75cv, etc.
- cv = ClearVue (down-looking)
- dv = Down-view (?)
- sv = SideView (Sidescan)
"""

# Map the file types we have to what they contain
SONAR_FILE_FORMAT_MAPPING = {
    "RSD (Standard)": {
        "description": "Garmin standard RSD container format",
        "examples": ["Sonar000.RSD", "Sonar001.RSD", "Holloway.RSD"],
        "contains": ["Side-scan sonar", "CHIRP/ClearVue data", "Navigation", "Attitude"],
        "channels": [4, 5, 6, 7, 8, 9, 10],  # Depends on unit
        "parsable": True,
    },
    "RSD (CV-54-UHD) - Streaming": {
        "description": "Raw streaming format from CHIRP device (CV = ClearVue)",
        "examples": ["CV-54-UHD.RSD"],
        "contains": ["Pure CHIRP/ClearVue sonar data", "No navigation wrapper"],
        "channels": "6-10 (variable, need to parse)",
        "format": "0x06 frame markers with variable-length payloads",
        "parsable": "False - need custom parser",
        "note": "Likely HDMI capture or device memory dump",
    },
    "SON (Garmin proprietary)": {
        "description": "Garmin SONaR format (different from RSD)",
        "examples": ["B001.SON"],
        "contains": ["Sonar data", "Possibly different encoding"],
        "parsable": "Unknown",
    },
    "XTF (Extended Triton Format)": {
        "description": "Industry standard for sonar data",
        "examples": ["general_xtf_clip_from_edgetech_4225i.xtf"],
        "contains": ["Side-scan", "CHIRP", "Bathymetry"],
        "parsable": True,
    },
    "JSF (Edgetech native)": {
        "description": "Edgetech native format (JSF = Jobson SonaR File?)",
        "examples": ["edgetech_native_file_format_clip.jsf"],
        "contains": ["Side-scan", "CHIRP", "Sub-bottom"],
        "parsable": True,
    },
}

# CHIRP/ClearVue Use Cases & Data Utilization
CHIRP_USE_CASES = {
    "Fish Detection & Mapping": {
        "user": "Recreational & Commercial Fishermen",
        "what": "CHIRP sonar specifically designed to detect fish schools",
        "how": "High-frequency pulses (50-200 kHz) create clear target signatures",
        "output_needed": [
            "📍 Georeferenced fish school locations (KML markers with dates/times)",
            "📊 Fish school statistics (depth, size, intensity)",
            "🎥 Video playback of fishing trips with overlay",
            "📈 Temporal patterns (best fishing times/locations)",
        ],
        "file_formats": ["KML (Google Earth)", "CSV", "GeoJSON"],
    },
    
    "Bottom Profiling": {
        "user": "Shipwreck hunters, bathymetry surveys",
        "what": "CHIRP excels at water column penetration & bottom detail",
        "how": "Returns detailed bottom structure, sub-bottom layers",
        "output_needed": [
            "🗺️ Bathymetric grid/DEM (GeoTIFF, NetCDF)",
            "📍 Anomaly detection (wrecks, rocks, drop-offs)",
            "📊 Cross-section profiles (SVG, PNG)",
            "3D 📦 3D model of bottom structure (optional)",
        ],
        "fill_gaps": "CHIRP down-view can fill gaps between side-scan passes",
    },
    
    "Navigation Safety": {
        "user": "Boaters, charts maintainers",
        "what": "Detect hazards (rocks, sandbars, wrecks)",
        "how": "CHIRP provides continuous coverage below boat track",
        "output_needed": [
            "⚠️ Hazard markers (KML, S-57 ENC format)",
            "📈 Depth profile along track",
            "🔴 Shallow water warnings",
        ],
    },
    
    "Scientific Research": {
        "user": "Geologists, marine scientists",
        "what": "Sub-bottom profiler capabilities, sediment layers",
        "how": "CHIRP penetrates multiple meters into bottom",
        "output_needed": [
            "📊 Stratigraphic profiles (SEG-Y, GeoTIFF)",
            "📋 Layer thickness measurements",
            "🔬 Scientific publication formats",
        ],
    },
}

# KEY INSIGHT: We need to distinguish between data TYPES
DATA_TYPE_DIFFERENCES = {
    "SideView (SV)": {
        "what": "Side-scan sonar - looks left/right of boat",
        "coverage": "Port and Starboard separately (channels 4, 5)",
        "resolution": "High lateral resolution, low vertical",
        "best_for": "Wreck location, object detection, seabed features",
        "channels": [4, 5],
    },
    
    "DownView (DV) / ClearVue (CV)": {
        "what": "CHIRP sonar - looks down below boat",
        "coverage": "Straight down (multiple frequencies 6-10)",
        "resolution": "High vertical resolution (water column detail)",
        "best_for": "Fish detection, bottom profiling, water column viz",
        "channels": [6, 7, 8, 9, 10],  # Multiple frequencies
    },
    
    "Sidescan": {
        "what": "Traditional sidescan - looks left/right",
        "coverage": "Port and Starboard",
        "resolution": "Medium res, good for features",
        "channels": [4, 5],
    },
}

# PARSING STRATEGY FOR CV-54-UHD.RSD
CV_PARSER_STRATEGY = """
CV-54-UHD.RSD PARSING ROADMAP
============================

CURRENT STATUS:
- File is NOT standard RSD format
- File contains 61,123 raw CHIRP frames (0x06 marker)
- Need to reverse-engineer frame structure

FRAME ANALYSIS SO FAR:
Frame 0: 262 bytes - Header/Configuration
  Header: 06 04 7c 4b 26 d9 0a 00 00 14 01 00 00 19 10 2f ...
  
Frame 1-3: 262-396 bytes - Setup/Calibration
Frame 3: 19,426 bytes - First major sonar data payload
Frames 4+: 1-10 bytes mostly (status/timing frames)

NEXT STEPS:
1. Identify frame structure:
   - Byte 0: 0x06 = frame type marker
   - Byte 1: Frame subtype? (0x04, 0x8f, 0xc4, 0xf9, etc.)
   - Bytes 2-?: Payload length or metadata?
   
2. Parse GT54 transducer metadata:
   - Frequency channels present
   - Transmit power levels
   - Gain settings
   - Filtering parameters
   
3. Extract sonar data:
   - Sample encoding (raw, compressed, etc.)
   - Beam information (angles, width)
   - Calibration data

4. Correlate with GPS/attitude if present:
   - Look for timestamp correlation
   - Navigation data (may be separate or interleaved)
   - Attitude (pitch, roll, heave)

STRATEGY:
Option A: Reverse-engineer from scratch (high effort, 3-5 days)
Option B: Check if Garmin firmware has decoder functions
Option C: Compare with known CHIRP files (if we can get standard RSD CHIRP)
Option D: Hybrid - Use frame type 0x06 analysis + firmware strings

RECOMMENDATION: Do B+C first
- Search firmware for CHIRP frame parsing functions
- Parse a standard RSD CHIRP file (Sonar000/001/002?)
- Then compare structure with CV-54-UHD
"""

# INTEGRATION WITH EXISTING GUI
INTEGRATION_OPPORTUNITIES = {
    "GUI Enhancements": {
        "Fish Detection Tab": {
            "display": "Detected fish schools with heatmap overlay",
            "export": "CSV + KML for fishing apps (e.g., BassCast, Navily)",
            "time_series": "Fish activity timeline (when/where most active)",
        },
        "Bottom Profile View": {
            "display": "Bathymetric cross-sections",
            "export": "Profile as SVG/PNG or GeoTIFF (entire DEM)",
            "fill_gaps": "CHIRP fills gaps left by side-scan passes",
        },
        "Hazard Map": {
            "display": "Detected anomalies (rocks, wrecks, drop-offs)",
            "export": "S-57 ENC format for chart plotters",
        },
    },
    
    "Export Formats": {
        "KML": "Fish locations, hazards, waypoints",
        "CSV": "Fish schools with depth/date/intensity",
        "GeoJSON": "Web mapping, Leaflet/Mapbox integration",
        "GeoTIFF": "Bathymetric grid, scientific use",
        "NetCDF": "Scientific datasets",
        "S-57": "Electronic Navigation Charts (ENCs)",
        "SVG": "Profile cross-sections for reports",
    },
}

print(__doc__)
print("\n" + "="*70)
print("SONAR FILE FORMAT MAPPING")
print("="*70)
for fmt, details in SONAR_FILE_FORMAT_MAPPING.items():
    print(f"\n{fmt}:")
    for k, v in details.items():
        print(f"  {k}: {v}")

print("\n" + "="*70)
print("CHIRP USE CASES FOR FISHERMEN & RESEARCHERS")
print("="*70)
for use_case, details in CHIRP_USE_CASES.items():
    print(f"\n🎯 {use_case}:")
    print(f"  👥 User: {details['user']}")
    print(f"  📋 What: {details['what']}")
    print(f"  ⚙️  How: {details['how']}")
    if 'fill_gaps' in details:
        print(f"  🔗 Gap filling: {details['fill_gaps']}")
    print(f"  📤 Outputs needed:")
    for output in details['output_needed']:
        print(f"      {output}")

print("\n" + "="*70)
print("DATA TYPE DIFFERENCES (CRITICAL!)")
print("="*70)
for dtype, details in DATA_TYPE_DIFFERENCES.items():
    print(f"\n{dtype}:")
    for k, v in details.items():
        print(f"  {k}: {v}")

print("\n" + "="*70)
print("CV-54-UHD.RSD PARSING STRATEGY")
print("="*70)
print(CV_PARSER_STRATEGY)

print("\n" + "="*70)
print("IMMEDIATE ACTION ITEMS")
print("="*70)
print("""
1. 🔍 PARSER REVERSE ENGINEERING:
   - Parse one of the standard RSD files (Sonar001.RSD) to understand
     how CHIRP channels (6-10) are encoded in a normal RSD file
   - Compare frame structure with CV-54-UHD.RSD
   - Identify the mapping

2. 🔬 FIRMWARE ANALYSIS:
   - Search GUPDATE.GCD for CHIRP frame parsing functions
   - Look for "0x06" marker handlers
   - Extract GT54 transducer constants

3. 🎯 USE CASE PRIORITIZATION:
   - Which features matter most for YOUR users?
   - Fish detection (fishermen) = high priority
   - Bottom profiling (wreck hunters) = medium
   - Scientific export = nice to have

4. 📊 DATA VISUALIZATION:
   - Heatmap of fish detections
   - Bottom profile cross-sections
   - Time-series of fishing activity
   - Hazard overlay on existing maps

5. 🚀 EXPORT PIPELINE:
   - Implement KML generation (easy, high user value)
   - CSV export (fish locations + metadata)
   - GeoJSON (web mapping)
   - GeoTIFF optional (advanced users)
""")
