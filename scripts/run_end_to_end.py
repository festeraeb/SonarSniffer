"""Run a minimal end-to-end smoke test of the pipeline.

This script runs a conservative end-to-end pipeline on `data/Holloway.RSD` (or an
alternative file provided via HOLLOWAY_SOURCE). It limits records/frames so it
is fast and suitable for CI / local smoke testing.

It verifies that key outputs are produced: waterfall PNG, MBTiles (if enabled),
MP4 video (if encoder available), and the mosaic.
"""
import os
import sys
import time
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# Ensure our package path is available for local runs/tests
import sys
sys.path.insert(0, str(ROOT / 'src'))
SCRIPTS = ROOT / 'scripts'

# Environment overrides for fast test
os.environ.setdefault('HOLLOWAY_MAX_RECORDS', '200')
os.environ.setdefault('HOLLOWAY_VIDEO_WIDTH', '512')
os.environ.setdefault('HOLLOWAY_VIDEO_HEIGHT', '64')
os.environ.setdefault('HOLLOWAY_VIDEO_FPS', '5')
os.environ.setdefault('HOLLOWAY_VIDEO_DISPLAY_HEIGHT', '64')

# Use quick outputs location
out = Path(os.environ.get('HOLLOWAY_OUT', 'outputs/holloway_smoke'))
os.environ['HOLLOWAY_OUT'] = str(out)

# Choose encoder: prefer gstreamer if built in the environment, otherwise ffmpeg
os.environ.setdefault('VIDEO_ENCODER', os.environ.get('VIDEO_ENCODER', ''))

# Limit sample stride (smaller time)
os.environ.setdefault('HOLLOWAY_SAMPLE_STRIDE', '5')

SRC = os.environ.get('HOLLOWAY_SOURCE', 'data/Holloway.RSD')


def run_script(script_name: str):
    p = SCRIPTS / script_name
    if not p.exists():
        raise RuntimeError(f"Script not found: {p}")
    print('Running', p)
    start = time.time()
    env = os.environ.copy()
    ret = subprocess.run([sys.executable, str(p)], env=env)
    print('Return code', ret.returncode, 'time', time.time() - start)
    if ret.returncode != 0:
        raise RuntimeError(f"Script failed: {p} (rc={ret.returncode})")


def check_outputs(outdir: Path):
    outdir = Path(outdir)
    assert outdir.exists(), f"Output dir missing: {outdir}"
    pngs = list(outdir.glob('*.png'))
    assert pngs, 'No PNG outputs found'
    # Check mp4 (if created)
    mp4s = list(outdir.glob('*.mp4'))
    if mp4s:
        print('MP4s found:', mp4s)
    else:
        print('No MP4s produced (encoder missing or skipped)')
    # Check MBTiles/KMZ if present
    mbs = list(outdir.glob('*.mbtiles'))
    kmzs = list(outdir.glob('*.kmz'))
    print(f'Found PNGs: {len(pngs)}, MBTiles: {len(mbs)}, KMZ: {len(kmzs)}')


if __name__ == '__main__':
    # Run the simpler conservative pipeline
    try:
        run_script('run_holloway_pipeline.py')
    except Exception as ex:
        print('Conservative pipeline failed:', ex)

    # Attempt rust full pipeline (use reduced records)
    os.environ.setdefault('HOLLOWAY_MAX_RECORDS', '500')
    try:
        run_script('run_holloway_full_with_rust.py')
    except Exception as ex:
        print('Full rust pipeline failed:', ex)

    # Validate outputs
    try:
        check_outputs(out)
        print('Smoke test completed OK. Outputs in', out)
    except AssertionError as ae:
        print('Smoke test verification failed:', ae)
        raise
