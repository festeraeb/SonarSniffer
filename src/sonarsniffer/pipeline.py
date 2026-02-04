#!/usr/bin/env python3
"""High-level pipeline to export waterfall, video, KML, and other artifacts
from a sonar file using canonical Scan objects.
"""
from typing import Iterable, List
import os
from pathlib import Path
import numpy as np
from .sonar_parser import SonarParser
# rsd_video_core may live at package level (src/rsd_video_core.py) or inside package
try:
    from .rsd_video_core import generate_sidescan_waterfall
except Exception:
    try:
        from rsd_video_core import generate_sidescan_waterfall
    except Exception:
        raise
# Encoder bridge (ffmpeg) may also be top-level. We also support a gstreamer-based encoder binary.
VIDEO_ENCODER = os.environ.get('VIDEO_ENCODER', '').lower()
encode_frames_to_mp4 = None
if VIDEO_ENCODER == 'gstreamer':
    try:
        from .gstreamer_bridge import encode_frames_with_fallback as encode_frames_to_mp4  # type: ignore
    except Exception:
        try:
            from gstreamer_bridge import encode_frames_with_fallback as encode_frames_to_mp4  # type: ignore
        except Exception:
            encode_frames_to_mp4 = None
# If not configured, fall back to python_cuda_bridge (ffmpeg-based)
if encode_frames_to_mp4 is None:
    try:
        from .python_cuda_bridge import encode_frames_to_mp4  # type: ignore
    except Exception:
        try:
            from python_cuda_bridge import encode_frames_to_mp4  # type: ignore
        except Exception:
            encode_frames_to_mp4 = None

from .canonical import Scan
from PIL import Image


def scans_to_waterfall_image(scans: Iterable[Scan], output_path: str, width: int = None):
    """Build a vertical waterfall image from Scan objects and save PNG."""
    rows = []
    max_width = 0
    for s in scans:
        if s.samples is None:
            continue
        arr = np.asarray(s.samples, dtype=np.float32)
        # Normalize sample length if needed
        if width is not None:
            # Resample or truncate/pad
            if arr.size < width:
                pad = np.zeros(width - arr.size, dtype=arr.dtype)
                arr = np.concatenate([arr, pad])
            elif arr.size > width:
                arr = arr[:width]
        max_width = max(max_width, arr.size)
        rows.append(arr)

    if not rows:
        raise RuntimeError("No valid scan samples to build waterfall")

    # If width not provided, use max_width and pad rows
    W = width or max_width
    H = len(rows)
    flat = np.zeros(W * H, dtype=np.float32)
    for i, r in enumerate(rows):
        if r.size < W:
            r2 = np.resize(r, W)
        else:
            r2 = r[:W]
        flat[i * W : (i + 1) * W] = r2

    img8 = np.asarray(generate_sidescan_waterfall(flat.tolist(), W, H), dtype=np.uint8).reshape((H, W))
    im = Image.fromarray(img8, mode='L')
    im.save(output_path)
    return output_path


def scans_to_video(scans: Iterable[Scan], output_path: str, fps: int = 10, width: int = None):
    # Build frames as RGB by stretching grayscale into 3 channels
    frames = []
    for s in scans:
        if s.samples is None:
            continue
        arr = np.asarray(s.samples, dtype=np.float32)
        if width is not None:
            if arr.size < width:
                pad = np.zeros(width - arr.size, dtype=arr.dtype)
                arr = np.concatenate([arr, pad])
            elif arr.size > width:
                arr = arr[:width]
        # Create 2D image one-ping tall for consistency then resize to small HxW
        H = 64
        W = width or arr.size
        img8 = np.asarray(generate_sidescan_waterfall(arr.tolist(), W, 1), dtype=np.uint8).reshape((1, W))
        # Upsample vertically to H
        frame = np.repeat(img8, H, axis=0)
        frame_rgb = np.stack([frame, frame, frame], axis=-1)
        frames.append(frame_rgb)

    # Use ffmpeg encoder
    return encode_frames_to_mp4(iter(frames), output_path, fps=fps)


def export_full(input_path: str, out_dir: str, formats: List[str] = None, batch_size: int = 1000):
    p = SonarParser()
    formats = formats or ['waterfall']
    os.makedirs(out_dir, exist_ok=True)
    scans = list(p.iter_scans(input_path, batch_size=batch_size))

    results = {}
    if 'waterfall' in formats:
        out = os.path.join(out_dir, Path(input_path).stem + '_waterfall.png')
        scans_to_waterfall_image(scans, out)
        results['waterfall'] = out
    if 'mp4' in formats:
        out = os.path.join(out_dir, Path(input_path).stem + '.mp4')
        scans_to_video(scans, out)
        results['mp4'] = out

    # KML exporter: generate simple KML linking to the waterfall PNG
    if 'kml' in formats:
        from typing import Tuple

        def _compute_bounds(scans) -> Tuple[float, float, float, float]:
            min_lat = 90.0
            max_lat = -90.0
            min_lon = 180.0
            max_lon = -180.0
            for s in scans:
                if s.lat and s.lon:
                    min_lat = min(min_lat, s.lat)
                    max_lat = max(max_lat, s.lat)
                    min_lon = min(min_lon, s.lon)
                    max_lon = max(max_lon, s.lon)
            if min_lat > max_lat:
                # No valid coords
                return (0.0, 0.0, 0.0, 0.0)
            return (min_lat, max_lat, min_lon, max_lon)

        out_png = results.get('waterfall')
        if out_png:
            bounds = _compute_bounds(scans)
            out_kml = os.path.join(out_dir, Path(input_path).stem + '.kml')
            scans_to_kml(out_png, bounds, out_kml)
            results['kml'] = out_kml

    # GeoTIFF exporter: create simple georeferenced image and worldfile fallback
    if 'geotiff' in formats:
        out_png = results.get('waterfall')
        if out_png:
            out_tiff = os.path.join(out_dir, Path(input_path).stem + '.tif')
            scans_to_geotiff(out_png, out_tiff, scans)
            results['geotiff'] = out_tiff

    if 'tiles' in formats:
        out_png = results.get('waterfall')
        if out_png:
            tiles_dir = os.path.join(out_dir, Path(input_path).stem + '_tiles')
            scans_to_tiles(out_png, tiles_dir, tile_size=256, max_zoom=4)
            results['tiles'] = tiles_dir

    if 'mosaic' in formats:
        # Simple mosaic: build from waterfall and any pngs in out_dir
        imgs = []
        for f in os.listdir(out_dir):
            if f.lower().endswith('.png'):
                imgs.append(os.path.join(out_dir, f))
        if imgs:
            out_mosaic = os.path.join(out_dir, Path(input_path).stem + '_mosaic.png')
            create_mosaic_from_images(imgs, out_mosaic, mode='average')
            results['mosaic'] = out_mosaic

    # MBTiles export: pack tiles into an MBTiles SQLite database (v1 schema)
    if 'mbtiles' in formats:
        tiles_dir = results.get('tiles')
        if tiles_dir:
            mb_path = os.path.join(out_dir, Path(input_path).stem + '.mbtiles')
            tiles_to_mbtiles(tiles_dir, mb_path, metadata={"name": Path(input_path).stem, "format": "png"})
            results['mbtiles'] = mb_path

    # KMZ (super-overlay) export: create KMZ containing tiles and KML overlays
    if 'kmz' in formats:
        out_png = results.get('waterfall')
        tiles_dir = results.get('tiles')
        if out_png and tiles_dir:
            bounds = None
            # Compute bounds from scans if available
            try:
                min_lat = min((s.lat for s in scans if s.lat), default=0.0)
                max_lat = max((s.lat for s in scans if s.lat), default=0.0)
                min_lon = min((s.lon for s in scans if s.lon), default=0.0)
                max_lon = max((s.lon for s in scans if s.lon), default=0.0)
                if min_lat <= max_lat and min_lon <= max_lon:
                    bounds = (min_lat, max_lat, min_lon, max_lon)
            except Exception:
                bounds = None

            if bounds:
                out_kmz = os.path.join(out_dir, Path(input_path).stem + '.kmz')
                generate_superoverlay_kmz(out_png, tiles_dir, bounds, out_kmz)
                results['kmz'] = out_kmz

    return results


def scans_to_kml(waterfall_png_path: str, bounds: tuple, output_kml_path: str):
    """Generate a minimal KML with GroundOverlay referencing the waterfall PNG.

    bounds: (min_lat, max_lat, min_lon, max_lon)
    """
    min_lat, max_lat, min_lon, max_lon = bounds
    name = Path(waterfall_png_path).stem
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <GroundOverlay>
      <name>{name} waterfall</name>
      <Icon>
        <href>{Path(waterfall_png_path).name}</href>
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
    # Write alongside the image so relative link works
    out_dir = os.path.dirname(output_kml_path)
    os.makedirs(out_dir, exist_ok=True)
    # Copy PNG to output dir if needed
    import shutil
    dst_png = os.path.join(out_dir, Path(waterfall_png_path).name)
    if os.path.abspath(waterfall_png_path) != os.path.abspath(dst_png):
        try:
            shutil.copy(waterfall_png_path, dst_png)
        except Exception:
            pass
    with open(output_kml_path, 'w', encoding='utf-8') as fh:
        fh.write(kml)
    return output_kml_path


def scans_to_geotiff(waterfall_png_path: str, out_tiff_path: str, scans: List[Scan]):
    """Attempt to write a GeoTIFF; fallback to PNG+worldfile (TFW) if rasterio not available.

    Note: This is a lightweight fallback that writes a TFW with approximate values when
    precise georeferencing is not available.
    """
    try:
        import rasterio
        from rasterio.transform import from_origin
        img = Image.open(waterfall_png_path)
        arr = np.array(img)
        # Compute simple transform using scan bounds
        min_lat = min((s.lat for s in scans if s.lat), default=0.0)
        max_lat = max((s.lat for s in scans if s.lat), default=0.0)
        min_lon = min((s.lon for s in scans if s.lon), default=0.0)
        max_lon = max((s.lon for s in scans if s.lon), default=0.0)
        if min_lat == max_lat or min_lon == max_lon:
            # fallback: set an arbitrary geotransform with pixel size 1
            transform = from_origin(0, 0, 1, 1)
        else:
            h, w = arr.shape[:2]
            xres = (max_lon - min_lon) / float(w)
            yres = (max_lat - min_lat) / float(h)
            transform = from_origin(min_lon, max_lat, xres, yres)
        # Write GeoTIFF (single band if grayscale; else write RGB)
        if arr.ndim == 2:
            count = 1
            dtype = arr.dtype
            with rasterio.open(out_tiff_path, 'w', driver='GTiff', height=arr.shape[0], width=arr.shape[1], count=1, dtype=dtype, transform=transform, crs='EPSG:4326') as dst:
                dst.write(arr, 1)
        else:
            # RGB
            count = 3
            dtype = arr.dtype
            with rasterio.open(out_tiff_path, 'w', driver='GTiff', height=arr.shape[0], width=arr.shape[1], count=3, dtype=dtype, transform=transform, crs='EPSG:4326') as dst:
                for i in range(3):
                    dst.write(arr[:, :, i], i + 1)
        return out_tiff_path
    except Exception:
        # Fallback: write PNG copy and a simplistic TFW (worldfile)
        img = Image.open(waterfall_png_path)
        out_png = str(Path(out_tiff_path).with_suffix('.png'))
        img.save(out_png)
        # Approximate georef values
        min_lat = min((s.lat for s in scans if s.lat), default=0.0)
        max_lat = max((s.lat for s in scans if s.lat), default=0.0)
        min_lon = min((s.lon for s in scans if s.lon), default=0.0)
        max_lon = max((s.lon for s in scans if s.lon), default=0.0)
        h, w = img.size[1], img.size[0]
        if w == 0 or h == 0:
            px_x = 1.0
            px_y = 1.0
        else:
            px_x = (max_lon - min_lon) / float(w) if max_lon != min_lon else 1.0
            px_y = (max_lat - min_lat) / float(h) if max_lat != min_lat else 1.0
        # World file: A D B E C F where A = pixel size in x, E = -pixel size in y
        tfw = f"{px_x}\n0.0\n0.0\n{-px_y}\n{min_lon}\n{max_lat}\n"
        with open(str(Path(out_tiff_path).with_suffix('.tfw')), 'w', encoding='utf-8') as fh:
            fh.write(tfw)
        # Write a simple meta file describing provenance
        with open(str(Path(out_tiff_path).with_suffix('.meta')), 'w', encoding='utf-8') as fh:
            fh.write(f"source_image={out_png}\nmin_lat={min_lat}\nmax_lat={max_lat}\nmin_lon={min_lon}\nmax_lon={max_lon}\n")
        return out_png


def scans_to_tiles(waterfall_png_path: str, out_tiles_dir: str, tile_size: int = 256, max_zoom: int = 4):
    """Generate simple tile pyramid (z/x/y.png) from an image.

    This is a lightweight super-overlay style generator (not Google-specific),
    producing tiles for zoom levels 0..max_zoom where 0 is lowest resolution.
    """
    os.makedirs(out_tiles_dir, exist_ok=True)
    img = Image.open(waterfall_png_path).convert('RGBA')
    w, h = img.size

    for z in range(0, max_zoom + 1):
        scale = 2 ** (max_zoom - z)
        # Downscale source to level z resolution
        target_w = max(1, w // scale)
        target_h = max(1, h // scale)
        resized = img.resize((target_w, target_h), resample=Image.LANCZOS)
        cols = (target_w + tile_size - 1) // tile_size
        rows = (target_h + tile_size - 1) // tile_size
        for x in range(cols):
            for y in range(rows):
                left = x * tile_size
                upper = y * tile_size
                right = min(left + tile_size, target_w)
                lower = min(upper + tile_size, target_h)
                tile = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
                region = resized.crop((left, upper, right, lower))
                tile.paste(region, (0, 0))
                tile_dir = os.path.join(out_tiles_dir, str(z), str(x))
                os.makedirs(tile_dir, exist_ok=True)
                tile_path = os.path.join(tile_dir, f"{y}.png")
                tile.save(tile_path)
    return out_tiles_dir


def create_mosaic_from_images(image_paths: List[str], output_path: str, mode: str = 'average'):
    """Create a simple mosaic by overlaying images. Mode can be 'average' or 'max'."""
    imgs = [Image.open(p).convert('RGBA') for p in image_paths]
    if not imgs:
        raise RuntimeError('No images provided')
    # Determine max canvas size
    max_w = max(im.size[0] for im in imgs)
    max_h = max(im.size[1] for im in imgs)
    canvas = Image.new('RGBA', (max_w, max_h), (0, 0, 0, 0))
    if mode == 'max':
        # For each pixel take max value across images
        import numpy as np
        arrs = [np.array(im, dtype=np.uint8) for im in imgs]
        stacked = np.maximum.reduce(arrs)
        out = Image.fromarray(stacked.astype(np.uint8))
        out.save(output_path)
        return output_path
    else:
        # Average overlay
        import numpy as np
        acc = np.zeros((max_h, max_w, 4), dtype=np.float32)
        count = np.zeros((max_h, max_w, 1), dtype=np.float32)
        for im in imgs:
            arr = np.array(im, dtype=np.float32)
            h, w = im.size[1], im.size[0]
            acc[:h, :w, :] += arr
            count[:h, :w, 0] += (arr[:, :, 3] > 0).astype(np.float32)
        # Avoid divide by zero
        count[count == 0] = 1.0
        avg = (acc / count)
        avg = np.clip(avg, 0, 255).astype(np.uint8)
        out = Image.fromarray(avg)
        out.save(output_path)
        return output_path


def tiles_to_mbtiles(tiles_dir: str, mbtiles_path: str, metadata: dict = None):
    """Create a simple MBTiles (v1) file from a tile directory structure z/x/y.png.

    This implementation writes tiles in PNG format and stores metadata in the metadata table.
    It streams tile files to sqlite without loading entire tile sets into memory.
    """
    import sqlite3
    metadata = metadata or {}
    # Remove existing file if present
    if os.path.exists(mbtiles_path):
        os.remove(mbtiles_path)
    conn = sqlite3.connect(mbtiles_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE metadata (name text, value text);')
    cur.execute('CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);')
    cur.execute('CREATE UNIQUE INDEX name ON metadata (name);')
    cur.execute('CREATE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);')
    # Insert metadata
    cur.executemany('INSERT INTO metadata (name,value) VALUES (?,?)', [(k, str(v)) for k, v in metadata.items()])
    conn.commit()
    # Walk tiles structure
    for z in os.listdir(tiles_dir):
        zdir = os.path.join(tiles_dir, z)
        if not os.path.isdir(zdir):
            continue
        zi = int(z)
        for x in os.listdir(zdir):
            xdir = os.path.join(zdir, x)
            if not os.path.isdir(xdir):
                continue
            xi = int(x)
            for yfn in os.listdir(xdir):
                if not yfn.lower().endswith('.png'):
                    continue
                yi = int(os.path.splitext(yfn)[0])
                tile_path = os.path.join(xdir, yfn)
                with open(tile_path, 'rb') as fh:
                    blob = fh.read()
                # MBTiles uses TMS tile scheme with flipped Y
                tms_y = (2 ** zi - 1) - yi
                cur.execute('INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?,?,?,?)', (zi, xi, tms_y, sqlite3.Binary(blob)))
        conn.commit()
    conn.close()
    return mbtiles_path


def generate_superoverlay_kmz(waterfall_png: str, tiles_dir: str, bounds: tuple, out_kmz_path: str, tile_size: int = 256, max_zoom: int = 4):
    """Create a KMZ (zip) containing KML GroundOverlays for tiles and the tiles themselves.

    bounds: (min_lat, max_lat, min_lon, max_lon)
    """
    import zipfile
    min_lat, max_lat, min_lon, max_lon = bounds
    out_dir = os.path.dirname(out_kmz_path)
    name = os.path.splitext(os.path.basename(out_kmz_path))[0]
    # Build doc.kml content incrementally and write into KMZ
    kmz_temp = out_kmz_path + '.tmp'
    with zipfile.ZipFile(kmz_temp, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Add tiles
        for root, dirs, files in os.walk(tiles_dir):
            for fn in files:
                if not fn.lower().endswith('.png'):
                    continue
                absf = os.path.join(root, fn)
                rel = os.path.relpath(absf, tiles_dir)
                zf.write(absf, arcname=os.path.join('tiles', rel))
        # Generate a KML with GroundOverlay entries for each tile at highest zoom (for simplicity)
        entries = []
        for z in range(max_zoom + 1):
            zdir = os.path.join(tiles_dir, str(z))
            if not os.path.isdir(zdir):
                continue
            # Determine scaled target size at this zoom level
            for x in os.listdir(zdir):
                xdir = os.path.join(zdir, x)
                if not os.path.isdir(xdir):
                    continue
                for yfn in os.listdir(xdir):
                    if not yfn.lower().endswith('.png'):
                        continue
                    y = int(os.path.splitext(yfn)[0])
                    xi = int(x)
                    # Compute bounds for this tile using linear mapping
                    # Determine number of tiles at this zoom
                    cols = sum(1 for _ in os.listdir(zdir))
                    # Estimate tile grid width/height by listing one column
                    anyx = next(iter(os.listdir(zdir)), None)
                    if anyx is None:
                        continue
                    rows = len(os.listdir(os.path.join(zdir, anyx)))
                    # Compute pixel fraction
                    left_frac = xi / cols
                    right_frac = (xi + 1) / cols
                    top_frac = y / rows
                    bottom_frac = (y + 1) / rows
                    west = min_lon + left_frac * (max_lon - min_lon)
                    east = min_lon + right_frac * (max_lon - min_lon)
                    # Pixel Y increases downward; map to lat accordingly
                    north = max_lat - top_frac * (max_lat - min_lat)
                    south = max_lat - bottom_frac * (max_lat - min_lat)
                    href = f"tiles/{z}/{xi}/{yfn}"
                    entries.append((href, north, south, east, west))
        # Build KML
        kml = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n  <Document>\n'
        for href, north, south, east, west in entries:
            kml += f'''    <GroundOverlay>\n      <Icon>\n        <href>{href}</href>\n      </Icon>\n      <LatLonBox>\n        <north>{north}</north>\n        <south>{south}</south>\n        <east>{east}</east>\n        <west>{west}</west>\n      </LatLonBox>\n    </GroundOverlay>\n'''
        kml += '  </Document>\n</kml>'
        # Write doc.kml at root of KMZ
        zf.writestr('doc.kml', kml)
    # Rename temp kmz to final
    os.replace(kmz_temp, out_kmz_path)
    return out_kmz_path

