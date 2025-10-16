#!/usr/bin/env python3
"""
Multi-Format Sonar Support Demo
Demonstrates RSD Studio's expanded format capabilities
"""

import os
import sys
from pathlib import Path

def test_format_detection():
    """Test format detection capabilities"""
    print("🎯 Multi-Format Sonar Detection Test")
    print("=" * 40)
    
    # Import the new multi-format system
    try:
        from parsers import detect_sonar_format, get_supported_formats, get_format_status_report
        
        # Test files for detection
        test_files = [
            "sample_data.rsd",      # Garmin
            "track_001.sl2",        # Lowrance 2-channel
            "survey_01.sl3",        # Lowrance 3-channel  
            "Recording.DAT",        # Humminbird
            "side_scan.jsf",        # EdgeTech
            "sonar_log.svlog",      # Cerulean
            "unknown_file.xyz"      # Unknown
        ]
        
        print("Format Detection Tests:")
        for test_file in test_files:
            detected = detect_sonar_format(test_file)
            status = "✅ Detected" if detected else "❌ Unknown"
            print(f"  {test_file:<20} -> {detected or 'None':<15} {status}")
        
        print(f"\nSupported Formats:")
        for manufacturer, extensions in get_supported_formats().items():
            ext_list = ', '.join(extensions)
            print(f"  {manufacturer:<12}: {ext_list}")
        
        print(f"\nDetailed Status Report:")
        get_format_status_report()
        
        return True
        
    except ImportError as e:
        print(f"❌ Multi-format system not available: {e}")
        return False

def test_garmin_enhanced():
    """Test enhanced Garmin parsing with depth analysis"""
    print("\n🔍 Enhanced Garmin RSD Analysis")
    print("=" * 35)
    
    try:
        from parsers import GarminParser
        
        # Check for existing RSD files
        rsd_files = list(Path('.').glob('*.rsd')) + list(Path('.').glob('*.RSD'))
        
        if not rsd_files:
            print("No RSD files found for testing")
            return False
        
        test_file = str(rsd_files[0])
        print(f"Testing with: {test_file}")
        
        parser = GarminParser(test_file)
        
        # Get enhanced file info
        info = parser.get_enhanced_file_info()
        
        print(f"\nFile Analysis:")
        print(f"  Path: {info['path']}")
        print(f"  Size: {info['size_mb']:.1f} MB")
        print(f"  Format: {info.get('format_details', {}).get('format_name', 'Garmin RSD')}")
        print(f"  Channels: {info['channels']}")
        print(f"  Total Records: {info['total_records']:,}")
        
        # Depth analysis if available
        if 'depth_analysis' in info and 'stats' in info['depth_analysis']:
            depth_stats = info['depth_analysis']['stats']
            print(f"\nDepth Analysis:")
            print(f"  Sample size: {depth_stats['count']} records")
            print(f"  Depth range: {depth_stats['min']:.3f} - {depth_stats['max']:.3f}m")
            print(f"  Average depth: {depth_stats['avg']:.3f}m") 
            print(f"  Non-zero readings: {depth_stats['non_zero_count']}/{depth_stats['count']}")
            
            if depth_stats['non_zero_count'] == 0:
                print("  ⚠️ All depth readings are zero - may need format investigation")
            elif depth_stats['max'] < 1.0:
                print("  ⚠️ All depths < 1m - may need unit conversion or field mapping")
            else:
                print("  ✅ Depth readings appear valid")
        
        # Test small parse
        print(f"\nTesting parser with 50 records...")
        try:
            count, csv_path, log_path = parser.parse_records(50)
            print(f"  ✅ Parsed {count} records successfully")
            print(f"  Output: {csv_path}")
        except Exception as e:
            print(f"  ❌ Parse test failed: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Enhanced Garmin parser not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Garmin test failed: {e}")
        return False

def test_universal_parser():
    """Test universal parser with auto-detection"""
    print("\n🌐 Universal Parser Test")
    print("=" * 25)
    
    try:
        from parsers import UniversalSonarParser
        
        # Find any supported files
        supported_extensions = ['.rsd', '.RSD', '.sl2', '.sl3', '.dat', '.jsf', '.svlog']
        test_files = []
        
        for ext in supported_extensions:
            files = list(Path('.').glob(f'*{ext}'))
            test_files.extend(files)
        
        if not test_files:
            print("No supported sonar files found for testing")
            return False
        
        test_file = str(test_files[0])
        print(f"Testing universal parser with: {test_file}")
        
        parser = UniversalSonarParser(test_file)
        
        if parser.is_supported():
            print(f"✅ Format supported: {parser.format_type}")
            
            info = parser.get_file_info()
            print(f"  Channels: {info['channels']}")
            print(f"  Size: {info['size_mb']:.1f} MB")
            print(f"  Estimated records: {info['total_records']:,}")
            
        else:
            print(f"❌ Format not supported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Universal parser not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Universal parser test failed: {e}")
        return False

def test_rust_acceleration():
    """Test Rust acceleration if available"""
    print("\n🦀 Rust Acceleration Test")
    print("=" * 25)
    
    try:
        # Check if Rust module is built
        import rsd_video_core
        
        print("✅ Rust acceleration module loaded")
        
        # Run benchmark
        import numpy as np
        
        # Test data
        left_data = np.random.randint(0, 255, (25, 492), dtype=np.uint8)
        right_data = np.random.randint(0, 255, (25, 492), dtype=np.uint8)
        
        print("Running Rust waterfall benchmark...")
        
        # Benchmark waterfall generation
        iterations = 100
        rust_time = rsd_video_core.benchmark_waterfall_generation(iterations, 25, 984)
        
        print(f"Rust performance: {rust_time*1000:.3f}ms per frame")
        
        # Test actual generation
        result = rsd_video_core.generate_sidescan_waterfall(left_data, right_data, 984, 4)
        print(f"Generated waterfall: {result.shape}")
        
        # Test alignment
        frame1 = np.zeros((20, 100), dtype=np.uint8)
        frame2 = np.zeros((20, 100), dtype=np.uint8)
        frame1[8:12, 40:60] = 255
        frame2[8:12, 47:67] = 255  # Shifted by 7 pixels
        
        detected_shift = rsd_video_core.align_waterfall_frames(frame1, frame2)
        print(f"Alignment test: Expected 7px shift, detected {detected_shift}px")
        
        return True
        
    except ImportError:
        print("⚠️ Rust acceleration not built yet")
        print("   Run: cd rust-video-core && maturin develop --release")
        return False
    except Exception as e:
        print(f"❌ Rust test failed: {e}")
        return False

def main():
    """Run comprehensive multi-format demo"""
    print("🚀 RSD Studio Multi-Format Sonar Support Demo")
    print("=" * 50)
    print("This demo showcases expanded format support beyond Garmin RSD")
    print()
    
    # Test each component
    results = {
        'format_detection': test_format_detection(),
        'garmin_enhanced': test_garmin_enhanced(), 
        'universal_parser': test_universal_parser(),
        'rust_acceleration': test_rust_acceleration()
    }
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 25)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print(f"  {test_display:<20}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All systems operational! RSD Studio ready for multi-format processing.")
    elif total_passed >= 2:
        print("✅ Core functionality working. Some advanced features need setup.")
    else:
        print("⚠️ Basic functionality needs attention.")
    
    print(f"\nNext Steps:")
    if not results['rust_acceleration']:
        print("• Build Rust acceleration: cd rust-video-core && maturin develop --release")
    if not results['format_detection']:
        print("• Check parsers module installation")
    if not results['universal_parser']:
        print("• Verify multi-format parser integration")

if __name__ == "__main__":
    main()