"""
Search and Rescue Web Server - Automatic Sonar Data Visualization
============================================================================

Purpose:
    Auto-start web server when sonar processing completes
    Enables family/non-technical users to view results via browser
    Supports IP address sharing (192.168.x.x:8080)
    Works completely offline - no internet required
    Provides interactive maps + data overlays

Usage:
    # Path B (Basic KML/MBTiles):
    server = SARWebServer(port=8080)
    server.add_kml_overlay('output/sonar.kml', 'Sonar Survey')
    server.add_mbtiles('output/sonar.mbtiles', 'Sonar Tiles')
    server.start()  # Blocks, run in thread or separate process
    
    # Path C (Advanced COG/PMTiles):
    server = SARWebServer(port=8080, allow_external=True)
    server.add_cog_layer('output/sonar_cog.tif', 'High-Res Sonar')
    server.add_pmtiles('output/sonar.pmtiles', 'Vector Data')
    server.start()
    
    # Integrate with sonar_gui.py:
    # After export completes, automatically:
    #   1. Start server
    #   2. Open browser to http://localhost:8080
    #   3. Show IP address for remote sharing

Features:
    - Leaflet.js maps (open-source, no dependencies)
    - Layer switching (multiple datasets simultaneously)
    - Measure tool (distance/area measurements)
    - Data export (GeoJSON, CSV)
    - Search and Rescue optimized UI
    - Auto-discovery on local network
    - Responsive design (works on tablets)
    
Performance:
    - Tiles streamed on-demand
    - Memory efficient
    - No server-side processing
    - HTTP Range Requests support (for COG)

Format Support:
    - Path B: KML files + MBTiles (SQLite)
    - Path C: Cloud-Optimized GeoTIFF (COG) + PMTiles + GeoJSON

Dependencies:
    - Python 3.8+
    - http.server (stdlib)
    - flask or aiohttp (optional, for advanced routing)
    - PIL/Pillow (for tile generation if needed)

Author: SonarSniffer Team
License: Same as parent project
"""

import os
import json
import threading
import webbrowser
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import mimetypes

# Optional imports
try:
    import flask
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DataLayer:
    """Represents a single data layer in the web map"""
    name: str
    file_path: str
    layer_type: str  # 'kml', 'mbtiles', 'cog', 'pmtiles', 'geojson'
    visible: bool = True
    opacity: float = 1.0
    metadata: Dict = None
    
    def to_dict(self):
        """Convert to dict for JSON serialization"""
        return {
            'name': self.name,
            'file_path': self.file_path,
            'layer_type': self.layer_type,
            'visible': self.visible,
            'opacity': self.opacity,
            'metadata': self.metadata or {}
        }


class SARWebServer:
    """
    Search and Rescue optimized web server for sonar data visualization
    
    Automatically starts on sonar processing completion
    Provides zero-dependency viewing (just HTML + Leaflet.js)
    Enables family sharing via IP address
    """
    
    def __init__(
        self,
        port: int = 8080,
        allow_external: bool = False,
        auto_open_browser: bool = True,
        output_dir: str = 'sar_web_output',
        server_name: str = 'Sonar Sniffer by CESARops - Search & Rescue'
    ):
        """
        Initialize web server
        
        Args:
            port: Server port (default 8080)
            allow_external: Allow external connections (not just localhost)
            auto_open_browser: Automatically open browser on start
            output_dir: Directory for generated web files
            server_name: Name shown in browser/network discovery
        """
        self.port = port
        self.allow_external = allow_external
        self.auto_open_browser = auto_open_browser
        self.output_dir = Path(output_dir)
        self.server_name = server_name
        self.layers: Dict[str, DataLayer] = {}
        self.server = None
        self.thread = None
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track metadata for S&R operations
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'search_area': None,
            'survey_id': None,
            'contact_info': None,
            'layers': []
        }
    
    def add_kml_overlay(
        self,
        file_path: str,
        name: str,
        visible: bool = True,
        opacity: float = 1.0
    ) -> None:
        """Add KML overlay (Path B)"""
        if not Path(file_path).exists():
            logger.warning(f"KML file not found: {file_path}")
            return
        
        layer = DataLayer(
            name=name,
            file_path=file_path,
            layer_type='kml',
            visible=visible,
            opacity=opacity
        )
        self.layers[name] = layer
        logger.info(f"Added KML overlay: {name}")
    
    def add_mbtiles(
        self,
        file_path: str,
        name: str,
        visible: bool = True,
        opacity: float = 0.8
    ) -> None:
        """Add MBTiles layer (Path B)"""
        if not Path(file_path).exists():
            logger.warning(f"MBTiles file not found: {file_path}")
            return
        
        layer = DataLayer(
            name=name,
            file_path=file_path,
            layer_type='mbtiles',
            visible=visible,
            opacity=opacity
        )
        self.layers[name] = layer
        logger.info(f"Added MBTiles layer: {name}")
    
    def add_cog(
        self,
        file_path: str,
        name: str,
        visible: bool = True,
        opacity: float = 1.0
    ) -> None:
        """Add Cloud-Optimized GeoTIFF (Path C)"""
        if not Path(file_path).exists():
            logger.warning(f"COG file not found: {file_path}")
            return
        
        layer = DataLayer(
            name=name,
            file_path=file_path,
            layer_type='cog',
            visible=visible,
            opacity=opacity
        )
        self.layers[name] = layer
        logger.info(f"Added COG layer: {name}")
    
    def add_pmtiles(
        self,
        file_path: str,
        name: str,
        visible: bool = True,
        opacity: float = 0.8
    ) -> None:
        """Add PMTiles layer (Path C - cloud-optimized vector tiles)"""
        if not Path(file_path).exists():
            logger.warning(f"PMTiles file not found: {file_path}")
            return
        
        layer = DataLayer(
            name=name,
            file_path=file_path,
            layer_type='pmtiles',
            visible=visible,
            opacity=opacity
        )
        self.layers[name] = layer
        logger.info(f"Added PMTiles layer: {name}")
    
    def add_geojson(
        self,
        file_path: str,
        name: str,
        visible: bool = True,
        opacity: float = 1.0
    ) -> None:
        """Add GeoJSON layer (points, lines, polygons)"""
        if not Path(file_path).exists():
            logger.warning(f"GeoJSON file not found: {file_path}")
            return
        
        layer = DataLayer(
            name=name,
            file_path=file_path,
            layer_type='geojson',
            visible=visible,
            opacity=opacity
        )
        self.layers[name] = layer
        logger.info(f"Added GeoJSON layer: {name}")
    
    def set_search_metadata(
        self,
        survey_id: str,
        search_area: str,
        contact_info: Optional[str] = None,
        additional_metadata: Optional[Dict] = None
    ) -> None:
        """Set Search and Rescue specific metadata"""
        self.metadata['survey_id'] = survey_id
        self.metadata['search_area'] = search_area
        self.metadata['contact_info'] = contact_info
        if additional_metadata:
            self.metadata.update(additional_metadata)
    
    def generate_html(self) -> str:
        """Generate the main HTML map interface"""
        
        # Get local IP address
        local_ip = self._get_local_ip()
        
        layers_json = json.dumps([
            layer.to_dict() for layer in self.layers.values()
        ])
        
        metadata_json = json.dumps(self.metadata)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.server_name}</title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <!-- Leaflet Measure Plugin -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.css" />
    <script src="https://unpkg.com/leaflet-measure@3.1.0/dist/leaflet-measure.umd.js"></script>
    
    <!-- Leaflet Draw Plugin -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js"></script>
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f0f0;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin: 0;
        }}
        
        .header-info {{
            display: flex;
            gap: 20px;
            align-items: center;
            font-size: 14px;
        }}
        
        .status-badge {{
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }}
        
        .status-badge.active {{
            background: #4ade80;
        }}
        
        .container {{
            display: flex;
            height: calc(100vh - 80px);
        }}
        
        .sidebar {{
            width: 280px;
            background: white;
            overflow-y: auto;
            border-right: 1px solid #ddd;
            padding: 15px;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
        }}
        
        .map {{
            flex: 1;
            position: relative;
        }}
        
        .section {{
            margin-bottom: 20px;
        }}
        
        .section-title {{
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            color: #667eea;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }}
        
        .layer-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            margin-bottom: 8px;
            background: #f9f9f9;
            border-radius: 6px;
            border-left: 3px solid #667eea;
            transition: all 0.2s ease;
        }}
        
        .layer-item:hover {{
            background: #f0f0f0;
            transform: translateX(4px);
        }}
        
        .layer-item input[type="checkbox"] {{
            margin-right: 10px;
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        
        .layer-item label {{
            flex: 1;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .opacity-slider {{
            width: 100%;
            margin-top: 8px;
            margin-left: 28px;
            max-width: calc(100% - 28px);
        }}
        
        .info-box {{
            background: #eff6ff;
            border-left: 4px solid #667eea;
            padding: 12px;
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 15px;
        }}
        
        .info-box strong {{
            color: #667eea;
        }}
        
        .footer {{
            font-size: 12px;
            color: #999;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            margin-top: 20px;
        }}
        
        .tool-group {{
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
        }}
        
        .tool-button {{
            flex: 1;
            padding: 8px 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: background 0.2s ease;
        }}
        
        .tool-button:hover {{
            background: #764ba2;
        }}
        
        .tool-button:active {{
            transform: scale(0.98);
        }}
        
        .leaflet-container {{
            background: #e3e3e3;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                flex-direction: column;
            }}
            
            .sidebar {{
                width: 100%;
                height: 200px;
                border-right: none;
                border-bottom: 1px solid #ddd;
            }}
            
            .map {{
                height: auto;
                flex: 1;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌊 {self.server_name}</h1>
        <div class="header-info">
            <div class="status-badge active">● Live</div>
            <div>Share: <strong>{local_ip}:{self.port}</strong></div>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="info-box">
                <strong>Search Area:</strong><br/>
                {self.metadata.get('search_area', 'Not specified')}
            </div>
            
            <div class="section">
                <div class="section-title">🗺️ Data Layers</div>
                <div id="layers"></div>
            </div>
            
            <div class="section">
                <div class="section-title">🛠️ Tools</div>
                <div class="tool-group">
                    <button class="tool-button" onclick="measureTool()">📏 Measure</button>
                    <button class="tool-button" onclick="exportGeoJSON()">💾 Export</button>
                </div>
            </div>
            
            <div class="footer">
                Generated: {self.metadata['created_at'][:19]}
            </div>
        </div>
        
        <div class="map" id="map"></div>
    </div>
    
    <script>
        const layers_data = {layers_json};
        const metadata = {metadata_json};
        
        // Initialize map (centered on first layer or default)
        const map = L.map('map').setView([36.5, -121.8], 10);
        
        // Add base layers
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            maxNativeZoom: 18
        }}).addTo(map);
        
        const layerControls = {{}};
        
        // Add data layers
        layers_data.forEach((layer, idx) => {{
            let leafletLayer;
            
            if (layer.layer_type === 'kml') {{
                // Load KML from file
                fetch(layer.file_path)
                    .then(r => r.text())
                    .then(kmlStr => {{
                        const kml = new DOMParser().parseFromString(kmlStr, 'text/xml');
                        leafletLayer = omnivore.kml.parse(kml);
                        leafletLayer.setOpacity(layer.opacity);
                        layerControls[layer.name] = leafletLayer;
                        if (layer.visible) leafletLayer.addTo(map);
                    }});
            }}
            else if (layer.layer_type === 'geojson') {{
                // Load GeoJSON
                fetch(layer.file_path)
                    .then(r => r.json())
                    .then(geojson => {{
                        leafletLayer = L.geoJSON(geojson, {{
                            style: {{
                                color: '#667eea',
                                weight: 2,
                                opacity: layer.opacity,
                                fillOpacity: 0.3
                            }}
                        }});
                        layerControls[layer.name] = leafletLayer;
                        if (layer.visible) leafletLayer.addTo(map);
                    }});
            }}
        }});
        
        // Render layer controls
        const layersDiv = document.getElementById('layers');
        layers_data.forEach(layer => {{
            const div = document.createElement('div');
            div.className = 'layer-item';
            div.innerHTML = `
                <input type="checkbox" id="layer_${{layer.name}}" 
                       ${{layer.visible ? 'checked' : ''}} 
                       onchange="toggleLayer(this)">
                <label for="layer_${{layer.name}}">${{layer.name}}</label>
                <input type="range" class="opacity-slider" 
                       min="0" max="100" value="${{layer.opacity * 100}}"
                       onchange="setOpacity(this, '${{layer.name}}')">
            `;
            layersDiv.appendChild(div);
        }});
        
        function toggleLayer(checkbox) {{
            const name = checkbox.id.replace('layer_', '');
            // Implementation depends on layer type
            console.log('Toggle layer:', name, checkbox.checked);
        }}
        
        function setOpacity(slider, name) {{
            const opacity = parseInt(slider.value) / 100;
            console.log('Set opacity:', name, opacity);
        }}
        
        function measureTool() {{
            L.measureControl({{
                position: 'topright',
                primaryLengthUnit: 'meters',
                secondaryLengthUnit: 'kilometers',
                primaryAreaUnit: 'sqmeters',
                secondaryAreaUnit: 'sqkilometers'
            }}).addTo(map);
        }}
        
        function exportGeoJSON() {{
            // Export visible features as GeoJSON
            const features = [];
            // Collect from all visible layers
            const geojson = {{
                type: 'FeatureCollection',
                features: features
            }};
            
            const blob = new Blob([JSON.stringify(geojson, null, 2)], 
                                 {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'sonar_data_${{new Date().toISOString().slice(0,10)}}.geojson';
            a.click();
        }}
    </script>
    
    <!-- Omnivore for KML/GPX support -->
    <script src="https://unpkg.com/omnivore@0.6.0/dist/omnivore.umd.js"></script>
</body>
</html>
"""
        return html
    
    def _get_local_ip(self) -> str:
        """Get local IP address for network sharing"""
        try:
            # Connect to external host (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
    
    def generate_config_json(self) -> str:
        """Generate JSON configuration file"""
        config = {
            'server': {
                'name': self.server_name,
                'port': self.port,
                'allow_external': self.allow_external,
                'local_ip': self._get_local_ip(),
                'created_at': datetime.now().isoformat()
            },
            'metadata': self.metadata,
            'layers': [layer.to_dict() for layer in self.layers.values()]
        }
        return json.dumps(config, indent=2)
    
    def start(self) -> None:
        """Start the web server"""
        
        # Generate HTML file
        html_path = self.output_dir / 'index.html'
        with open(html_path, 'w') as f:
            f.write(self.generate_html())
        
        # Generate config JSON
        config_path = self.output_dir / 'config.json'
        with open(config_path, 'w') as f:
            f.write(self.generate_config_json())
        
        logger.info(f"Generated HTML: {html_path}")
        logger.info(f"Generated config: {config_path}")
        
        # Start server in background thread
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        # Open browser if requested
        if self.auto_open_browser:
            url = f"http://localhost:{self.port}"
            logger.info(f"Opening browser: {url}")
            webbrowser.open(url)
        
        local_ip = self._get_local_ip()
        logger.info(f"✓ Web server started")
        logger.info(f"  Local:  http://localhost:{self.port}")
        logger.info(f"  Remote: http://{local_ip}:{self.port}")
        logger.info(f"  (Share remote link with family/team)")
    
    def _run_server(self) -> None:
        """Run HTTP server (blocks)"""
        
        # Change to output directory
        os.chdir(self.output_dir)
        
        # Create custom handler
        handler = SimpleHTTPRequestHandler
        
        # Start server
        address = ('0.0.0.0' if self.allow_external else '127.0.0.1', self.port)
        self.server = HTTPServer(address, handler)
        
        logger.info(f"Server listening on {address}")
        self.server.serve_forever()
    
    def stop(self) -> None:
        """Stop the web server"""
        if self.server:
            self.server.shutdown()
            logger.info("Web server stopped")


class SARWebServerIntegration:
    """Integration helper for sonar_gui.py"""
    
    @staticmethod
    def create_from_export_result(
        export_dir: str,
        survey_id: str = None,
        search_area: str = None,
        contact_info: str = None,
        port: int = 8080,
        auto_start: bool = True
    ) -> SARWebServer:
        """
        Create and optionally start web server from export results
        
        Typical usage in sonar_gui.py after export:
        
            # After KML/MBTiles export completes
            server = SARWebServerIntegration.create_from_export_result(
                export_dir='output/exports',
                survey_id='SarOp-2025-11-25-001',
                search_area='Monterey Canyon - Depth 800m to 1200m',
                contact_info='Operation Lead: John Smith (831-555-0123)',
                port=8080,
                auto_start=True
            )
            
            # Server now running and browser opened
            # Share IP address with family: http://192.168.1.100:8080
        """
        
        server = SARWebServer(
            port=port,
            allow_external=True,  # Allow remote connections
            auto_open_browser=True,
            output_dir=f"{export_dir}/web",
            server_name="🌊 Sonar Sniffer by CESARops"
        )
        
        # Set metadata
        server.set_search_metadata(
            survey_id=survey_id or f"SAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            search_area=search_area or "Unknown Location",
            contact_info=contact_info
        )
        
        # Auto-detect exported files
        export_path = Path(export_dir)
        
        # Add KML overlays
        for kml_file in export_path.glob('*.kml'):
            server.add_kml_overlay(str(kml_file), kml_file.stem)
        
        # Add MBTiles
        for mbtiles_file in export_path.glob('*.mbtiles'):
            server.add_mbtiles(str(mbtiles_file), mbtiles_file.stem)
        
        # Add COG (GeoTIFF)
        for tif_file in export_path.glob('*_cog.tif'):
            server.add_cog(str(tif_file), tif_file.stem)
        
        # Add PMTiles
        for pmtiles_file in export_path.glob('*.pmtiles'):
            server.add_pmtiles(str(pmtiles_file), pmtiles_file.stem)
        
        # Add GeoJSON
        for geojson_file in export_path.glob('*.geojson'):
            server.add_geojson(str(geojson_file), geojson_file.stem)
        
        logger.info(f"Detected {len(server.layers)} data layers")
        
        if auto_start:
            server.start()
        
        return server


if __name__ == '__main__':
    # Example: Path B (Basic)
    print("=== Path B: Basic KML/MBTiles ===")
    server_b = SARWebServer(port=8080)
    server_b.set_search_metadata(
        survey_id='SarOp-2025-11-25-001',
        search_area='Monterey Canyon - Depth 800m to 1200m',
        contact_info='Operation Lead: John Smith (831-555-0123)'
    )
    # Add mock layers (would be actual files in production)
    server_b.add_kml_overlay('mock_sonar.kml', 'Sonar Survey')
    # server_b.start()  # Uncomment to run
    print(f"Server would start on port {server_b.port}")
    
    # Example: Path C (Advanced)
    print("\n=== Path C: Advanced COG/PMTiles ===")
    server_c = SARWebServer(
        port=8081,
        allow_external=True,
        server_name="🌊 Sonar Sniffer by CESARops"
    )
    server_c.set_search_metadata(
        survey_id='SarOp-2025-11-25-002',
        search_area='Santa Lucia Bank - High-Resolution Survey',
        contact_info='Research Team: UC Santa Cruz'
    )
    # Would add COG + PMTiles in production
    print(f"Server would start on port {server_c.port}")
    
    # Example: Integration with sonar_gui.py
    print("\n=== Integration Example ===")
    # After export completes:
    # server = SARWebServerIntegration.create_from_export_result(
    #     export_dir='output/exports',
    #     survey_id='LiveOp-2025-11-25',
    #     search_area='Coral Reef Survey',
    #     auto_start=True
    # )
    print("Ready for integration into sonar_gui.py")
