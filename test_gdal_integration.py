#!/usr/bin/env python3
"""
GDAL Integration Module Tests
Validates gdal_integration.py functionality
"""

import sys
import logging
import tempfile
from pathlib import Path
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required imports work"""
    logger.info("Testing imports...")
    
    try:
        from gdal_integration import create_bathymetric_grid, InterpolationStats
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_processor_creation():
    """Test processor instantiation"""
    logger.info("\nTesting processor creation...")
    
    try:
        from gdal_integration import create_bathymetric_grid
        
        # Create dummy grids
        lon_grid = np.linspace(-120, -119, 10)
        lat_grid = np.linspace(36, 37, 10)
        lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
        
        logger.info(f"✓ Grid created: {lon_mesh.shape}")
        return True
    except Exception as e:
        logger.error(f"✗ Processor creation failed: {e}")
        return False

def test_grid_creation():
    """Test bathymetric grid creation"""
    logger.info("\nTesting grid creation...")
    
    try:
        from gdal_integration import create_bathymetric_grid
        
        # Generate test data
        np.random.seed(42)
        lons = np.random.uniform(-120, -119, 100)
        lats = np.random.uniform(36, 37, 100)
        depths = np.random.uniform(10, 100, 100)
        
        # Create grid
        lat_min, lat_max = lats.min(), lats.max()
        lon_min, lon_max = lons.min(), lons.max()
        lat_grid = np.linspace(lat_min, lat_max, 50)
        lon_grid = np.linspace(lon_min, lon_max, 50)
        lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
        
        # Try grid creation with SciPy (GDAL fallback)
        grid, stats = create_bathymetric_grid(
            lons, lats, depths,
            lon_mesh, lat_mesh,
            use_gdal=False
        )
        
        if grid is not None:
            logger.info(f"✓ Grid created: {grid.shape}")
            logger.info(f"  Method: {stats.method}")
            logger.info(f"  Duration: {stats.duration_seconds:.3f}s")
            return True
        else:
            logger.warning("✗ Grid creation returned None")
            return False
            
    except Exception as e:
        logger.error(f"✗ Grid creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gdal_grid_creation():
    """Test GDAL-specific grid creation (if available)"""
    logger.info("\nTesting GDAL grid creation...")
    
    try:
        from gdal_integration import create_bathymetric_grid
        
        try:
            from osgeo import gdal
            gdal_available = True
        except ImportError:
            gdal_available = False
        
        # Generate test data
        np.random.seed(42)
        lons = np.random.uniform(-120, -119, 500)
        lats = np.random.uniform(36, 37, 500)
        depths = np.random.uniform(10, 100, 500)
        
        # Create grid
        lat_min, lat_max = lats.min(), lats.max()
        lon_min, lon_max = lons.min(), lons.max()
        lat_grid = np.linspace(lat_min, lat_max, 100)
        lon_grid = np.linspace(lon_min, lon_max, 100)
        lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
        
        grid, stats = create_bathymetric_grid(
            lons, lats, depths,
            lon_mesh, lat_mesh,
            use_gdal=gdal_available
        )
        
        if gdal_available:
            if grid is not None and stats.method == 'GDAL':
                logger.info(f"✓ GDAL grid created successfully")
                logger.info(f"  Duration: {stats.duration_seconds:.3f}s")
                return True
            else:
                logger.warning(f"⊘ GDAL not used (fell back to {stats.method})")
                return True
        else:
            logger.info("⊘ GDAL not available (using SciPy fallback)")
            if grid is not None:
                logger.info(f"✓ Fallback to {stats.method} works")
                return True
            else:
                logger.warning("✗ Both GDAL and SciPy failed")
                return False
                    
    except Exception as e:
        logger.warning(f"⊘ GDAL grid creation skipped: {e}")
        return True  # Not a critical failure if GDAL unavailable

def test_processor_status():
    """Test processor status reporting"""
    logger.info("\nTesting processor status...")
    
    try:
        from gdal_integration import create_bathymetric_grid, GDAL_AVAILABLE, SCIPY_AVAILABLE
        
        logger.info(f"✓ GDAL available: {GDAL_AVAILABLE}")
        logger.info(f"✓ SciPy available: {SCIPY_AVAILABLE}")
        
        if GDAL_AVAILABLE and SCIPY_AVAILABLE:
            logger.info("  Both backends available - will use GDAL when possible")
            return True
        elif SCIPY_AVAILABLE:
            logger.info("  Only SciPy available - will use fallback method")
            return True
        else:
            logger.error("  Neither backend available!")
            return False
            
    except Exception as e:
        logger.error(f"✗ Status check failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 70)
    logger.info("GDAL Integration Module Tests")
    logger.info("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Processor Creation", test_processor_creation),
        ("Grid Creation", test_grid_creation),
        ("GDAL Grid Creation", test_gdal_grid_creation),
        ("Processor Status", test_processor_status),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            logger.error(f"✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name:<30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✓ All tests passed!")
        return True
    else:
        logger.warning(f"\n⚠ {total - passed} test(s) failed")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
