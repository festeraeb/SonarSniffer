# CHIRP/ClearVue Data Integration Strategy

## Summary of CV-54-UHD.RSD Discovery

You were **absolutely right** about this being a special file type. Here's what we found:

### What CV-54-UHD.RSD Actually Is:
- **Raw CHIRP sonar data stream** from a Garmin echoMAP CV-54 (ClearVue model)
- **61,123 sonar frames** marked with 0x06 type byte
- **NOT wrapped in standard RSD container** - this is pure device output
- Likely **HDMI capture or device memory dump** from the transducer
- GT54 transducer data (5-point Mega Imaging)

### Why This Matters for Your Users:

**1. FISHERMEN**
- CHIRP is specifically engineered for fish detection
- Shows water column detail, fish schools as clear targets
- They want: Fish location maps in KML, fishing hotspot times, fish school depth/intensity
- Current GUI doesn't touch this - it's skipped

**2. WRECK HUNTERS & BOTTOM PROFILERS**
- CHIRP excels at bottom penetration and detail
- Can show sub-bottom layers (sediment, geological structure)
- Fills gaps left by side-scan passes (side-scan = lateral, CHIRP = vertical)
- They want: Bathymetric DEM, anomaly markers, cross-section profiles

**3. NAVIGATION/CHART MAKERS**
- Hazard detection (rocks, sandbars, wrecks below track)
- Safety warnings
- They want: Hazard markers in S-57 ENC format or KML

---

## The Critical Data Type Distinction

Your firmware analysis already identified this, but we need to emphasize:

### SideView (SV) - Channels [4, 5]
- Left/right imaging of seabed (like looking sideways)
- What we currently process: Videos, mosaics, georeferenced imagery
- Good for: Wreck detection, features, object identification

### DownView/ClearVue (CV) - Channels [6, 7, 8, 9, 10]
- Multiple frequency sonar looking straight down
- What we currently SKIP: Fishfinder data, water column, bottom profiles
- Good for: Fish detection, bottom structure, gap filling

**Your SideView RSD files likely DON'T have CHIRP data** - they're sidescan focused. But the **other files (XTF, JSF, SON) probably do have both**, and your GUI isn't handling the down-view channels.

---

## Recommended Implementation Order

### Phase 1: Immediate (This Week - Low Effort, High Value)
**Enable CHIRP Channel Processing in Standard RSD Files**

```
Current state: Channels 6-10 are SKIPPED
Target state:  Extract and process CHIRP channels
Effort:        2-3 hours
Value:         Enables fish detection in existing files
```

What to do:
1. Check if Sonar001.RSD or Sonar002.RSD have channels 6-10
2. Parse those channels (they're already in RSD format)
3. Convert to heatmap/intensity visualization
4. Export as KML with depth annotations
5. Show fish school stats (size, depth, intensity)

### Phase 2: Short-term (Next Week - Medium Effort, Medium Value)
**Parse CV-54-UHD.RSD Streaming Format**

```
Effort:  3-5 days
Value:   Unlocks proprietary CHIRP captures
Result:  Can process raw device data
```

Approach:
- Option A: Reverse-engineer frame structure (3-5 days, full understanding)
- Option B: Find Garmin decoder in firmware (faster if available)
- Option C: Search forums for existing CV format parsers

Key data:
- Frame 0: 262 bytes = header/config
- Frame 3: 19.4 KB = first payload
- Rest: 1-10 bytes = status/timing frames

### Phase 3: Integration (2-3 Weeks)
**GUI Enhancement for CHIRP Data**

```
New Tab: "Fish Detection & Bottom Profile"
├─ Heatmap view (intensity by location/depth)
├─ Fish school markers (KML export)
├─ Bottom profile cross-sections
├─ Water column visualization
└─ Time-series (when fish were detected)

Export options:
├─ KML (Google Earth, fishermen apps)
├─ CSV (fishing logs, analytics)
├─ GeoJSON (web mapping)
└─ GeoTIFF (bathymetric DEM)
```

---

## File-by-File Analysis

From your samples directory:

| File | Type | Contains | Status | Priority |
|------|------|----------|--------|----------|
| Sonar000.RSD | Standard RSD | Unknown mix | Parse & check | HIGH |
| Sonar001.RSD | Standard RSD | Unknown mix | Parse & check | HIGH |
| Sonar002.RSD | Standard RSD | Unknown mix | Parse & check | HIGH |
| Holloway.RSD | Standard RSD | Large file | Parse if time | MEDIUM |
| 93SV-UHD-GT56.RSD | UHD SideView | Side-scan only | Already handled | LOW |
| CV-54-UHD.RSD | **CHIRP Streaming** | **Pure CHIRP** | **REVERSE-ENGINEER** | **CRITICAL** |
| general_xtf_... | XTF | Likely has both | Parse | MEDIUM |
| edgetech_native... | JSF | Likely has both | Parse | MEDIUM |
| B001.SON | Garmin SON | Unknown | Research | MEDIUM |

---

## What We Know from Firmware

From `extract_lookup_tables.py`:
```python
24.72: {'name': 'CV/Chirp', 'channel_ids': [6, 7, 8, 9, 10]}
```

From firmware strings:
- echoMAP CHIRP: 53cv, 54cv, 55cv, 73cv, 74cv, 75cv series
- cv = ClearVue (down-looking CHIRP)
- dv = Down-view variant
- sv = SideView (traditional sidescan)

From `firmware_analysis_summary.py`:
```
Channel 6-10: CV/Chirp frequency channels
```

**This means the firmware already has data about these channels** - we can use it!

---

## Recommended Next Steps

### For CV-54-UHD.RSD Parsing:
1. **Search firmware** for CHIRP frame handlers (look for 0x06 byte handler)
2. **Parse Sonar001.RSD** with existing parser to compare
3. **Map channels 6-10** in standard RSD (should be easier)
4. **Then tackle CV-54-UHD** with knowledge of how CHIRP data is encoded

### For Fishermen Feature:
1. Create `FishDetectionExtractor` class
2. Find high-intensity pixels/clusters in CHIRP channels
3. Geoference them (lat/lon from navigation)
4. Export as KML with:
   - Fish school location (lat/lon/depth)
   - Timestamp (when detected)
   - Intensity (how strong signal)
   - Frequency (which channel detected it)

### For Bottom Profiling:
1. Create `BathymetricProcessor` class
2. Convert CHIRP data to depth values
3. Build DEM (digital elevation model)
4. Detect anomalies (significant bottom variations)
5. Export as:
   - GeoTIFF (professional analysis)
   - SVG profiles (reports)
   - KML anomalies (hazard maps)

---

## Key Questions to Answer

Before implementing, let's clarify:

1. **Fish Detection Focus?**
   - How many of your users are fishermen?
   - Do they want real-time, playback, or just hotspot maps?
   - Should we show video alongside detection?

2. **Wreck Hunting?**
   - How many users search for wrecks?
   - Do they need 3D models or 2D anomaly maps?
   - S-57 ENC format important for chart plotters?

3. **Scientific?**
   - Are there academic users?
   - Do they need publication-ready exports (SEG-Y, NetCDF)?
   - How important is water column visualization?

4. **Device Dumps?**
   - Will users often capture raw CHIRP like CV-54-UHD.RSD?
   - Or mostly standard RSD files with CHIRP channels?
   - Do we need real-time streaming support?

---

## Technical Breakdown

### CV-54-UHD Frame Structure (What We Know)
```
Frame 0 (262 bytes): Configuration
  Offset  Type     Value      Meaning
  0       BYTE     0x06       Frame type = CHIRP sonar
  1       BYTE     0x04       Frame subtype (config)
  2-3     WORD     0x7c4b     ? (needs analysis)
  4-5     WORD     0x26d9     Possibly timestamp/count
  6-7     WORD     0x0a00     ? 
  ...     ...      ...        More metadata

Frame 3 (19,426 bytes): Sonar Data Payload
  Offset  Type     Value      Meaning
  0       BYTE     0x06       Frame type
  1       BYTE     0xf9       Frame subtype (data)
  2-3     ?        ?          Payload structure
  ...     SONAR DATA (19KB of sample data)
```

### Next Investigation Steps
1. Compare with Sonar001.RSD channel 6-10 data structure
2. Look for repeating patterns in frame data
3. Identify sample encoding (8-bit, 16-bit, floating-point, compressed?)
4. Map GT54 transducer frequency bands

---

## Expected Timeline

| Phase | Task | Effort | Complexity | Blocker |
|-------|------|--------|-----------|---------|
| 1 | Enable existing CHIRP channels | 2h | Low | None |
| 2a | Search firmware for parsers | 1h | Low | None |
| 2b | Parse CV-54-UHD if decoder found | 4h | Low | Decoder availability |
| 2c | Reverse-engineer CV-54-UHD | 3-5d | High | Frame structure clarity |
| 3 | GUI integration | 2d | Medium | Phase 2 completion |
| 4 | KML/CSV export | 1d | Low | Phase 3 completion |
| 5 | Bathymetric export (GeoTIFF) | 2d | Medium | Phase 3 completion |
| 6 | Testing with real fishermen | Ongoing | - | User feedback |

---

## Your Decision Point

**Which direction appeals most?**

A. **Fishermen-focused**: Fish detection, heatmaps, KML exports
   - ROI: Large user base, clear use case
   - Effort: Medium (once CHIRP parsing works)
   - Competition: Existing apps (BassCast, Navily) - but none have full sonar viz

B. **Wreck/Research-focused**: Bathymetric DEMs, anomaly detection, scientific exports
   - ROI: Smaller but dedicated user base
   - Effort: Higher (DEMs, interpolation)
   - Competition: Minimal (unique capability)

C. **All-in**: Support both use cases equally
   - ROI: Maximum flexibility
   - Effort: Significant (4-6 weeks)
   - Result: Best-in-class multi-purpose tool

**My recommendation**: Start with A (fishermen), it has the clearest value prop. Then extend to B if demand warrants.

---

## Summary

**Your CV-54-UHD.RSD discovery is important because:**

1. ✅ It shows Garmin outputs raw CHIRP data (useful for research/debugging)
2. ✅ It's a new format not currently handled (reverse-engineering opportunity)
3. ✅ It proves demand for CHIRP processing (users capturing it for a reason)
4. ✅ It highlights a gap in current GUI (CHIRP channels skipped entirely)
5. ✅ It opens new user markets (fishermen, wreck hunters, scientists)

**Immediate actionable items:**
1. Parse one standard RSD file to enable existing CHIRP channels
2. Search firmware for CHIRP frame decoder functions
3. Decide on primary use case (fishermen vs. researchers)
4. Build accordingly

Want me to start with parsing Sonar001.RSD to see what CHIRP channels it contains?
