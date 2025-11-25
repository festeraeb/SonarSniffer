#!/usr/bin/env python3
"""
Complete Integration Server - Sonar Sniffer Family Viewer & Path C Outputs
Serves family-friendly survey viewer with all generated outputs.

Features:
- Binds to 0.0.0.0:8080 for local network access
- Optional tunnel fallbacks for remote access:
  * ngrok (fastest, requires account)
  * Cloudflare Tunnel (enterprise-grade)
  * localhost.run (simple SSH, no account)
  * serveo.net (SSH alternative)
  * Tailscale (private VPN)
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SonarSnifferRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler for Sonar Sniffer family viewer."""
    
    def do_GET(self):
        """Handle GET requests."""
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        
        # Log access
        logger.info(f"Access: {self.path}")
        
        # Call parent handler
        super().do_GET()
    
    def end_headers(self):
        """Add CORS and caching headers."""
        # Allow cross-origin access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class FamilyViewerServer:
    """Server for family survey viewer."""
    
    def __init__(self, port: int = 8080, output_dir: str = 'family_viewer_output'):
        """Initialize server."""
        self.port = port
        self.output_dir = Path(output_dir)
        self.server = None
        self.thread = None
        self.running = False
    
    def start(self):
        """Start the server."""
        if not self.output_dir.exists():
            logger.error(f"Output directory not found: {self.output_dir}")
            return False
        
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            # Create server
            self.server = HTTPServer(('0.0.0.0', self.port), SonarSnifferRequestHandler)
            logger.info(f"Starting Sonar Sniffer Family Viewer on port {self.port}")
            logger.info(f"URL: http://localhost:{self.port}")
            
            # Run in thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.running = True
            
            logger.info("Server started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            os.chdir(original_dir)
            return False
    
    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.running = False
            logger.info("Server stopped")


def generate_access_document(
    server_port: int = 8080,
    family_name: str = "Search Team",
    survey_name: str = "Holloway Search Survey"
) -> str:
    """Generate family access information document."""
    
    local_ip = "192.168.1.100"  # Would be detected in production
    access_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonar Sniffer - Family Access Link</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            padding: 50px;
            border-radius: 16px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
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
            color: #666;
            font-size: 16px;
        }}
        
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .section p {{
            color: #666;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        
        .access-link {{
            background: white;
            border: 2px dashed #667eea;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin: 20px 0;
        }}
        
        .access-link p {{
            font-size: 12px;
            color: #999;
            margin-bottom: 10px;
        }}
        
        .link-box {{
            background: #667eea;
            color: white;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            word-break: break-all;
            font-size: 14px;
            margin: 10px 0;
        }}
        
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: transform 0.2s;
            border: none;
            cursor: pointer;
        }}
        
        .button:hover {{
            transform: translateY(-2px);
        }}
        
        .button-group {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .info-list {{
            list-style: none;
            margin: 15px 0;
        }}
        
        .info-list li {{
            padding: 8px 0;
            color: #666;
            border-bottom: 1px solid #eee;
        }}
        
        .info-list li:before {{
            content: "→ ";
            color: #667eea;
            font-weight: bold;
            margin-right: 8px;
        }}
        
        .status {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
        }}
        
        .features {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .feature-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #eee;
        }}
        
        .feature-card .icon {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .feature-card .label {{
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 Sonar Sniffer</h1>
            <p>Family Viewer Access Link</p>
        </div>
        
        <div class="status">
            ✓ Server is running and ready for use
            <br/>
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <div class="section">
            <h2>Your Access Link</h2>
            <p>Share this link with family members and search team members:</p>
            <div class="access-link">
                <p>Main Link:</p>
                <div class="link-box">
                    http://localhost:{server_port}
                </div>
                <p style="margin-top: 10px;">Network IP:</p>
                <div class="link-box">
                    http://{local_ip}:{server_port}
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Quick Links</h2>
            <ul class="info-list">
                <li><a href="http://localhost:{server_port}/" style="color: #667eea;">Home Page</a> - Main family viewer</li>
                <li><a href="http://localhost:{server_port}/map_viewer.html" style="color: #667eea;">Map Viewer</a> - Interactive sonar map</li>
                <li><a href="http://localhost:{server_port}/statistics.html" style="color: #667eea;">Statistics</a> - Survey data and metrics</li>
                <li><a href="http://localhost:{server_port}/help.html" style="color: #667eea;">Help & FAQ</a> - How to use the viewer</li>
                <li><a href="http://localhost:{server_port}/about.html" style="color: #667eea;">About</a> - Information about Sonar Sniffer</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Available Features</h2>
            <div class="features">
                <div class="feature-card">
                    <div class="icon">🗺️</div>
                    <div class="label">Interactive Map</div>
                </div>
                <div class="feature-card">
                    <div class="icon">📊</div>
                    <div class="label">Statistics</div>
                </div>
                <div class="feature-card">
                    <div class="icon">🌐</div>
                    <div class="label">Browser Ready</div>
                </div>
                <div class="feature-card">
                    <div class="icon">📱</div>
                    <div class="label">Mobile Friendly</div>
                </div>
                <div class="feature-card">
                    <div class="icon">🔄</div>
                    <div class="label">Real-Time</div>
                </div>
                <div class="feature-card">
                    <div class="icon">🔒</div>
                    <div class="label">Secure</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>How to Share</h2>
            <p><strong>Local Network (Same WiFi):</strong></p>
            <p>
                Use the Network IP link above. All devices on the same WiFi network can access the viewer.
            </p>
            <p style="margin-top: 10px;"><strong>Remote Access:</strong></p>
            <p>
                Have your IT coordinator or SAR team lead set up port forwarding or a VPN tunnel
                for remote team members to access the survey.
            </p>
        </div>
        
        <div class="section">
            <h2>Survey Details</h2>
            <ul class="info-list">
                <li>Survey Name: {survey_name}</li>
                <li>Total Records: 3,332</li>
                <li>GPS Points: 2,845</li>
                <li>Data Format: Sonar Sniffer v2.0</li>
                <li>Integration: CESARops compatible</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>
                <strong>Sonar Sniffer by CESARops</strong> - Search and Rescue Sonar Analysis Platform
                <br/>
                For technical support, contact your SAR team coordinator
                <br/>
                <a href="https://github.com/festeraeb/SonarSniffer" target="_blank">GitHub</a> |
                <a href="https://github.com/festeraeb/CESARops" target="_blank">CESARops</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    return access_html


def main():
    """Launch integrated viewer server."""
    print("\n" + "=" * 70)
    print("SONAR SNIFFER FAMILY VIEWER - COMPLETE INTEGRATION")
    print("=" * 70)
    
    # Generate access document
    access_html = generate_access_document(
        server_port=8080,
        family_name="Search Team",
        survey_name="Holloway Search Survey"
    )
    
    access_file = Path('family_viewer_output') / 'ACCESS_LINK.html'
    with open(access_file, 'w', encoding='utf-8') as f:
        f.write(access_html)
    
    print(f"\nGenerated access link page: {access_file}")
    
    # Create server
    server = FamilyViewerServer(port=8080, output_dir='family_viewer_output')
    
    if server.start():
        print("\n" + "=" * 70)
        print("FAMILY VIEWER IS RUNNING")
        print("=" * 70)
        print("\n✓ Binding Address: 0.0.0.0:8080")
        print("✓ Local Access:    http://localhost:8080")
        print("✓ Network Access:  http://192.168.1.100:8080 (replace with your IP)")
        print("✓ Access Link Page: http://localhost:8080/ACCESS_LINK.html")
        
        print("\nAvailable Pages:")
        print("  - /                 (Home Page)")
        print("  - /map_viewer.html  (Interactive Map)")
        print("  - /statistics.html  (Survey Statistics)")
        print("  - /help.html        (Help & FAQ)")
        print("  - /about.html       (About Sonar Sniffer)")
        print("  - /ACCESS_LINK.html (Access Information)")
        
        print("\nOptional Remote Access (Tunnels):")
        print("  Run: python tunnel_fallbacks.py")
        print("  Options:")
        print("    - ngrok (instant public URL)")
        print("    - Cloudflare Tunnel (enterprise)")
        print("    - localhost.run (SSH-based)")
        print("    - serveo.net (SSH alternative)")
        print("    - Tailscale (private VPN)")
        
        print("\n" + "=" * 70)
        print("Server running. Press Ctrl+C to stop.")
        print("=" * 70 + "\n")
        
        try:
            # Keep running
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.stop()
            print("Server stopped.")
    else:
        print("Failed to start server")
        sys.exit(1)


if __name__ == '__main__':
    main()
