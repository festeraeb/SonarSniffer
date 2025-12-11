#!/usr/bin/env python3
"""
SonarSniffer Command Line Interface

Usage:
    sonarsniffer analyze <file> [--output=<dir>] [--format=<fmt>]
    sonarsniffer web <file> [--port=<port>] [--host=<host>]
    sonarsniffer license [--generate] [--validate=<key>]
    sonarsniffer (-h | --help)
    sonarsniffer --version

Options:
    -h --help           Show this screen
    --version           Show version
    --output=<dir>      Output directory [default: ./output]
    --format=<fmt>      Output format (html,kml,geojson,pdf) [default: html]
    --port=<port>       Web server port [default: 8080]
    --host=<host>       Web server host [default: localhost]
    --generate          Generate a new license key
    --validate=<key>    Validate a license key
"""

import sys
import os
from pathlib import Path
from typing import Dict
from docopt import docopt

# Add the package to the path
sys.path.insert(0, os.path.dirname(__file__))

from sonarsniffer import LicenseManager, SonarParser, WebDashboardGenerator

def main():
    """Main CLI entry point"""
    args = docopt(__doc__, version=f"SonarSniffer {__import__('sonarsniffer').__version__}")

    # Check license first
    license_mgr = LicenseManager()
    is_valid, message = license_mgr.is_license_valid()
    if not is_valid:
        print(f"ERROR: {message}")
        print(f"Trial days remaining: {license_mgr.get_days_remaining()}")
        return 1

    if args['analyze']:
        return analyze_command(args)
    elif args['web']:
        return web_command(args)
    elif args['license']:
        return license_command(args)

    return 0

def analyze_command(args):
    """Handle analyze command"""
    file_path = args['<file>']
    output_dir = args['--output'] or './output'
    output_format = args['--format'] or 'html'

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return 1

    print(f"Analyzing sonar file: {file_path}")

    try:
        # Parse the sonar file
        parser = SonarParser()
        data = parser.parse_file(file_path)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate simple output based on format
        if output_format == 'html':
            output_file = generate_html_report(data, output_dir)
        elif output_format == 'kml':
            output_file = generate_kml_output(data, output_dir)
        elif output_format == 'geojson':
            output_file = generate_geojson_output(data, output_dir)
        else:
            output_file = generate_html_report(data, output_dir)

        print(f"Analysis complete. Output saved to: {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        return 1

def web_command(args):
    """Handle web command"""
    file_path = args['<file>']
    port = int(args['--port'] or 8080)
    host = args['--host'] or 'localhost'

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return 1

    print(f"Starting web server for: {file_path}")
    print(f"Access at: http://{host}:{port}")

    try:
        # Parse the sonar file
        parser = SonarParser()
        data = parser.parse_file(file_path)

        # Start web server using the web app
        from .web.app import SonarWebApp
        app = SonarWebApp(data)
        app.run(host=host, port=port)

    except Exception as e:
        print(f"ERROR: Web server failed: {e}")
        return 1

def generate_html_report(data: Dict, output_dir: str) -> str:
    """Generate HTML report from parsed data"""
    metadata = data.get('metadata', {})
    records = data.get('records', [])

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SonarSniffer Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #e8f4f8; padding: 15px; border-radius: 5px; flex: 1; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SonarSniffer Analysis Report</h1>
        <p><strong>File:</strong> {metadata.get('filename', 'Unknown')}</p>
        <p><strong>Format:</strong> {metadata.get('format', 'Unknown')}</p>
        <p><strong>Records:</strong> {metadata.get('record_count', 0)}</p>
    </div>

    <div class="stats">
        <div class="stat">
            <h3>Statistics</h3>
            <p><strong>Total Records:</strong> {len(records)}</p>
            <p><strong>File Size:</strong> {metadata.get('file_size', 0)} bytes</p>
    """

    if 'bounds' in metadata:
        bounds = metadata['bounds']
        html_content += f"""
            <p><strong>Latitude Range:</strong> {bounds.get('south', 0):.6f} to {bounds.get('north', 0):.6f}</p>
            <p><strong>Longitude Range:</strong> {bounds.get('west', 0):.6f} to {bounds.get('east', 0):.6f}</p>
        """

    if 'depth_range' in metadata:
        html_content += f"<p><strong>Depth Range:</strong> {metadata['depth_range']}</p>"

    html_content += """
        </div>
    </div>

    <h2>Sample Records</h2>
    <table>
        <tr>
            <th>Seq</th>
            <th>Latitude</th>
            <th>Longitude</th>
            <th>Depth (m)</th>
            <th>Time</th>
        </tr>
    """

    # Show first 10 records as sample
    for record in records[:10]:
        html_content += f"""
        <tr>
            <td>{record.get('seq', 0)}</td>
            <td>{record.get('lat', 0):.6f}</td>
            <td>{record.get('lon', 0):.6f}</td>
            <td>{record.get('depth_m', 0):.2f}</td>
            <td>{record.get('time_ms', 0)}</td>
        </tr>
        """

    html_content += """
    </table>
</body>
</html>
    """

    output_file = os.path.join(output_dir, f"{metadata.get('filename', 'report')}.html")
    with open(output_file, 'w') as f:
        f.write(html_content)

    return output_file

def generate_kml_output(data: Dict, output_dir: str) -> str:
    """Generate KML output for Google Earth"""
    metadata = data.get('metadata', {})
    records = data.get('records', [])

    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>SonarSniffer Survey - {metadata.get('filename', 'Unknown')}</name>
    <description>Marine survey data processed by SonarSniffer</description>
"""

    for record in records[:1000]:  # Limit for performance
        if record.get('lat', 0) != 0 and record.get('lon', 0) != 0:
            kml_content += f"""
    <Placemark>
      <name>Record {record.get('seq', 0)}</name>
      <Point>
        <coordinates>{record.get('lon', 0)},{record.get('lat', 0)},{record.get('depth_m', 0)}</coordinates>
      </Point>
    </Placemark>
"""

    kml_content += """
  </Document>
</kml>
    """

    output_file = os.path.join(output_dir, f"{metadata.get('filename', 'survey')}.kml")
    with open(output_file, 'w') as f:
        f.write(kml_content)

    return output_file

def generate_geojson_output(data: Dict, output_dir: str) -> str:
    """Generate GeoJSON output"""
    metadata = data.get('metadata', {})
    records = data.get('records', [])

    features = []
    for record in records[:1000]:  # Limit for performance
        if record.get('lat', 0) != 0 and record.get('lon', 0) != 0:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [record.get('lon', 0), record.get('lat', 0), record.get('depth_m', 0)]
                },
                "properties": {
                    "seq": record.get('seq', 0),
                    "depth_m": record.get('depth_m', 0),
                    "time_ms": record.get('time_ms', 0)
                }
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "filename": metadata.get('filename', 'Unknown'),
            "record_count": len(records),
            "generated_by": "SonarSniffer"
        }
    }

    import json
    output_file = os.path.join(output_dir, f"{metadata.get('filename', 'survey')}.geojson")
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)

    return output_file
    """Handle license command"""
    if args['--generate']:
        generator = LicenseKeyGenerator()
        key = generator.generate_key()
        print(f"Generated license key: {key}")
        return 0

def license_command(args):
    """Handle license command"""
    if args['--generate']:
        try:
            from sonarsniffer.license_key_generator import LicenseKeyGenerator
            generator = LicenseKeyGenerator()
            key = generator.generate_key()
            print(f"Generated license key: {key}")
            return 0
        except ImportError:
            print("ERROR: License key generator module not found")
            print("This feature requires the optional license_key_generator module")
            return 1

    elif args['--validate']:
        key = args['--validate']
        license_mgr = LicenseManager()
        # For now, just check if key is non-empty (simplified validation)
        if key and len(key.strip()) >= 10:
            print("License key is valid")
            return 0
        else:
            print("License key is invalid")
            return 1

    # Show license status
    license_mgr = LicenseManager()
    info = license_mgr.get_license_info()
    print("License Status:")
    print(f"  Valid: {info.get('is_valid', False)}")
    print(f"  Type: {info.get('license_type', 'unknown').title()}")
    print(f"  Days remaining: {info.get('days_remaining', 0)}")
    print(f"  Contact: festeraeb@yahoo.com")
    return 0

if __name__ == '__main__':
    sys.exit(main())