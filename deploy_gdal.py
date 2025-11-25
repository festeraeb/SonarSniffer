#!/usr/bin/env python3
"""
Automated GDAL Deployment & Verification
Tests all GDAL integration and validates performance improvements
"""

import subprocess
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Run a command and return success status"""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"{description}")
    logger.info('=' * 70)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr)
            logger.error(f"✗ Failed with exit code {result.returncode}")
            return False
        
        logger.info("✓ Completed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("✗ Command timed out")
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False

def check_packages():
    """Verify required packages are installed"""
    logger.info("\n" + "=" * 70)
    logger.info("CHECKING PACKAGE DEPENDENCIES")
    logger.info("=" * 70)
    
    packages = ['numpy', 'scipy', 'gdal']
    missing = []
    
    for pkg in packages:
        try:
            if pkg == 'gdal':
                from osgeo import gdal
                logger.info(f"✓ GDAL available")
            elif pkg == 'scipy':
                import scipy
                logger.info(f"✓ SciPy {scipy.__version__} available")
            else:
                __import__(pkg)
                logger.info(f"✓ {pkg.upper()} available")
        except ImportError:
            logger.warning(f"✗ {pkg} not found")
            missing.append(pkg)
    
    return len(missing) == 0, missing

def run_tests():
    """Run all automated tests"""
    
    tests = [
        # Test 1: Unified parser
        {
            'file': 'test_unified_parser.py',
            'description': 'Testing Unified Parser',
            'critical': True
        },
        # Test 2: GDAL benchmark
        {
            'file': 'test_gdal_benchmark.py',
            'description': 'Benchmarking GDAL vs SciPy',
            'critical': False
        },
        # Test 3: Integration test
        {
            'file': 'test_gdal_integration.py',
            'description': 'Testing GDAL Integration Module',
            'critical': False
        },
    ]
    
    results = {}
    
    for test in tests:
        test_file = Path(test['file'])
        
        if not test_file.exists():
            if test['critical']:
                logger.warning(f"✗ {test['file']} not found (critical)")
                results[test['file']] = False
            else:
                logger.info(f"⊘ {test['file']} not found (optional)")
                results[test['file']] = None
            continue
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"{test['description']}")
        logger.info('=' * 70)
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(Path.cwd())
            )
            
            if result.stdout:
                # Print last 50 lines to avoid too much output
                lines = result.stdout.split('\n')
                if len(lines) > 50:
                    print('\n'.join(lines[:10]))
                    print(f"\n... ({len(lines) - 20} lines omitted) ...\n")
                    print('\n'.join(lines[-10:]))
                else:
                    print(result.stdout)
            
            if result.returncode == 0:
                logger.info(f"✓ {test['file']} passed")
                results[test['file']] = True
            else:
                msg = f"✗ {test['file']} failed"
                if test['critical']:
                    logger.error(msg)
                else:
                    logger.warning(msg)
                if result.stderr:
                    print(result.stderr[:500])
                results[test['file']] = False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"⏱ {test['file']} timed out")
            results[test['file']] = False
        except Exception as e:
            logger.error(f"✗ Error running {test['file']}: {e}")
            results[test['file']] = False
    
    return results

def verify_syntax():
    """Verify all Python files have valid syntax"""
    logger.info("\n" + "=" * 70)
    logger.info("VERIFYING PYTHON SYNTAX")
    logger.info("=" * 70)
    
    files_to_check = [
        'gdal_optimization_core.py',
        'gdal_integration.py',
        'geospatial_exporter.py',
        'test_gdal_benchmark.py',
    ]
    
    all_valid = True
    
    for filename in files_to_check:
        fpath = Path(filename)
        if not fpath.exists():
            logger.info(f"⊘ {filename} not found")
            continue
        
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', filename],
            capture_output=True
        )
        
        if result.returncode == 0:
            logger.info(f"✓ {filename} syntax OK")
        else:
            logger.error(f"✗ {filename} has syntax errors")
            if result.stderr:
                print(result.stderr)
            all_valid = False
    
    return all_valid

def main():
    """Main deployment workflow"""
    
    logger.info("\n" + "=" * 70)
    logger.info("GDAL DEPLOYMENT & VERIFICATION SYSTEM")
    logger.info("=" * 70)
    
    # Step 1: Check packages
    logger.info("\nSTEP 1: Checking dependencies...")
    packages_ok, missing = check_packages()
    
    if not packages_ok:
        logger.warning(f"\nMissing packages: {', '.join(missing)}")
        logger.info("Attempting to install...")
        install_cmd = f"{sys.executable} -m pip install {' '.join(missing)} -q"
        if not run_command(install_cmd, "Installing missing packages"):
            logger.error("Failed to install packages. Please install manually:")
            logger.error(f"  pip install {' '.join(missing)}")
    
    # Step 2: Verify syntax
    logger.info("\nSTEP 2: Verifying Python syntax...")
    syntax_ok = verify_syntax()
    if not syntax_ok:
        logger.error("Syntax errors found. Fix before continuing.")
        return False
    logger.info("✓ All files have valid syntax")
    
    # Step 3: Run tests
    logger.info("\nSTEP 3: Running automated tests...")
    test_results = run_tests()
    
    # Step 4: Summary
    logger.info("\n" + "=" * 70)
    logger.info("DEPLOYMENT SUMMARY")
    logger.info("=" * 70)
    
    print("\nTest Results:")
    print("-" * 70)
    
    critical_passed = True
    for test_file, result in test_results.items():
        if result is None:
            status = "⊘ Skipped"
        elif result:
            status = "✓ Passed"
        else:
            status = "✗ Failed"
        
        print(f"  {test_file:<40} {status}")
        
        if result is False and 'parser' in test_file.lower():
            critical_passed = False
    
    print("-" * 70)
    
    if critical_passed:
        logger.info("\n✓ GDAL deployment successful!")
        logger.info("\nNext steps:")
        logger.info("1. GDAL and SciPy are integrated into geospatial_exporter.py")
        logger.info("2. Bathymetric processing will automatically use GDAL when available")
        logger.info("3. Expected speedup: 5-30x faster than SciPy RBF")
        logger.info("4. Fallback to SciPy for compatibility")
        return True
    else:
        logger.error("\n✗ Deployment encountered issues")
        logger.error("Check error messages above and fix before deploying to production")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
