#!/usr/bin/env python3
"""Run a conservative pipeline on a small sample file to validate exporters.
"""
import os
import time
from pathlib import Path
from sonarsniffer.sonar_parser import SonarParser
from sonarsniffer.pipeline import (
    scans_to_waterfall_image,
    scans_to_tiles,
    tiles_to_mbtiles,
    generate_superoverlay_kmz,
    scans_to_geotiff,
    create_mosaic_from_images,
)

SRC = os.environ.get('SAMPLE_SOURCE', 'samples/B001.SON')
OUT_ROOT = os.environ.get('SAMPLE_OUT', 'outputs/sample_run')
SAMPLE_STRIDE = int(os.environ.get('SAMPLE_STRIDE', '1'))
MAX_ROWS = int(os.environ.get('SAMPLE_MAX_ROWS', '200'))
TILE_MAX_ZOOM = int(os.environ.get('SAMPLE_TILE_MAX_ZOOM', '2'))

os.makedirs(OUT_ROOT, exist_ok=True)
start = time.time()
parser = SonarParser()

print('Opening', SRC)
scans_iter = parser.iter_scans(SRC, batch_size=200)
rows = []
count = 0
min_lat =  90.0
max_lat = -90.0
min_lon = 180.0
max_lon = -180.0

for i, scan in enumerate(scans_iter):
    count += 1
    if i % SAMPLE_STRIDE != 0:
        continue
    rows.append(scan)
    if scan.lat:
        min_lat = min(min_lat, scan.lat)
        max_lat = max(max_lat, scan.lat)
    if scan.lon:
        min_lon = min(min_lon, scan.lon)
        max_lon = max(max_lon, scan.lon)
    if len(rows) >= MAX_ROWS:
        break

print(f'Collected {len(rows)} sampled scans from {count} total records (stride={SAMPLE_STRIDE})')
if min_lat <= max_lat and min_lon <= max_lon:
    bounds = (min_lat, max_lat, min_lon, max_lon)
else:
    bounds = (0.0, 0.0, 0.0, 0.0)

wf = os.path.join(OUT_ROOT, 'sample_waterfall.png')
print('Generating waterfall', wf)
scans_to_waterfall_image(rows, wf, width=None)

print('Generating tiles (max_zoom=', TILE_MAX_ZOOM, ')')
tiles_dir = os.path.join(OUT_ROOT, 'tiles')
scans_to_tiles(wf, tiles_dir, tile_size=128, max_zoom=TILE_MAX_ZOOM)

print('Packaging MBTiles')
mb = os.path.join(OUT_ROOT, 'sample.mbtiles')
tiles_to_mbtiles(tiles_dir, mb, metadata={'name': 'sample'})

print('Generating KMZ super-overlay')
kmz = os.path.join(OUT_ROOT, 'sample.kmz')
generate_superoverlay_kmz(wf, tiles_dir, bounds, kmz, tile_size=128, max_zoom=TILE_MAX_ZOOM)

print('Generating GeoTIFF or fallback')
gt = os.path.join(OUT_ROOT, 'sample.tif')
res = scans_to_geotiff(wf, gt, rows)
print('GeoTIFF produced:', res)

print('Creating mosaic from PNGs in output dir')
pngs = [os.path.join(OUT_ROOT, f) for f in os.listdir(OUT_ROOT) if f.lower().endswith('.png')]
if pngs:
    mosaic = os.path.join(OUT_ROOT, 'sample_mosaic.png')
    create_mosaic_from_images(pngs, mosaic, mode='average')
    print('Mosaic saved to', mosaic)

print('Finished in', time.time() - start, 'seconds')
print('Outputs in', os.path.abspath(OUT_ROOT))
