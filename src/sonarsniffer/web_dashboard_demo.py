#!/usr/bin/env python3
"""
Web Dashboard Demo for Garmin RSD Processing
Demonstrates the new web-based NOAA ENC + MBTiles output capability

This addresses the user's specific request for webpage outputs to NOAA ENC with MBTiles,
providing a modern web-based alternative to Google Earth KML overlays.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def create_web_dashboard_demo():
    """Create a web dashboard demo using available RSD files"""

    print("🌐 Garmin RSD Web Dashboard Demo")
    print("=" * 50)

    # Find available RSD files
    rsd_files = list(Path(".").glob("*.RSD"))
    if not rsd_files:
        print("❌ No RSD files found in current directory")
        print("   Please run this script from the Garmin-Rsd directory")
        return False

    print(f"📁 Found {len(rsd_files)} RSD files:")
    for i, rsd_file in enumerate(rsd_files[:5]):  # Show first 5
        print(f"   {i+1}. {rsd_file.name}")
    if len(rsd_files) > 5:
        print(f"   ... and {len(rsd_files) - 5} more")

    # Use the first available RSD file for demo
    demo_file = rsd_files[0]
    print(f"\n🎯 Creating web dashboard for: {demo_file.name}")

    try:
        # Import the web dashboard generator
        from web_dashboard_generator import create_web_dashboard_from_rsd

        # Create the dashboard
        output_dir = f"web_dashboard_{demo_file.stem}"
        dashboard_path = create_web_dashboard_from_rsd(str(demo_file), output_dir)

        if dashboard_path and Path(dashboard_path).exists():
            print("\n✅ Web Dashboard Created Successfully!")
            print(f"📂 Location: {dashboard_path}")
            print(f"🌐 Open in browser: file://{Path(dashboard_path).absolute()}/index.html")

            # List created files
            dashboard_files = list(Path(dashboard_path).glob("*"))
            print("\n📄 Created files:")
            for file_path in sorted(dashboard_files):
                size = file_path.stat().st_size
                print(f"   • {file_path.name} ({size:,} bytes)")

            print("\n🎉 Dashboard Features:")
            print("   ✅ NOAA ENC base charts (official government data)")
            print("   ✅ MBTiles survey data overlay")
            print("   ✅ Interactive map controls")
            print("   ✅ Target detection and visualization")
            print("   ✅ Depth profiling tools")
            print("   ✅ Export capabilities (KML, GeoJSON, PDF)")
            print("   ✅ Mobile-responsive design")
            print("   ✅ Real-time analytics integration")

            return True
        else:
            print("❌ Failed to create dashboard")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure web_dashboard_generator.py is available")
        return False
    except Exception as e:
        print(f"❌ Error creating dashboard: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_web_dashboard_features():
    """Display information about web dashboard capabilities"""

    print("\n" + "="*60)
    print("🌐 WEB DASHBOARD FEATURES OVERVIEW")
    print("="*60)

    features = [
        ("NOAA ENC Integration", "Official government nautical charts as base layer"),
        ("MBTiles Support", "High-performance tiled survey data rendering"),
        ("Interactive Controls", "Layer toggling, opacity control, zoom levels"),
        ("Target Detection", "Visualize wrecks, anomalies with confidence scores"),
        ("Depth Profiling", "Cross-section analysis and depth statistics"),
        ("Real-time Analytics", "Live data processing and statistics"),
        ("Export Options", "KML, GeoJSON, and PDF report generation"),
        ("Mobile Responsive", "Works on tablets and smartphones"),
        ("Offline Capable", "Service worker for offline chart access"),
        ("Professional UI", "Marine survey industry standard interface")
    ]

    for feature, description in features:
        print("12")

    print("\n" + "="*60)
    print("🎯 COMPETITIVE ADVANTAGES")
    print("="*60)

    advantages = [
        "Zero cost vs $165-480/year commercial solutions",
        "Official NOAA data sources (same as commercial products)",
        "Modern web-based interface (no desktop software required)",
        "Open source transparency and customization",
        "Real-time data streaming capabilities",
        "Mobile accessibility for field operations",
        "Integration with existing GIS workflows"
    ]

    for advantage in advantages:
        print(f"   ✅ {advantage}")

def show_usage_examples():
    """Show usage examples for the web dashboard"""

    print("\n" + "="*60)
    print("📖 USAGE EXAMPLES")
    print("="*60)

    examples = [
        ("Basic Dashboard Creation", """
from web_dashboard_generator import create_web_dashboard_from_rsd

# Create dashboard from RSD file
dashboard_path = create_web_dashboard_from_rsd("Holloway.RSD")
print(f"Dashboard created: {dashboard_path}")
        """),

        ("Custom Configuration", """
from web_dashboard_generator import WebDashboardGenerator

# Create custom dashboard
generator = WebDashboardGenerator()
survey_data = {
    'filename': 'MySurvey.RSD',
    'record_count': 15000,
    'center_lat': 40.5,
    'center_lon': -74.2
}
dashboard_path = generator.create_dashboard(
    survey_data,
    'survey.mbtiles',
    'custom_dashboard'
)
        """),

        ("Batch Processing", """
import glob
from web_dashboard_generator import create_web_dashboard_from_rsd

# Process multiple RSD files
rsd_files = glob.glob("*.RSD")
for rsd_file in rsd_files:
    dashboard_name = f"dashboard_{Path(rsd_file).stem}"
    create_web_dashboard_from_rsd(rsd_file, dashboard_name)
    print(f"Created dashboard for {rsd_file}")
        """)
    ]

    for title, code in examples:
        print(f"\n🔧 {title}:")
        print("   " + "\n   ".join(code.strip().split("\n")))

if __name__ == "__main__":
    print("Garmin RSD Web Dashboard Generator")
    print("Creates interactive web-based marine survey visualizations")
    print("with NOAA ENC charts and MBTiles overlays")
    print()

    # Show features overview
    show_web_dashboard_features()

    # Show usage examples
    show_usage_examples()

    # Run demo if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("\n" + "="*60)
        print("🚀 RUNNING WEB DASHBOARD DEMO")
        print("="*60)

        success = create_web_dashboard_demo()
        if success:
            print("\n🎉 Demo completed successfully!")
            print("   Open the created dashboard in your web browser to explore the features.")
        else:
            print("\n❌ Demo failed. Check the error messages above.")
    else:
        print("\n" + "="*60)
        print("🚀 TO RUN THE DEMO:")
        print("   python web_dashboard_demo.py --demo")
        print("="*60)