#!/usr/bin/env python3
"""
Family-Friendly Sonar Survey Viewer - Complete Web Interface
Combines Path B (KML) and Path C (MBTiles) with family-focused design.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FamilySurveyViewer:
    """Generate family-friendly sonar survey web interface."""
    
    def __init__(self, output_dir: str = 'family_viewer_output'):
        """Initialize viewer."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_index(
        self,
        survey_name: str = 'Sonar Survey',
        location: str = 'Pacific Northwest',
        date: str = None,
        records_count: int = 3332,
        survey_url: str = 'http://192.168.1.100:8080'
    ) -> Path:
        """Generate main family viewer index page."""
        
        if not date:
            date = datetime.now().strftime('%B %d, %Y')
        
        index_file = self.output_dir / 'index.html'
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonar Sniffer by CESARops - Family Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 40px 30px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 48px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 18px;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .header .subtitle {{
            font-size: 14px;
            color: #999;
        }}
        
        .welcome-banner {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .welcome-banner h2 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .welcome-banner p {{
            font-size: 16px;
            opacity: 0.95;
            line-height: 1.6;
        }}
        
        .quick-links {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .quick-link {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            color: inherit;
        }}
        
        .quick-link:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }}
        
        .quick-link .icon {{
            font-size: 48px;
            margin-bottom: 15px;
        }}
        
        .quick-link h3 {{
            font-size: 18px;
            color: #333;
            margin-bottom: 8px;
        }}
        
        .quick-link p {{
            font-size: 14px;
            color: #666;
        }}
        
        .content-section {{
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            margin-bottom: 30px;
        }}
        
        .content-section h2 {{
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
        }}
        
        .content-section h3 {{
            font-size: 18px;
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        .content-section p {{
            color: #666;
            line-height: 1.7;
            margin-bottom: 15px;
        }}
        
        .survey-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .info-box {{
            background: #f8f9fa;
            padding: 20px;
            border-left: 4px solid #667eea;
            border-radius: 8px;
        }}
        
        .info-box .label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .info-box .value {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .feature {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        
        .feature h4 {{
            color: #667eea;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
        }}
        
        .feature h4:before {{
            content: "✓";
            margin-right: 10px;
            font-weight: bold;
        }}
        
        .feature p {{
            font-size: 14px;
            color: #666;
        }}
        
        .button-group {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .button {{
            display: inline-block;
            padding: 12px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .button-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .button-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        
        .button-secondary {{
            background: #f0f0f0;
            color: #333;
            border: 2px solid #667eea;
        }}
        
        .button-secondary:hover {{
            background: #667eea;
            color: white;
        }}
        
        .footer {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            text-align: center;
            margin-top: 30px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }}
        
        .footer p {{
            color: #666;
            margin-bottom: 10px;
        }}
        
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
        
        .code-block {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #333;
            overflow-x: auto;
            margin: 15px 0;
            border-left: 4px solid #667eea;
        }}
        
        .badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 10px;
        }}
        
        .badge-success {{
            background: #4caf50;
        }}
        
        .badge-info {{
            background: #2196f3;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 36px; }}
            .welcome-banner h2 {{ font-size: 22px; }}
            .content-section {{ padding: 20px; }}
            .button-group {{ flex-direction: column; }}
            .button {{ width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 Sonar Sniffer</h1>
            <p>by CESARops - Search and Rescue</p>
            <div class="subtitle">Family Viewer & Real-time Collaboration Platform</div>
        </div>
        
        <div class="welcome-banner">
            <h2>Welcome, Family & Search Team</h2>
            <p>
                This is your dedicated platform for viewing sonar survey data in real-time.
                Watch as the team searches, collaborate with remote family, and monitor progress.
            </p>
        </div>
        
        <div class="quick-links">
            <a href="map_viewer.html" class="quick-link">
                <div class="icon">🗺️</div>
                <h3>Interactive Map</h3>
                <p>Real-time sonar track visualization with GPS overlay</p>
            </a>
            <a href="statistics.html" class="quick-link">
                <div class="icon">📊</div>
                <h3>Survey Statistics</h3>
                <p>Detailed metrics and data analysis</p>
            </a>
            <a href="help.html" class="quick-link">
                <div class="icon">❓</div>
                <h3>How to Use</h3>
                <p>Guide for family members and observers</p>
            </a>
            <a href="about.html" class="quick-link">
                <div class="icon">ℹ️</div>
                <h3>About This Tool</h3>
                <p>Learn about Sonar Sniffer and CESARops</p>
            </a>
        </div>
        
        <div class="content-section">
            <h2>Survey Information</h2>
            <div class="survey-info">
                <div class="info-box">
                    <div class="label">Survey Name</div>
                    <div class="value">{survey_name}</div>
                </div>
                <div class="info-box">
                    <div class="label">Location</div>
                    <div class="value">{location}</div>
                </div>
                <div class="info-box">
                    <div class="label">Date</div>
                    <div class="value">{date}</div>
                </div>
                <div class="info-box">
                    <div class="label">Data Points</div>
                    <div class="value">{records_count:,}</div>
                </div>
            </div>
            
            <h3>Why Use Sonar Sniffer?</h3>
            <div class="feature-grid">
                <div class="feature">
                    <h4>Real-Time Access</h4>
                    <p>View sonar survey data as it's being collected, from anywhere</p>
                </div>
                <div class="feature">
                    <h4>Easy to Use</h4>
                    <p>No special software required - works in any web browser</p>
                </div>
                <div class="feature">
                    <h4>Remote Collaboration</h4>
                    <p>Share coordinates and observations with the entire search team</p>
                </div>
                <div class="feature">
                    <h4>Multi-Device</h4>
                    <p>View on desktop, tablet, or smartphone - works everywhere</p>
                </div>
                <div class="feature">
                    <h4>Family Updates</h4>
                    <p>Keep loved ones informed about search progress</p>
                </div>
                <div class="feature">
                    <h4>Professional Data</h4>
                    <p>Access the same high-quality sonar data the professionals use</p>
                </div>
            </div>
        </div>
        
        <div class="content-section">
            <h2>Getting Started</h2>
            
            <h3>Step 1: Access the Map</h3>
            <p>Click the "Interactive Map" button above to view the sonar survey in real-time.</p>
            
            <h3>Step 2: Understand the Display</h3>
            <div class="feature-grid">
                <div class="feature">
                    <h4>Blue Track</h4>
                    <p>Shows the path the sonar boat traveled during the survey</p>
                </div>
                <div class="feature">
                    <h4>Pin Markers</h4>
                    <p>Represent specific survey points or areas of interest</p>
                </div>
                <div class="feature">
                    <h4>Zoom Controls</h4>
                    <p>Use + and - buttons or scroll wheel to zoom in/out</p>
                </div>
                <div class="feature">
                    <h4>Layer Toggle</h4>
                    <p>Switch between different data visualizations</p>
                </div>
            </div>
            
            <h3>Step 3: Share Information</h3>
            <p>Use the coordinate system to communicate with other search team members.</p>
            <div class="code-block">
                "I see a strong sonar contact at 44.5°N, 127.5°W"
            </div>
            
            <h3>Step 4: Monitor Progress</h3>
            <p>Check the statistics page for survey metrics and coverage analysis.</p>
        </div>
        
        <div class="content-section">
            <h2>About CESARops Integration</h2>
            <p>
                <strong>CESARops</strong> is an open-source tool that models how objects drift in the ocean.
                When combined with Sonar Sniffer surveys, it helps predict search patterns based on:
            </p>
            <ul style="margin: 15px 0 15px 20px; color: #666;">
                <li>Ocean currents and tides</li>
                <li>Wind patterns</li>
                <li>Object characteristics (boat, debris, etc.)</li>
                <li>Last known position</li>
            </ul>
            <p>
                This combination of sonar data and drift modeling gives SAR teams the best possible tools
                for effective search operations.
            </p>
            <div class="button-group">
                <a href="https://github.com/festeraeb/CESARops" target="_blank" class="button button-primary">
                    Learn About CESARops
                </a>
            </div>
        </div>
        
        <div class="content-section">
            <h2>Important Information</h2>
            <div class="feature-grid">
                <div class="feature" style="background: #fff3cd; border-left-color: #ffc107;">
                    <h4>Stay Safe</h4>
                    <p>Always follow SAR team instructions and maintain communication on designated channels</p>
                </div>
                <div class="feature" style="background: #d1ecf1; border-left-color: #17a2b8;">
                    <h4>Data Privacy</h4>
                    <p>Survey data is shared only within your authorized search team. Protect access credentials.</p>
                </div>
                <div class="feature" style="background: #d4edda; border-left-color: #28a745;">
                    <h4>Technical Support</h4>
                    <p>Contact your SAR coordinator if you experience technical difficulties</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Sonar Sniffer by CESARops</strong> - Search and Rescue Sonar Analysis Platform</p>
            <p style="font-size: 12px;">
                Version 2.0 | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                <a href="https://github.com/festeraeb/SonarSniffer">GitHub</a> |
                <a href="https://github.com/festeraeb/CESARops">CESARops</a>
            </p>
            <p style="font-size: 12px; color: #999;">
                A tool for Search and Rescue operations. Use responsibly and always follow SAR team protocols.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated index: {index_file}")
        return index_file
    
    def generate_map_viewer(self, bounds: List[float] = None) -> Path:
        """Generate interactive map viewer."""
        if not bounds:
            bounds = [-122.50, 37.50, -122.40, 37.60]
        
        map_file = self.output_dir / 'map_viewer.html'
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonar Sniffer - Interactive Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; }}
        .container {{ display: flex; height: 100vh; }}
        #map {{ flex: 1; }}
        .sidebar {{
            width: 300px;
            background: white;
            box-shadow: -2px 0 10px rgba(0,0,0,0.1);
            padding: 20px;
            overflow-y: auto;
        }}
        .sidebar h2 {{ color: #667eea; margin-bottom: 15px; }}
        .sidebar p {{ color: #666; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }}
        .info-item {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid #667eea;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 15px;
            color: #667eea;
            text-decoration: none;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{
            .sidebar {{ width: 100%; height: auto; }}
            .container {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="map"></div>
        <div class="sidebar">
            <a href="index.html" class="back-link">← Back to Home</a>
            <h2>🗺️ Interactive Map</h2>
            <p>
                This map shows the sonar survey track and data points.
                Zoom in with the buttons or scroll wheel.
            </p>
            <div class="info-item">
                <strong>Blue Line:</strong> Survey track
            </div>
            <div class="info-item">
                <strong>Markers:</strong> GPS points
            </div>
            <div class="info-item">
                <strong>Rectangle:</strong> Survey bounds
            </div>
            <p style="margin-top: 20px; font-size: 12px; color: #999;">
                Powered by Leaflet.js and OpenStreetMap
            </p>
        </div>
    </div>
    
    <script>
        var bounds = {json.dumps(bounds)};
        var center = {json.dumps(center)};
        
        var map = L.map('map').setView([center[0], center[1]], 11);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // Add survey bounds
        var rectangle = L.rectangle(
            [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
            {{
                color: '#667eea',
                weight: 2,
                opacity: 0.8,
                fillOpacity: 0.1
            }}
        ).addTo(map);
        
        // Add sample points
        var points = [
            {{lat: {center[0]}, lng: {center[1]}}},
            {{lat: {center[0] + 0.05}, lng: {center[1] - 0.05}}},
            {{lat: {center[0] - 0.05}, lng: {center[1] + 0.05}}},
            {{lat: {center[0] - 0.05}, lng: {center[1] - 0.05}}}
        ];
        
        points.forEach(function(point, idx) {{
            L.circleMarker([point.lat, point.lng], {{
                radius: 6,
                fillColor: '#667eea',
                color: '#fff',
                weight: 2,
                opacity: 0.9,
                fillOpacity: 0.7
            }}).bindPopup('Survey Point ' + (idx + 1)).addTo(map);
        }});
        
        // Draw track
        L.polyline(points.map(p => [p.lat, p.lng]), {{
            color: '#764ba2',
            weight: 3,
            opacity: 0.7
        }}).addTo(map);
        
        map.fitBounds(rectangle.getBounds());
    </script>
</body>
</html>
"""
        
        with open(map_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated map viewer: {map_file}")
        return map_file
    
    def generate_statistics(self, survey_stats: Dict = None) -> Path:
        """Generate statistics page."""
        if not survey_stats:
            survey_stats = {
                'total_records': 3332,
                'gps_points': 2845,
                'depth_range': (5, 150),
                'area_coverage': 2.5,
                'duration': '8 hours 34 minutes'
            }
        
        stats_file = self.output_dir / 'statistics.html'
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Survey Statistics - Sonar Sniffer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{ color: #667eea; margin-bottom: 10px; }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: white;
            text-decoration: none;
            font-weight: 600;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .stat-label {{ color: #999; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }}
        .stat-value {{ color: #667eea; font-size: 32px; font-weight: bold; }}
        .info-section {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-top: 20px;
        }}
        .info-section h2 {{ color: #667eea; margin-bottom: 15px; }}
        .info-section p {{ color: #666; line-height: 1.6; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Home</a>
        
        <div class="header">
            <h1>📊 Survey Statistics</h1>
            <p>Detailed metrics and data analysis</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Records</div>
                <div class="stat-value">{survey_stats['total_records']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">GPS Points</div>
                <div class="stat-value">{survey_stats['gps_points']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Area Coverage</div>
                <div class="stat-value">{survey_stats['area_coverage']} km²</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duration</div>
                <div class="stat-value">{survey_stats['duration']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Min Depth</div>
                <div class="stat-value">{survey_stats['depth_range'][0]} m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Max Depth</div>
                <div class="stat-value">{survey_stats['depth_range'][1]} m</div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>What Do These Numbers Mean?</h2>
            <p>
                <strong>Total Records:</strong> The number of individual sonar readings taken during the survey.
                Higher numbers mean more detailed coverage.
            </p>
            <p>
                <strong>GPS Points:</strong> Specific locations where the sonar captured data.
                These are used to create the map view.
            </p>
            <p>
                <strong>Area Coverage:</strong> The size of the region that was searched.
                Larger areas require longer survey times.
            </p>
            <p>
                <strong>Depth Range:</strong> The minimum and maximum water depths found in the survey area.
                Important for understanding the sonar's scanning range.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated statistics: {stats_file}")
        return stats_file
    
    def generate_help_page(self) -> Path:
        """Generate help/FAQ page."""
        help_file = self.output_dir / 'help.html'
        
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Help & FAQ - Sonar Sniffer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { color: #667eea; margin-bottom: 10px; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: white;
            text-decoration: none;
        }
        .faq-section {
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .faq-item {
            margin-bottom: 20px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .faq-item:last-child { border-bottom: none; }
        .question { font-weight: 600; color: #667eea; margin-bottom: 10px; cursor: pointer; }
        .answer { color: #666; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Home</a>
        
        <div class="header">
            <h1>❓ Help & FAQ</h1>
            <p>Answers to common questions</p>
        </div>
        
        <div class="faq-section">
            <div class="faq-item">
                <div class="question">What is Sonar Sniffer?</div>
                <div class="answer">
                    Sonar Sniffer is a tool for viewing and analyzing sonar survey data in real-time.
                    It allows families and search teams to collaborate during Search and Rescue operations.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">Do I need special software?</div>
                <div class="answer">
                    No! Sonar Sniffer works in any web browser (Chrome, Safari, Firefox, Edge).
                    You don't need to install anything - just access the link your team provides.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">Can I view this on my phone?</div>
                <div class="answer">
                    Yes! Sonar Sniffer is designed to work on phones, tablets, and computers.
                    Just open the link in your mobile browser.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">What is CESARops?</div>
                <div class="answer">
                    CESARops is an open-source tool that models how objects drift in the ocean.
                    Combined with Sonar Sniffer, it helps SAR teams predict search patterns.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">How do I share coordinates with the team?</div>
                <div class="answer">
                    Use the map viewer to identify locations. Click on the map to see coordinates,
                    then share them with your team coordinator using your communication channel.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">Is my data private?</div>
                <div class="answer">
                    Yes. Survey data is only accessible to people with the link provided by your SAR team.
                    Protect the URL to maintain privacy and security.
                </div>
            </div>
            
            <div class="faq-item">
                <div class="question">What if I have a problem?</div>
                <div class="answer">
                    Contact your SAR team coordinator. They can help troubleshoot technical issues
                    or provide additional training if needed.
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        with open(help_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated help page: {help_file}")
        return help_file
    
    def generate_about_page(self) -> Path:
        """Generate about page."""
        about_file = self.output_dir / 'about.html'
        
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - Sonar Sniffer by CESARops</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { color: #667eea; margin-bottom: 10px; }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: white;
            text-decoration: none;
        }
        .content {
            background: white;
            padding: 30px;
            border-radius: 12px;
        }
        h2 { color: #667eea; margin: 20px 0 10px 0; }
        p { color: #666; line-height: 1.7; margin-bottom: 15px; }
        a { color: #667eea; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .feature { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Home</a>
        
        <div class="header">
            <h1>ℹ️ About Sonar Sniffer</h1>
        </div>
        
        <div class="content">
            <h2>What is Sonar Sniffer?</h2>
            <p>
                Sonar Sniffer is a professional-grade sonar data analysis and visualization platform
                designed specifically for Search and Rescue operations. It processes raw sonar files
                (Garmin RSD format) and makes the data accessible to entire search teams in real-time.
            </p>
            
            <h2>Our Mission</h2>
            <p>
                To provide Search and Rescue coordinators, families, and teams with cutting-edge tools
                for collaborative sonar survey visualization and analysis. We believe that better data
                sharing leads to faster, more effective search operations.
            </p>
            
            <h2>Key Features</h2>
            <div class="feature">
                <strong>Real-Time Collaboration</strong> - Share survey data with remote team members instantly
            </div>
            <div class="feature">
                <strong>Path B Technology</strong> - KML overlay support for immediate deployment
            </div>
            <div class="feature">
                <strong>Path C Technology</strong> - GDAL-powered MBTiles for large-scale surveys
            </div>
            <div class="feature">
                <strong>Family Access</strong> - Keep loved ones informed during search operations
            </div>
            <div class="feature">
                <strong>No Installation Required</strong> - Works in any web browser
            </div>
            <div class="feature">
                <strong>CESARops Integration</strong> - Connect with drift modeling for complete SAR workflow
            </div>
            
            <h2>CESARops Partnership</h2>
            <p>
                Sonar Sniffer integrates seamlessly with
                <a href="https://github.com/festeraeb/CESARops" target="_blank">CESARops</a>,
                an open-source drift modeling tool for Search and Rescue. Together, they form a complete
                platform for SAR analysis and planning.
            </p>
            
            <h2>Technology Stack</h2>
            <p>
                <strong>Path B:</strong> HTML5, Leaflet.js, KML/GeoJSON format
                <br/>
                <strong>Path C:</strong> GDAL, Rasterio, MBTiles/PMTiles format
                <br/>
                <strong>Backend:</strong> Python, FastAPI/Flask
                <br/>
                <strong>Data:</strong> Garmin RSD format parsing and conversion
            </p>
            
            <h2>Open Source</h2>
            <p>
                Both Sonar Sniffer and CESARops are open-source projects, free for anyone to use.
                Visit our repositories on GitHub to contribute, report issues, or adapt the tools
                for your specific needs.
            </p>
            <p>
                <a href="https://github.com/festeraeb/SonarSniffer" target="_blank">
                    Sonar Sniffer on GitHub
                </a> |
                <a href="https://github.com/festeraeb/CESARops" target="_blank">
                    CESARops on GitHub
                </a>
            </p>
            
            <h2>Credits</h2>
            <p>
                Built for the Search and Rescue community. Powered by Leaflet.js, GDAL, and
                open-source technologies.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(about_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated about page: {about_file}")
        return about_file


def main():
    """Generate complete family viewer."""
    print("\n" + "=" * 70)
    print("GENERATING FAMILY SURVEY VIEWER")
    print("=" * 70)
    
    viewer = FamilySurveyViewer('family_viewer_output')
    
    print("\nGenerating pages...")
    files = [
        viewer.generate_index(
            survey_name="Holloway Search Survey",
            location="Pacific Northwest",
            records_count=3332
        ),
        viewer.generate_map_viewer(bounds=[-122.50, 37.50, -122.40, 37.60]),
        viewer.generate_statistics(),
        viewer.generate_help_page(),
        viewer.generate_about_page()
    ]
    
    print("\nGenerated files:")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:30} {size_kb:6.1f} KB")
    
    print("\n" + "=" * 70)
    print("FAMILY VIEWER COMPLETE")
    print("=" * 70)
    print(f"\nStart server at: family_viewer_output/")
    print(f"Main page: file://{files[0]}")
    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    main()
