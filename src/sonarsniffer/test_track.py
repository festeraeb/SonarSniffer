#!/usr/bin/env python3
"""
Test the track coordinates and see if they're reasonable
"""

from engine_classic_varstruct import parse_rsd

# Parse more records to see the track
csv_out = parse_rsd("126SV-UHD2-GT54.RSD", "full_track_test.csv", limit_rows=200)

# Analyze the coordinates
import csv

coords = []
with open(csv_out, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if float(row['lat']) != 0 and float(row['lon']) != 0:
            coords.append((float(row['lat']), float(row['lon']), float(row['depth_m'])))

if coords:
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    depths = [c[2] for c in coords]
    
    print(f"Found {len(coords)} valid coordinate records")
    print(f"Latitude range: {min(lats):.6f} to {max(lats):.6f}")
    print(f"Longitude range: {min(lons):.6f} to {max(lons):.6f}")
    print(f"Depth range: {min(depths):.3f}m to {max(depths):.3f}m")
    
    # Calculate bounding box center
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    print(f"Track center: {center_lat:.6f}, {center_lon:.6f}")
    
    # Show some sample coordinates
    print("\nSample coordinates:")
    for i in range(min(10, len(coords))):
        lat, lon, depth = coords[i]
        print(f"  {i+1}: {lat:.6f}, {lon:.6f}, depth={depth:.1f}m")
else:
    print("No valid coordinates found")