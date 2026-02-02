#!/usr/bin/env python3
"""
Test suite for CESARops CLI with optimization features
"""

import subprocess
import sys
import os
import tempfile
import json
from pathlib import Path


def run_cesarops_command(args, env_vars=None):
    """Run CESARops and return output"""
    cmd = [sys.executable, "cesarops.py"] + args
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".", env=env)
    return result.returncode, result.stdout, result.stderr


def run_sarops_command(args, env_vars=None):
    """Run SAROps in headless mode and return output"""
    cmd = [sys.executable, "sarops.py"] + args
    env = os.environ.copy()
    env["HEADLESS"] = "1"
    env["CESAROPS_TEST_MODE"] = "1"
    if env_vars:
        env.update(env_vars)

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=".", env=env, timeout=30
    )
    return result.returncode, result.stdout, result.stderr


def test_cesarops_help():
    """Test --help flag"""
    print("Testing: CESARops --help")
    code, stdout, stderr = run_cesarops_command(["--help"])
    assert code == 0, f"Help failed: {stderr}"
    assert "usage" in stdout.lower() or "lake" in stdout.lower()
    print("  ✓ CESARops help works")


def test_cesarops_version():
    """Test --version flag"""
    print("Testing: CESARops --version")
    code, stdout, stderr = run_cesarops_command(["--version"])
    assert code == 0, f"Version failed: {stderr}"
    assert "version" in stdout.lower() or stdout.strip()
    print("  ✓ CESARops version works")


def test_cesarops_module_imports():
    """Test that optimization modules can be imported"""
    print("Testing: CESARops module imports")

    try:
        from src.cesarops import (
            ML_PIPELINE_AVAILABLE,
            GEOSPATIAL_EXPORT_AVAILABLE,
            INCREMENTAL_LOADING_AVAILABLE,
        )

        print("  ✓ Optimization flags available")
        print(f"    - ML Pipeline: {ML_PIPELINE_AVAILABLE}")
        print(f"    - Geospatial Export: {GEOSPATIAL_EXPORT_AVAILABLE}")
        print(f"    - Incremental Loading: {INCREMENTAL_LOADING_AVAILABLE}")
    except ImportError as e:
        print(f"  ✗ Module import failed: {e}")
        return False

    return True


def test_cesarops_ml_pipeline():
    """Test ML pipeline availability"""
    print("Testing: ML Pipeline module")
    try:
        from src.cesarops import DriftCorrectionPipeline

        print("  ✓ DriftCorrectionPipeline imported")

        # Try to instantiate
        pipeline = DriftCorrectionPipeline()
        print("  ✓ DriftCorrectionPipeline instantiated")
        return True
    except Exception as e:
        print(f"  ✗ ML Pipeline test failed: {e}")
        return False


def test_cesarops_incremental_loading():
    """Test incremental loading module"""
    print("Testing: Incremental Loading module")
    try:
        from src.cesarops import StreamingDataLoader, ChunkedDataProcessor

        print("  ✓ StreamingDataLoader imported")
        print("  ✓ ChunkedDataProcessor imported")
        return True
    except Exception as e:
        print(f"  ✗ Incremental Loading test failed: {e}")
        return False


def test_sarops_import():
    """Test that sarops.py has optimization modules imported"""
    print("Testing: sarops.py optimization imports")
    try:
        import sarops

        # Check flags
        if hasattr(sarops, "ML_PIPELINE_AVAILABLE"):
            print(f"  ✓ ML_PIPELINE_AVAILABLE: {sarops.ML_PIPELINE_AVAILABLE}")
        if hasattr(sarops, "GEOSPATIAL_EXPORT_AVAILABLE"):
            print(
                f"  ✓ GEOSPATIAL_EXPORT_AVAILABLE: {sarops.GEOSPATIAL_EXPORT_AVAILABLE}"
            )
        if hasattr(sarops, "INCREMENTAL_LOADING_AVAILABLE"):
            print(
                f"  ✓ INCREMENTAL_LOADING_AVAILABLE: {sarops.INCREMENTAL_LOADING_AVAILABLE}"
            )

        return True
    except Exception as e:
        print(f"  ✗ sarops.py import failed: {e}")
        return False


def test_cesarops_config():
    """Test config.yaml loading"""
    print("Testing: CESARops configuration")

    if not os.path.exists("config.yaml"):
        print("  ⚠ config.yaml not found (optional)")
        return True

    try:
        import yaml

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        print(f"  ✓ Configuration loaded")
        if "lakes" in config:
            print(f"  ✓ Found {len(config['lakes'])} lakes defined")
        return True
    except Exception as e:
        print(f"  ✗ Config test failed: {e}")
        return False


def test_database_initialization():
    """Test database can be initialized"""
    print("Testing: Database initialization")
    try:
        import sqlite3

        db_file = "test_drift_objects.db"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create a simple test table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """
        )
        conn.commit()
        conn.close()

        if os.path.exists(db_file):
            os.remove(db_file)

        print("  ✓ Database initialization works")
        return True
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("CESARops Optimization Integration Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_cesarops_help,
        test_cesarops_version,
        test_cesarops_module_imports,
        test_cesarops_ml_pipeline,
        test_cesarops_incremental_loading,
        test_sarops_import,
        test_cesarops_config,
        test_database_initialization,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result is None or result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test exception: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
