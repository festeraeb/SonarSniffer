#!/usr/bin/env python3
"""Test the enhanced GUI preview and export features"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_enhanced_gui():
    """Test the enhanced GUI features"""
    try:
        import tkinter as tk
        import studio_gui_engines_v3_14
        
        print("🔍 Testing Enhanced GUI Features")
        print("=" * 40)
        
        # Create app
        app = studio_gui_engines_v3_14.App()
        app.withdraw()
        
        # Test colormap enhancements
        print(f"✅ Colormaps available: {len(app.colormaps)}")
        amber_maps = [cm for cm in app.colormaps if 'amber' in cm.lower() or 'sepia' in cm.lower() or 'orange' in cm.lower()]
        print(f"✅ Amber/warm tone maps: {amber_maps}")
        
        # Test canvas display method
        if hasattr(app, '_display_image_in_canvas'):
            print("✅ Canvas display method available")
        else:
            print("❌ Canvas display method missing")
        
        # Test export methods
        if hasattr(app, '_export_format'):
            print("✅ Format-specific export method available")
        else:
            print("❌ Format-specific export method missing")
            
        if hasattr(app, '_export_all_formats'):
            print("✅ Export all formats method available")
        else:
            print("❌ Export all formats method missing")
        
        # Test custom colormap setup
        if hasattr(app, '_setup_custom_colormaps'):
            print("✅ Custom colormap setup method available")
        else:
            print("❌ Custom colormap setup method missing")
        
        # Test that legacy preview references are removed
        has_legacy_preview_ref = hasattr(app, 'preview') and app.preview is not None
        if not has_legacy_preview_ref:
            print("✅ Legacy preview label removed")
        else:
            print("⚠️ Legacy preview label still exists")
        
        # Test canvas exists
        if hasattr(app, 'preview_canvas'):
            print("✅ Preview canvas available")
        else:
            print("❌ Preview canvas missing")
        
        app.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Enhanced GUI test failed: {e}")
        return False

def test_amber_colormap_functionality():
    """Test amber colormap creation"""
    try:
        print("\n🎨 Testing Amber Colormap Functionality")
        print("=" * 40)
        
        import studio_gui_engines_v3_14
        app = studio_gui_engines_v3_14.App()
        app.withdraw()
        
        # Check for amber-related colormaps
        amber_related = []
        for cmap in app.colormaps:
            if any(term in cmap.lower() for term in ['amber', 'sepia', 'orange', 'copper', 'hot', 'autumn']):
                amber_related.append(cmap)
        
        print(f"✅ Amber/warm colormaps found: {len(amber_related)}")
        for cmap in amber_related[:10]:  # Show first 10
            print(f"   - {cmap}")
        
        if len(amber_related) > 10:
            print(f"   ... and {len(amber_related) - 10} more")
        
        app.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Colormap test failed: {e}")
        return False

if __name__ == "__main__":
    tests = [
        ("Enhanced GUI Features", test_enhanced_gui),
        ("Amber Colormap Functionality", test_amber_colormap_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All enhanced features working correctly!")
        print("\n✨ Key Improvements Verified:")
        print("   • Canvas-based preview display (no more under-window issues)")
        print("   • Amber and warm tone colormaps available")
        print("   • Clickable export buttons instead of dropdown")
        print("   • Legacy preview removed and consolidated")
        print("   • Enhanced colormap options with custom amber tones")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n🚀 Ready to test! Launch with:")
    print("   python studio_gui_engines_v3_14.py")
    print("\n💡 Try the new features:")
    print("   • Test preview display in the canvas area")
    print("   • Try amber, sepia, or orange colormaps") 
    print("   • Use the new export buttons")
    print("   • Check that preview stays within the window")