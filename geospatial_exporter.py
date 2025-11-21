#!/usr/bin/env python3
"""
Unified Geospatial Exporter for SonarSniffer
Consolidates KML, MBTiles, and bathymetric data exports for Google Earth and web mapping.

Provides:
- Bathymetric KML with depth contours and color-coded zones
- Target detection and classification to KML
- MBTiles for web-based map overlays
- Digital Elevation Models (DEM) for 3D visualization
- Coverage area visualization
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
import struct
import sqlite3
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import logging

# Optional imports for enhanced functionality
try:
    import simplekml
    SIMPLEKML_AVAILABLE = True
except ImportError:
    SIMPLEKML_AVAILABLE = False

try:
    from scipy import interpolate, ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SonarPoint:
    """Single sonar measurement point"""
    latitude: float
    longitude: float
    depth: float
    timestamp: float = 0.0
    confidence: float = 1.0
    channel: int = 0
    frequency: float = 200.0
    
    def to_dict(self):
        return {
            'lat': self.latitude,
            'lon': self.longitude,
            'depth': self.depth,
            'ts': self.timestamp,
            'conf': self.confidence,
            'ch': self.channel,
            'freq': self.frequency,
        }


@dataclass
class DetectedTarget:
    """Detected object/feature in sonar data"""
    latitude: float
    longitude: float
    depth: float
    target_type: str  # 'rock', 'wreck', 'debris', 'structure', 'anomaly'
    confidence: float  # 0.0-1.0
    size_estimate: float = 0.0  # meters
    heading: float = 0.0  # degrees
    description: str = ""
    timestamp: float = 0.0


# ============================================================================
# BATHYMETRIC DATA PROCESSING
# ============================================================================

class BathymetricProcessor:
    """Process sonar points into bathymetric grids and contours"""
    
    def __init__(self, sonar_points: List[SonarPoint], grid_resolution: float = None):
        """
        Initialize processor
        
        Args:
            sonar_points: List of SonarPoint objects
            grid_resolution: Grid cell size in decimal degrees (~10m at equator)
                           Auto-calculated based on survey size if not provided
        """
        self.points = sonar_points
        self.grid_data = None
        self.bounds = self._calculate_bounds()
        
        # Auto-calculate grid resolution based on survey area to avoid memory issues
        if grid_resolution is None:
            self.grid_resolution = self._calculate_optimal_resolution()
        else:
            # Clamp resolution to reasonable bounds (min 0.001 degrees = 100m)
            self.grid_resolution = max(0.001, grid_resolution)
    
    def _calculate_optimal_resolution(self) -> float:
        """
        Calculate optimal grid resolution based on survey area to avoid memory issues.
        
        Large surveys with fine resolution can require terabytes of memory.
        This method ensures reasonable memory usage while maintaining detail.
        """
        bounds = self._calculate_bounds()
        lat_range = bounds['north'] - bounds['south']
        lon_range = bounds['east'] - bounds['west']
        
        # Estimate grid size at different resolutions
        # Memory limit: Keep grid < 50,000 x 50,000 points (~25 GB for float64)
        max_grid_points = 50000
        
        estimated_lat_points = max(10, lat_range / 0.0001)
        estimated_lon_points = max(10, lon_range / 0.0001)
        total_points = estimated_lat_points * estimated_lon_points
        
        if total_points > max_grid_points * max_grid_points:
            # Need coarser resolution
            scale_factor = (total_points / (max_grid_points * max_grid_points)) ** 0.5
            optimal_resolution = 0.0001 * scale_factor
            logging.warning(f"Large survey detected ({total_points:.0e} grid points). "
                          f"Using resolution: {optimal_resolution:.6f} degrees (~{optimal_resolution*111000:.0f}m)")
            return optimal_resolution
        else:
            # Can use fine resolution
            return 0.0001
        
    def _calculate_bounds(self) -> Dict[str, float]:
        """Calculate geographic bounds of data"""
        if not self.points:
            return {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        
        lats = [p.latitude for p in self.points]
        lons = [p.longitude for p in self.points]
        
        return {
            'north': max(lats),
            'south': min(lats),
            'east': max(lons),
            'west': min(lons),
        }
    
    def create_grid(self) -> np.ndarray:
        """
        Create interpolated bathymetric grid using SciPy with memory limits
        
        Returns:
            2D numpy array with depth values at regular grid points
        """
        if not SCIPY_AVAILABLE:
            logging.warning("SciPy not available, skipping grid interpolation")
            return None
            
        if not self.points:
            return None
        
        # Extract coordinates
        lats = np.array([p.latitude for p in self.points])
        lons = np.array([p.longitude for p in self.points])
        depths = np.array([p.depth for p in self.points])
        
        # Create regular grid
        lat_min, lat_max = self.bounds['south'], self.bounds['north']
        lon_min, lon_max = self.bounds['west'], self.bounds['east']
        
        # Handle single point or very small area - expand bounds
        if lat_min == lat_max:
            lat_min -= 0.01
            lat_max += 0.01
        if lon_min == lon_max:
            lon_min -= 0.01
            lon_max += 0.01
        
        # Ensure minimum separation for very small areas
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        if lat_range < 0.001:
            lat_center = (lat_min + lat_max) / 2
            lat_min = lat_center - 0.01
            lat_max = lat_center + 0.01
        if lon_range < 0.001:
            lon_center = (lon_min + lon_max) / 2
            lon_min = lon_center - 0.01
            lon_max = lon_center + 0.01
        
        # Ensure we have valid bounds
        if lat_min >= lat_max or lon_min >= lon_max:
            logging.warning(f"Invalid bounds for grid: lat({lat_min}-{lat_max}) lon({lon_min}-{lon_max})")
            return None
        
        # Create grid using linspace with memory limit check
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        
        # Calculate grid dimensions
        lat_cells = max(10, int(lat_range / self.grid_resolution))
        lon_cells = max(10, int(lon_range / self.grid_resolution))
        
        # Check memory requirement (float64 = 8 bytes per point)
        memory_bytes = lat_cells * lon_cells * 8
        memory_gb = memory_bytes / (1024**3)
        
        if memory_gb > 4:  # Warn if > 4 GB for single grid
            logging.warning(f"Grid interpolation will use ~{memory_gb:.1f} GB. "
                          f"Grid size: {lat_cells} x {lon_cells} = {lat_cells*lon_cells:,} points")
        
        try:
            lat_grid = np.linspace(lat_min, lat_max, lat_cells)
            lon_grid = np.linspace(lon_min, lon_max, lon_cells)
            lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
            
            # Interpolate depths using RBF (Radial Basis Function)
            # Use thin_plate with smooth to avoid overfitting and improve memory efficiency
            rbf = interpolate.Rbf(lons, lats, depths, function='thin_plate', smooth=0.1)
            depth_grid = rbf(lon_mesh, lat_mesh)
            
            self.grid_data = {
                'depths': depth_grid,
                'lats': lat_mesh,
                'lons': lon_mesh,
                'lat_grid': lat_grid,
                'lon_grid': lon_grid,
            }
            
            logging.info(f"Grid created successfully: {lat_cells}x{lon_cells} = {lat_cells*lon_cells:,} points "
                        f"({memory_gb:.2f} GB)")
            return depth_grid
            
        except MemoryError as e:
            logging.error(f"Memory error during grid creation: {e}. "
                        f"Survey area may be too large with current resolution. "
                        f"Try using coarser grid resolution or processing smaller areas.")
            return None
        except Exception as e:
            logging.error(f"Grid interpolation failed: {e}")
            return None
    
    def get_contours(self, interval: float = 1.0) -> List[List[Tuple[float, float, float]]]:
        """
        Generate depth contour lines
        
        Args:
            interval: Contour interval in meters
            
        Returns:
            List of contour lines (each is list of (lat, lon, depth) tuples)
        """
        if not SCIPY_AVAILABLE:
            return []
            
        if self.grid_data is None:
            self.create_grid()
        
        if self.grid_data is None:
            return []
        
        depth_grid = self.grid_data['depths']
        lat_mesh = self.grid_data['lats']
        lon_mesh = self.grid_data['lons']
        
        contours = []
        depth_min = np.nanmin(depth_grid)
        depth_max = np.nanmax(depth_grid)
        
        levels = np.arange(
            int(depth_min / interval) * interval,
            int(depth_max / interval) * interval + interval,
            interval
        )
        
        try:
            contour_set = plt.contour(
                lon_mesh, lat_mesh, depth_grid,
                levels=levels
            ) if MATPLOTLIB_AVAILABLE else None
            
            if contour_set:
                for contour_collection in contour_set.collections:
                    for contour_path in contour_collection.get_paths():
                        vertices = contour_path.vertices
                        if len(vertices) > 0:
                            depth = depth_grid[int(vertices[0, 0]), int(vertices[0, 1])]
                            contour_line = [(v[1], v[0], float(depth)) for v in vertices]
                            if len(contour_line) > 2:
                                contours.append(contour_line)
            
            plt.close('all')
        except Exception as e:
            logging.warning(f"Contour generation failed: {e}")
        
        return contours
    
    def classify_depth_zone(self, depth: float) -> Tuple[str, str]:
        """
        Classify depth into zone and return name and color
        
        Returns:
            (zone_name, hex_color)
        """
        if depth < 5:
            return ('Shallow', '#00ff00')  # Green
        elif depth < 20:
            return ('Medium', '#ffff00')  # Yellow
        elif depth < 50:
            return ('Deep', '#ff8800')  # Orange
        else:
            return ('Very Deep', '#ff0000')  # Red


# ============================================================================
# KML GENERATION
# ============================================================================

class KMLGenerator:
    """Generate KML files for Google Earth"""
    
    def __init__(self, name: str = "Sonar Survey"):
        self.name = name
        if SIMPLEKML_AVAILABLE:
            self.kml = simplekml.Kml()
        else:
            self.kml = None
        self.features = []
    
    def add_bathymetry(self, processor: BathymetricProcessor, contour_interval: float = 5.0):
        """Add bathymetric contours and heatmap to KML"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available, skipping bathymetry KML")
            return
        
        # Create folder for bathymetry
        bath_folder = self.kml.newfolder(name="Bathymetry")
        
        # Add sonar points as colored placemarks
        points_folder = bath_folder.newfolder(name="Sonar Points")
        for i, point in enumerate(processor.points):
            zone_name, color_hex = processor.classify_depth_zone(point.depth)
            
            pm = points_folder.newpoint(
                name=f"Point {i+1}",
                description=f"Depth: {point.depth:.1f}m\nZone: {zone_name}\nConfidence: {point.confidence:.0%}",
                coords=[(point.longitude, point.latitude)]
            )
            
            # Convert hex color to KML format (ABgR)
            rgb = color_hex.lstrip('#')
            abgr = f"ff{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"
            
            # Safely set icon style color
            try:
                # iconstyle already exists on new placemarks, color is initially None
                if pm.iconstyle.color is None:
                    pm.iconstyle.color = simplekml.Color()
                
                # Now we can set the color text
                pm.iconstyle.color.text = abgr
                pm.iconstyle.scale = 0.5 + (point.confidence * 0.5)
            except (AttributeError, TypeError) as e:
                # If styling fails, continue silently (style is optional)
                pass
        
        # Add contour lines
        contours_folder = bath_folder.newfolder(name="Depth Contours")
        for depth_contour in processor.get_contours(contour_interval):
            if len(depth_contour) > 1:
                coords = [(p[1], p[0]) for p in depth_contour]  # (lon, lat)
                depth = depth_contour[0][2]
                zone_name, color_hex = processor.classify_depth_zone(depth)
                
                ls = contours_folder.newlinestring(
                    name=f"{depth:.1f}m",
                    description=f"Depth: {depth:.1f}m\nZone: {zone_name}",
                    coords=coords
                )
                
                # Style the line
                rgb = color_hex.lstrip('#')
                abgr = f"ff{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"
                try:
                    if ls.linestyle is not None:
                        ls.linestyle.color.text = abgr
                        ls.linestyle.width = 2
                    else:
                        # Create linestyle if it doesn't exist
                        ls.linestyle = simplekml.LineStyle()
                        ls.linestyle.color.text = abgr
                        ls.linestyle.width = 2
                except (AttributeError, TypeError) as e:
                    logging.warning(f"Could not set line style for {depth:.1f}m contour: {e}")
    
    def add_targets(self, targets: List[DetectedTarget]):
        """Add detected targets to KML"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available, skipping targets KML")
            return
        
        targets_folder = self.kml.newfolder(name="Detected Targets")
        
        target_colors = {
            'rock': '#ff0000',      # Red
            'wreck': '#000000',     # Black
            'debris': '#ff6600',    # Orange
            'structure': '#0000ff', # Blue
            'anomaly': '#ffff00',   # Yellow
        }
        
        for i, target in enumerate(targets):
            color_hex = target_colors.get(target.target_type, '#ffffff')
            
            pm = targets_folder.newpoint(
                name=f"{target.target_type.title()} {i+1}",
                description=f"""
Type: {target.target_type.title()}
Depth: {target.depth:.1f}m
Confidence: {target.confidence:.0%}
Size: {target.size_estimate:.1f}m
{getattr(target, 'description', '')}
                """.strip(),
                coords=[(target.longitude, target.latitude)]
            )
            
            # Style based on type
            rgb = color_hex.lstrip('#')
            abgr = f"ff{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"
            
            # Safe icon style update
            try:
                if pm.iconstyle and pm.iconstyle.color:
                    pm.iconstyle.color.text = abgr
                    pm.iconstyle.scale = 0.7 + (target.confidence * 0.5)
            except (AttributeError, TypeError):
                # fallback if icon style not available
                logging.debug(f"Could not set icon style for target {i+1}")
    
    def add_coverage_area(self, processor: BathymetricProcessor):
        """Add survey coverage area to KML"""
        if not SIMPLEKML_AVAILABLE or not processor.points:
            return
        
        bounds = processor.bounds
        
        # Create a polygon showing coverage bounds
        coords = [
            (bounds['west'], bounds['south']),
            (bounds['east'], bounds['south']),
            (bounds['east'], bounds['north']),
            (bounds['west'], bounds['north']),
            (bounds['west'], bounds['south']),
        ]
        
        coverage_folder = self.kml.newfolder(name="Coverage")
        poly = coverage_folder.newpolygon(
            name="Survey Area",
            description=f"""
North: {bounds['north']:.6f}
South: {bounds['south']:.6f}
East: {bounds['east']:.6f}
West: {bounds['west']:.6f}
            """.strip(),
            outerboundaryis=coords
        )
        
        # Semi-transparent green fill
        try:
            if poly.polystyle is not None:
                poly.polystyle.color.text = '7700ff00'
                poly.polystyle.outline.text = '1'
            if poly.linestyle is not None:
                poly.linestyle.color.text = 'ff00ff00'
                poly.linestyle.width = 2
        except (AttributeError, TypeError) as e:
            logging.warning(f"Could not set polygon style for coverage area: {e}")
    
    def save(self, filepath: Path):
        """Save KML to file"""
        if not SIMPLEKML_AVAILABLE:
            logging.error("simplekml not available, cannot save KML")
            return False
        
        try:
            self.kml.save(str(filepath))
            logging.info(f"KML saved to {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to save KML: {e}")
            return False


# ============================================================================
# MBTILES GENERATION (Map Tiles)
# ============================================================================

class MBTilesGenerator:
    """Generate MBTiles format for web map overlays (compatible with Leaflet, etc.)"""
    
    def __init__(self, name: str = "Sonar Tiles", output_path: Path = None):
        self.name = name
        self.output_path = output_path or Path.cwd() / f"{name}.mbtiles"
        self.db = None
        self.tiles = {}
    
    def create_tile_grid(self, processor: BathymetricProcessor, zoom_levels: List[int] = None):
        """
        Create tile pyramid for multiple zoom levels
        
        Args:
            processor: BathymetricProcessor with sonar data
            zoom_levels: List of zoom levels to generate (default: 8-18)
        """
        if zoom_levels is None:
            zoom_levels = range(8, 19)
        
        if not MATPLOTLIB_AVAILABLE:
            logging.warning("Matplotlib not available, skipping tile generation")
            return False
        
        if processor.grid_data is None:
            processor.create_grid()
        
        if processor.grid_data is None:
            logging.error("Cannot create grid for tiles")
            return False
        
        try:
            for zoom in zoom_levels:
                self._generate_zoom_level_tiles(processor, zoom)
            return True
        except Exception as e:
            logging.error(f"Tile generation failed: {e}")
            return False
    
    def _generate_zoom_level_tiles(self, processor: BathymetricProcessor, zoom: int):
        """Generate tiles for a specific zoom level"""
        # Web Mercator projection setup
        import math
        
        bounds = processor.bounds
        
        # Convert to Web Mercator
        def lat_lon_to_mercator(lat, lon):
            x = lon * 20037508.34 / 180.0
            y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) * 20037508.34 / math.pi
            return x, y
        
        # Get tile numbers at zoom level
        n = 2.0 ** zoom
        
        # Simplified: generate sample tiles at this zoom level
        for lon in np.linspace(bounds['west'], bounds['east'], max(1, int(n / 256))):
            for lat in np.linspace(bounds['south'], bounds['north'], max(1, int(n / 256))):
                # Create simple tile image (would be properly rendered in production)
                x, y = lat_lon_to_mercator(lat, lon)
                tile_x = int((x + 20037508.34) / (40075016.68) * n)
                tile_y = int((20037508.34 - y) / (40075016.68) * n)
                
                # Store tile reference
                tile_key = f"{zoom}/{tile_x}/{tile_y}"
                if tile_key not in self.tiles:
                    self.tiles[tile_key] = True
    
    def save(self, filepath: Path = None) -> bool:
        """
        Save MBTiles database
        
        Args:
            filepath: Output path (uses self.output_path if not provided)
            
        Returns:
            True if successful
        """
        filepath = filepath or self.output_path
        
        try:
            # Create SQLite database with MBTiles schema
            conn = sqlite3.connect(str(filepath))
            cursor = conn.cursor()
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT,
                    value TEXT,
                    PRIMARY KEY (name)
                )
            ''')
            
            # Create tiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tiles (
                    zoom_level INTEGER,
                    tile_column INTEGER,
                    tile_row INTEGER,
                    tile_data BLOB,
                    PRIMARY KEY (zoom_level, tile_column, tile_row)
                )
            ''')
            
            # Add metadata
            metadata = {
                'name': self.name,
                'type': 'overlay',
                'version': '1.0',
                'description': 'Sonar survey bathymetric tiles',
                'attribution': 'SonarSniffer',
                'mbtiles_version': '1.3',
            }
            
            for key, value in metadata.items():
                cursor.execute(
                    'INSERT OR REPLACE INTO metadata (name, value) VALUES (?, ?)',
                    (key, value)
                )
            
            # Note: Actual tile image data would be inserted here
            # For now, this creates the MBTiles structure
            
            conn.commit()
            conn.close()
            
            logging.info(f"MBTiles saved to {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"MBTiles save failed: {e}")
            return False


# ============================================================================
# UNIFIED EXPORTER
# ============================================================================

class GeospatialExporter:
    """Unified interface for all geospatial exports"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        log_file = self.output_dir / "export.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ]
        )
    
    def export_all(
        self,
        sonar_points: List[SonarPoint],
        targets: List[DetectedTarget] = None,
        basename: str = "sonar_survey",
        contour_interval: float = 5.0,
        generate_mbtiles: bool = True,
        generate_dem: bool = True,
        depth_unit: str = "feet",
    ) -> Dict[str, Path]:
        """
        Generate all geospatial outputs with automatic memory management
        
        Args:
            sonar_points: List of SonarPoint objects
            targets: List of DetectedTarget objects (optional)
            basename: Base filename for outputs
            contour_interval: Bathymetric contour interval in meters
            generate_mbtiles: Whether to generate MBTiles
            generate_dem: Whether to generate DEM
            depth_unit: Unit to display depth in (feet, meters, fathoms)
            
        Returns:
            Dictionary of {format: filepath} for generated files
        """
        results = {}
        
        if not sonar_points:
            logging.error("No sonar points provided")
            return results
        
        # Memory management: Thin points for very large datasets
        num_points = len(sonar_points)
        points_to_process = sonar_points
        decimation_factor = 1
        
        if num_points > 100000:
            # For very large surveys, decimate points to keep memory reasonable
            decimation_factor = max(1, num_points // 50000)
            points_to_process = sonar_points[::decimation_factor]
            logging.warning(f"Large survey detected ({num_points:,} points). "
                          f"Using every {decimation_factor}th point ({len(points_to_process):,} total) "
                          f"to keep memory usage reasonable")
        elif num_points > 50000:
            logging.info(f"Large survey: {num_points:,} points. Processing may take longer.")
        
        # Process bathymetry
        logging.info(f"Processing {len(points_to_process)} sonar points...")
        processor = BathymetricProcessor(points_to_process)
        
        # Generate KML with 3D visualization (ENHANCED)
        logging.info("Generating 3D KML with bathymetry and waterfall visualization...")
        try:
            from kml_3d_generator import KML3DGenerator
            
            kml_gen = KML3DGenerator(f"{basename} - 3D Bathymetry")
            kml_gen.add_track_with_altitude(points_to_process, self.output_dir)
            kml_gen.add_depth_grid(points_to_process, self.output_dir)
            kml_gen.add_waterfall_3d(points_to_process, self.output_dir)
            kml_gen.add_depth_profile(points_to_process)
            kml_gen.add_coverage_area(points_to_process)
            
            kml_3d_path = self.output_dir / f"{basename}_3d.kml"
            if kml_gen.save(kml_3d_path):
                results['kml_3d'] = kml_3d_path
                logging.info(f"✓ 3D KML saved: {kml_3d_path}")
        except Exception as e:
            logging.warning(f"Could not generate 3D KML: {e}")
        
        # Also generate traditional bathymetric KML for compatibility
        logging.info("Generating traditional bathymetric KML...")
        kml_gen = KMLGenerator(f"{basename} - Bathymetry")
        kml_gen.add_bathymetry(processor, contour_interval)
        kml_gen.add_coverage_area(processor)
        
        if targets:
            logging.info(f"Adding {len(targets)} detected targets to KML...")
            kml_gen.add_targets(targets)
        
        kml_path = self.output_dir / f"{basename}_bathymetry.kml"
        if kml_gen.save(kml_path):
            results['kml'] = kml_path
            logging.info(f"✓ Bathymetric KML saved: {kml_path}")
        else:
            logging.warning("Failed to save bathymetric KML")
        
        # Generate MBTiles
        if generate_mbtiles:
            logging.info("Generating MBTiles for web mapping...")
            mbtiles_gen = MBTilesGenerator(
                f"{basename} Tiles",
                self.output_dir / f"{basename}_tiles.mbtiles"
            )
            if mbtiles_gen.create_tile_grid(processor):
                if mbtiles_gen.save():
                    results['mbtiles'] = mbtiles_gen.output_path
                    logging.info(f"✓ MBTiles saved: {mbtiles_gen.output_path}")
        
        # Generate DEM (GeoTIFF) - Skip for very large datasets to save memory
        if generate_dem and SCIPY_AVAILABLE:
            if len(points_to_process) > 50000:
                logging.warning(f"Skipping DEM generation for large dataset ({len(points_to_process):,} points). "
                              f"DEM would require excessive memory. Use smaller area or reduced point density.")
            else:
                logging.info("Generating Digital Elevation Model...")
                dem_path = self._generate_dem(processor, f"{basename}_dem.tif")
                if dem_path:
                    results['dem'] = dem_path
                    logging.info(f"✓ DEM saved: {dem_path}")
        
        # Generate summary HTML
        summary_path = self._generate_summary_html(processor, results, basename, depth_unit)
        if summary_path:
            results['summary'] = summary_path
            logging.info(f"✓ Summary HTML saved: {summary_path}")
        
        logging.info(f"Export complete: {len(results)} files generated")
        return results
    
    def _generate_dem(self, processor: BathymetricProcessor, filename: str) -> Optional[Path]:
        """Generate GeoTIFF DEM file"""
        try:
            if processor.grid_data is None:
                processor.create_grid()
            
            if processor.grid_data is None:
                return None
            
            # Try to use rasterio for GeoTIFF, fall back to simple array
            try:
                import rasterio
                from rasterio.transform import Affine
                
                depth_grid = processor.grid_data['depths']
                bounds = processor.bounds
                
                lat_grid = processor.grid_data['lat_grid']
                lon_grid = processor.grid_data['lon_grid']
                
                transform = Affine.translation(
                    lon_grid[0],
                    lat_grid[-1]
                ) * Affine.scale(
                    lon_grid[1] - lon_grid[0],
                    lat_grid[0] - lat_grid[1]
                )
                
                dem_path = self.output_dir / filename
                
                with rasterio.open(
                    str(dem_path), 'w',
                    driver='GTiff',
                    height=depth_grid.shape[0],
                    width=depth_grid.shape[1],
                    count=1,
                    dtype=depth_grid.dtype,
                    crs='EPSG:4326',
                    transform=transform,
                ) as dst:
                    dst.write(depth_grid, 1)
                
                logging.info(f"DEM saved to {dem_path}")
                return dem_path
                
            except ImportError:
                logging.warning("rasterio not available, skipping GeoTIFF DEM")
                return None
                
        except Exception as e:
            logging.error(f"DEM generation failed: {e}")
            return None
    
    def _generate_summary_html(self, processor: BathymetricProcessor, outputs: Dict, basename: str, depth_unit: str = "feet") -> Optional[Path]:
        """Generate summary HTML report with depth in specified unit"""
        try:
            bounds = processor.bounds
            # Depths are already in the requested unit from the points
            # But skip any invalid values (like -200000 or 0.0 from parsing errors)
            valid_depths = [p.depth for p in processor.points if 0.1 < p.depth < 50000]
            if not valid_depths:
                valid_depths = [p.depth for p in processor.points if p.depth > 0]
            
            depth_stats = {
                'min': min(valid_depths) if valid_depths else 0,
                'max': max(valid_depths) if valid_depths else 0,
                'mean': np.mean(valid_depths) if valid_depths else 0,
            }
            
            # Format depth unit label
            depth_label = depth_unit if depth_unit in ["feet", "meters", "fathoms"] else "feet"
            depth_symbol = {"feet": "ft", "meters": "m", "fathoms": "fa"}.get(depth_label, "ft")
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sonar Survey Summary - {basename}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; }}
        .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #0066cc; }}
        .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .stat-value {{ font-size: 24px; color: #333; font-weight: bold; }}
        .outputs {{ margin: 20px 0; }}
        .output-link {{ display: block; margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px; text-decoration: none; color: #0066cc; }}
        .output-link:hover {{ background: #e0e0e0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️ Sonar Survey Summary Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Survey Statistics</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Total Points</div>
                <div class="stat-value">{len(processor.points):,}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Min Depth</div>
                <div class="stat-value">{depth_stats['min']:.1f} {depth_symbol}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Max Depth</div>
                <div class="stat-value">{depth_stats['max']:.1f} {depth_symbol}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Mean Depth</div>
                <div class="stat-value">{depth_stats['mean']:.1f} {depth_symbol}</div>
            </div>
        </div>
        
        <h2>Coverage Area</h2>
        <table>
            <tr>
                <th>Direction</th>
                <th>Coordinate</th>
            </tr>
            <tr>
                <td>North</td>
                <td>{bounds['north']:.6f}°</td>
            </tr>
            <tr>
                <td>South</td>
                <td>{bounds['south']:.6f}°</td>
            </tr>
            <tr>
                <td>East</td>
                <td>{bounds['east']:.6f}°</td>
            </tr>
            <tr>
                <td>West</td>
                <td>{bounds['west']:.6f}°</td>
            </tr>
        </table>
        
        <h2>Generated Files</h2>
        <div class="outputs">
"""
            
            file_descriptions = {
                'kml': '📍 Bathymetric KML - Open in Google Earth',
                'mbtiles': '🗺️ MBTiles - Web map tiles',
                'dem': '🏔️ Digital Elevation Model - GeoTIFF format',
                'summary': '📄 This Summary Report',
            }
            
            for format_key, output_path in outputs.items():
                if output_path:
                    html_content += f"""            <a href="{output_path.name}" class="output-link">
                ✓ {file_descriptions.get(format_key, format_key)} - {output_path.name}
            </a>
"""
            
            html_content += """        </div>
        
        <h2>How to Use</h2>
        <ul>
            <li><strong>Google Earth:</strong> Open the KML file in Google Earth Pro or the free Google Earth desktop app</li>
            <li><strong>Web Maps:</strong> Use MBTiles with Leaflet or other web mapping libraries</li>
            <li><strong>GIS Software:</strong> Import DEM into ArcGIS, QGIS, or other GIS tools</li>
            <li><strong>3D Visualization:</strong> Use DEM to generate 3D models for presentations</li>
        </ul>
    </div>
</body>
</html>
"""
            
            summary_path = self.output_dir / f"{basename}_summary.html"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logging.info(f"Summary HTML saved to {summary_path}")
            return summary_path
            
        except Exception as e:
            logging.error(f"Summary HTML generation failed: {e}")
            return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def export_sonar_records(
    records: List[Dict],
    output_dir: str,
    basename: str = "sonar_survey",
    **kwargs
) -> Dict[str, Path]:
    """
    Convenience function to export sonar records in various geospatial formats
    
    Args:
        records: List of record dictionaries with 'latitude', 'longitude', 'depth' keys
        output_dir: Output directory path
        basename: Base filename for outputs
        **kwargs: Additional arguments passed to GeospatialExporter.export_all()
        
    Returns:
        Dictionary of {format: filepath}
    """
    # Convert records to SonarPoint objects
    sonar_points = []
    for i, rec in enumerate(records):
        point = SonarPoint(
            latitude=rec.get('latitude', 0),
            longitude=rec.get('longitude', 0),
            depth=rec.get('depth', 0),
            timestamp=rec.get('timestamp', i),
            confidence=rec.get('confidence', 1.0),
            channel=rec.get('channel', 0),
            frequency=rec.get('frequency', 200.0),
        )
        sonar_points.append(point)
    
    # Export
    exporter = GeospatialExporter(output_dir)
    return exporter.export_all(sonar_points, basename=basename, **kwargs)


# ============================================================================
# MAIN / TESTING
# ============================================================================

if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create sample sonar data
    sample_points = [
        SonarPoint(
            latitude=40.0 + np.random.random() * 0.01,
            longitude=-75.0 + np.random.random() * 0.01,
            depth=5 + np.random.random() * 30,
            confidence=0.8 + np.random.random() * 0.2,
        )
        for _ in range(100)
    ]
    
    # Create sample targets
    sample_targets = [
        DetectedTarget(
            latitude=40.005,
            longitude=-75.005,
            depth=15,
            target_type='rock',
            confidence=0.95,
            size_estimate=2.5,
            description="Large rock formation",
        ),
        DetectedTarget(
            latitude=40.002,
            longitude=-74.998,
            depth=25,
            target_type='wreck',
            confidence=0.85,
            size_estimate=5.0,
            description="Possible wreck debris",
        ),
    ]
    
    # Export
    exporter = GeospatialExporter(Path.cwd() / "sonar_output")
    results = exporter.export_all(
        sonar_points=sample_points,
        targets=sample_targets,
        basename="example_survey",
        contour_interval=2.0,
    )
    
    print("\nGenerated files:")
    for format_key, filepath in results.items():
        print(f"  {format_key}: {filepath}")
