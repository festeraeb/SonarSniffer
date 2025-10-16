#!/usr/bin/env python3
"""
3D Bathymetric Mapping Module
Direct ReefMaster competitor - create 3D underwater maps from sonar data

This module extracts depth and coordinate data from parsed sonar records
and creates professional bathymetric maps for export in multiple formats.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import tri
import pandas as pd
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import json
from scipy.spatial import ConvexHull
from scipy.interpolate import griddata

class BathymetricMapper:
    """
    Create 3D bathymetric maps from sonar data
    Competes directly with ReefMaster's mapping capabilities
    """
    
    def __init__(self):
        self.depth_points = []
        self.bounds = None
        self.grid_resolution = 100  # Default grid size
        
    def load_sonar_data(self, csv_file: str) -> bool:
        """
        Load parsed sonar data from CSV files
        Works with our universal parser output
        """
        try:
            df = pd.read_csv(csv_file)
            
            # Extract coordinates and depth data
            if all(col in df.columns for col in ['lat', 'lon', 'depth_m']):
                # Filter out invalid coordinates and depths
                valid_data = df[
                    (df['lat'] != 0) & 
                    (df['lon'] != 0) & 
                    (df['depth_m'] > 0) & 
                    (df['depth_m'] < 1000)  # Reasonable depth limit
                ].copy()
                
                if len(valid_data) > 0:
                    self.depth_points = list(zip(
                        valid_data['lon'], 
                        valid_data['lat'], 
                        valid_data['depth_m']
                    ))
                    
                    print(f"Loaded {len(self.depth_points)} valid depth points")
                    self._calculate_bounds()
                    return True
                else:
                    print("No valid depth data found")
                    return False
            else:
                print("Required columns (lat, lon, depth_m) not found")
                return False
                
        except Exception as e:
            print(f"Error loading sonar data: {e}")
            return False
    
    def _calculate_bounds(self):
        """Calculate the geographical bounds of the data"""
        if not self.depth_points:
            return
            
        lons, lats, depths = zip(*self.depth_points)
        self.bounds = {
            'min_lon': min(lons),
            'max_lon': max(lons),
            'min_lat': min(lats), 
            'max_lat': max(lats),
            'min_depth': min(depths),
            'max_depth': max(depths)
        }
        
        print(f"Map bounds: {self.bounds}")
    
    def create_contour_map(self, contour_interval: float = 1.0) -> Dict:
        """
        Create contour map similar to ReefMaster
        Returns matplotlib figure and contour data
        """
        if not self.depth_points:
            raise ValueError("No depth data loaded")
        
        # Extract coordinates and depths
        lons, lats, depths = zip(*self.depth_points)
        
        # Create grid for interpolation
        lon_range = self.bounds['max_lon'] - self.bounds['min_lon']
        lat_range = self.bounds['max_lat'] - self.bounds['min_lat']
        
        grid_lon = np.linspace(self.bounds['min_lon'], self.bounds['max_lon'], self.grid_resolution)
        grid_lat = np.linspace(self.bounds['min_lat'], self.bounds['max_lat'], self.grid_resolution)
        grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
        
        # Interpolate depths onto regular grid
        try:
            grid_depths = griddata(
                (lons, lats), depths,
                (grid_lon_mesh, grid_lat_mesh),
                method='linear',
                fill_value=np.nan
            )
            
            # Create contour levels
            depth_range = self.bounds['max_depth'] - self.bounds['min_depth']
            num_contours = max(5, int(depth_range / contour_interval))
            contour_levels = np.linspace(
                self.bounds['min_depth'], 
                self.bounds['max_depth'], 
                num_contours
            )
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Fill contours for better visualization
            contour_filled = ax.contourf(
                grid_lon_mesh, grid_lat_mesh, grid_depths,
                levels=contour_levels,
                cmap='viridis_r',  # Deeper = darker (like ReefMaster)
                alpha=0.8
            )
            
            # Add contour lines
            contour_lines = ax.contour(
                grid_lon_mesh, grid_lat_mesh, grid_depths,
                levels=contour_levels,
                colors='white',
                linewidths=0.5,
                alpha=0.7
            )
            
            # Add labels to contour lines
            ax.clabel(contour_lines, inline=True, fontsize=8, fmt='%.1fm')
            
            # Add colorbar
            cbar = plt.colorbar(contour_filled, ax=ax, shrink=0.8)
            cbar.set_label('Depth (m)', rotation=270, labelpad=20)
            
            # Formatting
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_title(f'Bathymetric Map (Contour Interval: {contour_interval}m)')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            plt.tight_layout()
            
            return {
                'figure': fig,
                'contour_data': {
                    'levels': contour_levels,
                    'grid_lon': grid_lon_mesh,
                    'grid_lat': grid_lat_mesh,
                    'depths': grid_depths
                },
                'bounds': self.bounds,
                'point_count': len(self.depth_points)
            }
            
        except Exception as e:
            raise ValueError(f"Failed to create contour map: {e}")
    
    def create_3d_surface(self) -> Dict:
        """
        Create 3D surface plot similar to ReefMaster's 3D view
        """
        if not self.depth_points:
            raise ValueError("No depth data loaded")
        
        # Extract coordinates and depths
        lons, lats, depths = zip(*self.depth_points)
        
        # Create grid
        grid_lon = np.linspace(self.bounds['min_lon'], self.bounds['max_lon'], self.grid_resolution)
        grid_lat = np.linspace(self.bounds['min_lat'], self.bounds['max_lat'], self.grid_resolution)
        grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
        
        # Interpolate depths
        grid_depths = griddata(
            (lons, lats), depths,
            (grid_lon_mesh, grid_lat_mesh),
            method='linear',
            fill_value=np.nan
        )
        
        # Create 3D plot
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Invert depths for underwater appearance
        surface = ax.plot_surface(
            grid_lon_mesh, grid_lat_mesh, -grid_depths,  # Negative for underwater
            cmap='viridis_r',
            alpha=0.9,
            linewidth=0,
            antialiased=True
        )
        
        # Formatting
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_zlabel('Depth (m, inverted)')
        ax.set_title('3D Bathymetric Surface')
        
        # Add colorbar
        fig.colorbar(surface, ax=ax, shrink=0.8, label='Depth (m)')
        
        return {
            'figure': fig,
            'surface_data': {
                'grid_lon': grid_lon_mesh,
                'grid_lat': grid_lat_mesh,
                'depths': grid_depths
            },
            'bounds': self.bounds
        }
    
    def export_kml(self, output_path: str, contour_interval: float = 1.0) -> bool:
        """
        Export bathymetric data to Google Earth KML format
        Competes with ReefMaster's KML export
        """
        try:
            from simplekml import Kml, Style
            
            if not self.depth_points:
                raise ValueError("No depth data loaded")
            
            kml = Kml()
            kml.document.name = "Bathymetric Map"
            kml.document.description = f"Generated by Universal Sonar Parser\nContour Interval: {contour_interval}m"
            
            # Create depth point placemarks
            depth_folder = kml.newfolder(name="Depth Points")
            
            for i, (lon, lat, depth) in enumerate(self.depth_points[:1000]):  # Limit for performance
                point = depth_folder.newpoint(name=f"Depth: {depth:.1f}m")
                point.coords = [(lon, lat)]
                point.description = f"Depth: {depth:.1f}m\nLat: {lat:.6f}\nLon: {lon:.6f}"
                
                # Color-code by depth
                style = Style()
                if depth < 5:
                    style.iconstyle.color = 'ff00ff00'  # Green - shallow
                elif depth < 20:
                    style.iconstyle.color = 'ff00ffff'  # Yellow - medium
                else:
                    style.iconstyle.color = 'ff0000ff'  # Red - deep
                    
                point.style = style
            
            # Save KML
            kml.save(output_path)
            print(f"KML exported to: {output_path}")
            return True
            
        except ImportError:
            print("simplekml not installed. Run: pip install simplekml")
            return False
        except Exception as e:
            print(f"KML export failed: {e}")
            return False
    
    def export_shapefile(self, output_path: str) -> bool:
        """
        Export bathymetric data to ESRI Shapefile format
        Professional GIS compatibility like ReefMaster
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Point
            
            if not self.depth_points:
                raise ValueError("No depth data loaded")
            
            # Create GeoDataFrame
            geometry = [Point(lon, lat) for lon, lat, depth in self.depth_points]
            depths = [depth for lon, lat, depth in self.depth_points]
            
            gdf = gpd.GeoDataFrame({
                'depth_m': depths,
                'geometry': geometry
            }, crs='EPSG:4326')  # WGS84
            
            # Save shapefile
            gdf.to_file(output_path)
            print(f"Shapefile exported to: {output_path}")
            return True
            
        except ImportError:
            print("geopandas not installed. Run: pip install geopandas")
            return False
        except Exception as e:
            print(f"Shapefile export failed: {e}")
            return False

def test_bathymetric_mapping():
    """
    Test the bathymetric mapping with our parsed sonar data
    """
    mapper = BathymetricMapper()
    
    # Look for parsed CSV files
    csv_files = list(Path('.').glob('*_records.csv'))
    if not csv_files:
        print("No parsed CSV files found. Run the sonar parser first.")
        return
    
    print(f"Found {len(csv_files)} CSV files to process")
    
    for csv_file in csv_files[:1]:  # Test with first file
        print(f"\nProcessing: {csv_file}")
        
        if mapper.load_sonar_data(str(csv_file)):
            try:
                # Create contour map
                print("Creating contour map...")
                contour_result = mapper.create_contour_map(contour_interval=1.0)
                contour_result['figure'].savefig(f'{csv_file.stem}_contour_map.png', dpi=300, bbox_inches='tight')
                print(f"Contour map saved: {csv_file.stem}_contour_map.png")
                
                # Create 3D surface
                print("Creating 3D surface...")
                surface_result = mapper.create_3d_surface()
                surface_result['figure'].savefig(f'{csv_file.stem}_3d_surface.png', dpi=300, bbox_inches='tight')
                print(f"3D surface saved: {csv_file.stem}_3d_surface.png")
                
                # Export KML
                print("Exporting KML...")
                mapper.export_kml(f'{csv_file.stem}_bathymetric.kml')
                
                # Export Shapefile
                print("Exporting Shapefile...")
                mapper.export_shapefile(f'{csv_file.stem}_bathymetric.shp')
                
                print(f"✅ Bathymetric mapping completed for {csv_file}")
                
            except Exception as e:
                print(f"❌ Error processing {csv_file}: {e}")
        else:
            print(f"❌ Failed to load data from {csv_file}")

if __name__ == "__main__":
    print("🗺️ Universal Sonar Bathymetric Mapper")
    print("Direct ReefMaster competitor with superior format support")
    print("="*60)
    
    test_bathymetric_mapping()