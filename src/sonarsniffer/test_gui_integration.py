#!/usr/bin/env python3
"""Test script to verify GUI target detection integration"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_target_detection_import():
    """Test that target detection can be imported"""
    try:
        import block_target_detection
        print("✅ Target detection module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Target detection import failed: {e}")
        return False

def test_gui_import():
    """Test that enhanced GUI can be imported"""
    try:
        import studio_gui_engines_v3_14
        print("✅ Enhanced GUI module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ GUI import failed: {e}")
        return False

def test_gui_target_detection_availability():
    """Test that GUI properly detects target detection availability"""
    try:
        import studio_gui_engines_v3_14
        
        # Check the TARGET_DETECTION_AVAILABLE flag
        if hasattr(studio_gui_engines_v3_14, 'TARGET_DETECTION_AVAILABLE'):
            available = studio_gui_engines_v3_14.TARGET_DETECTION_AVAILABLE
            print(f"✅ TARGET_DETECTION_AVAILABLE flag found: {available}")
            return available
        else:
            print("❌ TARGET_DETECTION_AVAILABLE flag not found in GUI module")
            return False
    except Exception as e:
        print(f"❌ Error checking target detection availability: {e}")
        return False

def test_csv_file_exists():
    """Test that test CSV file exists"""
    csv_path = "./outputs/records.csv"
    if os.path.exists(csv_path):
        print(f"✅ Test CSV file found: {csv_path}")
        # Check file size
        size = os.path.getsize(csv_path)
        print(f"   File size: {size:,} bytes")
        return True
    else:
        print(f"❌ Test CSV file not found: {csv_path}")
        return False

if __name__ == "__main__":
    print("🔍 Testing GUI Target Detection Integration")
    print("=" * 50)
    
    tests = [
        ("Target Detection Import", test_target_detection_import),
        ("GUI Import", test_gui_import), 
        ("Target Detection Availability", test_gui_target_detection_availability),
        ("Test CSV File", test_csv_file_exists)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! GUI target detection integration is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n🚀 You can now run the GUI with:")
    print("   python studio_gui_engines_v3_14.py")
    print("\n📋 The target detection tab will be available if all components are working.")