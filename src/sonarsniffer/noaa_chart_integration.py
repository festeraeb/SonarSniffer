#!/usr/bin/env python3
"""
NOAA Chart Integration System
Professional marine chart overlays using official NOAA GIS services
"""

import os
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io

class NOAAChartManager:
    """
    Professional NOAA chart integration using official NOAA GIS services
    Based on https://www.nauticalcharts.noaa.gov/data/gis-data-and-services.html
    """
    
    def __init__(self):
        self.base_url = "https://gis.charttools.noaa.gov/arcgis/rest/services"
        
        # Official NOAA chart services
        self.chart_services = {
            'enc_online': {
                'service': 'MCS/ENCOnline/MapServer',
                'name': 'NOAA ENC (Electronic Navigational Charts)',
                'description': 'Official NOAA Electronic Navigational Charts - most current',
                'tile_url': f'{self.base_url}/MCS/ENCOnline/MapServer/tile/{{z}}/{{y}}/{{x}}',
                'zoom_range': (1, 18),
                'best_for': 'Navigation, detailed coastal features'
            },
            'chart_display': {
                'service': 'MCS/NOAAChartDisplay/MapServer', 
                'name': 'NOAA Chart Display Service',
                'description': 'Comprehensive chart display with multiple layers',
                'tile_url': f'{self.base_url}/MCS/NOAAChartDisplay/MapServer/tile/{{z}}/{{y}}/{{x}}',
                'zoom_range': (1, 16),
                'best_for': 'General marine charts, harbor charts'
            },
            'enc_direct': {
                'service': 'MCS/ENCDirect/MapServer',
                'name': 'ENC Direct to GIS',
                'description': 'Direct ENC data access for GIS applications',
                'tile_url': f'{self.base_url}/MCS/ENCDirect/MapServer/tile/{{z}}/{{y}}/{{x}}',
                'zoom_range': (1, 17),
                'best_for': 'GIS integration, detailed analysis'
            }
        }
        
        # Bathymetry services from NCEI
        self.bathymetry_services = {
            'multibeam': {
                'service': 'NCEI Multibeam Bathymetry',
                'tile_url': 'https://gis.ngdc.noaa.gov/arcgis/rest/services/web_mercator/multibeam/MapServer/tile/{z}/{y}/{x}',
                'description': 'High-resolution multibeam bathymetry data'
            },
            'dem': {
                'service': 'NCEI Coastal Relief Model',
                'tile_url': 'https://gis.ngdc.noaa.gov/arcgis/rest/services/DEM_mosaics/DEM_all/MapServer/tile/{z}/{y}/{x}',
                'description': 'Coastal digital elevation models'
            }
        }
        
    def get_service_info(self, service_name: str) -> Dict:
        """Get information about a chart service"""
        if service_name in self.chart_services:
            return self.chart_services[service_name]
        elif service_name in self.bathymetry_services:
            return self.bathymetry_services[service_name]
        else:
            raise ValueError(f"Unknown service: {service_name}")
    
    def get_available_services(self) -> Dict[str, Dict]:
        """Get all available NOAA services"""
        return {
            'chart_services': self.chart_services,
            'bathymetry_services': self.bathymetry_services
        }
    
    def create_service_capabilities_report(self) -> str:
        """Create a report of available NOAA services"""
        report = []
        report.append("NOAA CHART SERVICES AVAILABLE:\n")
        
        report.append("📊 NAVIGATIONAL CHART SERVICES:")
        for name, info in self.chart_services.items():
            report.append(f"  • {info['name']}")
            report.append(f"    Description: {info['description']}")
            report.append(f"    Best for: {info['best_for']}")
            report.append(f"    Zoom levels: {info['zoom_range'][0]}-{info['zoom_range'][1]}")
            report.append("")
        
        report.append("🌊 BATHYMETRY SERVICES:")
        for name, info in self.bathymetry_services.items():
            report.append(f"  • {info['service']}")
            report.append(f"    Description: {info['description']}")
            report.append("")
            
        report.append("💡 USAGE RECOMMENDATIONS:")
        report.append("  • Use 'enc_online' for most current navigation charts")
        report.append("  • Use 'chart_display' for general marine applications")
        report.append("  • Use 'multibeam' bathymetry for detailed depth data")
        report.append("  • Combine services for comprehensive marine displays")
        
        return "\n".join(report)

class SonarChartComposer:
    """
    Compose sonar data with NOAA charts for professional marine displays
    Similar to SonarTRX front page presentations
    """
    
    def __init__(self, chart_manager: NOAAChartManager):
        self.chart_manager = chart_manager
        self.cache_dir = Path("chart_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def download_chart_tile(self, service_name: str, x: int, y: int, z: int) -> Optional[bytes]:
        """Download a chart tile from NOAA services"""
        cache_file = self.cache_dir / f"{service_name}_{z}_{x}_{y}.png"
        
        # Check cache
        if cache_file.exists():
            return cache_file.read_bytes()
        
        try:
            service_info = self.chart_manager.get_service_info(service_name)
            url = service_info['tile_url'].format(x=x, y=y, z=z)
            
            headers = {
                'User-Agent': 'Advanced-Sonar-Studio/2.0 (Professional Marine Survey)',
                'Referer': 'https://nauticalcharts.noaa.gov/'
            }
            
            response = requests.get(url, timeout=20, headers=headers)
            response.raise_for_status()
            
            # Cache the result
            cache_file.write_bytes(response.content)
            return response.content
            
        except Exception as e:
            print(f"Error downloading {service_name} tile {z}/{x}/{y}: {e}")
            return None
    
    def create_professional_overlay(self, sonar_data: List[Dict], 
                                  bounds: Tuple[float, float, float, float],
                                  output_dir: str,
                                  chart_service: str = 'enc_online',
                                  include_bathymetry: bool = True) -> Dict[str, str]:
        """
        Create professional chart overlay like SonarTRX presentations
        
        Args:
            sonar_data: List of sonar records with lat/lon/depth
            bounds: (west, south, east, north) bounding box
            output_dir: Output directory for files
            chart_service: NOAA chart service to use
            include_bathymetry: Whether to include bathymetry layer
            
        Returns:
            Dictionary with paths to generated files
        """
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        west, south, east, north = bounds
        
        # Calculate appropriate zoom level
        zoom_level = self._calculate_optimal_zoom(bounds)
        
        print(f"Creating professional overlay using NOAA {chart_service} service")
        print(f"Area: {west:.4f}, {south:.4f} to {east:.4f}, {north:.4f}")
        print(f"Zoom level: {zoom_level}")
        
        # Download base chart
        chart_image = self._create_chart_base(chart_service, bounds, zoom_level)
        
        # Add bathymetry if requested
        if include_bathymetry:
            bathymetry_image = self._create_bathymetry_layer(bounds, zoom_level)
            if bathymetry_image:
                chart_image = self._blend_images(chart_image, bathymetry_image, alpha=0.3)
        
        # Create sonar overlay
        sonar_overlay = self._create_professional_sonar_overlay(sonar_data, bounds, chart_image.size)
        
        # Composite everything
        final_image = Image.alpha_composite(chart_image.convert('RGBA'), sonar_overlay)
        
        # Add professional annotations
        annotated_image = self._add_professional_annotations(final_image, sonar_data, bounds)
        
        # Save outputs
        results = {}
        
        # Main overlay image
        main_output = output_dir / "professional_chart_overlay.png"
        annotated_image.save(main_output, dpi=(300, 300))  # High DPI for professional use
        results['main_image'] = str(main_output)
        
        # Create KML overlay
        kml_output = output_dir / "professional_overlay.kml"
        self._create_professional_kml(kml_output, main_output, bounds, sonar_data)
        results['kml_file'] = str(kml_output)
        
        # Create metadata file
        metadata_output = output_dir / "overlay_metadata.json"
        metadata = {
            'chart_service': chart_service,
            'bounds': bounds,
            'zoom_level': zoom_level,
            'sonar_records': len(sonar_data),
            'created_by': 'Advanced Sonar Studio v2',
            'noaa_attribution': 'NOAA Office of Coast Survey',
            'projection': 'Web Mercator (EPSG:3857)'
        }
        metadata_output.write_text(json.dumps(metadata, indent=2))
        results['metadata'] = str(metadata_output)
        
        print(f"Professional overlay created: {len(results)} files generated")
        return results
    
    def _calculate_optimal_zoom(self, bounds: Tuple[float, float, float, float]) -> int:
        """Calculate optimal zoom level for given bounds"""
        west, south, east, north = bounds
        
        # Calculate span
        lat_span = north - south
        lon_span = east - west
        
        # Determine zoom based on span (rough approximation)
        if max(lat_span, lon_span) > 1.0:
            return 10
        elif max(lat_span, lon_span) > 0.1:
            return 12
        elif max(lat_span, lon_span) > 0.01:
            return 14
        else:
            return 16
    
    def _create_chart_base(self, service_name: str, bounds: Tuple[float, float, float, float], zoom: int) -> Image.Image:
        """Create base chart image from NOAA tiles"""
        west, south, east, north = bounds
        
        # Calculate tile coordinates
        min_x, max_y = self._deg2tile(north, west, zoom)
        max_x, min_y = self._deg2tile(south, east, zoom)
        
        # Create mosaic
        tile_size = 256
        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        
        base_image = Image.new('RGBA', (width, height), (135, 206, 235, 255))  # Light blue background
        
        print(f"Downloading {(max_x - min_x + 1) * (max_y - min_y + 1)} chart tiles...")
        
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                tile_data = self.download_chart_tile(service_name, x, y, zoom)
                if tile_data:
                    try:
                        tile_image = Image.open(io.BytesIO(tile_data))
                        x_offset = (x - min_x) * tile_size
                        y_offset = (y - min_y) * tile_size
                        base_image.paste(tile_image, (x_offset, y_offset))
                    except Exception as e:
                        print(f"Error processing tile {x},{y}: {e}")
        
        return base_image
    
    def _create_bathymetry_layer(self, bounds: Tuple[float, float, float, float], zoom: int) -> Optional[Image.Image]:
        """Create bathymetry layer from NOAA NCEI services"""
        # Similar to chart base but using bathymetry service
        # Implementation would be similar to _create_chart_base but with bathymetry tiles
        return None  # Placeholder for now
    
    def _create_professional_sonar_overlay(self, sonar_data: List[Dict], 
                                         bounds: Tuple[float, float, float, float],
                                         image_size: Tuple[int, int]) -> Image.Image:
        """Create professional sonar data overlay"""
        west, south, east, north = bounds
        width, height = image_size
        
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Convert sonar positions to pixel coordinates
        track_points = []
        depth_points = []
        
        for record in sonar_data:
            lat = record.get('lat', 0)
            lon = record.get('lon', 0)
            depth = record.get('depth_m', 0)
            
            if lat != 0 and lon != 0:
                # Convert to pixel coordinates
                x = int((lon - west) / (east - west) * width)
                y = int((north - lat) / (north - south) * height)
                
                track_points.append((x, y))
                
                if depth > 0:
                    # Professional depth color scheme
                    if depth < 5:
                        color = (255, 0, 0, 180)    # Red - shallow water warning
                    elif depth < 10:
                        color = (255, 165, 0, 160)  # Orange - caution
                    elif depth < 20:
                        color = (255, 255, 0, 140)  # Yellow - moderate
                    else:
                        color = (0, 255, 0, 120)    # Green - deep water
                    
                    depth_points.append((x, y, depth, color))
        
        # Draw professional track line
        if len(track_points) > 1:
            for i in range(len(track_points) - 1):
                draw.line([track_points[i], track_points[i+1]], 
                         fill=(255, 255, 255, 200), width=3)  # White track line
                draw.line([track_points[i], track_points[i+1]], 
                         fill=(0, 0, 255, 255), width=1)      # Blue center line
        
        # Draw depth points
        for x, y, depth, color in depth_points:
            size = min(8, max(2, int(depth / 5)))  # Size based on depth
            draw.ellipse([x-size, y-size, x+size, y+size], fill=color, outline=(255, 255, 255, 255))
        
        return overlay
    
    def _add_professional_annotations(self, image: Image.Image, 
                                    sonar_data: List[Dict],
                                    bounds: Tuple[float, float, float, float]) -> Image.Image:
        """Add professional annotations like scale, attribution, statistics"""
        draw = ImageDraw.Draw(image)
        
        try:
            # Try to use a professional font
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            # Fallback to default font
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Add title
        title = "PROFESSIONAL MARINE SURVEY"
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        x_pos = (image.width - title_width) // 2
        
        # Title background
        draw.rectangle([x_pos-10, 10, x_pos + title_width + 10, 50], 
                      fill=(0, 0, 0, 180))
        draw.text((x_pos, 20), title, fill=(255, 255, 255, 255), font=font_large)
        
        # Add attribution
        attribution = "Chart Data: NOAA Office of Coast Survey | Sonar: Advanced Sonar Studio"
        attr_bbox = draw.textbbox((0, 0), attribution, font=font_small)
        attr_width = attr_bbox[2] - attr_bbox[0]
        attr_x = image.width - attr_width - 10
        attr_y = image.height - 30
        
        draw.rectangle([attr_x-5, attr_y-5, attr_x + attr_width + 5, attr_y + 20], 
                      fill=(255, 255, 255, 200))
        draw.text((attr_x, attr_y), attribution, fill=(0, 0, 0, 255), font=font_small)
        
        # Add survey statistics
        if sonar_data:
            depths = [r.get('depth_m', 0) for r in sonar_data if r.get('depth_m', 0) > 0]
            if depths:
                stats = [
                    f"Survey Points: {len(sonar_data):,}",
                    f"Depth Range: {min(depths):.1f}m - {max(depths):.1f}m",
                    f"Average Depth: {np.mean(depths):.1f}m",
                    f"Area: {bounds[0]:.4f}°, {bounds[1]:.4f}° to {bounds[2]:.4f}°, {bounds[3]:.4f}°"
                ]
                
                # Stats box
                y_start = 70
                for i, stat in enumerate(stats):
                    draw.rectangle([10, y_start + i*25 - 2, 400, y_start + i*25 + 18], 
                                  fill=(255, 255, 255, 200))
                    draw.text((15, y_start + i*25), stat, fill=(0, 0, 0, 255), font=font_small)
        
        return image
    
    def _create_professional_kml(self, kml_path: Path, image_path: Path, 
                               bounds: Tuple[float, float, float, float],
                               sonar_data: List[Dict]):
        """Create professional KML file for the overlay"""
        west, south, east, north = bounds
        
        kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Professional Marine Survey Overlay</name>
    <description><![CDATA[
      <h3>Advanced Sonar Studio - Professional Marine Survey</h3>
      <p><strong>Chart Data:</strong> NOAA Office of Coast Survey</p>
      <p><strong>Survey Points:</strong> {len(sonar_data):,} sonar records</p>
      <p><strong>Area:</strong> {west:.4f}°, {south:.4f}° to {east:.4f}°, {north:.4f}°</p>
      <p><strong>Created:</strong> Advanced Sonar Studio v2.0</p>
      <p><strong>Competitive Alternative to:</strong> SonarTRX ($165-280/year)</p>
    ]]></description>
    
    <GroundOverlay>
      <name>Marine Chart with Sonar Overlay</name>
      <Icon>
        <href>{image_path.name}</href>
      </Icon>
      <LatLonBox>
        <north>{north}</north>
        <south>{south}</south>
        <east>{east}</east>
        <west>{west}</west>
      </LatLonBox>
    </GroundOverlay>
  </Document>
</kml>'''
        
        kml_path.write_text(kml_content)
    
    def _deg2tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """Convert lat/lon to tile coordinates"""
        import math
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def _blend_images(self, base: Image.Image, overlay: Image.Image, alpha: float = 0.5) -> Image.Image:
        """Blend two images with specified alpha"""
        return Image.blend(base.convert('RGBA'), overlay.convert('RGBA'), alpha)

def create_professional_demo():
    """Create a professional demo using real NOAA services"""
    print("NOAA Chart Integration Demo")
    print("=" * 50)
    
    # Initialize NOAA chart manager
    chart_manager = NOAAChartManager()
    
    # Print available services
    print(chart_manager.create_service_capabilities_report())
    
    # Sample sonar data (Boston Harbor area)
    sonar_data = [
        {'lat': 42.354, 'lon': -71.045, 'depth_m': 8.2},
        {'lat': 42.355, 'lon': -71.044, 'depth_m': 9.1},
        {'lat': 42.356, 'lon': -71.043, 'depth_m': 7.8},
        {'lat': 42.357, 'lon': -71.042, 'depth_m': 10.5},
        {'lat': 42.358, 'lon': -71.041, 'depth_m': 12.3},
    ]
    
    # Define bounds (Boston Harbor)
    bounds = (-71.05, 42.35, -71.04, 42.36)
    
    # Create professional overlay
    composer = SonarChartComposer(chart_manager)
    
    try:
        results = composer.create_professional_overlay(
            sonar_data=sonar_data,
            bounds=bounds,
            output_dir="professional_demo",
            chart_service='enc_online',
            include_bathymetry=True
        )
        
        print("\nPROFESSIONAL OVERLAY CREATED!")
        print("Files generated:")
        for file_type, path in results.items():
            print(f"  {file_type}: {path}")
            
    except Exception as e:
        print(f"Demo error: {e}")
        print("Note: This requires internet access to download NOAA chart tiles")

if __name__ == "__main__":
    create_professional_demo()