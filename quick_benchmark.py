#!/usr/bin/env python3
"""
Quick GDAL Benchmark (Simplified)
Tests GDAL vs SciPy with smaller dataset to avoid timeout
"""

import sys
import time
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def quick_benchmark():
    """Run quick benchmark"""
    
    logger.info("=" * 70)
    logger.info("QUICK GDAL BENCHMARK")
    logger.info("=" * 70)
    
    # Check availability
    try:
        from osgeo import gdal
        gdal_avail = True
    except:
        gdal_avail = False
    
    try:
        from scipy import interpolate
        scipy_avail = True
    except:
        scipy_avail = False
    
    logger.info(f"\nBackends available:")
    logger.info(f"  GDAL:  {'YES' if gdal_avail else 'NO'}")
    logger.info(f"  SciPy: {'YES' if scipy_avail else 'NO'}")
    
    if not scipy_avail:
        logger.error("SciPy required for benchmark. Install: pip install scipy")
        return False
    
    # Small test
    logger.info("\n" + "-" * 70)
    logger.info("Test: Small (1000 points, 100x100 grid)")
    logger.info("-" * 70)
    
    np.random.seed(42)
    lons = np.random.uniform(-120, -119, 1000)
    lats = np.random.uniform(36, 37, 1000)
    depths = np.random.uniform(10, 100, 1000)
    
    lat_grid = np.linspace(36, 37, 100)
    lon_grid = np.linspace(-120, -119, 100)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    
    # SciPy RBF
    logger.info("\nSciPy RBF interpolation...")
    start = time.time()
    try:
        rbf = interpolate.Rbf(lons, lats, depths, function='thin_plate', smooth=0.1)
        depth_grid = rbf(lon_mesh, lat_mesh)
        scipy_time = time.time() - start
        logger.info(f"  OK: {scipy_time:.3f}s")
    except Exception as e:
        logger.warning(f"  Failed: {e}")
        scipy_time = None
    
    # GDAL (if available)
    gdal_time = None
    if gdal_avail:
        logger.info("\nGDAL rasterization...")
        try:
            from gdal_integration import create_bathymetric_grid
            start = time.time()
            grid, stats = create_bathymetric_grid(
                lons, lats, depths,
                lon_mesh, lat_mesh,
                use_gdal=True
            )
            gdal_time = stats.duration_seconds
            logger.info(f"  OK: {gdal_time:.3f}s (Method: {stats.method})")
        except Exception as e:
            logger.warning(f"  Failed: {e}")
    
    # Compare
    if scipy_time and gdal_time:
        speedup = scipy_time / gdal_time
        logger.info(f"\n*** Speedup: {speedup:.1f}x ***")
        if speedup >= 1:
            logger.info("✓ GDAL is faster!")
            return True
    
    logger.info("\n" + "=" * 70)
    logger.info("Benchmark complete")
    logger.info("=" * 70)
    return True

if __name__ == '__main__':
    success = quick_benchmark()
    sys.exit(0 if success else 1)
