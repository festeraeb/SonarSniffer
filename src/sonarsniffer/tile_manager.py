#!/usr/bin/env python3
"""Tile manager for RSD Studio - handles MBTiles and KML super-overlays."""
from typing import Tuple, List, Optional
import sqlite3
import numpy as np
from PIL import Image
from pathlib import Path
import math
import json
from color_manager import ColorManager

class TileManager:
    """Manages tile generation and storage for various formats."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.color_manager = ColorManager()
        self._init_paths()
        
    def _init_paths(self):
        """Initialize output directories."""
        self.tiles_path = self.base_path / "tiles"
        self.kml_path = self.base_path / "kml"
        self.mbtiles_path = self.base_path / "mbtiles"
        
        for p in [self.tiles_path, self.kml_path, self.mbtiles_path]:
            p.mkdir(parents=True, exist_ok=True)
    
    def _calculate_bounds(self, csv_path: str) -> Tuple[float, float, float, float]:
        """Calculate lat/lon bounds from CSV data."""
        import csv
        min_lat = float('inf')
        max_lat = float('-inf')
        min_lon = float('inf')
        max_lon = float('-inf')
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    lat = float(row['lat'])
                    lon = float(row['lon'])
                    min_lat = min(min_lat, lat)
                    max_lat = max(max_lat, lat)
                    min_lon = min(min_lon, lon)
                    max_lon = max(max_lon, lon)
                except (ValueError, KeyError):
                    continue
                    
        return min_lon, min_lat, max_lon, max_lat
    
    def create_mbtiles(self, images: List[str], csv_path: str, colormap: str = "grayscale",
                      min_zoom: int = 8, max_zoom: int = 12, tile_size: int = 256,
                      on_progress=None, check_cancel=None) -> str:
        """Create MBTiles database from images with geo-reference from CSV."""
        print(f"Creating MBTiles: min_zoom={min_zoom}, max_zoom={max_zoom}")

        db_path = self.mbtiles_path / "output.mbtiles"

        # Get bounds
        bounds = self._calculate_bounds(csv_path)
        print(f"Data bounds: {bounds}")

        # Initialize database
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()

        # Create schema
        c.executescript('''
            CREATE TABLE IF NOT EXISTS metadata (name text, value text);
            CREATE TABLE IF NOT EXISTS tiles (
                zoom_level integer,
                tile_column integer,
                tile_row integer,
                tile_data blob
            );
            CREATE UNIQUE INDEX IF NOT EXISTS tile_index ON tiles
                (zoom_level, tile_column, tile_row);
        ''')

        # Add metadata
        metadata = {
            "name": "RSD Sidescan",
            "type": "overlay",
            "version": "1.0.0",
            "description": "Garmin side-scan sonar data",
            "format": "png",
            "bounds": ",".join(map(str, bounds)),
            "minzoom": str(min_zoom),
            "maxzoom": str(max_zoom)
        }

        c.executemany("INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                     [(k, v) for k, v in metadata.items()])

        total_tiles = 0

        # Process images and create tiles
        for img_idx, img_path in enumerate(images):
            if check_cancel and check_cancel():
                print("MBTiles creation cancelled")
                break
                
            if on_progress:
                on_progress(20 + img_idx * 60 // len(images), f"Processing image {img_idx+1}/{len(images)}")
            
            print(f"Processing image {img_idx+1}/{len(images)}: {img_path}")
            try:
                img = np.array(Image.open(img_path))
                colored = self.color_manager.apply(img, colormap)

                # Generate tiles for each zoom level
                for zoom in range(min_zoom, max_zoom + 1):
                    tiles_created = self._generate_tiles_for_zoom(colored, zoom, bounds, c, tile_size)
                    total_tiles += tiles_created
                    print(f"  Zoom {zoom}: {tiles_created} tiles created")

            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue
        
        conn.commit()
        conn.close()

        print(f"MBTiles creation complete: {total_tiles} total tiles")
        return str(db_path)
    
    def create_kml_overlay(self, images: List[str], csv_path: str, colormap: str = "grayscale",
                          min_zoom: int = 8, max_zoom: int = 12, on_progress=None, check_cancel=None) -> str:
        """Create KML super-overlay structure."""
        print(f"Creating KML overlay: min_zoom={min_zoom}, max_zoom={max_zoom}")

        bounds = self._calculate_bounds(csv_path)
        print(f"Data bounds: {bounds}")

        root_kml = self.kml_path / "doc.kml"

        # Create directory structure
        for zoom in range(min_zoom, max_zoom + 1):
            (self.kml_path / str(zoom)).mkdir(exist_ok=True)
            (self.tiles_path / str(zoom)).mkdir(exist_ok=True)

        total_tiles = 0

        # Process images and create tiles
        for img_idx, img_path in enumerate(images):
            if check_cancel and check_cancel():
                print("KML overlay creation cancelled")
                break
                
            if on_progress:
                on_progress(20 + img_idx * 60 // len(images), f"Processing image {img_idx+1}/{len(images)}")
            
            print(f"Processing image {img_idx+1}/{len(images)}: {img_path}")
            try:
                img = np.array(Image.open(img_path))
                colored = self.color_manager.apply(img, colormap)

                for zoom in range(min_zoom, max_zoom + 1):
                    tiles_created = self._generate_kml_tiles(colored, zoom, bounds, img_path)
                    total_tiles += tiles_created
                    print(f"  Zoom {zoom}: {tiles_created} tiles created")

            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue
        
        # Create root KML
        self._create_root_kml(root_kml, bounds, min_zoom, max_zoom)

        print(f"KML overlay creation complete: {total_tiles} total tiles")
        return str(root_kml)
    
    def _generate_tiles_for_zoom(self, img: np.ndarray, zoom: int,
                               bounds: Tuple[float, float, float, float],
                               cursor: sqlite3.Cursor, tile_size: int = 256) -> int:
        """Generate and store tiles for a specific zoom level. Returns number of tiles created."""
        min_lon, min_lat, max_lon, max_lat = bounds

        # Calculate tile range that covers our data bounds
        n = 2.0 ** zoom

        # Convert lat/lon bounds to tile coordinates
        def lon_to_tile(lon): return int((lon + 180.0) / 360.0 * n)
        def lat_to_tile(lat): return int((1.0 - math.log(math.tan(lat * math.pi / 180.0) + 1.0 / math.cos(lat * math.pi / 180.0)) / math.pi) / 2.0 * n)

        min_tile_x = max(0, lon_to_tile(min_lon) - 1)  # Add padding
        max_tile_x = min(int(n) - 1, lon_to_tile(max_lon) + 1)
        min_tile_y = max(0, lat_to_tile(max_lat) - 1)  # Note: lat is inverted
        max_tile_y = min(int(n) - 1, lat_to_tile(min_lat) + 1)

        tiles_created = 0

        # Only iterate over tiles that could potentially intersect our data
        for y in range(min_tile_y, max_tile_y + 1):
            for x in range(min_tile_x, max_tile_x + 1):
                # Calculate tile bounds
                tile_min_lon = x / n * 360.0 - 180.0
                tile_max_lon = (x + 1) / n * 360.0 - 180.0
                tile_max_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
                tile_min_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))

                tile_bounds = (tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat)

                if self._bounds_intersect(bounds, tile_bounds):
                    try:
                        tile_img = self._render_tile(img, tile_bounds, bounds)
                        if tile_img is not None:
                            # Convert to PNG bytes
                            from io import BytesIO
                            buf = BytesIO()
                            tile_img.save(buf, format='PNG')
                            tile_data = buf.getvalue()

                            # Store in database
                            cursor.execute(
                                "INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)",
                                (zoom, x, y, sqlite3.Binary(tile_data))
                            )
                            tiles_created += 1
                        else:
                            print(f"Warning: No tile image generated for {zoom}/{x}/{y}")
                    except Exception as e:
                        print(f"Error creating MBTiles tile {zoom}/{x}/{y}: {e}")
                        continue
        
        return tiles_created
    
    def _generate_kml_tiles(self, img: np.ndarray, zoom: int,
                          bounds: Tuple[float, float, float, float],
                          image_path: str) -> int:
        """Generate tiles and KML files for super-overlay. Returns number of tiles created."""
        min_lon, min_lat, max_lon, max_lat = bounds
        n = 2.0 ** zoom

        # Calculate tile range that covers our data bounds
        def lon_to_tile(lon): return int((lon + 180.0) / 360.0 * n)
        def lat_to_tile(lat): return int((1.0 - math.log(math.tan(lat * math.pi / 180.0) + 1.0 / math.cos(lat * math.pi / 180.0)) / math.pi) / 2.0 * n)

        min_tile_x = max(0, lon_to_tile(min_lon) - 1)  # Add padding
        max_tile_x = min(int(n) - 1, lon_to_tile(max_lon) + 1)
        min_tile_y = max(0, lat_to_tile(max_lat) - 1)  # Note: lat is inverted
        max_tile_y = min(int(n) - 1, lat_to_tile(min_lat) + 1)

        tiles_created = 0

        for y in range(min_tile_y, max_tile_y + 1):
            for x in range(min_tile_x, max_tile_x + 1):
                # Calculate tile bounds
                tile_min_lon = x / n * 360.0 - 180.0
                tile_max_lon = (x + 1) / n * 360.0 - 180.0
                tile_max_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
                tile_min_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))

                tile_bounds = (tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat)

                if self._bounds_intersect(bounds, tile_bounds):
                    try:
                        tile_img = self._render_tile(img, tile_bounds, bounds)
                        if tile_img is not None:
                            # Save tile image
                            tile_path = self.tiles_path / str(zoom) / f"{x}_{y}.png"
                            tile_img.save(tile_path)

                            # Create tile KML
                            self._create_tile_kml(zoom, x, y, tile_bounds, tile_path)
                            tiles_created += 1
                        else:
                            print(f"Warning: No tile image generated for KML {zoom}/{x}/{y}")
                    except Exception as e:
                        print(f"Error creating KML tile {zoom}/{x}/{y}: {e}")
                        continue
        
        return tiles_created
    
    def _render_tile(self, img: np.ndarray, tile_bounds: Tuple[float, float, float, float],
                    img_bounds: Tuple[float, float, float, float]) -> Optional[Image.Image]:
        """Render a map tile from the image."""
        try:
            # Calculate pixel coordinates
            img_h, img_w = img.shape[:2]
            min_lon, min_lat, max_lon, max_lat = img_bounds
            tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat = tile_bounds

            # Check for invalid bounds
            if max_lon <= min_lon or max_lat <= min_lat:
                print(f"Invalid image bounds: {img_bounds}")
                return None

            # Convert to pixel coordinates
            lon_range = max_lon - min_lon
            lat_range = max_lat - min_lat

            if lon_range <= 0 or lat_range <= 0:
                print(f"Invalid coordinate ranges: lon_range={lon_range}, lat_range={lat_range}")
                return None

            x1 = int((tile_min_lon - min_lon) / lon_range * img_w)
            x2 = int((tile_max_lon - min_lon) / lon_range * img_w)
            y1 = int((max_lat - tile_max_lat) / lat_range * img_h)
            y2 = int((max_lat - tile_min_lat) / lat_range * img_h)

            # Clamp coordinates to image bounds
            x1 = max(0, min(x1, img_w))
            x2 = max(0, min(x2, img_w))
            y1 = max(0, min(y1, img_h))
            y2 = max(0, min(y2, img_h))

            # Ensure valid slice
            if x2 <= x1 or y2 <= y1:
                return None

            # Extract tile
            if img.ndim == 3:
                # RGB image
                tile = img[y1:y2, x1:x2, :]
            else:
                # Grayscale image
                tile = img[y1:y2, x1:x2]

            # Ensure tile has valid data
            if tile.size == 0:
                return None

            # Create PIL image
            if tile.ndim == 3:
                # RGB
                tile_img = Image.fromarray(tile.astype(np.uint8), mode='RGB')
            else:
                # Grayscale
                tile_img = Image.fromarray(tile.astype(np.uint8), mode='L')

            # Resize to standard tile size
            tile_img = tile_img.resize((256, 256), Image.Resampling.LANCZOS)

            return tile_img

        except Exception as e:
            print(f"Error in _render_tile: {e}")
            print(f"  img.shape: {img.shape}")
            print(f"  tile_bounds: {tile_bounds}")
            print(f"  img_bounds: {img_bounds}")
            return None
    
    def _create_tile_kml(self, zoom: int, x: int, y: int, bounds: Tuple[float, float, float, float],
                        tile_path: Path):
        """Create KML file for a single tile."""
        min_lon, min_lat, max_lon, max_lat = bounds
        kml_path = self.kml_path / str(zoom) / f"{x}_{y}.kml"
        
        kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Region>
      <LatLonAltBox>
        <north>{max_lat}</north>
        <south>{min_lat}</south>
        <east>{max_lon}</east>
        <west>{min_lon}</west>
      </LatLonAltBox>
      <Lod>
        <minLodPixels>128</minLodPixels>
        <maxLodPixels>-1</maxLodPixels>
      </Lod>
    </Region>
    <GroundOverlay>
      <drawOrder>{zoom}</drawOrder>
      <Icon>
        <href>{tile_path.relative_to(self.base_path)}</href>
      </Icon>
      <LatLonBox>
        <north>{max_lat}</north>
        <south>{min_lat}</south>
        <east>{max_lon}</east>
        <west>{min_lon}</west>
      </LatLonBox>
    </GroundOverlay>
  </Document>
</kml>'''
        
        kml_path.write_text(kml_content)
    
    def _create_root_kml(self, kml_path: Path, bounds: Tuple[float, float, float, float],
                        min_zoom: int, max_zoom: int):
        """Create root KML file with network links."""
        min_lon, min_lat, max_lon, max_lat = bounds
        
        links = []
        for zoom in range(min_zoom, max_zoom + 1):
            n = 2.0 ** zoom
            for y in range(int(n)):
                for x in range(int(n)):
                    tile_kml = self.kml_path / str(zoom) / f"{x}_{y}.kml"
                    if tile_kml.exists():
                        links.append(f'''
    <NetworkLink>
      <name>Zoom {zoom} Tile {x},{y}</name>
      <Region>
        <LatLonAltBox>
          <north>{(1 - y / n) * 170.1022}</north>
          <south>{(1 - (y + 1) / n) * 170.1022}</south>
          <east>{(x + 1) / n * 360.0 - 180.0}</east>
          <west>{x / n * 360.0 - 180.0}</west>
        </LatLonAltBox>
        <Lod>
          <minLodPixels>128</minLodPixels>
          <maxLodPixels>-1</maxLodPixels>
        </Lod>
      </Region>
      <Link>
        <href>{tile_kml.relative_to(self.base_path)}</href>
        <viewRefreshMode>onRegion</viewRefreshMode>
      </Link>
    </NetworkLink>''')
        
        kml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>RSD Sidescan Data</name>
    <description>Generated by RSD Studio</description>
    <Region>
      <LatLonAltBox>
        <north>{max_lat}</north>
        <south>{min_lat}</south>
        <east>{max_lon}</east>
        <west>{min_lon}</west>
      </LatLonAltBox>
      <Lod>
        <minLodPixels>128</minLodPixels>
        <maxLodPixels>-1</maxLodPixels>
      </Lod>
    </Region>
    {"".join(links)}
  </Document>
</kml>'''
        
        kml_path.write_text(kml_content)
    
    @staticmethod
    def _bounds_intersect(bounds1: Tuple[float, float, float, float],
                         bounds2: Tuple[float, float, float, float]) -> bool:
        """Check if two bounding boxes intersect."""
        min_lon1, min_lat1, max_lon1, max_lat1 = bounds1
        min_lon2, min_lat2, max_lon2, max_lat2 = bounds2
        
        return not (max_lon1 < min_lon2 or min_lon1 > max_lon2 or
                   max_lat1 < min_lat2 or min_lat1 > max_lat2)