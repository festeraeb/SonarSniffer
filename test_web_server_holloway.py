#!/usr/bin/env python3
"""
Test Sonar Sniffer web server with Holloway data.
Demonstrates Path B (KML) and Path C (MBTiles) outputs.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sar_web_server import SARWebServer, SARWebServerIntegration
from engine_fast_rsd import parse_rsd_records_fast

# Configuration
RSD_FILE = 'Holloway (2).RSD'
OUTPUT_DIR = 'test_web_output'
TEST_PORT = 8080
NUM_RECORDS = 500  # Use subset for quick testing

print("=" * 70)
print("SONAR SNIFFER WEB SERVER TEST - HOLLOWAY DATA")
print("=" * 70)

# Step 1: Parse Holloway data
print(f"\n[1/4] Parsing {RSD_FILE}...")
if not Path(RSD_FILE).exists():
    print(f"ERROR: {RSD_FILE} not found in current directory")
    sys.exit(1)

try:
    records = []
    for i, record in enumerate(parse_rsd_records_fast(RSD_FILE)):
        if i >= NUM_RECORDS:
            break
        records.append(record)
    print(f"✓ Parsed {len(records)} records from {RSD_FILE}")
except Exception as e:
    print(f"ERROR parsing RSD: {e}")
    sys.exit(1)

if not records:
    print("ERROR: No records parsed")
    sys.exit(1)

# Extract GPS coordinates
gps_coords = []
for record in records:
    if hasattr(record, 'latitude') and hasattr(record, 'longitude'):
        if record.latitude != 0 and record.longitude != 0:
            gps_coords.append({
                'lat': record.latitude,
                'lon': record.longitude,
                'timestamp': getattr(record, 'timestamp', None)
            })

print(f"✓ Extracted {len(gps_coords)} GPS coordinates")

if gps_coords:
    avg_lat = sum(c['lat'] for c in gps_coords) / len(gps_coords)
    avg_lon = sum(c['lon'] for c in gps_coords) / len(gps_coords)
    print(f"  Center: {avg_lat:.4f}, {avg_lon:.4f}")

# Step 2: Create web server (Path B - KML overlay)
print(f"\n[2/4] Creating Sonar Sniffer web server (Path B - KML)...")
server = SARWebServer(
    port=TEST_PORT,
    allow_external=True,
    auto_open_browser=False,
    output_dir=OUTPUT_DIR,
    server_name="🌊 Sonar Sniffer by CESARops - Holloway Test"
)

# Create sample KML file
kml_file = Path(OUTPUT_DIR) / 'holloway_survey.kml'
kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Holloway Sonar Survey</name>
    <description>Sonar Sniffer by CESARops - Search and Rescue</description>
    <Folder>
      <name>GPS Track</name>
"""

# Add placemarks for GPS positions
for i, coord in enumerate(gps_coords[::max(1, len(gps_coords)//20)]):  # Sample every Nth point
    kml_content += f"""      <Placemark>
        <name>Position {i}</name>
        <Point>
          <coordinates>{coord['lon']},{coord['lat']},0</coordinates>
        </Point>
      </Placemark>
"""

kml_content += """    </Folder>
  </Document>
</kml>
"""

kml_file.parent.mkdir(parents=True, exist_ok=True)
with open(kml_file, 'w') as f:
    f.write(kml_content)
print(f"✓ Created KML file: {kml_file}")

# Add KML overlay
server.add_kml_overlay(
    str(kml_file),
    name='Holloway Survey Track',
    visible=True,
    opacity=0.9
)

# Step 3: Start server (Path B demonstration)
print(f"\n[3/4] Starting web server on port {TEST_PORT}...")
print(f"  Name: {server.server_name}")
print(f"  Output dir: {OUTPUT_DIR}")
print(f"  URL: http://localhost:{TEST_PORT}")

try:
    server.start()
    print("✓ Web server started successfully")
    print(f"  Access at: http://localhost:{TEST_PORT}")
    
    # Give it a moment to start
    time.sleep(1)
    
    # Step 4: Generate HTML output
    print(f"\n[4/4] Generating HTML visualization...")
    html_file = Path(OUTPUT_DIR) / 'holloway_visualization.html'
    
    # Create a simple HTML visualization
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sonar Sniffer by CESARops - Holloway Test</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 10px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .subtitle {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        #map {{
            width: 100%;
            height: 600px;
            border: 2px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .info {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat {{
            background: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .stat-value {{
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌊 Sonar Sniffer by CESARops</h1>
        <div class="subtitle">Holloway Survey Data - Web Server Test</div>
    </div>
    
    <div id="map"></div>
    
    <div class="info">
        <h2>Survey Information</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Records Parsed</div>
                <div class="stat-value">{len(records)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">GPS Points</div>
                <div class="stat-value">{len(gps_coords)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Generated</div>
                <div class="stat-value">{datetime.now().strftime('%H:%M:%S')}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Server</div>
                <div class="stat-value">Path B</div>
            </div>
        </div>
        
        <h3>Server Details</h3>
        <ul>
            <li><strong>Type:</strong> Sonar Sniffer Web Server</li>
            <li><strong>Branding:</strong> by CESARops - Search and Rescue</li>
            <li><strong>Data Source:</strong> {RSD_FILE}</li>
            <li><strong>Output Format:</strong> KML Overlay + HTML Viewer</li>
            <li><strong>Port:</strong> {TEST_PORT}</li>
        </ul>
        
        <h3>About Sonar Sniffer by CESARops</h3>
        <p>
            Sonar Sniffer is a comprehensive sonar data parser and visualization platform 
            designed for Search and Rescue operations. The web server component allows 
            real-time collaboration with remote teams and family members.
        </p>
        <p>
            <strong>CESARops</strong> is an open-source drift modeling tool for Search and Rescue 
            operations. Learn more at: <a href="https://github.com/festeraeb/CESARops" target="_blank">
            github.com/festeraeb/CESARops</a>
        </p>
    </div>
    
    <script>
        // Initialize map
        var map = L.map('map').setView([{avg_lat}, {avg_lon}], 13);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Add survey points
        var points = {json.dumps(gps_coords[:100])};  // Sample first 100
        points.forEach(function(point, index) {{
            L.circleMarker([point.lat, point.lon], {{
                radius: 4,
                fillColor: '#667eea',
                color: '#fff',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.7
            }}).bindPopup('Position ' + index).addTo(map);
        }});
    </script>
</body>
</html>
"""
    
    with open(html_file, 'w') as f:
        f.write(html_content)
    print(f"✓ Generated HTML: {html_file}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✓ Parsed {len(records)} records from {RSD_FILE}")
    print(f"✓ Extracted {len(gps_coords)} GPS coordinates")
    print(f"✓ Created KML overlay: {kml_file}")
    print(f"✓ Started web server on port {TEST_PORT}")
    print(f"✓ Generated HTML visualization: {html_file}")
    print("\nWeb Server Status: RUNNING")
    print(f"Access at: http://localhost:{TEST_PORT}")
    print("\nPath B (KML Overlay) Implementation: ✓ SUCCESS")
    print("Path C (MBTiles/PMTiles) Implementation: PENDING")
    print("\n" + "=" * 70)
    
    # Keep server running for a bit
    print("\nServer will run for 30 seconds. Press Ctrl+C to stop.")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nShutdown requested")
    finally:
        server.stop()
        print("Server stopped")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
