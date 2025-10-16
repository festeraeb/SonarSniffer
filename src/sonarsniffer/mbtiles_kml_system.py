#!/usr/bin/env python3
"""
MBTiles and KML Super Overlay System
Display sonar data over NOAA ENC charts like SonarTRX front page
"""

import sqlite3
import os
import json
import math
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import requests
import numpy as np
from PIL import Image, ImageDraw

@dataclass
class TileInfo:
    """Information about a map tile"""
    x: int
    y: int 
    z: int
    bounds: Tuple[float, float, float, float]  # west, south, east, north

class NOAAChartDownloader:
    """Download NOAA ENC chart tiles using official NOAA services"""
    
    def __init__(self, cache_dir: str = "chart_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # NOAA Official Chart Services (updated from nauticalcharts.noaa.gov)
        self.services = {
            # NOAA ENC (Electronic Navigational Charts) - Primary
            'enc': {
                'url': 'https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/ENCOnline/MapServer/tile/{z}/{y}/{x}',
                'name': 'NOAA ENC Charts',
                'attribution': 'NOAA Office of Coast Survey'
            },
            # NOAA RNC (Raster Navigational Charts) - Alternative
            'rnc': {
                'url': 'https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/NOAAChartDisplay/MapServer/tile/{z}/{y}/{x}',
                'name': 'NOAA RNC Charts', 
                'attribution': 'NOAA Office of Coast Survey'
            },
            # NOAA Bathymetry
            'bathymetry': {
                'url': 'https://gis.ngdc.noaa.gov/arcgis/rest/services/web_mercator/multibeam/MapServer/tile/{z}/{y}/{x}',
                'name': 'NOAA Bathymetry',
                'attribution': 'NOAA NCEI'
            },
            # USGS Topo for context
            'topo': {
                'url': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
                'name': 'USGS Topographic',
                'attribution': 'USGS'
            }
        }
        
        # Default to ENC charts
        self.current_service = 'enc'
        
    def deg2num(self, lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
        """Convert lat/lon to tile coordinates"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def num2deg(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert tile coordinates to lat/lon"""
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def set_chart_service(self, service_name: str):
        """Set which chart service to use"""
        if service_name in self.services:
            self.current_service = service_name
        else:
            raise ValueError(f"Unknown service: {service_name}. Available: {list(self.services.keys())}")
    
    def get_available_services(self) -> Dict[str, str]:
        """Get available chart services"""
        return {name: info['name'] for name, info in self.services.items()}
    
    def download_tile(self, x: int, y: int, z: int) -> Optional[bytes]:
        """Download a single tile from current service"""
        service_info = self.services[self.current_service]
        cache_path = self.cache_dir / f"{self.current_service}_{z}_{x}_{y}.png"
        
        # Check cache first
        if cache_path.exists():
            return cache_path.read_bytes()
        
        # Download from NOAA
        try:
            url = service_info['url'].format(x=x, y=y, z=z)
            headers = {
                'User-Agent': 'Advanced-Sonar-Studio/1.0 (Marine Survey Application)',
                'Referer': 'https://nauticalcharts.noaa.gov/'
            }
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            
            # Cache the tile
            cache_path.write_bytes(response.content)
            return response.content
            
        except Exception as e:
            print(f"Failed to download {self.current_service} tile {z}/{x}/{y}: {e}")
            return None
    
    def get_tiles_for_bounds(self, west: float, south: float, 
                           east: float, north: float, zoom: int) -> List[TileInfo]:
        """Get all tiles needed for given bounds"""
        min_x, max_y = self.deg2num(north, west, zoom)
        max_x, min_y = self.deg2num(south, east, zoom)
        
        tiles = []
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                # Calculate tile bounds
                nw_lat, nw_lon = self.num2deg(x, y, zoom)
                se_lat, se_lon = self.num2deg(x + 1, y + 1, zoom)
                bounds = (nw_lon, se_lat, se_lon, nw_lat)  # west, south, east, north
                
                tiles.append(TileInfo(x, y, zoom, bounds))
        
        return tiles

class MBTilesCreator:
    """Create MBTiles database for offline viewing"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.db = None
        
    def create_database(self, metadata: Dict[str, str]):
        """Create MBTiles database with metadata"""
        # Remove existing file
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
        
        self.db = sqlite3.connect(self.output_path)
        
        # Create tables
        self.db.execute('''
            CREATE TABLE metadata (name text, value text)
        ''')
        
        self.db.execute('''
            CREATE TABLE tiles (zoom_level integer, tile_column integer, 
                              tile_row integer, tile_data blob)
        ''')
        
        # Insert metadata
        for key, value in metadata.items():
            self.db.execute('INSERT INTO metadata (name, value) VALUES (?, ?)', 
                          (key, value))
        
        self.db.commit()
    
    def add_tile(self, x: int, y: int, z: int, tile_data: bytes):
        """Add a tile to the database"""
        if self.db is None:
            raise RuntimeError("Database not created")
        
        # MBTiles uses TMS coordinates (y flipped)
        tms_y = (2 ** z) - 1 - y
        
        self.db.execute('''
            INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data)
            VALUES (?, ?, ?, ?)
        ''', (z, x, tms_y, tile_data))
    
    def close(self):
        """Close the database"""
        if self.db:
            self.db.commit()
            self.db.close()

class KMLSuperOverlayCreator:
    """Create KML super overlays like SonarTRX"""
    
    def __init__(self, name: str = "Sonar Survey"):
        self.name = name
        self.overlays = []
        
    def add_sonar_overlay(self, image_path: str, bounds: Tuple[float, float, float, float],
                         description: str = ""):
        """Add a sonar image overlay"""
        overlay = {
            'image_path': image_path,
            'bounds': bounds,  # west, south, east, north
            'description': description
        }
        self.overlays.append(overlay)
    
    def create_kml(self, output_path: str) -> str:
        """Create KML file with super overlays"""
        # Create root KML element
        kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, 'Document')
        ET.SubElement(document, 'name').text = self.name
        
        # Add description
        description = ET.SubElement(document, 'description')
        description.text = f"""
        <![CDATA[
        <h3>Sonar Survey Data</h3>
        <p>Generated by Advanced Sonar Studio</p>
        <p>Competitive alternative to SonarTRX</p>
        <p>Total overlays: {len(self.overlays)}</p>
        ]]>
        """
        
        # Create folder for overlays
        folder = ET.SubElement(document, 'Folder')
        ET.SubElement(folder, 'name').text = 'Sonar Overlays'
        ET.SubElement(folder, 'open').text = '1'
        
        # Add each overlay
        for i, overlay in enumerate(self.overlays):
            placemark = ET.SubElement(folder, 'Placemark')
            ET.SubElement(placemark, 'name').text = f"Sonar Track {i+1}"
            
            if overlay['description']:
                ET.SubElement(placemark, 'description').text = overlay['description']
            
            # Ground overlay
            ground_overlay = ET.SubElement(placemark, 'GroundOverlay')
            icon = ET.SubElement(ground_overlay, 'Icon')
            ET.SubElement(icon, 'href').text = overlay['image_path']
            
            # Lat/Lon box
            latlonbox = ET.SubElement(ground_overlay, 'LatLonBox')
            west, south, east, north = overlay['bounds']
            ET.SubElement(latlonbox, 'north').text = str(north)
            ET.SubElement(latlonbox, 'south').text = str(south)
            ET.SubElement(latlonbox, 'east').text = str(east)
            ET.SubElement(latlonbox, 'west').text = str(west)
        
        # Create network links for different zoom levels (super overlay structure)
        self._add_network_links(document)
        
        # Write KML file
        tree = ET.ElementTree(kml)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        return output_path
    
    def _add_network_links(self, document):
        """Add network links for super overlay structure"""
        # This creates the hierarchical structure that allows for efficient loading
        # at different zoom levels, similar to how SonarTRX organizes their overlays
        
        network_link = ET.SubElement(document, 'NetworkLink')
        ET.SubElement(network_link, 'name').text = 'High Resolution Sonar'
        
        link = ET.SubElement(network_link, 'Link')
        ET.SubElement(link, 'href').text = 'high_res_sonar.kml'
        
        # View-based refresh
        ET.SubElement(link, 'viewRefreshMode').text = 'onRegion'

class SonarChartIntegrator:
    """Integrate sonar data with NOAA charts"""
    
    def __init__(self, chart_downloader: NOAAChartDownloader):
        self.chart_downloader = chart_downloader
        
    def create_sonar_chart_overlay(self, sonar_data: List[Dict], 
                                  output_dir: str) -> str:
        """Create integrated sonar/chart overlay like SonarTRX front page"""
        
        if not sonar_data:
            return ""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Calculate bounds from sonar data
        lats = [record.get('lat', 0) for record in sonar_data if record.get('lat', 0) != 0]
        lons = [record.get('lon', 0) for record in sonar_data if record.get('lon', 0) != 0]
        
        if not lats or not lons:
            raise ValueError("No valid position data in sonar records")
        
        west, east = min(lons), max(lons)
        south, north = min(lats), max(lats)
        
        # Add padding
        lat_padding = (north - south) * 0.1
        lon_padding = (east - west) * 0.1
        
        west -= lon_padding
        east += lon_padding
        south -= lat_padding
        north += lat_padding
        
        # Download base chart tiles
        zoom_level = 12  # Good balance of detail and coverage
        tiles = self.chart_downloader.get_tiles_for_bounds(west, south, east, north, zoom_level)
        
        print(f"Downloading {len(tiles)} chart tiles...")
        
        # Create base chart image
        chart_image = self._create_chart_mosaic(tiles, zoom_level)
        
        # Overlay sonar data
        overlay_image = self._create_sonar_overlay(sonar_data, (west, south, east, north), 
                                                 chart_image.size)
        
        # Composite the images
        composite = Image.alpha_composite(chart_image.convert('RGBA'), 
                                        overlay_image.convert('RGBA'))
        
        # Save result
        output_path = output_dir / "sonar_chart_overlay.png"
        composite.save(output_path)
        
        # Create KML
        kml_creator = KMLSuperOverlayCreator("Sonar Survey with NOAA Charts")
        kml_creator.add_sonar_overlay(str(output_path), (west, south, east, north),
                                    f"Sonar data with {len(sonar_data)} records")
        
        kml_path = output_dir / "sonar_overlay.kml"
        kml_creator.create_kml(str(kml_path))
        
        return str(kml_path)
    
    def _create_chart_mosaic(self, tiles: List[TileInfo], zoom: int) -> Image.Image:
        """Create mosaic image from chart tiles"""
        if not tiles:
            return Image.new('RGBA', (512, 512), (0, 0, 255, 128))  # Blue placeholder
        
        # Calculate mosaic dimensions
        min_x = min(tile.x for tile in tiles)
        max_x = max(tile.x for tile in tiles)
        min_y = min(tile.y for tile in tiles)
        max_y = max(tile.y for tile in tiles)
        
        tile_size = 256
        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        
        mosaic = Image.new('RGBA', (width, height), (0, 0, 255, 128))
        
        for tile in tiles:
            tile_data = self.chart_downloader.download_tile(tile.x, tile.y, tile.z)
            if tile_data:
                try:
                    tile_image = Image.open(io.BytesIO(tile_data))
                    x_offset = (tile.x - min_x) * tile_size
                    y_offset = (tile.y - min_y) * tile_size
                    mosaic.paste(tile_image, (x_offset, y_offset))
                except Exception as e:
                    print(f"Error processing tile {tile.x},{tile.y}: {e}")
        
        return mosaic
    
    def _create_sonar_overlay(self, sonar_data: List[Dict], bounds: Tuple[float, float, float, float],
                            image_size: Tuple[int, int]) -> Image.Image:
        """Create sonar data overlay"""
        west, south, east, north = bounds
        width, height = image_size
        
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Convert sonar positions to pixel coordinates
        points = []
        for record in sonar_data:
            lat = record.get('lat', 0)
            lon = record.get('lon', 0)
            depth = record.get('depth_m', 0)
            
            if lat != 0 and lon != 0:
                # Convert to pixel coordinates
                x = int((lon - west) / (east - west) * width)
                y = int((north - lat) / (north - south) * height)
                
                # Color based on depth
                if depth > 0:
                    intensity = min(255, int(depth * 10))  # Scale depth to color intensity
                    color = (intensity, 0, 255 - intensity, 128)  # Blue to red gradient
                    points.append((x, y, color))
        
        # Draw sonar points
        for x, y, color in points:
            draw.ellipse([x-2, y-2, x+2, y+2], fill=color)
        
        # Draw track line
        if len(points) > 1:
            track_points = [(x, y) for x, y, _ in points]
            for i in range(len(track_points) - 1):
                draw.line([track_points[i], track_points[i+1]], fill=(255, 255, 0, 128), width=2)
        
        return overlay

def create_demo_sonar_chart():
    """Create a demo sonar chart overlay"""
    # Sample sonar data (replace with real data)
    sonar_data = [
        {'lat': 42.3601, 'lon': -71.0589, 'depth_m': 5.2},  # Boston area
        {'lat': 42.3611, 'lon': -71.0579, 'depth_m': 6.1},
        {'lat': 42.3621, 'lon': -71.0569, 'depth_m': 4.8},
        {'lat': 42.3631, 'lon': -71.0559, 'depth_m': 7.3},
    ]
    
    # Create chart downloader
    downloader = NOAAChartDownloader()
    
    # Create integrator
    integrator = SonarChartIntegrator(downloader)
    
    # Create overlay
    try:
        kml_path = integrator.create_sonar_chart_overlay(sonar_data, "demo_output")
        print(f"Demo sonar chart overlay created: {kml_path}")
    except Exception as e:
        print(f"Error creating demo: {e}")

if __name__ == "__main__":
    import io
    create_demo_sonar_chart()