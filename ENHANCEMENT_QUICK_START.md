# Enhancement System Quick Start Guide

## For End Users

### The Easy Way (Most Users)

1. **Load your RSD file**
   - File → Open RSD File
   - Select your sonar data file
   - Click Process

2. **Done!** 
   - Your mosaics are automatically enhanced with optimal baseline settings
   - Output: `*_enhanced.png` files with superior image quality
   - No configuration needed

### Want More? (Advanced Analysis)

Go to **Advanced Tab → Optional Secondary Enhancements**:

#### Automatic Gain Control (AGC)
- **When**: Your image has brightness varying across the range
- **How**: Check the box and adjust Sensitivity (0.0 = light, 1.0 = aggressive)
- **Result**: Additional `*_agc.png` file

#### Physically-Based Rendering (PBR)
- **When**: You want advanced material property visualization
- **How**: Just check the box (DIFFERENTIAL mode is pre-selected as best for sonar)
- **Result**: Additional `*_pbr.png` file with enhanced 3D-like appearance

#### Automated Target Detection
- **When**: You're looking for rocks, wrecks, or anomalies
- **How**: Check the box and adjust Sensitivity (0.0 = only strong targets, 1.0 = include weak features)
- **Result**: Additional `*_targets.png` with detected targets marked and confidence scores

#### Reference Data Overlay
- **When**: You need geospatial context for navigation/reporting
- **How**: Just check the box
- **Result**: Additional overlay version with coordinate grid and depth markers

---

## For Developers

### Use the Enhancement Classes

```python
from baseline_enhancements import BaselineEnhancer
from enhancement_pipeline import EnhancementPipeline, SecondaryEnhancementApplier
import numpy as np
import cv2

# Load a sonar image
image = cv2.imread('sonar_mosaic.png')
image_array = np.array(image)

# Apply baseline (automatic, no parameters)
baseline = BaselineEnhancer.apply_baseline_enhancements(image_array)

# Save baseline result
cv2.imwrite('output_baseline.png', baseline)

# Optional: Apply secondary enhancements
# AGC enhancement
agc_result = SecondaryEnhancementApplier.apply_agc(baseline, sensitivity=0.7)
cv2.imwrite('output_agc.png', agc_result)

# PBR rendering
pbr_result = SecondaryEnhancementApplier.apply_pbr(baseline, mode='DIFFERENTIAL')
cv2.imwrite('output_pbr.png', pbr_result)

# Target detection
marked, targets = SecondaryEnhancementApplier.apply_target_detection(
    baseline, sensitivity=0.5
)
cv2.imwrite('output_targets.png', marked)
print(f"Found {len(targets)} targets")
```

### Batch Processing Example

```python
from enhancement_pipeline import EnhancementPipeline
from pathlib import Path

# Process all mosaics in a directory
mosaic_dir = Path('mosaics/')
output_dir = Path('enhanced_output/')

for mosaic_file in mosaic_dir.glob('*.png'):
    print(f"Processing {mosaic_file.name}...")
    success, enhanced_path = EnhancementPipeline.apply_baseline_to_mosaic(
        str(mosaic_file),
        str(output_dir),
        create_backup=False
    )
    
    if success:
        print(f"  ✓ Baseline: {enhanced_path}")
        
        # Optionally apply secondary enhancements
        from enhancement_pipeline import SecondaryEnhancementApplier
        import cv2
        
        img = cv2.imread(enhanced_path)
        agc_img = SecondaryEnhancementApplier.apply_agc(img, 0.6)
        cv2.imwrite(str(output_dir / f"{mosaic_file.stem}_agc.png"), agc_img)
```

### Extending with Custom Enhancements

```python
from baseline_enhancements import BaselineEnhancer
import numpy as np
import cv2

class CustomEnhancer(BaselineEnhancer):
    """Extend baseline with custom enhancement"""
    
    @staticmethod
    def apply_custom_stretch(img: np.ndarray, power: float = 1.5) -> np.ndarray:
        """Apply power-law stretching"""
        normalized = img.astype(np.float32) / 255.0
        stretched = np.power(normalized, power) * 255.0
        return np.uint8(np.clip(stretched, 0, 255))

# Use it
enhanced = BaselineEnhancer.apply_baseline_enhancements(image)
custom = CustomEnhancer.apply_custom_stretch(enhanced, power=1.2)
```

---

## Command Line Usage

### Basic Processing

```bash
# Process single file with baseline only
python -c "
from enhancement_pipeline import EnhancementPipeline
EnhancementPipeline.apply_baseline_to_mosaic(
    'input_mosaic.png',
    'output_directory/'
)
"
```

### Batch Processing with Secondary Enhancements

```bash
# Create Python script: process_batch.py
from pathlib import Path
from enhancement_pipeline import EnhancementPipeline, SecondaryEnhancementApplier
import cv2
import numpy as np

input_dir = Path('raw_mosaics')
output_dir = Path('processed')
output_dir.mkdir(exist_ok=True)

for mosaic in input_dir.glob('*.png'):
    # Baseline
    success, enhanced = EnhancementPipeline.apply_baseline_to_mosaic(
        str(mosaic), str(output_dir)
    )
    
    if success:
        # Secondary enhancements
        img = cv2.imread(enhanced)
        
        # AGC
        agc = SecondaryEnhancementApplier.apply_agc(img, 0.6)
        cv2.imwrite(str(output_dir / f"{mosaic.stem}_agc.png"), agc)
        
        # Target detection
        marked, targets = SecondaryEnhancementApplier.apply_target_detection(img, 0.5)
        cv2.imwrite(str(output_dir / f"{mosaic.stem}_targets.png"), marked)

# Run:
# python process_batch.py
```

---

## Architecture Overview

```
sonar_gui.py (Main Application)
    │
    ├─ File Selection & RSD Parsing
    │
    ├─ Mosaic Generation
    │
    └─ Enhancement Processing
         │
         ├─ [AUTOMATIC] baseline_enhancements.py
         │   └─ Apply optimized baseline to every image
         │
         └─ [OPTIONAL] enhancement_pipeline.py
             ├─ EnhancementPipeline
             │   └─ Orchestrate baseline application
             │
             └─ SecondaryEnhancementApplier
                 ├─ apply_agc()
                 ├─ apply_pbr()
                 ├─ apply_target_detection()
                 └─ apply_coordinate_overlay()
```

---

## Output Files Explained

For input file: `channel_01_mosaic.png`

| File | Generated | When | Purpose |
|------|-----------|------|---------|
| `channel_01_mosaic_enhanced.png` | Always | Processing starts | Baseline enhanced (default result) |
| `channel_01_mosaic_enhanced.json` | Always | With baseline | Metadata about enhancement parameters |
| `channel_01_mosaic_agc.png` | Optional | AGC enabled | Additional AGC pass |
| `channel_01_mosaic_pbr.png` | Optional | PBR enabled | Physically-based rendering |
| `channel_01_mosaic_targets.png` | Optional | Target detection enabled | Targets marked with confidence |
| `channel_01_mosaic_overlay.png` | Optional | Coordinate overlay enabled | With grid and reference data |

---

## Troubleshooting

### "Baseline enhancement failed" error
**Check:**
- Does output directory exist and is writable?
- Is input mosaic file valid PNG/JPG?
- Is there sufficient disk space?

**Solution:**
```python
from pathlib import Path
Path('output_dir').mkdir(parents=True, exist_ok=True)
```

### Enhancement takes too long
**If you see slow processing on AGC or PBR:**
- AGC uses adaptive algorithms - normal
- PBR uses GPU if available - check CUDA installation
- Target detection varies with resolution
- Can disable optional enhancements if speed critical

### Results look wrong
**If baseline enhancement looks incorrect:**
- Input may be corrupted
- Try reprocessing the RSD file
- Check if mosaic has unusual format

**If secondary enhancement looks wrong:**
- Adjust sensitivity sliders
- Baseline image must be good quality first
- PBR works best with clean baseline

---

## Performance Tips

1. **Baseline is Fast**: Only ~300ms per image, always worth it
2. **Disable Unnecessary Secondary**: Each adds processing time
3. **Target Detection is Slowest**: 500-2000ms per image depending on resolution
4. **Batch Processing**: Process multiple files in parallel threads
5. **GPU Acceleration**: PBR is GPU-accelerated if CUDA available

---

## Best Practices

✅ **Do:**
- Use baseline enhancement (it's automatic and optimal)
- Enable secondary enhancements only when needed
- Save all output versions (baseline + any enabled secondary)
- Review enhancement parameters in JSON sidecars

❌ **Don't:**
- Disable baseline enhancement (no reason to)
- Enable all secondary enhancements unless you need them (wastes time)
- Overwrite original mosaic files
- Ignore error messages

---

## Version & Updates

**Current Version**: 2.0 (Automatic Baseline + Optional Secondary)

**What's New:**
- Automatic baseline enhancement (no configuration)
- Simplified UI (fewer options = better defaults)
- Modular architecture (reusable enhancement classes)
- Better documentation
- Consistent output quality

**Previous**: v1.0 (All enhancements optional)

---

## Support & Issues

For problems or questions:
1. Check ENHANCEMENT_SYSTEM.md for detailed technical info
2. Review BEFORE_AFTER_ANALYSIS.md for architecture changes
3. Check error messages in application output
4. Review JSON sidecar files for enhancement parameters used

