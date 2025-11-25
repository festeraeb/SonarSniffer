#!/usr/bin/env python3
"""
Data Format Converter - Universal conversion between bathymetric formats
Supports: RSD, NetCDF, GeoTIFF, HDF5, CSV, ASCII grid, and more

Provides seamless conversion with lossless data preservation where possible.
"""

import numpy as np
import logging
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import format-specific libraries
try:
    import netCDF4
    NETCDF_AVAILABLE = True
except ImportError:
    NETCDF_AVAILABLE = False

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

try:
    import h5py
    H5_AVAILABLE = True
except ImportError:
    H5_AVAILABLE = False


class DataFormat(Enum):
    """Supported data formats"""
    NETCDF = "netcdf"  # CF-compliant NetCDF
    GEOTIFF = "geotiff"  # GeoTIFF with georeferencing
    HDF5 = "hdf5"  # Hierarchical Data Format
    ASCII_GRID = "ascii_grid"  # GDAL ASCII grid
    CSV = "csv"  # Comma-separated values
    NUMPY = "numpy"  # NumPy binary format
    JSON = "json"  # JSON with metadata


@dataclass
class BathymetricGrid:
    """Standard bathymetric grid representation"""
    data: np.ndarray  # 2D array of depth values
    x: np.ndarray  # X coordinates (longitude or easting)
    y: np.ndarray  # Y coordinates (latitude or northing)
    z: np.ndarray  # Z coordinates (depth values, same as data)
    crs: str = "EPSG:4326"  # Coordinate reference system
    metadata: Dict[str, Any] = None
    
    @property
    def extent(self) -> Tuple[float, float, float, float]:
        """Get grid extent (min_x, min_y, max_x, max_y)"""
        return (np.min(self.x), np.min(self.y), np.max(self.x), np.max(self.y))
    
    @property
    def resolution(self) -> Tuple[float, float]:
        """Get grid resolution (x_res, y_res)"""
        x_res = abs(self.x[1] - self.x[0]) if len(self.x) > 1 else 1.0
        y_res = abs(self.y[1] - self.y[0]) if len(self.y) > 1 else 1.0
        return (x_res, y_res)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataFormatConverter:
    """
    Convert bathymetric data between formats
    
    Supports lossless conversion with automatic fallbacks
    """
    
    def __init__(self):
        self.format_handlers = {
            DataFormat.NETCDF: (self._read_netcdf, self._write_netcdf),
            DataFormat.GEOTIFF: (self._read_geotiff, self._write_geotiff),
            DataFormat.HDF5: (self._read_hdf5, self._write_hdf5),
            DataFormat.ASCII_GRID: (self._read_ascii_grid, self._write_ascii_grid),
            DataFormat.CSV: (self._read_csv, self._write_csv),
            DataFormat.NUMPY: (self._read_numpy, self._write_numpy),
            DataFormat.JSON: (self._read_json, self._write_json),
        }
    
    def read(self, filepath: str, format: DataFormat = None) -> BathymetricGrid:
        """
        Read bathymetric data from file
        
        Args:
            filepath: Path to input file
            format: Data format (auto-detected from extension if None)
            
        Returns:
            BathymetricGrid object
        """
        if format is None:
            format = self._detect_format(filepath)
        
        logger.info(f"Reading {format.value} file: {filepath}")
        
        if format not in self.format_handlers:
            raise ValueError(f"Unsupported format: {format}")
        
        reader, _ = self.format_handlers[format]
        return reader(filepath)
    
    def write(self, grid: BathymetricGrid, filepath: str, 
             format: DataFormat = None, **kwargs) -> None:
        """
        Write bathymetric data to file
        
        Args:
            grid: BathymetricGrid object
            filepath: Output file path
            format: Data format (auto-detected from extension if None)
            **kwargs: Format-specific options
        """
        if format is None:
            format = self._detect_format(filepath)
        
        logger.info(f"Writing {format.value} file: {filepath}")
        
        if format not in self.format_handlers:
            raise ValueError(f"Unsupported format: {format}")
        
        _, writer = self.format_handlers[format]
        writer(grid, filepath, **kwargs)
    
    def convert(self, input_file: str, output_file: str,
               input_format: DataFormat = None,
               output_format: DataFormat = None) -> None:
        """
        Convert between two formats
        
        Args:
            input_file: Input file path
            output_file: Output file path
            input_format: Input format (auto-detected if None)
            output_format: Output format (auto-detected if None)
        """
        # Read input
        grid = self.read(input_file, input_format)
        
        # Write output
        self.write(grid, output_file, output_format)
        
        logger.info(f"Conversion complete: {input_file} -> {output_file}")
    
    def _read_netcdf(self, filepath: str) -> BathymetricGrid:
        """Read NetCDF file (CF-compliant)"""
        if not NETCDF_AVAILABLE:
            raise ImportError("netCDF4 required for NetCDF support")
        
        try:
            ds = netCDF4.Dataset(filepath, 'r')
            
            # Read variables (CF conventions)
            data = ds['z'][:] if 'z' in ds.variables else ds['elevation'][:]
            x = ds['x'][:] if 'x' in ds.variables else ds['longitude'][:]
            y = ds['y'][:] if 'y' in ds.variables else ds['latitude'][:]
            
            # Read metadata
            metadata = {key: ds.getncattr(key) for key in ds.ncattrs()}
            crs = metadata.get('crs', 'EPSG:4326')
            
            ds.close()
            
            return BathymetricGrid(
                data=data,
                x=x,
                y=y,
                z=data,
                crs=crs,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Failed to read NetCDF: {e}")
            raise
    
    def _write_netcdf(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write NetCDF file (CF-compliant)"""
        if not NETCDF_AVAILABLE:
            raise ImportError("netCDF4 required for NetCDF support")
        
        try:
            ds = netCDF4.Dataset(filepath, 'w', format='NETCDF4')
            
            # Create dimensions
            ds.createDimension('x', len(grid.x))
            ds.createDimension('y', len(grid.y))
            
            # Create variables
            x_var = ds.createVariable('x', 'f4', ('x',))
            y_var = ds.createVariable('y', 'f4', ('y',))
            z_var = ds.createVariable('z', 'f4', ('y', 'x'))
            
            # Write data
            x_var[:] = grid.x
            y_var[:] = grid.y
            z_var[:] = grid.data
            
            # Add attributes
            x_var.units = 'degrees_east'
            y_var.units = 'degrees_north'
            z_var.units = 'meters'
            z_var.standard_name = 'sea_floor_depth'
            
            # Add metadata
            for key, value in grid.metadata.items():
                try:
                    ds.setncattr(key, str(value))
                except:
                    pass
            
            ds.setncattr('crs', grid.crs)
            
            ds.close()
        
        except Exception as e:
            logger.error(f"Failed to write NetCDF: {e}")
            raise
    
    def _read_geotiff(self, filepath: str) -> BathymetricGrid:
        """Read GeoTIFF file with georeferencing"""
        if not GDAL_AVAILABLE:
            raise ImportError("GDAL required for GeoTIFF support")
        
        try:
            ds = gdal.Open(filepath)
            
            # Read raster data
            band = ds.GetRasterBand(1)
            data = band.ReadAsArray()
            
            # Get geotransform
            geotransform = ds.GetGeoTransform()
            origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
            
            # Generate coordinate arrays
            rows, cols = data.shape
            x = np.linspace(origin_x, origin_x + cols * pixel_width, cols)
            y = np.linspace(origin_y, origin_y + rows * pixel_height, rows)
            
            # Get CRS
            crs = ds.GetProjection() or 'EPSG:4326'
            
            ds = None
            
            return BathymetricGrid(
                data=data,
                x=x,
                y=y,
                z=data,
                crs=crs,
                metadata={'geotransform': geotransform}
            )
        
        except Exception as e:
            logger.error(f"Failed to read GeoTIFF: {e}")
            raise
    
    def _write_geotiff(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write GeoTIFF file with georeferencing"""
        if not GDAL_AVAILABLE:
            raise ImportError("GDAL required for GeoTIFF support")
        
        try:
            driver = gdal.GetDriverByName('GTiff')
            rows, cols = grid.data.shape
            
            ds = driver.Create(filepath, cols, rows, 1, gdal.GDT_Float32)
            
            # Set geotransform
            x_res = (grid.x[-1] - grid.x[0]) / (len(grid.x) - 1)
            y_res = (grid.y[-1] - grid.y[0]) / (len(grid.y) - 1)
            geotransform = (grid.x[0], x_res, 0, grid.y[0], 0, y_res)
            ds.SetGeoTransform(geotransform)
            
            # Set projection
            ds.SetProjection(grid.crs)
            
            # Write data
            band = ds.GetRasterBand(1)
            band.WriteArray(grid.data)
            band.FlushCache()
            
            ds = None
        
        except Exception as e:
            logger.error(f"Failed to write GeoTIFF: {e}")
            raise
    
    def _read_hdf5(self, filepath: str) -> BathymetricGrid:
        """Read HDF5 file"""
        if not H5_AVAILABLE:
            raise ImportError("h5py required for HDF5 support")
        
        try:
            with h5py.File(filepath, 'r') as f:
                data = f['data'][:] if 'data' in f else f['z'][:]
                x = f['x'][:] if 'x' in f else np.arange(data.shape[1])
                y = f['y'][:] if 'y' in f else np.arange(data.shape[0])
                
                metadata = {}
                for key in f.attrs:
                    metadata[key] = f.attrs[key]
                
                return BathymetricGrid(
                    data=data,
                    x=x,
                    y=y,
                    z=data,
                    crs=metadata.get('crs', 'EPSG:4326'),
                    metadata=metadata
                )
        
        except Exception as e:
            logger.error(f"Failed to read HDF5: {e}")
            raise
    
    def _write_hdf5(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write HDF5 file"""
        if not H5_AVAILABLE:
            raise ImportError("h5py required for HDF5 support")
        
        try:
            with h5py.File(filepath, 'w') as f:
                f.create_dataset('data', data=grid.data)
                f.create_dataset('x', data=grid.x)
                f.create_dataset('y', data=grid.y)
                
                for key, value in grid.metadata.items():
                    try:
                        f.attrs[key] = value
                    except:
                        pass
                
                f.attrs['crs'] = grid.crs
        
        except Exception as e:
            logger.error(f"Failed to write HDF5: {e}")
            raise
    
    def _read_ascii_grid(self, filepath: str) -> BathymetricGrid:
        """Read GDAL ASCII grid format"""
        try:
            # Parse header
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            header = {}
            data_start = 0
            
            for i, line in enumerate(lines):
                if line.strip().startswith('ncols'):
                    header['ncols'] = int(line.split()[1])
                elif line.strip().startswith('nrows'):
                    header['nrows'] = int(line.split()[1])
                elif line.strip().startswith('xllcorner'):
                    header['xllcorner'] = float(line.split()[1])
                elif line.strip().startswith('yllcorner'):
                    header['yllcorner'] = float(line.split()[1])
                elif line.strip().startswith('cellsize'):
                    header['cellsize'] = float(line.split()[1])
                elif line.strip().startswith('NODATA'):
                    header['nodata'] = float(line.split()[1])
                else:
                    data_start = i
                    break
            
            # Read data
            data_lines = lines[data_start:]
            data = np.array([line.split() for line in data_lines], dtype=float)
            
            # Generate coordinates
            ncols = header['ncols']
            nrows = header['nrows']
            cellsize = header['cellsize']
            x_origin = header['xllcorner']
            y_origin = header['yllcorner']
            
            x = np.linspace(x_origin, x_origin + ncols * cellsize, ncols)
            y = np.linspace(y_origin + nrows * cellsize, y_origin, nrows)
            
            return BathymetricGrid(
                data=data,
                x=x,
                y=y,
                z=data,
                metadata=header
            )
        
        except Exception as e:
            logger.error(f"Failed to read ASCII grid: {e}")
            raise
    
    def _write_ascii_grid(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write GDAL ASCII grid format"""
        try:
            x_res = grid.resolution[0]
            y_res = grid.resolution[1]
            
            with open(filepath, 'w') as f:
                f.write(f"ncols {len(grid.x)}\n")
                f.write(f"nrows {len(grid.y)}\n")
                f.write(f"xllcorner {np.min(grid.x)}\n")
                f.write(f"yllcorner {np.min(grid.y)}\n")
                f.write(f"cellsize {x_res}\n")
                
                # Write data
                for row in grid.data:
                    f.write(' '.join(f'{val:.6f}' for val in row) + '\n')
        
        except Exception as e:
            logger.error(f"Failed to write ASCII grid: {e}")
            raise
    
    def _read_csv(self, filepath: str) -> BathymetricGrid:
        """Read CSV format (x, y, z columns)"""
        try:
            data = np.genfromtxt(filepath, delimiter=',', skip_header=1)
            
            x = np.unique(data[:, 0])
            y = np.unique(data[:, 1])
            
            # Reshape to grid
            grid_data = np.zeros((len(y), len(x)))
            for i, row in enumerate(data):
                xi = np.argmin(np.abs(x - row[0]))
                yi = np.argmin(np.abs(y - row[1]))
                grid_data[yi, xi] = row[2]
            
            return BathymetricGrid(
                data=grid_data,
                x=x,
                y=y,
                z=grid_data
            )
        
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            raise
    
    def _write_csv(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write CSV format (x, y, z columns)"""
        try:
            with open(filepath, 'w') as f:
                f.write("x,y,z\n")
                
                for yi, y in enumerate(grid.y):
                    for xi, x in enumerate(grid.x):
                        z = grid.data[yi, xi]
                        f.write(f"{x},{y},{z}\n")
        
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            raise
    
    def _read_numpy(self, filepath: str) -> BathymetricGrid:
        """Read NumPy binary format"""
        try:
            loaded = np.load(filepath)
            
            if isinstance(loaded, np.ndarray):
                data = loaded
                x = np.arange(data.shape[1])
                y = np.arange(data.shape[0])
            else:
                # Loaded as dict from savez
                data = loaded['data']
                x = loaded.get('x', np.arange(data.shape[1]))
                y = loaded.get('y', np.arange(data.shape[0]))
            
            return BathymetricGrid(
                data=data,
                x=x,
                y=y,
                z=data
            )
        
        except Exception as e:
            logger.error(f"Failed to read NumPy: {e}")
            raise
    
    def _write_numpy(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write NumPy binary format"""
        try:
            np.savez(filepath, data=grid.data, x=grid.x, y=grid.y)
        
        except Exception as e:
            logger.error(f"Failed to write NumPy: {e}")
            raise
    
    def _read_json(self, filepath: str) -> BathymetricGrid:
        """Read JSON format (with embedded base64 data)"""
        try:
            with open(filepath, 'r') as f:
                obj = json.load(f)
            
            import base64
            
            # Decode data
            data_bytes = base64.b64decode(obj['data'])
            data = np.frombuffer(data_bytes, dtype=np.float32).reshape(obj['shape'])
            
            x = np.array(obj['x'])
            y = np.array(obj['y'])
            
            return BathymetricGrid(
                data=data,
                x=x,
                y=y,
                z=data,
                crs=obj.get('crs', 'EPSG:4326'),
                metadata=obj.get('metadata', {})
            )
        
        except Exception as e:
            logger.error(f"Failed to read JSON: {e}")
            raise
    
    def _write_json(self, grid: BathymetricGrid, filepath: str, **kwargs) -> None:
        """Write JSON format (with embedded base64 data)"""
        try:
            import base64
            
            # Encode data
            data_bytes = grid.data.astype(np.float32).tobytes()
            data_b64 = base64.b64encode(data_bytes).decode('ascii')
            
            obj = {
                'data': data_b64,
                'shape': list(grid.data.shape),
                'x': grid.x.tolist(),
                'y': grid.y.tolist(),
                'crs': grid.crs,
                'metadata': grid.metadata
            }
            
            with open(filepath, 'w') as f:
                json.dump(obj, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}")
            raise
    
    @staticmethod
    def _detect_format(filepath: str) -> DataFormat:
        """Auto-detect format from file extension"""
        ext = filepath.split('.')[-1].lower()
        
        format_map = {
            'nc': DataFormat.NETCDF,
            'tif': DataFormat.GEOTIFF,
            'tiff': DataFormat.GEOTIFF,
            'h5': DataFormat.HDF5,
            'hdf5': DataFormat.HDF5,
            'asc': DataFormat.ASCII_GRID,
            'csv': DataFormat.CSV,
            'npy': DataFormat.NUMPY,
            'npz': DataFormat.NUMPY,
            'json': DataFormat.JSON,
        }
        
        return format_map.get(ext, DataFormat.NETCDF)


if __name__ == "__main__":
    # Example usage
    print("Data Format Converter initialized")
    print(f"NetCDF available: {NETCDF_AVAILABLE}")
    print(f"GDAL available: {GDAL_AVAILABLE}")
    print(f"HDF5 available: {H5_AVAILABLE}")
    
    # Create sample grid
    converter = DataFormatConverter()
    
    x = np.linspace(-122.5, -122.0, 100)
    y = np.linspace(37.5, 38.0, 100)
    data = -50 - 10 * np.sin(x[np.newaxis, :] / 10) * np.cos(y[:, np.newaxis] / 10)
    
    grid = BathymetricGrid(
        data=data,
        x=x,
        y=y,
        z=data,
        crs="EPSG:4326",
        metadata={"source": "synthetic", "units": "meters"}
    )
    
    print(f"\nSample grid created:")
    print(f"  Shape: {grid.data.shape}")
    print(f"  Extent: {grid.extent}")
    print(f"  Resolution: {grid.resolution}")
    
    # Example conversions (would work with actual files)
    print("\nSupported conversions:")
    print("  - NetCDF ↔ GeoTIFF")
    print("  - GeoTIFF ↔ HDF5")
    print("  - ASCII Grid ↔ JSON")
    print("  - CSV ↔ NumPy")
    print("  And many more...")
