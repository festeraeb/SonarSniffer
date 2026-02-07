"""Test script: parse an RSD file using the Rust parser (if available) and generate a simple sidescan waterfall PNG.

Usage: python scripts/test_rust_parser_waterfall.py [path/to/file.RSD] [max_pings]
"""
import sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / 'src'
import sys
sys.path.insert(0, str(SRC))

DATA = REPO / 'data'
OUT = REPO / 'outputs'
OUT.mkdir(exist_ok=True)

from rsd_video_core import generate_sidescan_waterfall


def get_parser_records(path, max_pings=200):
    """Try rust parser first then fallback to Python generator"""
    try:
        import rsd_parser_rust as rustp
        if hasattr(rustp, 'parse_rsd_records'):
            print('Using rsd_parser_rust')
            recs = list(rustp.parse_rsd_records(str(path), max_pings))
            return recs[:max_pings]
    except Exception as e:
        print('Rust parser not available or failed:', e)

    from sonarsniffer.engine_nextgen_syncfirst import parse_rsd_records_nextgen
    print('Using Python parser parse_rsd_records_nextgen')
    out = []
    for r in parse_rsd_records_nextgen(str(path), limit_records=max_pings):
        out.append(r)
        if len(out) >= max_pings:
            break
    return out


def extract_sample_array(path, record):
    """Read the raw sonar data bytes for a record and return a numpy 1-D array of samples.

    We don't know exact sample encoding; attempt to interpret as uint8 first."""
    try:
        with open(path, 'rb') as f:
            ofs = int(record.sonar_ofs)
            size = int(record.sonar_size)
            if size <= 0:
                return None
            f.seek(ofs)
            data = f.read(size)
            if not data:
                return None
            # Interpret as uint8 samples
            arr = np.frombuffer(data, dtype=np.uint8)
            if arr.size == 0:
                return None
            return arr.astype(np.float32)
    except Exception as e:
        print('Error reading sample bytes:', e)
        return None


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / 'Sonar001.RSD'
    max_pings = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    if not path.exists():
        print('File not found:', path)
        sys.exit(2)

    recs = get_parser_records(path, max_pings=max_pings)
    print(f'Parsed {len(recs)} records')

    samples = []
    widths = []
    for r in recs:
        s = extract_sample_array(path, r)
        if s is not None and s.size > 0:
            samples.append(s)
            widths.append(s.size)

    if not samples:
        print('No sonar sample arrays found to build waterfall')
        sys.exit(1)

    maxw = max(widths)
    # Build 2D buffer (height x width), pad with zeros for shorter rows
    height = len(samples)
    flat = np.zeros((height, maxw), dtype=np.float32)
    for i, s in enumerate(samples):
        n = min(s.size, maxw)
        flat[i, :n] = s[:n]

    # Normalize to 0..1
    flat_norm = flat
    if flat_norm.max() > 0:
        flat_norm = flat_norm / float(flat_norm.max())

    flat_buffer = flat_norm.flatten().tolist()

    img8_flat = generate_sidescan_waterfall(flat_buffer, width=maxw, height=height)
    img = np.asarray(img8_flat, dtype=np.uint8).reshape((height, maxw))

    # Save with matplotlib
    try:
        import matplotlib.pyplot as plt
        out_path = OUT / f'waterfall_{path.stem}.png'
        plt.imsave(str(out_path), img, cmap='gray', vmin=0, vmax=255)
        print('Waterfall image saved to', out_path)
    except Exception as e:
        print('Could not save image (matplotlib missing?):', e)
        # Fallback: save as raw .npy
        np.save(OUT / f'waterfall_{path.stem}.npy', img)
        print('Saved raw numpy array instead')
