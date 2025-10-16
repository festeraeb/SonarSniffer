#!/usr/bin/env python3
"""
Real File Multi-Format Parser Test
Test all parsers with actual sonar files found in the workspace
"""

import os
import glob
from pathlib import Path

def find_sonar_files():
    """Find all sonar files in the current directory and subdirectories"""
    extensions = ['*.rsd', '*.RSD', '*.sl2', '*.sl3', '*.SL2', '*.SL3', 
                  '*.dat', '*.DAT', '*.son', '*.SON', '*.jsf', '*.JSF', 
                  '*.svlog', '*.SVLOG']
    
    files = []
    for ext in extensions:
        # Search current directory
        files.extend(glob.glob(ext))
        # Search subdirectories recursively 
        files.extend(glob.glob(f'**/{ext}', recursive=True))
    
    # Remove duplicates and sort by size (larger files first, likely real data)
    unique_files = list(set(files))
    files_with_size = [(f, os.path.getsize(f)) for f in unique_files]
    files_with_size.sort(key=lambda x: x[1], reverse=True)  # Sort by size, largest first
    
    return [f[0] for f in files_with_size]

def test_parser_with_file(parser_name, parser_class, file_path):
    """Test a specific parser with a real file"""
    print(f"\n🔍 Testing {parser_name} with {file_path}")
    print("-" * 50)
    
    try:
        # Create parser instance
        parser = parser_class(file_path)
        
        # Test format support
        is_supported = parser.is_supported()
        print(f"  Format supported: {'✅ Yes' if is_supported else '❌ No'}")
        
        if not is_supported:
            return False
        
        # Get basic file info
        info = parser.get_file_info()
        print(f"  File size: {info['size_mb']:.2f} MB")
        print(f"  Format: {info.get('format_details', {}).get('format_name', 'Unknown')}")
        print(f"  Channels: {info['channels']}")
        
        # Test enhanced info if available
        try:
            enhanced = parser.get_enhanced_file_info()
            if 'total_records' in enhanced:
                print(f"  Total records: {enhanced['total_records']:,}")
            if 'channel_analysis' in enhanced:
                print(f"  Channel analysis: {len(enhanced['channel_analysis'])} channels analyzed")
        except Exception as e:
            print(f"  Enhanced info: ⚠️ {str(e)[:40]}...")
        
        # Test parsing a small sample
        try:
            print(f"  Testing parse with 10 records...")
            count, csv_path, log_path = parser.parse_records(max_records=10)
            print(f"  ✅ Parsed {count} records")
            print(f"  Output: {os.path.basename(csv_path)}")
            
            # Check CSV content
            if os.path.exists(csv_path):
                with open(csv_path, 'r') as f:
                    lines = f.readlines()
                    print(f"  CSV lines: {len(lines)} (including header)")
        except Exception as e:
            print(f"  ⚠️ Parse test failed: {str(e)[:40]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Real File Multi-Format Parser Test")
    print("=" * 45)
    
    # Find sonar files
    sonar_files = find_sonar_files()
    
    if not sonar_files:
        print("❌ No sonar files found in current directory")
        return
    
    print(f"Found {len(sonar_files)} sonar files:")
    for file in sonar_files:
        size = os.path.getsize(file) / (1024*1024)
        print(f"  📁 {file} ({size:.1f} MB)")
    
    # Parser mappings
    parsers = [
        ('Garmin RSD', 'parsers.garmin_parser', 'GarminParser', ['.rsd', '.RSD']),
        ('Lowrance SL2/SL3', 'parsers.lowrance_parser_enhanced', 'LowranceParser', ['.sl2', '.sl3', '.SL2', '.SL3']),
        ('Humminbird DAT/SON', 'parsers.humminbird_parser', 'HumminbirdParser', ['.dat', '.son', '.DAT', '.SON']),
        ('EdgeTech JSF', 'parsers.edgetech_parser', 'EdgeTechParser', ['.jsf', '.JSF']),
        ('Cerulean SVLOG', 'parsers.cerulean_parser', 'CeruleanParser', ['.svlog', '.SVLOG'])
    ]
    
    test_results = {}
    
    # Test each parser type
    for parser_name, module_name, class_name, extensions in parsers:
        print(f"\n🎯 Testing {parser_name} Parser")
        print("=" * (len(parser_name) + 15))
        
        try:
            # Import parser
            module = __import__(module_name, fromlist=[class_name])
            parser_class = getattr(module, class_name)
            print(f"✅ Parser imported successfully")
            
            # Find matching files
            matching_files = [f for f in sonar_files if any(f.endswith(ext) for ext in extensions)]
            
            if not matching_files:
                print(f"⚠️ No {parser_name} files found")
                test_results[parser_name] = {'tested': False, 'reason': 'No files found'}
                continue
            
            print(f"Found {len(matching_files)} matching files")
            
            # Test with first matching file
            test_file = matching_files[0]
            success = test_parser_with_file(parser_name, parser_class, test_file)
            
            test_results[parser_name] = {
                'tested': True,
                'success': success,
                'file': test_file,
                'files_available': len(matching_files)
            }
            
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            test_results[parser_name] = {'tested': False, 'reason': f'Import error: {e}'}
        except Exception as e:
            print(f"❌ Test failed: {e}")
            test_results[parser_name] = {'tested': False, 'reason': f'Error: {e}'}
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 25)
    
    total_parsers = len(parsers)
    successful_tests = 0
    
    for parser_name, result in test_results.items():
        if result.get('tested', False):
            if result.get('success', False):
                status = f"✅ SUCCESS with {result['file']}"
                successful_tests += 1
            else:
                status = f"⚠️ FAILED during testing"
        else:
            status = f"❌ {result.get('reason', 'Unknown error')}"
        
        files_info = f"({result.get('files_available', 0)} files)" if result.get('files_available') else ""
        print(f"  {parser_name:<20}: {status} {files_info}")
    
    print(f"\nOverall: {successful_tests}/{total_parsers} parsers successfully tested with real files")
    
    if successful_tests == total_parsers:
        print("🎉 All parsers working with real sonar data!")
    elif successful_tests >= total_parsers // 2:
        print("✅ Most parsers working. Great progress!")
    else:
        print("⚠️ Several parsers need attention.")
    
    # Rust acceleration test
    print(f"\n🦀 Rust Acceleration Status")
    print("-" * 25)
    try:
        import rsd_video_core
        print("✅ Rust acceleration available and ready")
        
        # Quick performance test
        import numpy as np
        left_data = np.random.randint(0, 255, (50, 492), dtype=np.uint8)
        right_data = np.random.randint(0, 255, (50, 492), dtype=np.uint8)
        
        result = rsd_video_core.generate_sidescan_waterfall(left_data, right_data, 984, 4)
        print(f"✅ Rust waterfall generation working: {result.shape}")
        
    except ImportError:
        print("⚠️ Rust acceleration not available (expected if not built)")
    except Exception as e:
        print(f"❌ Rust acceleration error: {e}")

if __name__ == "__main__":
    main()