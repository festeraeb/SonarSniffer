#!/usr/bin/env python3
"""
Simple Web Dashboard Demo
Creates a basic web dashboard using existing output generation
"""

import os
import json
from pathlib import Path

# Import license manager
try:
    from .license_manager import require_license
    require_license()  # Check license on import
except ImportError:
    print("⚠️  License manager not found. Running in unlicensed mode.")
    print("📧 Contact festeraeb@yahoo.com for proper licensing.")

def create_simple_web_demo():
    """Create a simple web dashboard demo"""

    print("🌐 Creating Simple Web Dashboard Demo")
    print("=" * 50)

    # Create demo directory
    demo_dir = Path("web_demo")
    demo_dir.mkdir(exist_ok=True)

    # Create sample survey data
    survey_data = {
        "filename": "Demo_Survey.RSD",
        "record_count": 2500,
        "coverage_area": "2.3 sq miles",
        "depth_range": "0.5m - 35.2m",
        "processing_time": "0.8s",
        "center_lat": 40.0,
        "center_lon": -74.0,
        "bounds": {
            "north": 40.05,
            "south": 39.95,
            "east": -73.95,
            "west": -74.05
        }
    }

    # Create HTML dashboard
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Marine Survey Web Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #007cba 0%, #005a87 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header-content {{ display: flex; align-items: center; gap: 20px; }}
        .logo {{ flex-shrink: 0; }}
        .sonar-sniffer-logo {{ filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); }}
        .title-section h1 {{ margin: 0 0 5px 0; font-size: 2em; }}
        .title-section p {{ margin: 0; opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .map-placeholder {{ background: #e0e0e0; height: 400px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <!-- Animated SonarSniffer Logo with Vizsla Silhouette -->
                <svg width="120" height="40" viewBox="0 0 120 40" xmlns="http://www.w3.org/2000/svg" class="sonar-sniffer-logo-animated">
                    <defs>
                        <!-- Sonar wave animation -->
                        <style>
                            @keyframes sonarPulse {{
                                0% {{
                                    opacity: 0.8;
                                    transform: scale(0.2);
                                }}
                                50% {{
                                    opacity: 0.4;
                                    transform: scale(0.6);
                                }}
                                100% {{
                                    opacity: 0;
                                    transform: scale(1.2);
                                }}
                            }}

                            .sonar-wave {{
                                animation: sonarPulse 2s infinite ease-out;
                                transform-origin: center;
                            }}

                            .sonar-wave:nth-child(1) {{ animation-delay: 0s; }}
                            .sonar-wave:nth-child(2) {{ animation-delay: 0.5s; }}
                            .sonar-wave:nth-child(3) {{ animation-delay: 1s; }}
                            .sonar-wave:nth-child(4) {{ animation-delay: 1.5s; }}
                        </style>
                    </defs>

                    <!-- Sonar waves emanating from nose -->
                    <g transform="translate(15, 20)">
                        <!-- Wave 1 -->
                        <circle cx="0" cy="-3" r="3" fill="none" stroke="#007cba" stroke-width="0.5" class="sonar-wave" opacity="0"/>
                        <!-- Wave 2 -->
                        <circle cx="0" cy="-3" r="5" fill="none" stroke="#007cba" stroke-width="0.5" class="sonar-wave" opacity="0"/>
                        <!-- Wave 3 -->
                        <circle cx="0" cy="-3" r="7" fill="none" stroke="#007cba" stroke-width="0.5" class="sonar-wave" opacity="0"/>
                        <!-- Wave 4 -->
                        <circle cx="0" cy="-3" r="9" fill="none" stroke="#007cba" stroke-width="0.5" class="sonar-wave" opacity="0"/>
                    </g>

                    <!-- Vizsla silhouette (compact, pointed nose forward) -->
                    <g transform="translate(15, 20)">
                        <!-- Vizsla body (sleeker, more athletic) -->
                        <ellipse cx="0" cy="2" rx="8" ry="4" fill="#8B4513"/>
                        <!-- Vizsla head (more refined, pointed muzzle) -->
                        <ellipse cx="-6" cy="-0.5" rx="5" ry="3.5" fill="#8B4513"/>
                        <!-- Vizsla ears (floppy, characteristic of vizsla) -->
                        <ellipse cx="-7.5" cy="-3.5" rx="1.5" ry="3" fill="#654321"/>
                        <ellipse cx="-4.5" cy="-3.5" rx="1.5" ry="3" fill="#654321"/>
                        <!-- Vizsla nose (prominent, pointed) -->
                        <ellipse cx="-9.5" cy="0" rx="1" ry="0.6" fill="#000"/>
                        <!-- Vizsla eyes -->
                        <circle cx="-5.5" cy="-2" r="0.7" fill="#000"/>
                        <!-- Vizsla tail (curved, docked) -->
                        <path d="M 6 0.5 Q 8.5 -1 7.5 0" stroke="#8B4513" stroke-width="1" fill="none"/>
                        <!-- Vizsla legs (sleek) -->
                        <rect x="-4" y="6" width="1" height="4" fill="#654321"/>
                        <rect x="-1.5" y="6" width="1" height="4" fill="#654321"/>
                        <rect x="1.5" y="6" width="1" height="4" fill="#654321"/>
                        <rect x="4" y="6" width="1" height="4" fill="#654321"/>
                    </g>

                    <!-- Text -->
                    <text x="30" y="15" font-family="Arial, sans-serif" font-size="10" font-weight="bold" fill="#007cba">SonarSniffer</text>
                    <text x="30" y="25" font-family="Arial, sans-serif" font-size="6" fill="#666">by NautiDog Inc.</text>
                </svg>
            </div>
            <div class="title-section">
                <h1>🛳️ Marine Survey Dashboard</h1>
                <p>Interactive visualization of sonar survey data</p>
            </div>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>📊 Survey Records</h3>
            <p style="font-size: 2em; color: #007cba;">{survey_data['record_count']:,}</p>
        </div>
        <div class="stat-card">
            <h3>📐 Coverage Area</h3>
            <p style="font-size: 2em; color: #007cba;">{survey_data['coverage_area']}</p>
        </div>
        <div class="stat-card">
            <h3>🌊 Depth Range</h3>
            <p style="font-size: 2em; color: #007cba;">{survey_data['depth_range']}</p>
        </div>
        <div class="stat-card">
            <h3>⚡ Processing Time</h3>
            <p style="font-size: 2em; color: #007cba;">{survey_data['processing_time']}</p>
        </div>
    </div>

    <div class="map-placeholder">
        <div style="text-align: center;">
            <h2>🗺️ Interactive Map View</h2>
            <p>NOAA ENC Charts + MBTiles Survey Overlay</p>
            <p style="color: #666;">Center: {survey_data['center_lat']:.4f}°N, {survey_data['center_lon']:.4f}°W</p>
            <div style="margin: 20px;">
                <button style="padding: 10px 20px; background: #007cba; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    🔍 View Full Interactive Map
                </button>
            </div>
        </div>
    </div>

    <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3>🎯 Key Features</h3>
        <ul>
            <li>✅ NOAA ENC base charts (official government data)</li>
            <li>✅ MBTiles survey data overlay</li>
            <li>✅ Interactive zoom and pan controls</li>
            <li>✅ Target detection visualization</li>
            <li>✅ Depth profiling tools</li>
            <li>✅ Mobile-responsive design</li>
            <li>✅ Export to KML, GeoJSON, PDF</li>
        </ul>
    </div>

    <div style="text-align: center; margin: 40px 0; padding: 20px; background: #e8f4f8; border-radius: 8px;">
        <h3>🚀 Ready for Full Implementation</h3>
        <p>This demo shows the web dashboard concept. The full implementation provides:</p>
        <ul style="display: inline-block; text-align: left;">
            <li>Real-time NOAA ENC chart integration</li>
            <li>High-performance MBTiles rendering</li>
            <li>Advanced analytics and target detection</li>
            <li>Professional marine survey interface</li>
        </ul>
    </div>

    <footer style="text-align: center; margin-top: 40px; padding: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em;">
        <p><strong>SonarSniffer by NautiDog Inc.</strong> | Trial License</p>
        <p>For commercial licensing or full license activation, contact: <a href="mailto:festeraeb@yahoo.com" style="color: #007cba;">festeraeb@yahoo.com</a></p>
        <p>Search & Rescue organizations: Request free permanent license</p>
    </footer>
</body>
</html>"""

    # Write HTML file
    with open(demo_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Create metadata file
    with open(demo_dir / "survey_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(survey_data, f, indent=2)

    print("✅ Simple web dashboard created!")
    print(f"📂 Location: {demo_dir.absolute()}")
    print(f"🌐 Open: file://{demo_dir.absolute()}/index.html")

    return str(demo_dir)

if __name__ == "__main__":
    create_simple_web_demo()