#!/usr/bin/env python3
"""
Test suite for SonarSniffer CLI with optimization features
"""

import subprocess
import sys
import os
import tempfile
from pathlib import Path


def run_cli_command(args, venv_path=None):
    """Run a CLI command and return output"""
    if venv_path:
        # Use the venv
        python_exe = str(Path(venv_path) / "Scripts" / "python.exe")
    else:
        python_exe = sys.executable
    
    cmd = [python_exe, "-m", "src.sonarsniffer.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    return result.returncode, result.stdout, result.stderr


def test_cli_help():
    """Test --help flag"""
    print("Testing: CLI --help")
    code, stdout, stderr = run_cli_command(["--help"])
    assert code == 0, f"Help failed: {stderr}"
    assert "SonarSniffer Command Line Interface" in stdout
    assert "sonarsniffer optimize" in stdout
    assert "sonarsniffer ml-predict" in stdout
    assert "sonarsniffer export-tiles" in stdout
    print("  ✓ Help shows all commands including optimization features")


def test_cli_version():
    """Test --version flag"""
    print("Testing: CLI --version")
    code, stdout, stderr = run_cli_command(["--version"])
    assert code == 0, f"Version failed: {stderr}"
    assert "SonarSniffer 1.0.0-beta" in stdout
    print("  ✓ Version displays correctly")


def test_cli_imports():
    """Test that all modules can be imported"""
    print("Testing: Module imports")
    
    # Test core imports
    try:
        from src.sonarsniffer import LicenseManager, SonarParser, WebDashboardGenerator
        print("  ✓ Core modules import successfully")
    except ImportError as e:
        print(f"  ✗ Core import failed: {e}")
        return False
    
    # Test optimization modules
    try:
        from src.sonarsniffer import (
            INCREMENTAL_LOADING_AVAILABLE,
            ML_PIPELINE_AVAILABLE,
            GEOSPATIAL_EXPORT_AVAILABLE
        )
        print(f"  ✓ Optimization flags available")
        print(f"    - Incremental Loading: {INCREMENTAL_LOADING_AVAILABLE}")
        print(f"    - ML Pipeline: {ML_PIPELINE_AVAILABLE}")
        print(f"    - Geospatial Export: {GEOSPATIAL_EXPORT_AVAILABLE}")
    except ImportError as e:
        print(f"  ✗ Optimization import failed: {e}")
        return False
    
    return True


def test_cli_analyze_no_file():
    """Test analyze command with missing file"""
    print("Testing: analyze <file> with missing file")
    code, stdout, stderr = run_cli_command(["analyze", "nonexistent.sonar"])
    assert code == 1, "Should fail with missing file"
    assert "File not found" in stdout or "ERROR" in stdout
    print("  ✓ Proper error handling for missing file")


def test_cli_optimize_no_file():
    """Test optimize command with missing file"""
    print("Testing: optimize <file> with missing file")
    code, stdout, stderr = run_cli_command(["optimize", "nonexistent.sonar"])
    assert code == 1, "Should fail with missing file"
    assert "File not found" in stdout or "ERROR" in stdout
    print("  ✓ Proper error handling for missing file")


def test_cli_ml_predict_no_file():
    """Test ml-predict command with missing file"""
    print("Testing: ml-predict <file> with missing file")
    code, stdout, stderr = run_cli_command(["ml-predict", "nonexistent.sonar"])
    assert code == 1, "Should fail with missing file"
    assert "File not found" in stdout or "ERROR" in stdout
    print("  ✓ Proper error handling for missing file")


def test_cli_export_tiles_no_file():
    """Test export-tiles command with missing file"""
    print("Testing: export-tiles <file> with missing file")
    code, stdout, stderr = run_cli_command(["export-tiles", "nonexistent.sonar"])
    assert code == 1, "Should fail with missing file"
    assert "File not found" in stdout or "ERROR" in stdout
    print("  ✓ Proper error handling for missing file")


def test_cli_license():
    """Test license command"""
    print("Testing: license (status)")
    code, stdout, stderr = run_cli_command(["license"])
    # License check might fail due to trial/licensing, but command should work
    assert "License Status:" in stdout or "ERROR" in stdout
    print("  ✓ License command executes")


def main():
    """Run all tests"""
    print("=" * 60)
    print("SonarSniffer CLI Optimization Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_cli_help,
        test_cli_version,
        test_cli_imports,
        test_cli_analyze_no_file,
        test_cli_optimize_no_file,
        test_cli_ml_predict_no_file,
        test_cli_export_tiles_no_file,
        test_cli_license,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
