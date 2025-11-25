#!/usr/bin/env python3
"""
GDAL vs SciPy Benchmark Test
Compares performance of GDAL rasterization vs SciPy RBF interpolation
"""

import sys
import time
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_benchmark():
    """Run comprehensive GDAL vs SciPy benchmark"""
    
    logger.info("=" * 70)
    logger.info("GDAL vs SciPy Bathymetric Interpolation Benchmark")
    logger.info("=" * 70)
    
    # Check what's available
    scipy_available = False
    gdal_available = False
    
    try:
        import scipy.interpolate
        scipy_available = True
        logger.info("✓ SciPy available")
    except ImportError:
        logger.warning("✗ SciPy not available")
    
    try:
        from osgeo import gdal
        gdal_available = True
        logger.info("✓ GDAL available")
    except ImportError:
        logger.warning("✗ GDAL not available")
    
    if not scipy_available and not gdal_available:
        logger.error("Neither SciPy nor GDAL available. Install with: pip install scipy gdal")
        return False
    
    # Test parameters
    test_configs = [
        {'points': 1000, 'grid': 500, 'name': 'Small'},
        {'points': 5000, 'grid': 1000, 'name': 'Medium'},
        {'points': 10000, 'grid': 2000, 'name': 'Large'},
    ]
    
    results = []
    
    for config in test_configs:
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Test: {config['name']} ({config['points']} points, {config['grid']}x{config['grid']} grid)")
        logger.info('=' * 70)
        
        # Generate test data
        np.random.seed(42)
        lons = np.random.uniform(-120, -119, config['points'])
        lats = np.random.uniform(36, 37, config['points'])
        depths = np.random.uniform(10, 100, config['points'])
        
        logger.info(f"Generated {config['points']} random points")
        
        test_result = {
            'name': config['name'],
            'points': config['points'],
            'grid_size': config['grid'],
            'gdal_time': None,
            'scipy_time': None,
            'speedup': None,
        }
        
        # Test GDAL
        if gdal_available:
            logger.info("\nTesting GDAL rasterization...")
            try:
                import tempfile
                from gdal_optimization_core import GDALOptimizer, GDALConfig
                
                config_obj = GDALConfig()
                optimizer = GDALOptimizer(config_obj)
                
                with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as f:
                    output_path = f.name
                
                start = time.time()
                success = optimizer.create_dem_from_points(
                    lons, lats, depths,
                    output_path,
                    resolution=0.0001
                )
                gdal_time = time.time() - start
                
                if success:
                    logger.info(f"✓ GDAL completed in {gdal_time:.2f}s")
                    test_result['gdal_time'] = gdal_time
                else:
                    logger.warning("GDAL rasterization failed")
                
                # Cleanup
                try:
                    Path(output_path).unlink()
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"GDAL benchmark failed: {e}")
        
        # Test SciPy
        if scipy_available:
            logger.info("\nTesting SciPy RBF interpolation...")
            try:
                from scipy import interpolate
                
                # Create grid
                lat_min, lat_max = lats.min(), lats.max()
                lon_min, lon_max = lons.min(), lons.max()
                lat_grid = np.linspace(lat_min, lat_max, config['grid'])
                lon_grid = np.linspace(lon_min, lon_max, config['grid'])
                lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
                
                start = time.time()
                try:
                    rbf = interpolate.Rbf(lons, lats, depths, function='thin_plate', smooth=0.1)
                    depth_grid = rbf(lon_mesh, lat_mesh)
                    scipy_time = time.time() - start
                    logger.info(f"✓ SciPy RBF completed in {scipy_time:.2f}s")
                    test_result['scipy_time'] = scipy_time
                except Exception as rbf_err:
                    logger.warning(f"RBF failed, trying linear: {rbf_err}")
                    from scipy.interpolate import griddata
                    start = time.time()
                    depth_grid = griddata((lons, lats), depths, (lon_mesh, lat_mesh), method='linear')
                    scipy_time = time.time() - start
                    logger.info(f"✓ SciPy linear completed in {scipy_time:.2f}s")
                    test_result['scipy_time'] = scipy_time
                    
            except Exception as e:
                logger.error(f"SciPy benchmark failed: {e}")
        
        # Calculate speedup
        if test_result['gdal_time'] and test_result['scipy_time']:
            speedup = test_result['scipy_time'] / test_result['gdal_time']
            test_result['speedup'] = speedup
            logger.info(f"\n{'SPEEDUP: GDAL is ' + f'{speedup:.1f}x FASTER than SciPy':^70}")
        
        results.append(test_result)
    
    # Print summary
    logger.info(f"\n\n{'=' * 70}")
    logger.info("BENCHMARK SUMMARY")
    logger.info('=' * 70)
    
    print("\n{:<12} {:<10} {:<12} {:<12} {:<10}".format(
        "Test", "Points", "GDAL (s)", "SciPy (s)", "Speedup"
    ))
    print("-" * 60)
    
    total_gdal = 0
    total_scipy = 0
    
    for r in results:
        gdal_str = f"{r['gdal_time']:.2f}" if r['gdal_time'] else "N/A"
        scipy_str = f"{r['scipy_time']:.2f}" if r['scipy_time'] else "N/A"
        speedup_str = f"{r['speedup']:.1f}x" if r['speedup'] else "N/A"
        
        print("{:<12} {:<10} {:<12} {:<12} {:<10}".format(
            r['name'], r['points'], gdal_str, scipy_str, speedup_str
        ))
        
        if r['gdal_time']:
            total_gdal += r['gdal_time']
        if r['scipy_time']:
            total_scipy += r['scipy_time']
    
    print("-" * 60)
    
    if total_gdal > 0 and total_scipy > 0:
        overall_speedup = total_scipy / total_gdal
        print("{:<12} {:<10} {:<12.2f} {:<12.2f} {:<10.1f}x".format(
            "TOTAL", "", total_gdal, total_scipy, overall_speedup
        ))
        logger.info(f"\n✓ Overall speedup: {overall_speedup:.1f}x faster with GDAL")
    
    logger.info("\n" + "=" * 70)
    logger.info("CONCLUSION")
    logger.info("=" * 70)
    
    if gdal_available and scipy_available and total_gdal > 0 and total_scipy > 0:
        overall_speedup = total_scipy / total_gdal
        if overall_speedup >= 5:
            logger.info(f"✓ GDAL is {overall_speedup:.1f}x faster - ready for production use")
            logger.info("✓ Recommendation: Replace SciPy RBF with GDAL in geospatial_exporter.py")
            return True
        elif overall_speedup >= 1:
            logger.info(f"✓ GDAL is {overall_speedup:.1f}x faster - use for large datasets")
            return True
        else:
            logger.info("✗ GDAL not faster on tested datasets")
            return False
    else:
        logger.warning("Could not complete full benchmark (missing packages)")
        return False

if __name__ == '__main__':
    success = run_benchmark()
    sys.exit(0 if success else 1)
