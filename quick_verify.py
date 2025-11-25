#!/usr/bin/env python3
"""
Quick GDAL & SciPy Verification
Lightweight check that packages are properly installed and working
"""

import sys

def check_scipy():
    """Check SciPy installation"""
    try:
        import scipy
        from scipy import interpolate
        print(f"✓ SciPy {scipy.__version__} with interpolate module")
        return True
    except ImportError as e:
        print(f"✗ SciPy: {e}")
        return False

def check_gdal():
    """Check GDAL installation"""
    try:
        from osgeo import gdal
        version = gdal.__version__
        print(f"✓ GDAL {version} with osgeo bindings")
        
        # Test GDAL functionality
        driver = gdal.GetDriverByName('GTiff')
        if driver:
            print("  ✓ GeoTIFF driver available")
        return True
    except ImportError as e:
        print(f"✗ GDAL: {e}")
        return False
    except Exception as e:
        print(f"⚠ GDAL installed but with issues: {e}")
        return False

def check_numpy():
    """Check NumPy installation"""
    try:
        import numpy
        print(f"✓ NumPy {numpy.__version__}")
        return True
    except ImportError as e:
        print(f"✗ NumPy: {e}")
        return False

def main():
    print("=" * 70)
    print("GDAL & SciPy Installation Verification")
    print("=" * 70)
    print()
    
    results = {
        'NumPy': check_numpy(),
        'SciPy': check_scipy(),
        'GDAL': check_gdal(),
    }
    
    print()
    print("-" * 70)
    
    all_ok = all(results.values())
    
    if all_ok:
        print("✓ All packages installed and ready!")
        print()
        print("Next: Run deploy_gdal.py for full testing")
        return 0
    else:
        missing = [k for k, v in results.items() if not v]
        print(f"✗ Missing or broken: {', '.join(missing)}")
        print()
        print("Install with:")
        if not results['SciPy']:
            print("  conda install scipy -y")
        if not results['GDAL']:
            print("  conda install gdal -y")
        return 1

if __name__ == '__main__':
    sys.exit(main())
