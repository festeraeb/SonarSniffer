#!/usr/bin/env python3
"""Run full Holloway.RSD using the Rust parser path (shim if no compiled module)
and generate a high-resolution MP4 (streaming frames to ffmpeg to avoid building
frames list in memory).

Environment overrides:
  HOLLOWAY_SOURCE: path to input (default data/Holloway.RSD)
  HOLLOWAY_OUT: output dir (default outputs/holloway_full)
  HOLLOWAY_VIDEO_WIDTH: width in pixels for video (default 8192)
  HOLLOWAY_VIDEO_HEIGHT: frame height in pixels (default 512)
  HOLLOWAY_VIDEO_FPS: fps (default 15)
  HOLLOWAY_MAX_RECORDS: limit number of records (0 => no cap)
"""
import os
import math
from pathlib import Path
import sys
# Ensure local package imports work when running the script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np

SOURCE = os.environ.get('HOLLOWAY_SOURCE', 'data/Holloway.RSD')
OUT_ROOT = os.environ.get('HOLLOWAY_OUT', 'outputs/holloway_full')
VIDEO_WIDTH = int(os.environ.get('HOLLOWAY_VIDEO_WIDTH', '8192'))
VIDEO_HEIGHT = int(os.environ.get('HOLLOWAY_VIDEO_HEIGHT', '512'))
VIDEO_FPS = int(os.environ.get('HOLLOWAY_VIDEO_FPS', '15'))
MAX_RECORDS = int(os.environ.get('HOLLOWAY_MAX_RECORDS', '0'))

os.makedirs(OUT_ROOT, exist_ok=True)

from sonarsniffer.sonar_parser import SonarParser
# Ensure adapter registration
try:
    import sonarsniffer.adapters.rsd_adapter
except Exception:
    pass

from sonarsniffer.adapters.rsd_adapter import rsd_record_to_scan
try:
    from sonarsniffer.rsd_video_core import generate_sidescan_waterfall
except Exception:
    from rsd_video_core import generate_sidescan_waterfall
# Choose encoder bridge according to environment (prefer gstreamer if configured)
VIDEO_ENCODER = os.environ.get("VIDEO_ENCODER", "").lower()
encode_frames_fn = None
if VIDEO_ENCODER == "gstreamer":
    try:
        from sonarsniffer.gstreamer_bridge import (
            encode_frames_with_fallback as encode_frames_fn,
        )
    except Exception:
        try:
            from gstreamer_bridge import encode_frames_with_fallback as encode_frames_fn
        except Exception:
            encode_frames_fn = None
if encode_frames_fn is None:
    try:
        from sonarsniffer.python_cuda_bridge import (
            encode_frames_to_mp4 as encode_frames_fn,
        )
    except Exception:
        try:
            from python_cuda_bridge import encode_frames_to_mp4 as encode_frames_fn
        except Exception:
            encode_frames_fn = None

print('Using Rust parser path (shim if no compiled module)')
parser = SonarParser()

# Try to use rust parser directly via the private helper _try_use_rust_parser
records = None
try:
    records = parser._try_use_rust_parser(SOURCE, MAX_RECORDS if MAX_RECORDS > 0 else None)
except Exception as e:
    print('Rust parser path failed:', e)

if not records:
    # Fall back to explicit import of rsd_parser_rust shim/extension
    try:
        import rsd_parser_rust as rustp
        records = list(rustp.parse_rsd_records(SOURCE, MAX_RECORDS))
    except Exception as e:
        raise RuntimeError('Rust parser unavailable and shim import failed: ' + str(e))

print('Records retrieved:', len(records))

# Convert records to canonical scans and filter those with actual samples
scans = []
for r in records:
    try:
        # r may already be SimpleNamespace-like from shim
        s = rsd_record_to_scan(r, SOURCE)
        if s.samples is not None and getattr(s, 'samples').size > 0:
            scans.append(s)
    except Exception:
        continue

print('Scans with samples:', len(scans))
if not scans:
    raise RuntimeError('No scans with samples found - cannot build video')

# Create a streaming generator of RGB frames that scrolls the waterfall over time
def frame_generator(scans_iter, width: int, height: int):
    # sliding window buffer: newest row at the bottom, older rows above
    buf = np.zeros((height, width), dtype=np.uint8)
    # Pre-allocate a reusable RGB buffer to avoid repeated large temporaries
    rgb_buf = np.empty((height, width, 3), dtype=np.uint8)
    filled = 0
    for s in scans_iter:
        arr = np.asarray(s.samples, dtype=np.float32)
        if arr.size == 0:
            continue
        if arr.size < width:
            pad = np.zeros(width - arr.size, dtype=arr.dtype)
            arr2 = np.concatenate([arr, pad])
        else:
            arr2 = arr[:width]
        W = width
        # generate 1xW waterfall row (flattened)
        img8_row = np.asarray(generate_sidescan_waterfall(arr2.tolist(), W, 1), dtype=np.uint8).reshape((W,))
        # scroll buffer up by one and insert new row at bottom
        buf = np.roll(buf, -1, axis=0)
        buf[-1, :] = img8_row
        filled = min(height, filled + 1)
        # produce RGB frame from the buffer by assigning channels in-place
        rgb_buf[..., 0] = buf
        rgb_buf[..., 1] = buf
        rgb_buf[..., 2] = buf
        yield rgb_buf

video_out = os.path.join(OUT_ROOT, Path(SOURCE).stem + '_rust_full.mp4')
DISPLAY_H = os.environ.get('HOLLOWAY_VIDEO_DISPLAY_HEIGHT')
if DISPLAY_H:
    try:
        DISPLAY_H = int(DISPLAY_H)
    except Exception:
        DISPLAY_H = None
print('Encoding video to', video_out, f'(W={VIDEO_WIDTH} H={VIDEO_HEIGHT} fps={VIDEO_FPS})',
      f"display_H={DISPLAY_H if DISPLAY_H else VIDEO_HEIGHT}")
frames = frame_generator(scans, VIDEO_WIDTH, VIDEO_HEIGHT)
try:
    if encode_frames_fn is None:
        raise RuntimeError("No encoder function available (gstreamer or ffmpeg)")
    # If gstreamer bridge is used, its function signature may be encode_frames_with_fallback
    # which returns output_path. Call it accordingly.
    encode_result = None
    try:
        encode_result = encode_frames_fn(
            frames,
            video_out,
            fps=VIDEO_FPS,
            width=VIDEO_WIDTH,
            height=(DISPLAY_H if DISPLAY_H else VIDEO_HEIGHT),
        )
    except TypeError:
        # Fallback: some bridges use output_height kw; try with output_height
        encode_result = encode_frames_fn(
            frames,
            video_out,
            fps=VIDEO_FPS,
            output_height=(DISPLAY_H if DISPLAY_H else None),
        )
    print('Video written:', video_out)
except Exception as e:
    import traceback
    tb = traceback.format_exc()
    err_log = os.path.join(OUT_ROOT, 'ffmpeg_error.log')
    try:
        with open(err_log, 'w', encoding='utf-8') as fh:
            fh.write(tb)
    except Exception:
        pass
    print('Video encoding FAILED. See', err_log)
    # Report runtime error to telemetry (best-effort)
    try:
        from sonarsniffer.telemetry import report_runtime_error

        details = {"ffmpeg_error_log": err_log, "video_out": video_out, "video_width": VIDEO_WIDTH, "video_height": VIDEO_HEIGHT}
        report_runtime_error(e, feature_used='video_export', processing_step='frame_encoding', details=details)
    except Exception:
        pass

print('Finished')
