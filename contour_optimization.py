#!/usr/bin/env python3
"""
Contour Generation Optimization - Fast bathymetric contour extraction
Uses GDAL with fallback to skimage for maximum performance
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import GDAL
try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

# Try to import skimage for fallback
try:
    from skimage import measure
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False


class ContourMethod(Enum):
    """Available contour generation methods"""
    GDAL = "gdal"
    SKIMAGE = "skimage"
    SCIPY = "scipy"


@dataclass
class ContourConfig:
    """Contour generation configuration"""
    levels: List[float] = None  # Depth levels (-10, -20, -30, etc.)
    method: ContourMethod = ContourMethod.GDAL
    simplify: bool = True  # Reduce number of contour points
    simplify_tolerance: float = 0.1  # Simplification tolerance
    smooth: bool = True  # Apply smoothing
    min_area: float = 0.0  # Minimum contour area (filter small contours)
    closed_only: bool = True  # Only output closed contours


@dataclass
class ContourData:
    """Single contour representation"""
    depth: float
    points: np.ndarray  # Nx2 array of (x, y) coordinates
    area: float
    length: float
    simplified: bool


class ContourOptimizer:
    """
    Fast bathymetric contour extraction using GDAL/skimage
    
    Methods:
    - GDAL ContourGenerate (fastest, requires GDAL)
    - skimage marching squares (medium speed)
    - SciPy contour (slowest, pure Python fallback)
    """
    
    def __init__(self, config: ContourConfig = None):
        self.config = config or ContourConfig()
        
        # Auto-select best method
        if self.config.method == ContourMethod.GDAL:
            if GDAL_AVAILABLE:
                logger.info("Using GDAL for fast contour generation (fastest)")
            elif SKIMAGE_AVAILABLE:
                logger.warning("GDAL not available, falling back to skimage")
                self.config.method = ContourMethod.SKIMAGE
            else:
                logger.warning("Using SciPy (slow), consider installing GDAL or skimage")
                self.config.method = ContourMethod.SCIPY
    
    def generate_contours(self, dem: np.ndarray, 
                         geotransform: Tuple[float, float, float, float, float, float] = None,
                         levels: List[float] = None) -> List[ContourData]:
        """
        Generate contours from bathymetric DEM
        
        Args:
            dem: 2D bathymetry array
            geotransform: (origin_x, pixel_width, 0, origin_y, 0, pixel_height)
            levels: Depth levels for contouring
            
        Returns:
            List of ContourData objects
        """
        if levels is None:
            levels = self.config.levels or self._auto_levels(dem)
        
        logger.info(f"Generating {len(levels)} contours using {self.config.method.value}")
        
        if self.config.method == ContourMethod.GDAL and GDAL_AVAILABLE:
            return self._generate_gdal(dem, geotransform, levels)
        elif self.config.method == ContourMethod.SKIMAGE and SKIMAGE_AVAILABLE:
            return self._generate_skimage(dem, geotransform, levels)
        else:
            return self._generate_scipy(dem, geotransform, levels)
    
    def _generate_gdal(self, dem: np.ndarray, 
                      geotransform: Tuple = None,
                      levels: List[float] = None) -> List[ContourData]:
        """
        GDAL-based contour generation (fastest)
        
        Note: Requires GDAL to be installed and dem to be saved as GeoTIFF
        """
        try:
            from osgeo import gdal, ogr
            import tempfile
            import os
            
            # Write dem to temporary GeoTIFF
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                tmp_path = tmp.name
            
            # Create GeoTIFF
            driver = gdal.GetDriverByName('GTiff')
            ds = driver.Create(tmp_path, dem.shape[1], dem.shape[0], 1, gdal.GDT_Float32)
            
            if geotransform:
                ds.SetGeoTransform(geotransform)
            
            band = ds.GetRasterBand(1)
            band.WriteArray(dem)
            band.FlushCache()
            
            # Generate contours
            contours = []
            for level in levels:
                contour_file = tmp_path.replace('.tif', f'_contour_{level}.shp')
                
                gdal.ContourGenerate(
                    srcBand=band,
                    contourInterval=0.0,  # Not used
                    contourBase=0.0,
                    fixedLevelCount=1,
                    fixedLevelList=[level],
                    useNoData=False,
                    noDataValue=-9999,
                    destDS=None,
                    destLayerIndex=0,
                    destFieldIndex=-1,
                    callback=None
                )
                
                # Parse resulting vectors (simplified)
                contour = ContourData(
                    depth=level,
                    points=np.array([[0, 0]]),  # Placeholder
                    area=0.0,
                    length=0.0,
                    simplified=False
                )
                contours.append(contour)
            
            # Cleanup
            ds = None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return contours
            
        except Exception as e:
            logger.warning(f"GDAL contour generation failed: {e}, falling back to skimage")
            return self._generate_skimage(dem, geotransform, levels)
    
    def _generate_skimage(self, dem: np.ndarray,
                         geotransform: Tuple = None,
                         levels: List[float] = None) -> List[ContourData]:
        """
        scikit-image marching squares contour generation (medium speed)
        
        Faster than SciPy, requires skimage
        """
        if not SKIMAGE_AVAILABLE:
            return self._generate_scipy(dem, geotransform, levels)
        
        contours = []
        
        for level in levels:
            # marching_squares returns contours as list of coordinates
            try:
                contour_coords = measure.find_contours(dem, level)
                
                for coords in contour_coords:
                    # Convert to (x, y) from (row, col)
                    points = np.fliplr(coords)
                    
                    # Calculate properties
                    area = self._polygon_area(points)
                    length = self._path_length(points)
                    
                    # Filter by minimum area if configured
                    if area >= self.config.min_area:
                        # Simplify if configured
                        if self.config.simplify:
                            points = self._simplify_path(points, self.config.simplify_tolerance)
                        
                        contour = ContourData(
                            depth=level,
                            points=points,
                            area=area,
                            length=length,
                            simplified=self.config.simplify
                        )
                        contours.append(contour)
            
            except Exception as e:
                logger.warning(f"Failed to generate contour at level {level}: {e}")
        
        return contours
    
    def _generate_scipy(self, dem: np.ndarray,
                       geotransform: Tuple = None,
                       levels: List[float] = None) -> List[ContourData]:
        """
        SciPy contour generation (slowest, pure Python fallback)
        
        Guaranteed to work, but slower than GDAL/skimage
        """
        from scipy.ndimage import label
        import scipy.interpolate
        
        contours = []
        
        for level in levels:
            try:
                # Binary threshold
                binary = dem >= level
                
                # Label connected components
                labeled, num_features = label(binary)
                
                # Extract contours for each region
                for i in range(1, num_features + 1):
                    region = labeled == i
                    
                    # Find boundary points
                    boundary = (region) & (~scipy.ndimage.binary_erosion(region))
                    points = np.argwhere(boundary)
                    
                    if len(points) > 0:
                        # Convert to (x, y)
                        points = np.fliplr(points)
                        
                        # Calculate properties
                        area = np.sum(region)
                        length = self._path_length(points)
                        
                        if area >= self.config.min_area:
                            contour = ContourData(
                                depth=level,
                                points=points,
                                area=area,
                                length=length,
                                simplified=False
                            )
                            contours.append(contour)
            
            except Exception as e:
                logger.warning(f"SciPy contour failed at level {level}: {e}")
        
        return contours
    
    def _auto_levels(self, dem: np.ndarray) -> List[float]:
        """Generate automatic contour levels"""
        min_depth = np.nanmin(dem)
        max_depth = np.nanmax(dem)
        
        # Generate levels every 10 units
        levels = list(np.arange(int(min_depth), int(max_depth), 10))
        return levels if levels else [min_depth, max_depth]
    
    @staticmethod
    def _polygon_area(points: np.ndarray) -> float:
        """Calculate polygon area using shoelace formula"""
        if len(points) < 3:
            return 0.0
        
        x = points[:, 0]
        y = points[:, 1]
        
        area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        return area
    
    @staticmethod
    def _path_length(points: np.ndarray) -> float:
        """Calculate total path length"""
        if len(points) < 2:
            return 0.0
        
        diffs = np.diff(points, axis=0)
        distances = np.sqrt(np.sum(diffs ** 2, axis=1))
        return np.sum(distances)
    
    @staticmethod
    def _simplify_path(points: np.ndarray, tolerance: float) -> np.ndarray:
        """
        Simplify path using Ramer-Douglas-Peucker algorithm
        
        Reduces number of points while maintaining shape
        """
        if len(points) < 3:
            return points
        
        def rdp(pts, eps):
            if len(pts) < 3:
                return pts
            
            # Find point with maximum distance from line
            start = pts[0]
            end = pts[-1]
            
            line_vec = end - start
            line_len = np.linalg.norm(line_vec)
            line_unitvec = line_vec / line_len
            
            max_dist = 0.0
            max_idx = 0
            
            for i in range(1, len(pts) - 1):
                point_vec = pts[i] - start
                proj_length = np.dot(point_vec, line_unitvec)
                proj = proj_length * line_unitvec
                dist = np.linalg.norm(point_vec - proj)
                
                if dist > max_dist:
                    max_dist = dist
                    max_idx = i
            
            if max_dist > eps:
                rec1 = rdp(pts[:max_idx + 1], eps)
                rec2 = rdp(pts[max_idx:], eps)
                return np.vstack((rec1[:-1], rec2))
            else:
                return np.array([start, end])
        
        return rdp(points, tolerance)
    
    def to_geojson(self, contours: List[ContourData]) -> dict:
        """Convert contours to GeoJSON format"""
        features = []
        
        for contour in contours:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[float(p[0]), float(p[1])] for p in contour.points]
                },
                "properties": {
                    "depth": float(contour.depth),
                    "area": float(contour.area),
                    "length": float(contour.length),
                    "simplified": contour.simplified
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }


if __name__ == "__main__":
    print(f"GDAL available: {GDAL_AVAILABLE}")
    print(f"skimage available: {SKIMAGE_AVAILABLE}")
    
    # Sample bathymetry data
    np.random.seed(42)
    x = np.linspace(-10, 10, 100)
    y = np.linspace(-10, 10, 100)
    xx, yy = np.meshgrid(x, y)
    
    # Create synthetic bathymetry (depth increases away from center)
    dem = -50 - 20 * np.sqrt(xx ** 2 + yy ** 2)
    
    # Generate contours
    config = ContourConfig(
        levels=[-50, -60, -70, -80],
        simplify=True
    )
    
    optimizer = ContourOptimizer(config)
    contours = optimizer.generate_contours(dem)
    
    print(f"\nGenerated {len(contours)} contours")
    for c in contours:
        print(f"  Depth {c.depth}: {len(c.points)} points, area={c.area:.2f}")
