#!/usr/bin/env python3
"""
GUI Integration Layer - Sonar Sniffer
Bridges GUI post-processing with web outputs and tunnel fallbacks.
Provides unified pipeline: Parse → Process → Export → Share
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, List
import threading
import subprocess
import webbrowser
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for complete processing pipeline"""
    input_file: str
    output_dir: str
    generate_video: bool = True
    generate_kml: bool = True
    generate_mbtiles: bool = True
    generate_dem: bool = True
    generate_web_outputs: bool = True
    generate_pathc_tiles: bool = False
    launch_web_server: bool = True
    setup_tunnel: bool = False
    tunnel_type: Optional[str] = None  # ngrok, cloudflare, localhost_run, etc.


class WebOutputsIntegration:
    """Integrates web-based outputs with sonar processing pipeline"""
    
    def __init__(self, output_dir: str, survey_name: str = "Sonar Survey"):
        """Initialize web outputs integration.
        
        Args:
            output_dir: Directory where processed data is stored
            survey_name: Name of the survey for web outputs
        """
        self.output_dir = Path(output_dir)
        self.survey_name = survey_name
        self.web_outputs_dir = self.output_dir / 'web_outputs'
        self.web_outputs_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_viewer(self, records: List[Dict], kml_path: Optional[Path] = None,
                       dem_path: Optional[Path] = None) -> bool:
        """
        Generate web-based output interface.
        
        Args:
            records: List of sonar records with lat/lon/depth data
            kml_path: Path to generated KML file (optional)
            dem_path: Path to generated DEM file (optional)
            
        Returns:
            True if successful
        """
        try:
            logger.info("Generating web-based outputs interface...")
            
            # Import web outputs generator
            from family_survey_viewer import FamilySurveyViewer
            
            # Calculate statistics from records
            stats = self._calculate_statistics(records)
            
            # Generate HTML pages
            viewer = FamilySurveyViewer(str(self.web_outputs_dir))
            
            # Generate all pages
            viewer.generate_index()
            viewer.generate_map_viewer()
            viewer.generate_statistics()
            viewer.generate_help_page()
            viewer.generate_about_page()
            
            # Generate access link page
            self._generate_access_link(stats)
            
            logger.info(f"✓ Web outputs generated in {self.web_outputs_dir}")
            return True
        
        except Exception as e:
            logger.error(f"Web outputs generation failed: {e}")
            return False
    
    def _calculate_statistics(self, records: List[Dict]) -> Dict:
        """Calculate survey statistics from records."""
        if not records:
            return {
                'total_records': 0,
                'gps_points': 0,
                'coverage_area': 0,
                'duration': 0,
                'min_depth': 0,
                'max_depth': 0,
                'avg_depth': 0,
            }
        
        lats = [r.get('latitude', r.get('lat', 0)) for r in records]
        lons = [r.get('longitude', r.get('lon', 0)) for r in records]
        depths = [r.get('depth', r.get('depth_m', 0)) for r in records]
        
        import math
        
        # Simple bounding box area estimate (rough)
        if lats and lons:
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            # At ~40°N: 1° ≈ 85 km lat, 65 km lon
            area = lat_range * 85 * lon_range * 65
        else:
            area = 0
        
        return {
            'total_records': len(records),
            'gps_points': len([r for r in records if r.get('latitude') and r.get('longitude')]),
            'coverage_area': area,
            'duration': len(records) / 30,  # Assume 30 Hz sonar
            'min_depth': min(depths) if depths else 0,
            'max_depth': max(depths) if depths else 0,
            'avg_depth': sum(depths) / len([d for d in depths if d]) if depths else 0,
        }
    
    def _generate_access_link(self, stats: Dict) -> None:
        """Generate access information page."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sonar Sniffer - Survey Results</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #999;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            text-align: center;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }}
        .navigation {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }}
        .nav-button {{
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 12px;
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s;
        }}
        .nav-button:hover {{
            transform: translateY(-2px);
        }}
        .nav-icon {{
            font-size: 32px;
            display: block;
            margin-bottom: 10px;
        }}
        @media (max-width: 768px) {{
            .stats {{ grid-template-columns: 1fr; }}
            .navigation {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Sonar Sniffer Survey Results</h1>
        <p class="subtitle">Generated by Sonar Sniffer by CESARops</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total_records']}</div>
                <div class="stat-label">Total Records</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['gps_points']}</div>
                <div class="stat-label">GPS Points</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_depth']:.1f}m</div>
                <div class="stat-label">Average Depth</div>
            </div>
        </div>
        
        <div class="navigation">
            <a href="index.html" class="nav-button">
                <span class="nav-icon">🏠</span>
                Home Page
            </a>
            <a href="map_viewer.html" class="nav-button">
                <span class="nav-icon">🗺️</span>
                Interactive Map
            </a>
            <a href="statistics.html" class="nav-button">
                <span class="nav-icon">📊</span>
                Statistics
            </a>
            <a href="help.html" class="nav-button">
                <span class="nav-icon">❓</span>
                Help & FAQ
            </a>
        </div>
    </div>
</body>
</html>
"""
        access_file = self.web_outputs_dir / 'SURVEY_RESULTS.html'
        with open(access_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"✓ Access link generated: {access_file}")


class TunnelIntegration:
    """Integrates tunnel fallbacks with GUI"""
    
    def __init__(self, local_port: int = 8080):
        """Initialize tunnel integration."""
        self.local_port = local_port
        self.tunnel_process = None
        self.tunnel_url = None
    
    def setup_tunnel(self, tunnel_type: str = 'localhost_run') -> tuple[bool, Optional[str]]:
        """
        Setup tunnel for remote access.
        
        Args:
            tunnel_type: Type of tunnel (ngrok, cloudflare, localhost_run, serveo, tailscale)
            
        Returns:
            (success, url)
        """
        try:
            from tunnel_fallbacks import TunnelManager, TunnelType
            
            manager = TunnelManager(local_port=self.local_port)
            
            # Try specified tunnel
            tunnel_enum = TunnelType[tunnel_type.upper()] if tunnel_type else None
            success, url = manager.setup_fallback_tunnel(preferred=tunnel_enum)
            
            if success and url:
                logger.info(f"✓ Tunnel established: {url}")
                self.tunnel_url = url
                return (True, url)
            else:
                logger.warning("Tunnel setup failed - using local network only")
                return (False, None)
        
        except Exception as e:
            logger.error(f"Tunnel integration failed: {e}")
            return (False, None)
    
    def launch_server(self, output_dir: str) -> bool:
        """
        Launch web server.
        
        Args:
            output_dir: Directory containing web_outputs
            
        Returns:
            True if successful
        """
        try:
            from integration_server import FamilyViewerServer
            
            web_outputs_path = Path(output_dir) / 'web_outputs'
            server = FamilyViewerServer(port=self.local_port, output_dir=str(web_outputs_path))
            
            if server.start():
                logger.info(f"✓ Web server started on port {self.local_port}")
                
                # Open browser to local access
                url = f"http://localhost:{self.local_port}/"
                logger.info(f"Opening browser: {url}")
                webbrowser.open(url)
                
                return True
            else:
                logger.error("Failed to start web server")
                return False
        
        except Exception as e:
            logger.error(f"Server launch failed: {e}")
            return False


class FullPipeline:
    """Complete sonar processing pipeline from RSD to web outputs"""
    
    def __init__(self, config: PipelineConfig, progress_callback: Optional[Callable] = None):
        """
        Initialize pipeline.
        
        Args:
            config: Pipeline configuration
            progress_callback: Callback function for progress updates (msg, percent)
        """
        self.config = config
        self.progress_callback = progress_callback or (lambda msg, pct: None)
        self.results = {}
    
    def execute(self) -> bool:
        """Execute complete pipeline."""
        try:
            self.progress_callback("Initializing pipeline...", 0)
            
            # Create output directory
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
            
            # Step 1: Parse RSD file
            self.progress_callback("Parsing sonar data...", 10)
            if not self._parse_rsd():
                return False
            
            # Step 2: Generate video
            if self.config.generate_video:
                self.progress_callback("Generating video...", 30)
                self._generate_video()
            
            # Step 3: Geospatial exports (KML, MBTiles, DEM)
            self.progress_callback("Generating geospatial exports...", 50)
            if not self._generate_geospatial():
                return False
            
            # Step 4: Generate web outputs
            if self.config.generate_web_outputs:
                self.progress_callback("Generating web outputs...", 70)
                if not self._generate_web_outputs():
                    return False
            
            # Step 5: Setup tunnel (optional)
            if self.config.setup_tunnel:
                self.progress_callback("Setting up remote tunnel...", 80)
                self._setup_tunnel()
            
            # Step 6: Launch server (optional)
            if self.config.launch_web_server:
                self.progress_callback("Launching web server...", 85)
                self._launch_server()
            
            self.progress_callback("Pipeline complete!", 100)
            return True
        
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.progress_callback(f"Error: {e}", 0)
            return False
    
    def _parse_rsd(self) -> bool:
        """Parse RSD file."""
        try:
            # This would be called from GUI with appropriate parser
            logger.info(f"Parsing RSD: {self.config.input_file}")
            # Actual parsing would happen here via the parser modules
            self.results['records'] = []  # Placeholder
            return True
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            return False
    
    def _generate_video(self) -> bool:
        """Generate video output."""
        try:
            logger.info("Generating video...")
            # Video generation would happen here
            return True
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return False
    
    def _generate_geospatial(self) -> bool:
        """Generate KML, MBTiles, DEM."""
        try:
            logger.info("Generating geospatial exports...")
            # Geospatial generation would happen here
            return True
        except Exception as e:
            logger.error(f"Geospatial export failed: {e}")
            return False
    
    def _generate_web_outputs(self) -> bool:
        """Generate web outputs."""
        try:
            if not self.results.get('records'):
                logger.warning("No records for web outputs")
                return False
            
            viewer = WebOutputsIntegration(
                self.config.output_dir,
                survey_name="Sonar Survey"
            )
            
            return viewer.generate_viewer(
                self.results['records'],
                kml_path=self.results.get('kml_path'),
                dem_path=self.results.get('dem_path')
            )
        
        except Exception as e:
            logger.error(f"Web outputs generation failed: {e}")
            return False
    
    def _setup_tunnel(self) -> bool:
        """Setup tunnel for remote access."""
        try:
            tunnel = TunnelIntegration(local_port=8080)
            success, url = tunnel.setup_tunnel(
                tunnel_type=self.config.tunnel_type or 'localhost_run'
            )
            if success:
                self.results['tunnel_url'] = url
            return success
        except Exception as e:
            logger.error(f"Tunnel setup failed: {e}")
            return False
    
    def _launch_server(self) -> bool:
        """Launch family viewer server."""
        try:
            tunnel = TunnelIntegration(local_port=8080)
            return tunnel.launch_server(self.config.output_dir)
        except Exception as e:
            logger.error(f"Server launch failed: {e}")
            return False


def main():
    """Demonstrate pipeline usage."""
    print("\n" + "=" * 70)
    print("SONAR SNIFFER - FULL PIPELINE INTEGRATION")
    print("=" * 70)
    
    # Example configuration
    config = PipelineConfig(
        input_file="sample.rsd",
        output_dir="pipeline_output",
        generate_video=True,
        generate_kml=True,
        generate_mbtiles=True,
        generate_dem=True,
        generate_family_viewer=True,
        launch_family_viewer=True,
        setup_tunnel=False,
    )
    
    # Create pipeline
    def progress(msg, pct):
        print(f"[{pct:3d}%] {msg}")
    
    pipeline = FullPipeline(config, progress)
    success = pipeline.execute()
    
    print("\n" + "=" * 70)
    if success:
        print("✓ PIPELINE COMPLETE")
        print(f"Results: {pipeline.results}")
    else:
        print("✗ PIPELINE FAILED")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
