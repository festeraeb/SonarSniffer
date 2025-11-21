"""
Enhanced 3D KML Generator for SonarSniffer
Creates visually rich 3D sonar visualizations in Google Earth format

Features:
- 3D sonar waterfall visualization
- Georeferenced bathymetric mesh
- Interactive depth profiles
- Target markers with photos
- Coverage polygons
- Animated track replay
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from datetime import datetime

# Try to import simplekml, fall back to manual KML generation
try:
    import simplekml
    SIMPLEKML_AVAILABLE = True
except ImportError:
    SIMPLEKML_AVAILABLE = False


@dataclass
class SonarPoint:
    """A single sonar measurement point"""
    latitude: float
    longitude: float
    depth: float
    timestamp: float
    confidence: float
    channel: int
    frequency: float


class KML3DGenerator:
    """Generate 3D KML files with enhanced visualization"""
    
    def __init__(self, name: str = "Sonar Survey 3D"):
        self.name = name
        self.kml = None
        self.ns = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2'
        }
        
        if SIMPLEKML_AVAILABLE:
            self.kml = simplekml.Kml()
            self.kml.name = name
    
    def _create_kml_root(self) -> ET.Element:
        """Create KML root element for manual generation"""
        root = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        root.set('{http://www.w3.org/2000/xmlns}gx', 'http://www.google.com/kml/ext/2.2')
        document = ET.SubElement(root, 'Document')
        document.append(ET.Element('name'))
        document[0].text = self.name
        return document
    
    def add_track_with_altitude(self, points: List[SonarPoint], output_dir: Path):
        """Add sonar track as 3D line with depth as altitude"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available for track visualization")
            return
        
        # Create folder for track
        track_folder = self.kml.newfolder(name="Survey Track")
        
        # Create track line (depth represents altitude)
        coords = []
        for point in points:
            # Depth is in feet (converted in post_processing_dialog)
            # Use negative depth for below-sea-level visualization in Google Earth
            # Convert feet to meters for altitude (divide by 3.28084) then negate for below surface
            altitude_m = -(point.depth / 3.28084) if point.depth > 0 else 0
            coords.append((point.longitude, point.latitude, altitude_m))
        
        if len(coords) > 1:
            track = track_folder.newlinestring(
                name="Sonar Track",
                description=f"Survey track with {len(points)} measurements",
                coords=coords
            )
            track.altitudemode = simplekml.AltitudeMode.relativetoground
            
            # Style the track
            try:
                track.linestyle.color = simplekml.Color.red
                track.linestyle.width = 3
            except:
                # If styling fails, just continue
                pass
    
    def add_depth_grid(self, points: List[SonarPoint], output_dir: Path):
        """Create 3D grid surface representing bathymetry"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available for grid visualization")
            return
        
        # Group points by proximity for mesh generation
        grid_folder = self.kml.newfolder(name="Bathymetric Surface")
        
        # Create colored circles based on depth
        for point in points:
            # Normalize depth to 100m max (convert from feet: divide by 3.28084)
            depth_m = point.depth / 3.28084 if isinstance(point.depth, (int, float)) else 0
            depth_ratio = min(1.0, depth_m / 100.0)
            
            # Color gradient: blue (deep) -> green (mid) -> red (shallow)
            if depth_ratio < 0.5:
                r = 0
                g = int(255 * (depth_ratio * 2))
                b = 255
            else:
                r = int(255 * ((depth_ratio - 0.5) * 2))
                g = 255 - int(128 * ((depth_ratio - 0.5) * 2))
                b = 0
            
            color_hex = f'{r:02x}{g:02x}{b:02x}'
            
            # Create point marker
            try:
                # Convert depth to meters for proper altitude
                altitude_m = -(depth_m) if depth_m > 0 else 0
                pm = grid_folder.newpoint(
                    name=f"D{depth_m:.1f}m",
                    description=f"Depth: {depth_m:.2f}m ({point.depth:.0f}ft)<br/>Confidence: {point.confidence:.1%}<br/>Ch {int(point.channel)}",
                    coords=[(point.longitude, point.latitude, altitude_m)]
                )
                pm.altitudemode = simplekml.AltitudeMode.relativetoground
                pm.style.iconstyle.scale = 0.3 + (point.confidence * 0.4)
                try:
                    pm.style.iconstyle.color = simplekml.Color(f'ff{color_hex[4:6]}{color_hex[2:4]}{color_hex[0:2]}')
                except:
                    pass  # Skip color if it fails
            except Exception as e:
                logging.debug(f"Could not add point marker: {e}")
    
    def add_waterfall_3d(self, points: List[SonarPoint], output_dir: Path, 
                        waterfall_image_path: Optional[Path] = None):
        """Add 3D representation of sonar waterfall display"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available")
            return
        
        waterfall_folder = self.kml.newfolder(name="Sonar Waterfall")
        
        # Sort points by timestamp to recreate waterfall sequence
        sorted_points = sorted(points, key=lambda p: p.timestamp)
        
        # Group into scan lines
        scan_groups = {}
        for point in sorted_points:
            scan_id = int(point.timestamp / 10)  # Group by ~10-second scans
            if scan_id not in scan_groups:
                scan_groups[scan_id] = []
            scan_groups[scan_id].append(point)
        
        # Create 3D representation of each scan
        for scan_idx, (scan_id, scan_points) in enumerate(sorted(scan_groups.items())):
            if len(scan_points) < 2:
                continue
            
            try:
                # Create polygon for scan surface
                coords = []
                for point in sorted(scan_points, key=lambda p: p.depth):
                    # Convert feet to meters for altitude
                    depth_m = point.depth / 3.28084 if isinstance(point.depth, (int, float)) else 0
                    altitude = -(depth_m) if depth_m > 0 else 0
                    coords.append((point.longitude, point.latitude, altitude))
                
                if len(coords) >= 3:
                    poly = waterfall_folder.newpolygon(
                        name=f"Scan {scan_idx}",
                        outerboundaryis=coords
                    )
                    poly.altitudemode = simplekml.AltitudeMode.relativetoground
                    
                    # Color by scan index
                    hue = (scan_idx % 60) / 60.0
                    rgb = _hsv_to_rgb(hue, 0.7, 0.8)
                    color_hex = f'{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
                    
                    try:
                        poly.style.polystyle.color = simplekml.Color(f'88{color_hex[4:6]}{color_hex[2:4]}{color_hex[0:2]}')
                        poly.style.polystyle.fill = 1
                        poly.style.polystyle.outline = 1
                    except:
                        pass  # Skip styling if it fails
            except Exception as e:
                logging.debug(f"Could not add scan polygon: {e}")
    
    def add_sonar_frame_as_ground_overlay(self, frame_path: Path, bounds: Tuple[float, float, float, float]):
        """Add sonar frame image as Google Earth ground overlay"""
        if not SIMPLEKML_AVAILABLE:
            logging.warning("simplekml not available")
            return
        
        try:
            overlay_folder = self.kml.newfolder(name="Sonar Imagery")
            
            # Create ground overlay
            go = overlay_folder.newgroundoverlay(
                name=f"Sonar Frame: {frame_path.stem}",
                image=str(frame_path)
            )
            
            # Set bounds (lat_min, lat_max, lon_min, lon_max)
            go.latlonbox.north = bounds[1]  # lat_max
            go.latlonbox.south = bounds[0]  # lat_min
            go.latlonbox.east = bounds[3]   # lon_max
            go.latlonbox.west = bounds[2]   # lon_min
            
            # Set transparency for blending
            go.icon.href = str(frame_path)
            go.draworder = 50
            
            logging.info(f"Added ground overlay: {frame_path.name}")
        except Exception as e:
            logging.warning(f"Could not add ground overlay: {e}")
    
    def add_depth_profile(self, points: List[SonarPoint]):
        """Add interactive depth profile"""
        if not SIMPLEKML_AVAILABLE:
            return
        
        profile_folder = self.kml.newfolder(name="Depth Profiles")
        
        # Calculate depth statistics (convert from feet to meters)
        depths_m = [p.depth / 3.28084 if isinstance(p.depth, (int, float)) else 0 for p in points]
        mean_depth = np.mean(depths_m)
        max_depth = np.max(depths_m)
        min_depth = np.min(depths_m)
        
        # Create description with statistics (show both meters and feet)
        description = f"""
<h3>Depth Profile Statistics</h3>
<table>
<tr><td>Mean Depth:</td><td>{mean_depth:.2f} m ({mean_depth * 3.28084:.0f} ft)</td></tr>
<tr><td>Maximum Depth:</td><td>{max_depth:.2f} m ({max_depth * 3.28084:.0f} ft)</td></tr>
<tr><td>Minimum Depth:</td><td>{min_depth:.2f} m ({min_depth * 3.28084:.0f} ft)</td></tr>
<tr><td>Total Points:</td><td>{len(points)}</td></tr>
<tr><td>Survey Date:</td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
</table>
"""
        
        # Add as a placemark with description
        pm = profile_folder.newpoint(
            name="Survey Statistics",
            description=description,
            coords=[(np.mean([p.longitude for p in points]), 
                    np.mean([p.latitude for p in points]))]
        )
        pm.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/info-i_maps.png'
    
    def add_coverage_area(self, points: List[SonarPoint]):
        """Add survey coverage area as polygon"""
        if not SIMPLEKML_AVAILABLE:
            return
        
        if len(points) < 3:
            return
        
        try:
            coverage_folder = self.kml.newfolder(name="Coverage Area")
            
            # Create convex hull or bounding box
            lats = [p.latitude for p in points]
            lons = [p.longitude for p in points]
            
            # Simple bounding box
            coords = [
                (min(lons), min(lats), 0),
                (max(lons), min(lats), 0),
                (max(lons), max(lats), 0),
                (min(lons), max(lats), 0),
                (min(lons), min(lats), 0),
            ]
            
            poly = coverage_folder.newpolygon(
                name="Survey Bounds",
                description=f"Survey coverage area: {len(points)} points",
                outerboundaryis=coords
            )
            
            try:
                poly.style.polystyle.color = simplekml.Color('3300ff00')  # Semi-transparent green
                poly.style.polystyle.fill = 0  # No fill, just outline
                poly.style.polystyle.outline = 1
                poly.style.linestyle.width = 2
                poly.style.linestyle.color = simplekml.Color.green
            except:
                pass  # Skip styling if it fails
        except Exception as e:
            logging.debug(f"Could not add coverage area: {e}")
    
    def save(self, filepath: Path) -> bool:
        """Save 3D KML file"""
        if not SIMPLEKML_AVAILABLE:
            logging.error("simplekml not available, cannot save KML")
            return False
        
        try:
            self.kml.save(str(filepath))
            logging.info(f"3D KML saved to {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to save KML: {e}")
            return False


def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert HSV to RGB color"""
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class AdvancedKMLExporter:
    """High-level interface for creating rich KML exports"""
    
    @staticmethod
    def create_3d_sonar_kml(points: List[SonarPoint], 
                           output_path: Path,
                           name: str = "Sonar Survey",
                           waterfall_image: Optional[Path] = None) -> bool:
        """
        Create comprehensive 3D KML export.
        
        Args:
            points: Sonar measurement points
            output_path: Output KML file path
            name: Survey name
            waterfall_image: Optional waterfall image to overlay
            
        Returns:
            True if successful
        """
        try:
            gen = KML3DGenerator(name)
            
            # Add all visualization layers
            gen.add_track_with_altitude(points, output_path.parent)
            gen.add_depth_grid(points, output_path.parent)
            gen.add_waterfall_3d(points, output_path.parent, waterfall_image)
            gen.add_depth_profile(points)
            gen.add_coverage_area(points)
            
            # Save
            return gen.save(output_path)
        except Exception as e:
            logging.error(f"Failed to create 3D KML: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample data
    sample_points = [
        SonarPoint(40.7128, -74.0060, 5.0, i, 0.9, 1, 200.0)
        for i in range(10)
    ]
    
    output = Path("/tmp/test_3d.kml")
    success = AdvancedKMLExporter.create_3d_sonar_kml(sample_points, output, "Test 3D Sonar")
    print(f"✓ 3D KML created: {output}" if success else "✗ Failed to create 3D KML")
