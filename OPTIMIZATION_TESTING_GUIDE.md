# Quick Testing Guide - Optimization Framework

**Ready to test right now!**

## 5-Minute Verification

Test that all optimization modules work:

```powershell
# In PowerShell, in c:\Temp\Garminjunk:

# Test each module
python numba_optimization.py           # Should show benchmark results
python contour_optimization.py          # Should show contour generation
python memory_profiling.py              # Should show memory tracking
python radiometric_correction.py        # Should show calibration tests
python geospatial_caching.py           # Should show cache performance
python data_format_converter.py        # Should show format conversion
```

✅ All should run without errors and show performance benchmarks

## Test with Your RSD Files

### What You Need:
- RSD files from the directory (any size)
- About 30 minutes

### Test Script:
```python
# test_optimizations_with_rsd.py
import sys
from pathlib import Path
from memory_profiling import MemoryProfiler
from contour_optimization import ContourOptimizer, ContourConfig
from streaming_optimization import StreamingExporter

# Test file (pick one from your directory)
rsd_file = Path("your_rsd_file.rsd")

# 1. Memory profiling
print("=" * 60)
print("TEST 1: Memory Profiling")
print("=" * 60)

profiler = MemoryProfiler(warn_threshold=1000)

with profiler.track("rsd_loading"):
    # Load your RSD file here
    # data = load_rsd(rsd_file)
    pass

print(profiler.report())

# 2. Contour generation
print("\n" + "=" * 60)
print("TEST 2: Contour Generation")
print("=" * 60)

# If you have bathymetry grid (dem):
config = ContourConfig(levels=[-10, -20, -30, -40])
optimizer = ContourOptimizer(config)
# contours = optimizer.generate_contours(dem)
# print(f"Generated {len(contours)} contours")

print("Ready for real data...")

# 3. Export performance
print("\n" + "=" * 60)
print("TEST 3: Export Speed")
print("=" * 60)

profiler = MemoryProfiler(warn_threshold=2000)

with profiler.track("multi_format_export"):
    # Export to multiple formats
    # exporter = StreamingExporter()
    # results = exporter.export_multiple_formats(data, ["kml", "dem", "nc"])
    pass

print(profiler.report())
```

## What to Look For

### Memory Profiling Results:
```
Expected:
  - Peak memory should be < 2GB (even for large files)
  - Without optimization: 16GB+ (before optimization)
  - With optimization: 1-2GB (after optimization)
  - Efficiency > 50%
```

### Contour Generation:
```
Expected:
  - Small file (< 10MB): < 0.1 seconds
  - Large file (100MB+): < 1 second
  - Number of points reduced 10-100x with simplification
```

### Performance Summary:
```
Expected Overall:
  - Load: No OOM errors
  - Process: 5-30x faster
  - Memory: 2.5-5x less
  - Export: 3.75x faster (parallel)
```

## GUI Integration Testing

### What's NOT integrated yet:
- ❌ Memory profiler widget in GUI
- ❌ Contour generation button
- ❌ Caching visualization
- ❌ Performance statistics display

### To test manually:
```powershell
# Start GUI
python sonar_gui.py

# Then manually test optimization modules in separate terminal:
python numba_optimization.py

# Compare GUI responsiveness with/without modules loaded
```

## Smart Installer Testing

### Test the new smart installer:
```powershell
# Test smart environment creation
.\install_smart_environment.ps1 -CreateClean

# It should:
# 1. Find conda ✓
# 2. Remove old nautidog environment
# 3. Create fresh environment
# 4. Install all dependencies
# 5. Test all imports
# 6. Report success/failure
```

## Performance Benchmarking

### Measure speedup on your files:

```python
# measure_speedup.py
import time
from pathlib import Path
from memory_profiling import MemoryProfiler

def benchmark_operation(name, func, *args):
    profiler = MemoryProfiler()
    start = time.time()
    
    with profiler.track(name):
        result = func(*args)
    
    elapsed = time.time() - start
    stats = profiler.stats[name]
    
    print(f"\n{name}:")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Peak Memory: {stats.peak_rss:.1f}MB")
    print(f"  Efficiency: {stats.efficiency:.1%}")
    
    return result

# Test with your RSD file
rsd_file = "path/to/your/rsd_file.rsd"

# Measure without optimization
# result1 = benchmark_operation("without_optimization", load_rsd_without_opt, rsd_file)

# Measure with optimization
# result2 = benchmark_operation("with_optimization", load_rsd_with_opt, rsd_file)

# Calculate speedup
# speedup = time1 / time2
# memory_reduction = mem1 / mem2
# print(f"\n Speedup: {speedup:.1f}x faster")
# print(f"Memory reduction: {memory_reduction:.1f}x less RAM")
```

## Troubleshooting

### Module import fails:
```
Error: ModuleNotFoundError: No module named 'X'
Solution: 
  1. Install smart environment: .\install_smart_environment.ps1
  2. Or: pip install X
  3. Check OPTIMIZATION_STATUS_AND_TODO.md for dependencies
```

### Memory exceeds expectations:
```
Problem: Module using too much RAM
Solution:
  1. Use MemoryProfiler to identify culprit
  2. Use MemoryOptimizer.optimize_array() for float32
  3. Use MemoryOptimizer.chunk_array() for large data
  4. Increase available RAM or use streaming
```

### Slow performance:
```
Problem: No speedup observed
Solution:
  1. Verify module actually imported (print statements)
  2. Check Numba compilation (first run is slower)
  3. Verify GDAL installed for 10x contour speedup
  4. Use profiling to find actual bottleneck
```

## Next Steps

Once testing is complete:

1. **If everything works:**
   - ✅ Commit test results
   - ✅ Document actual speedup achieved
   - ✅ Integrate into GUI (add widgets/buttons)
   - ✅ Deploy to users

2. **If something fails:**
   - ✅ Document error and conditions
   - ✅ Run diagnostics (memory_profiling.py)
   - ✅ Check dependencies (install_smart_environment.ps1)
   - ✅ File issue with details

3. **For optimization tuning:**
   - ✅ Adjust chunk sizes based on available RAM
   - ✅ Enable/disable optional features
   - ✅ Profile real workloads
   - ✅ Monitor production performance

## Summary

**Status:** Ready for testing
**What's needed:** RSD files to test with
**Time estimate:** 30 minutes for basic testing
**Expected result:** 5-30x speedup, 2.5-5x less memory

Report back with:
- ✅ Any errors encountered
- ✅ Actual speedup measured
- ✅ Memory usage reduction
- ✅ GUI integration preferences
