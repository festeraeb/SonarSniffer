# SonarSniffer Enhanced Enhancement System

## Overview

The enhanced enhancement system simplifies sonar image processing by separating automatic baseline enhancements from optional secondary enhancements.

### Philosophy

**Baseline (Automatic)**: Always applied to every sonar image
- No user configuration needed
- Provides best all-around quality
- Consistent, reproducible results
- Optimized specifically for sonar imagery

**Secondary (Optional)**: Applied selectively for specialized processing
- User-configurable sensitivity
- Trade-offs between processing time and quality
- Targets specific analysis goals

---

## Baseline Enhancements (Automatic)

Applied automatically to every mosaic image. No configuration required.

### 1. Contrast Stretching
- **Method**: Percentile-based stretching (2nd to 98th percentile)
- **Purpose**: Optimize contrast without outlier-driven clipping
- **Benefit**: Brings out subtle features while maintaining detail

### 2. Adaptive Histogram Equalization (CLAHE)
- **Method**: Contrast Limited Adaptive Histogram Equalization
  - Tile size: 8x8 pixels
  - Clip limit: 2.0
- **Purpose**: Enhance local contrast throughout image
- **Benefit**: Reveals details in both bright and dark regions

### 3. Edge Enhancement
- **Method**: Unsharp masking (Gaussian blur + weighted addition)
  - Strength: 0.3 (gentle)
  - Kernel: 5x5
- **Purpose**: Subtle sharpening without halos
- **Benefit**: Improves target visibility and edge definition

### 4. Bilateral Denoising
- **Method**: Bilateral filtering
  - Diameter: 5 pixels
  - Sigma color: 50
  - Sigma space: 50
- **Purpose**: Reduce noise while preserving edges
- **Benefit**: Cleaner images with maintained sharp boundaries

---

## Optional Secondary Enhancements

Configure in the GUI's "Optional Secondary Enhancements" section.

### 1. Automatic Gain Control (AGC)
- **When to use**: When range-dependent brightness variations are problematic
- **Sensitivity**: 0.0 (light) to 1.0 (aggressive)
- **Processing time**: Medium
- **Output**: Additional `_agc` version
- **Note**: Best used on raw mosaics, after baseline enhancement

### 2. Physically-Based Rendering (PBR)
- **When to use**: For advanced 3D visualization or material property analysis
- **Mode**: DIFFERENTIAL (pre-selected as best for sonar)
- **Features**: 
  - Fresnel-Schlick reflection equations
  - Physical material property simulation
  - Differential rendering for target contrast
- **Processing time**: High
- **Output**: Additional `_pbr` version

### 3. Automated Target Detection
- **When to use**: To identify and mark rocks, wrecks, anomalies
- **Sensitivity**: 0.0 (only strong targets) to 1.0 (include weak features)
- **Features**:
  - Multi-scale blob detection
  - Statistical anomaly analysis
  - Confidence scoring
  - Type classification (rock/wreck/anomaly)
- **Processing time**: Medium
- **Output**: Marked image with target overlays

### 4. Reference Data Overlay
- **When to use**: To add geospatial context to images
- **Features**:
  - Coordinate grid overlay
  - Depth markers
  - GPS/navigation data
  - Supports both static PNG and interactive HTML
- **Processing time**: Low
- **Output**: Overlay version or standalone HTML viewer

---

## File Structure

```
sonar_gui.py                    # Main GUI application
baseline_enhancements.py        # Baseline enhancement implementations
enhancement_pipeline.py         # Integration and pipeline management
```

---

## Enhancement Processing Workflow

```
1. USER LOADS RSD FILE
   ↓
2. GUI PARSES AND GENERATES MOSAICS
   ↓
3. AUTOMATIC BASELINE ENHANCEMENTS APPLIED
   ├─ Contrast Stretching
   ├─ Adaptive Histogram Equalization
   ├─ Edge Enhancement
   └─ Bilateral Denoising
   ↓
4. USER SELECTS OPTIONAL SECONDARY ENHANCEMENTS
   ├─ AGC (optional, configurable)
   ├─ PBR Rendering (optional, configurable)
   ├─ Target Detection (optional, configurable)
   └─ Reference Overlays (optional, configurable)
   ↓
5. OUTPUTS GENERATED
   ├─ baseline_enhanced (default, always)
   ├─ _agc (if AGC enabled)
   ├─ _pbr (if PBR enabled)
   ├─ _targets (if Target Detection enabled)
   └─ overlay variants (if overlays enabled)
```

---

## GUI Configuration

### Advanced Tab: Enhancement Settings

**Baseline Section**
- Display only: Shows what's automatically applied
- No user controls (these run on every image)

**Optional Secondary Enhancements Section**
- ✓ Automatic Gain Control (AGC) - Sensitivity slider (0.0-1.0)
- ✓ Physically-Based Rendering (PBR) - Toggle only (DIFFERENTIAL mode is default)
- ✓ Automated Target Detection - Sensitivity slider (0.0-1.0)
- ✓ Add Reference Data (Coordinates, Depth, GPS) - Toggle only

---

## Output File Naming

| Enhancement | Output Suffix | Example |
|-------------|---|---|
| Baseline (automatic) | `_enhanced` | `mosaic_enhanced.png` |
| AGC | `_agc` | `mosaic_agc.png` |
| PBR | `_pbr` | `mosaic_pbr.png` |
| Target Detection | `_targets` | `mosaic_targets.png` |
| Coordinate Overlay | `_overlay` | `mosaic_overlay.png` |

---

## Configuration Files

Each enhanced image gets a sidecar JSON file with enhancement parameters:

```json
{
  "enhancement": "baseline",
  "type": "contrast_stretch + adaptive_contrast + edge_enhance + denoise",
  "parameters": {
    "contrast_percentile_low": 2.0,
    "contrast_percentile_high": 98.0,
    "adaptive_clip_limit": 2.0,
    "adaptive_tile_size": 8,
    "edge_strength": 0.3,
    "bilateral_d": 5,
    "bilateral_sigma_color": 50,
    "bilateral_sigma_space": 50
  }
}
```

---

## Performance & Resource Usage

### Baseline Enhancements
- **Processing time per image**: 100-300ms
- **Memory overhead**: Minimal (in-place operations)
- **Always applied**: Every sonar image

### Secondary Enhancements (Optional)
| Enhancement | Time | Memory | Notes |
|---|---|---|---|
| AGC | 200ms | Medium | Adaptive algorithms |
| PBR | 1-5s | High | GPU-accelerated if available |
| Target Detection | 500-2000ms | Medium | Depends on image resolution |
| Overlays | 50-200ms | Low | Simple rendering |

---

## Best Practices

1. **Use Baseline by Default**: Baseline enhancements are optimized for sonar. They're sufficient for most analyses.

2. **Add AGC if**: You have significant range-dependent gain variations that baseline can't handle.

3. **Add PBR if**: You need advanced visualization or material property analysis.

4. **Add Target Detection if**: You're looking for specific objects (rocks, wrecks, anomalies).

5. **Add Overlays if**: You need geospatial context or are sharing with non-technical users.

---

## Troubleshooting

### "Baseline enhancement failed" warning
- Check disk space in output directory
- Verify input mosaic file is not corrupted
- Check file permissions

### PBR takes too long
- Disable PBR if not needed for your analysis
- PBR is GPU-accelerated if CUDA is available
- Consider processing smaller images first

### Target Detection finds too many false positives
- Reduce sensitivity slider (move toward 0.0)
- Ensure baseline enhancements produced clean image
- Check if image has significant noise

### Overlays look incorrect
- Verify coordinate data in source records
- Check if using correct viewer type (Static vs HTML)
- Ensure geo-reference bounds are reasonable

---

## Advanced Usage

### Batch Processing Secondary Enhancements

Use `EnhancementPipeline` and `SecondaryEnhancementApplier` classes:

```python
from enhancement_pipeline import EnhancementPipeline, SecondaryEnhancementApplier
from pathlib import Path
import cv2

# Apply baseline
success, baseline_path = EnhancementPipeline.apply_baseline_to_mosaic(
    "raw_mosaic.png",
    "output_directory"
)

# Apply secondary enhancements
if success:
    mosaic = cv2.imread(baseline_path)
    
    # Apply AGC
    agc_result = SecondaryEnhancementApplier.apply_agc(mosaic, sensitivity=0.7)
    cv2.imwrite("output_agc.png", agc_result)
    
    # Apply PBR
    pbr_result = SecondaryEnhancementApplier.apply_pbr(mosaic)
    cv2.imwrite("output_pbr.png", pbr_result)
    
    # Detect targets
    marked, targets = SecondaryEnhancementApplier.apply_target_detection(
        mosaic, sensitivity=0.5
    )
    cv2.imwrite("output_targets.png", marked)
```

---

## Version History

### v2.0 (Current)
- Introduced automatic baseline enhancements
- Simplified UI to show only essential options
- Separated baseline from secondary enhancements
- Added enhancement_pipeline.py for integration

### v1.0 (Previous)
- All enhancements were optional
- More complex UI with many configuration options
- No automatic enhancement on load

---

## Future Enhancements

Potential additions to baseline or secondary:
- AI-powered contrast optimization
- Spectral enhancement for frequency-specific targets
- Multi-beam adaptive processing
- Real-time GPU acceleration pipeline
- Machine learning-based enhancement suggestion
