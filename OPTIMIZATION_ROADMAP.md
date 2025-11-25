# Optimization Roadmap - Next Phase

## Current State
✅ Complete Python pipeline working (CLI + GUI)  
✅ All components tested with synthetic data  
✅ Ready for real-world performance profiling  
✅ Identified 4 optimization targets  

---

## Phase 1: Performance Profiling (REQUIRED FIRST)

Before optimizing, we need to **measure real bottlenecks** with actual SAR data:

### What to Profile
1. **Parser**: Time to parse full Holloway RSD file
   - Current: ~0.01s for empty file (test file invalid)
   - Need: Full RSD file benchmark
   - Tool: `python -m cProfile`

2. **Geospatial Export**: Time per stage
   - KML generation: Currently ~10s for 500 points
   - MBTiles creation: Currently ~2s
   - DEM generation: Currently ~1.5s
   - Grid interpolation: Most expensive?

3. **Family Viewer**: Time to generate HTML
   - Current: ~0.05s (very fast, low priority)

4. **Memory Usage**: Peak RAM during processing
   - Current: Unknown (need to measure)
   - Large files could hit 1GB+

### Commands to Run
```bash
# Get full Holloway RSD file first
# Then measure parsing
python -c "
import cProfile
import pstats
from io import StringIO
from engine_classic_varstruct import parse_rsd_records_classic

pr = cProfile.Profile()
pr.enable()
records = list(parse_rsd_records_classic('holloway.rsd'))
pr.disable()

s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(20)
print(s.getvalue())
print(f'Total records: {len(records)}')
"

# Memory profiling
pip install memory_profiler
python -m memory_profiler engine_classic_varstruct.py
```

---

## Phase 2: Optimization Targets (Priority Order)

### 1. **PARSER OPTIMIZATION** ⚡ Likely Highest ROI

**Current Implementation**: `engine_classic_varstruct.py`  
**Type**: Pure Python generator parsing RSD binary format  
**Estimated Bottleneck**: Byte-level parsing in Python loop

**Python Implementation**:
```python
# In engine_classic_varstruct.py, roughly:
while pos < file_size:
    # Unpack bytes (slow in Python)
    header = unpack_from('>I', data, pos)
    depth = unpack_from('>f', data, pos+4)
    # ... more unpacking
    # Yield record (good for memory)
    yield record
```

**Optimization: Rust Wrapper**

Option A: Pure Rust (Best Performance)
```rust
// rust_rsd_parser/src/lib.rs
pub fn parse_rsd(file_path: &str) -> Vec<Record> {
    // Memory-mapped file IO
    // SIMD byte parsing where possible
    // Direct memory layout matching
    // Expected: 50-100x faster
}

#[pyclass]
pub struct RSDParser {
    #[pyo3(get)]
    records: Vec<Record>,
}

#[pymethods]
impl RSDParser {
    #[new]
    pub fn new(file_path: &str) -> Self { ... }
}
```

Option B: Hybrid (Easier Integration)
```python
# Wrap existing Rust code with PyO3
from _rsd_parser import parse_rsd  # C extension
records = parse_rsd('file.rsd')
```

**Development Effort**: 3-4 hours
**Expected Speedup**: 10-50x
**Risk**: Low (Python fallback available)

**Steps**:
1. Benchmark current parser (required)
2. Profile hotspots
3. Implement Rust wrapper
4. Add FFI bindings (PyO3)
5. Fallback to Python if unavailable
6. Test compatibility

---

### 2. **KML GENERATION OPTIMIZATION** 🗺️ Medium ROI

**Current Implementation**: `geospatial_exporter.py` - `KMLGenerator` class  
**Type**: Pure Python using matplotlib/scipy  
**Estimated Bottleneck**: Contour generation, KML XML creation

**Python Bottlenecks**:
```python
# In KMLGenerator._generate_contours():
# Slow: Python loop creating contours
for level in contour_levels:
    # Matplotlib contour generation (Python)
    contours = ax.contour(X, Y, Z, levels=[level])
    # XML string manipulation (slow)
    kml_string += generate_kml_from_contours(contours)
```

**Optimization: GDAL Integration**

GDAL (Geospatial Data Abstraction Library) is C++ with Python bindings:
```python
from osgeo import gdal, gdalconst

# Create GeoTIFF from points
ds = gdal.GetDriverByName('GTiff').Create('dem.tif', ...)

# Use GDAL's native contour generation (fast C++)
gdal.ContourGenerate(src_band, interval=5.0, ...)

# Direct KML output (GDAL native)
ogr.GetDriverByName('KML').CopyDataSource(ds, 'output.kml')
```

**Alternative: QGIS Python API**
```python
from qgis.core import QgsRasterLayer, QgsConrourRenderer
# QGIS has optimized contour rendering
```

**Development Effort**: 2-3 hours  
**Expected Speedup**: 5-20x  
**Risk**: Low (GDAL stable, widely used)  
**Requirement**: GDAL installed (`pip install gdal` or `conda install gdal`)

**Steps**:
1. Profile KML generation (required)
2. Identify contour step as bottleneck
3. Replace contour generation with GDAL
4. Test output compatibility
5. Add GDAL as optional dependency

---

### 3. **BATHYMETRIC INTERPOLATION** 🌊 Medium ROI

**Current Implementation**: `geospatial_exporter.py` - `BathymetricProcessor`  
**Type**: NumPy griddata interpolation  
**Estimated Bottleneck**: Creating 900x900 grid from scattered points

**Python Implementation**:
```python
# In BathymetricProcessor:
from scipy.interpolate import griddata

# Slow: Python wrapper around C library
Z = griddata((X, Y), values, (xi, yi), method='cubic')
# Creates 900x920 = 828,000 grid points
```

**Optimization Options**:

Option A: **Matlab**
```matlab
% bathymetric_interpolation.m
function Z = interpolate_sonar_data(X, Y, depth, method)
    [Xi, Yi] = meshgrid(...);
    Z = griddata(X, Y, depth, Xi, Yi, method);
    Z = smooth_bathymetry(Z);
end
```
Then wrap with `scipy.io.savemat` or `matlab.engine`

Option B: **C Extension**
```c
// bathymetry_c.c - Fast interpolation
#include <Python.h>
static PyObject* interpolate(PyObject* self, PyObject* args) {
    // Direct C implementation
    // No GIL release overhead
}
```

Option C: **Use GDAL Native Interpolation**
```python
from osgeo import gdal
# GDAL has faster interpolation routines
vrt = gdal.Translate(..., outputType=gdal.GDT_Float32)
```

**Development Effort**: 2-4 hours  
**Expected Speedup**: 3-10x  
**Risk**: Medium (depends on choice)  
**Recommendation**: Start with GDAL (lowest friction)

**Steps**:
1. Profile grid creation vs interpolation
2. Choose GDAL approach (easiest)
3. Replace griddata with GDAL
4. Test DEM output quality
5. Benchmark against current

---

### 4. **IMAGE PROCESSING** 🖼️ Lower Priority

**Current Implementation**: 
- `pbr_*.py` modules (already C++ OpenCV wrapped)
- `streaming_video_encoder.py` (already GPU accelerated)

**Status**: Already optimized!
- PBR: Uses compiled OpenCV (fast)
- Video: CUDA support, streaming buffer (24x memory reduction)
- No further optimization needed

---

## Phase 2a: Quick Wins (No Rust/C Needed)

Before complex optimizations, try these easy improvements:

### 1. **Caching**
```python
# Cache parsed records
@lru_cache(maxsize=10)
def parse_rsd_cached(file_path):
    return list(parse_rsd(file_path))
```

### 2. **Parallel Processing**
```python
# Process independent stages in parallel
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor() as exe:
    kml_task = exe.submit(export_kml, points)
    mbtiles_task = exe.submit(export_mbtiles, points)
    dem_task = exe.submit(export_dem, points)
    
    kml = kml_task.result()
    mbtiles = mbtiles_task.result()
    dem = dem_task.result()
```

### 3. **Numba JIT Compilation**
```python
import numba

@numba.jit(nopython=True, cache=True)
def interpolate_points(x, y, depth, xi, yi):
    # Compiled C code
    ...
```

**Expected speedup**: 2-5x  
**Time to implement**: 1 hour  
**No external dependencies**

---

## Decision Matrix

| Target | Speedup | Effort | Risk | Priority |
|--------|---------|--------|------|----------|
| Parser (Rust) | 10-50x | 4h | Low | **HIGH** |
| KML (GDAL) | 5-20x | 3h | Low | **HIGH** |
| Bathymetry (GDAL) | 3-10x | 3h | Low | **MEDIUM** |
| Interpolation (Matlab) | 3-10x | 4h | Medium | **MEDIUM** |
| Quick wins (Numba) | 2-5x | 1h | Low | **NOW** |

---

## Recommended Execution Order

### Week 1: Quick Wins + Profiling
1. **Day 1-2**: Profiling with real data
   - Get actual Holloway RSD file
   - Run benchmarks on current pipeline
   - Identify actual bottleneck
   
2. **Day 3**: Numba optimization (easy win)
   - Add `@numba.jit` to expensive loops
   - Parallel processing setup
   - Measure improvement

### Week 2: Major Optimization
3. **Day 4-6**: GDAL KML/Bathymetry
   - Install GDAL
   - Implement new KML generator
   - Implement new interpolation
   - Test compatibility

4. **Day 7**: Rust Parser (if parser is bottleneck)
   - Benchmark confirms parser is slow
   - Implement Rust wrapper
   - FFI integration
   - Fallback handling

### Week 3: Production
5. **Day 8-9**: Testing & Performance
   - Real-world SAR file testing
   - Performance comparison
   - Error handling
   
6. **Day 10**: Deployment
   - Documentation
   - Version bump
   - Release

---

## Success Criteria

✅ **Current State** (before optimization):
- Full pipeline: ~15 seconds for 500 points
- Memory: Unknown (need to measure)
- Works on Windows/Mac/Linux

✅ **Target After Optimization**:
- Full pipeline: <5 seconds for 500 points
- Large files (10,000+ points): <30 seconds
- Memory: <500 MB for large surveys
- Error handling preserved
- CLI + GUI both functional

---

## Dependencies to Add

If we implement all optimizations:

```bash
# Rust (for parser)
pip install PyO3  # Actually: cargo new --name python-bindings

# GDAL (for KML/bathymetry)
conda install gdal  # OR pip install gdal

# Numba (quick wins)
pip install numba

# Optional: Matlab
# License required, probably skip

# Optional: QGIS
# conda install qgis
```

---

## Rollback Plan

All optimizations have Python fallbacks:
1. Parser: If Rust fails, use Python
2. KML: If GDAL unavailable, use current matplotlib
3. Bathymetry: If GDAL fails, use scipy.griddata
4. Numba: Pure Python works without it

**Zero risk of breaking existing pipeline**

---

## Next Action

**[REQUIRED] Run profiling on real Holloway RSD data:**

```bash
# 1. Get actual Holloway.RSD file (ask user)
# 2. Run benchmark:
python -m cProfile -o profile.stats test_full_pipeline_holloway.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(30)"

# 3. Analyze results:
# - Which function takes most time?
# - Parser? KML generation? Interpolation?
# - Memory peaks?

# 4. Decide optimization strategy:
# - If parser > 50%: Rust wrapper
# - If KML > 30%: GDAL integration
# - If both: Do both in parallel
```

**Once we know the bottleneck, optimization is straightforward.**

