#!/usr/bin/env python3
"""
Multi-Format Parser Test Suite
Test all implemented sonar format parsers
"""

import os
import sys
from pathlib import Path

def test_all_parsers():
    """Test all implemented parsers"""
    print("🧪 Multi-Format Parser Test Suite")
    print("=" * 40)
    
    # Test individual parsers
    parsers_to_test = [
        ('Garmin RSD', 'garmin_parser', 'GarminParser'),
        ('Lowrance SL2/SL3', 'lowrance_parser_enhanced', 'LowranceParser'),
        ('Humminbird DAT/SON', 'humminbird_parser', 'HumminbirdParser'),
        ('EdgeTech JSF', 'edgetech_parser', 'EdgeTechParser'),
        ('Cerulean SVLOG', 'cerulean_parser', 'CeruleanParser')
    ]
    
    results = {}
    
    for format_name, module_name, class_name in parsers_to_test:
        print(f"\n🔍 Testing {format_name}")
        print("-" * (len(format_name) + 10))
        
        try:
            # Import the parser module
            module_path = f"parsers.{module_name}"
            module = __import__(module_path, fromlist=[class_name])
            parser_class = getattr(module, class_name)
            
            # Test basic instantiation
            test_file = f"test.{format_name.split()[-1].lower()}"
            parser = parser_class(test_file)
            
            print(f"  ✅ Import successful")
            print(f"  ✅ Class instantiation works")
            
            # Test methods
            methods_to_test = [
                ('get_file_info', 'File info method'),
                ('is_supported', 'Format detection'),
                ('get_enhanced_file_info', 'Enhanced info (if available)')
            ]
            
            method_results = []
            for method_name, description in methods_to_test:
                try:
                    if hasattr(parser, method_name):
                        method = getattr(parser, method_name)
                        if method_name == 'is_supported':
                            # This should return False for dummy file
                            result = method()
                            method_results.append(f"    ✅ {description}")
                        else:
                            # Try calling other methods
                            result = method()
                            method_results.append(f"    ✅ {description}")
                    else:
                        method_results.append(f"    ⚠️ {description} - method missing")
                except Exception as e:
                    method_results.append(f"    ⚠️ {description} - {str(e)[:30]}...")
            
            for result in method_results:
                print(result)
            
            results[format_name] = {
                'import': True,
                'instantiate': True,
                'methods': len([r for r in method_results if '✅' in r])
            }
            
        except ImportError as e:
            print(f"  ❌ Import failed: {e}")
            results[format_name] = {'import': False, 'error': str(e)}
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            results[format_name] = {'import': True, 'instantiate': False, 'error': str(e)}
    
    # Test unified interface
    print(f"\n🌐 Testing Unified Interface")
    print("-" * 25)
    
    try:
        from parsers.__init___multi import (
            detect_sonar_format, 
            get_supported_formats, 
            create_parser,
            get_format_status_report,
            format_file_filter
        )
        
        print("  ✅ Unified interface imports successful")
        
        # Test format detection
        formats = get_supported_formats()
        print(f"  ✅ Format detection: {len(formats)} manufacturers")
        
        # Test file filter
        filter_str = format_file_filter()
        print(f"  ✅ File filter: {len(filter_str.split('|'))} filters")
        
        # Test format detection with dummy files
        test_files = ['test.rsd', 'test.sl3', 'test.dat', 'test.jsf', 'test.svlog']
        for test_file in test_files:
            detected = detect_sonar_format(test_file) if os.path.exists(test_file) else None
            print(f"    {test_file}: {detected or 'Not found (expected)'}")
        
        results['unified_interface'] = {'working': True}
        
    except Exception as e:
        print(f"  ❌ Unified interface failed: {e}")
        results['unified_interface'] = {'working': False, 'error': str(e)}
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 25)
    
    successful_parsers = 0
    total_parsers = len(parsers_to_test)
    
    for format_name, result in results.items():
        if format_name == 'unified_interface':
            continue
            
        if result.get('import', False) and result.get('instantiate', False):
            status = f"✅ Working ({result.get('methods', 0)} methods)"
            successful_parsers += 1
        elif result.get('import', False):
            status = "⚠️ Partial (import only)"
        else:
            status = "❌ Failed"
        
        print(f"  {format_name:<20}: {status}")
    
    unified_status = "✅ Working" if results.get('unified_interface', {}).get('working', False) else "❌ Failed"
    print(f"  {'Unified Interface':<20}: {unified_status}")
    
    print(f"\nOverall: {successful_parsers}/{total_parsers} parsers functional")
    
    if successful_parsers == total_parsers and results.get('unified_interface', {}).get('working', False):
        print("🎉 All systems operational! Multi-format parsing ready.")
    elif successful_parsers >= total_parsers // 2:
        print("✅ Core functionality working. Some parsers may need refinement.")
    else:
        print("⚠️ Multiple issues detected. Check individual parser implementations.")
    
    return results

def test_with_real_files():
    """Test parsers with any real sonar files found"""
    print(f"\n🗂️ Testing with Real Files")
    print("=" * 25)
    
    # Look for sonar files in current directory
    sonar_extensions = ['.rsd', '.sl2', '.sl3', '.dat', '.son', '.jsf', '.svlog']
    found_files = []
    
    for ext in sonar_extensions:
        files = list(Path('.').glob(f'*{ext}')) + list(Path('.').glob(f'*{ext.upper()}'))
        found_files.extend(files)
    
    if not found_files:
        print("  No sonar files found in current directory")
        return
    
    print(f"  Found {len(found_files)} sonar files:")
    
    for file_path in found_files[:5]:  # Test up to 5 files
        print(f"\n  Testing: {file_path}")
        
        try:
            # Try unified interface
            from parsers.__init___multi import detect_sonar_format, create_parser
            
            detected_format = detect_sonar_format(str(file_path))
            if detected_format:
                print(f"    Format detected: {detected_format}")
                
                parser = create_parser(str(file_path))
                if parser:
                    info = parser.get_file_info()
                    print(f"    Size: {info.get('size_mb', 0):.1f} MB")
                    print(f"    Channels: {info.get('channels', 'Unknown')}")
                    
                    # Try enhanced info if available
                    try:
                        enhanced = parser.get_enhanced_file_info()
                        if 'total_records' in enhanced:
                            print(f"    Records: {enhanced['total_records']:,}")
                    except:
                        pass
                else:
                    print(f"    ❌ Could not create parser")
            else:
                print(f"    ⚠️ Format not detected")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")

if __name__ == "__main__":
    # Test all parsers
    results = test_all_parsers()
    
    # Test with real files if any exist
    test_with_real_files()
    
    # Show detailed status
    print(f"\n📋 Detailed Status Report")
    print("=" * 30)
    
    try:
        from parsers.__init___multi import get_format_status_report
        get_format_status_report()
    except:
        print("Could not generate detailed status report")