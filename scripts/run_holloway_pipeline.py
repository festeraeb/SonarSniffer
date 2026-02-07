#!/usr/bin/env python3
"""Run a conservative end-to-end pipeline on data/Holloway.RSD with resource limits.

Behavior:
- Samples every Nth scan (sample_stride)
- Caps number of rows (max_rows)
- Generates waterfall PNG, tiles (max_zoom=2), MBTiles, KMZ, GeoTIFF fallback, mosaic
"""
import os
import time
from pathlib import Path
import sys
# Ensure local package imports work when running the script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sonarsniffer.sonar_parser import SonarParser
from sonarsniffer.pipeline import (
    scans_to_waterfall_image,
    scans_to_tiles,
    tiles_to_mbtiles,
    generate_superoverlay_kmz,
    scans_to_geotiff,
    create_mosaic_from_images,
    scans_to_video,
)

SOURCE = os.environ.get('HOLLOWAY_SOURCE', 'data/Holloway.RSD')
OUT_ROOT = os.environ.get('HOLLOWAY_OUT', 'outputs/holloway_run')
SAMPLE_STRIDE = int(os.environ.get('HOLLOWAY_SAMPLE_STRIDE', '10'))
MAX_ROWS = int(os.environ.get('HOLLOWAY_MAX_ROWS', '2000'))
TILE_MAX_ZOOM = int(os.environ.get('HOLLOWAY_TILE_MAX_ZOOM', '2'))
# Optional color mapping for waterfall/video: 'amber' or 'grayscale'
COLOR = os.environ.get("HOLLOWAY_COLOR", "amber")
# Optional flag to enable/disable MP4 generation: '1'/'true' enable, '0'/'false' disable
VIDEO = os.environ.get("HOLLOWAY_VIDEO", "1")
# Tune video parameters and channel gap via env vars
VIDEO_HEIGHT = int(os.environ.get("HOLLOWAY_VIDEO_HEIGHT", "256"))
VIDEO_FPS = int(os.environ.get("HOLLOWAY_VIDEO_FPS", "5"))
SCANS_PER_FRAME = int(os.environ.get("HOLLOWAY_SCANS_PER_FRAME", "1"))
CHANNEL_GAP = int(os.environ.get("HOLLOWAY_CHANNEL_GAP", "16"))
PAIRING_DEBUG = str(os.environ.get("HOLLOWAY_PAIRING_DEBUG", "0")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
ALIGNMENT_MODE = os.environ.get("HOLLOWAY_ALIGNMENT_MODE", "auto")
# New preprocessing options
BEAM_GAIN = str(os.environ.get("HOLLOWAY_BEAM_GAIN", "0")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
NADIR_MASK = int(os.environ.get("HOLLOWAY_NADIR_MASK", "0"))
# Generation flags
GEN_WF = str(os.environ.get("HOLLOWAY_GEN_WATERFALL", "1")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
GEN_MP4 = str(os.environ.get("HOLLOWAY_GEN_MP4", "1")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
GEN_KMZ = str(os.environ.get("HOLLOWAY_GEN_KMZ", "1")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
GEN_MBTILES = str(os.environ.get("HOLLOWAY_GEN_MBTILES", "1")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)
GEN_TIFF = str(os.environ.get("HOLLOWAY_GEN_TIFF", "1")).lower() in (
    "1",
    "true",
    "yes",
    "y",
)

os.makedirs(OUT_ROOT, exist_ok=True)
start = time.time()
parser = SonarParser()

print('Opening', SOURCE)
rows = []
count = 0
min_lat =  90.0
max_lat = -90.0
min_lon = 180.0
max_lon = -180.0

# Ensure adapters are loaded so canonical.to_scan finds the right adapter
try:
    import sonarsniffer.adapters.rsd_adapter
except Exception:
    pass

# Use chunked parsing and convert parsed records to canonical Scan objects via adapter
for batch in parser.parse_file_in_chunks(SOURCE, batch_size=200):
    for r in batch:
        # Use a running count so sampling stride is consistent across batches
        count += 1
        if (count - 1) % SAMPLE_STRIDE != 0:
            continue
        # Convert record to Scan using RSD adapter if available, otherwise build minimal object
        try:
            from sonarsniffer.canonical import to_scan
            rec = r
            # When parse_file_in_chunks returns dicts, convert to a namespace with attributes
            if isinstance(r, dict):
                from types import SimpleNamespace

                # Ensure keys exist that adapter expects
                safe = {
                    'ofs': r.get('ofs', 0),
                    'channel_id': r.get('channel_id', 0),
                    'seq': r.get('seq', 0),
                    'time_ms': r.get('time_ms', 0),
                    'lat': r.get('lat', 0.0) or 0.0,
                    'lon': r.get('lon', 0.0) or 0.0,
                    'depth_m': r.get('depth_m', 0.0) or 0.0,
                    'sample_cnt': r.get('sample_cnt', 0) or 0,
                    'sonar_ofs': r.get('sonar_ofs', 0) or 0,
                    'sonar_size': r.get('sonar_size', 0) or 0,
                    'beam_deg': r.get('beam_deg', 0.0) or 0.0,
                    'extras': r.get('extras', {}),
                }
                rec = SimpleNamespace(**safe)
            scan = to_scan('rsd', rec, SOURCE)
        except Exception:
            # Fallback: minimal object with lat, lon and samples attributes
            class _Minimal:
                pass

            scan = _Minimal()
            if isinstance(r, dict):
                scan.lat = r.get('lat', 0.0) or 0.0
                scan.lon = r.get('lon', 0.0) or 0.0
                scan.samples = None
            else:
                scan.lat = getattr(r, 'lat', 0.0) or 0.0
                scan.lon = getattr(r, 'lon', 0.0) or 0.0
                scan.samples = None
        # Keep only scans that have actual sonar samples so the waterfall can be built
        if getattr(scan, 'samples', None) is None:
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
    if len(rows) >= MAX_ROWS:
        break

print(f'Collected {len(rows)} sampled scans from {count} total records (stride={SAMPLE_STRIDE})')
if min_lat <= max_lat and min_lon <= max_lon:
    bounds = (min_lat, max_lat, min_lon, max_lon)
else:
    bounds = (0.0, 0.0, 0.0, 0.0)

wf = os.path.join(OUT_ROOT, 'Holloway_waterfall.png')
if GEN_WF:
    print("Generating waterfall", wf)
    scans_to_waterfall_image(
        rows,
        wf,
        width=None,
        color=COLOR,
        channel_gap=CHANNEL_GAP,
        pairing_debug=PAIRING_DEBUG,
        alignment_mode=ALIGNMENT_MODE,
        debug_out=OUT_ROOT,
        beam_gain=BEAM_GAIN,
        nadir_mask=NADIR_MASK,
    )
else:
    print("Skipping waterfall (GEN_WF disabled)")

# Tiles/MBTiles (optional depending on generation flags)
if GEN_MBTILES or GEN_KMZ:
    print("Generating tiles (max_zoom=", TILE_MAX_ZOOM, ")")
    tiles_dir = os.path.join(OUT_ROOT, "tiles")
    scans_to_tiles(wf, tiles_dir, tile_size=256, max_zoom=TILE_MAX_ZOOM)
else:
    tiles_dir = os.path.join(OUT_ROOT, "tiles")
    print("Skipping tiles (GEN_MBTILES and GEN_KMZ disabled)")

if GEN_MBTILES:
    print("Packaging MBTiles")
    mb = os.path.join(OUT_ROOT, "Holloway.mbtiles")
    tiles_to_mbtiles(tiles_dir, mb, metadata={"name": "Holloway"})
else:
    print("Skipping MBTiles (GEN_MBTILES disabled)")

if GEN_KMZ:
    print("Generating KMZ super-overlay")
    kmz = os.path.join(OUT_ROOT, "Holloway.kmz")
    generate_superoverlay_kmz(
        wf, tiles_dir, bounds, kmz, tile_size=256, max_zoom=TILE_MAX_ZOOM
    )
else:
    print("Skipping KMZ (GEN_KMZ disabled)")

if GEN_TIFF:
    print("Generating GeoTIFF or fallback")
    gt = os.path.join(OUT_ROOT, "Holloway.tif")
    res = scans_to_geotiff(wf, gt, rows)
    print("GeoTIFF produced:", res)
else:
    print("Skipping GeoTIFF (GEN_TIFF disabled)")
print('Creating mosaic from PNGs in output dir')
pngs = [os.path.join(OUT_ROOT, f) for f in os.listdir(OUT_ROOT) if f.lower().endswith('.png')]
if pngs:
    mosaic = os.path.join(OUT_ROOT, 'Holloway_mosaic.png')
    create_mosaic_from_images(pngs, mosaic, mode='average')
    print('Mosaic saved to', mosaic)

# Also produce an MP4 video of the scans (amber color by default for better contrast)
if GEN_MP4 and str(VIDEO).lower() not in ("0", "false", "no", "n"):
    try:
        mp4 = os.path.join(OUT_ROOT, Path(SOURCE).stem + ".mp4")
        print("Generating MP4 video", mp4)
        scans_to_video(
            rows,
            mp4,
            fps=VIDEO_FPS,
            color=COLOR,
            height=VIDEO_HEIGHT,
            scans_per_frame=SCANS_PER_FRAME,
            channel_gap=CHANNEL_GAP,
            pairing_debug=PAIRING_DEBUG,
            alignment_mode=ALIGNMENT_MODE,
            debug_out=OUT_ROOT,
            beam_gain=BEAM_GAIN,
            nadir_mask=NADIR_MASK,
        )
        print("MP4 saved to", mp4)
    except Exception as e:
        print("MP4 generation failed:", e)
else:
    print("Skipping MP4 generation (GEN_MP4 disabled or HOLLOWAY_VIDEO disabled)")

print('Finished in', time.time() - start, 'seconds')
print('Outputs in', os.path.abspath(OUT_ROOT))
