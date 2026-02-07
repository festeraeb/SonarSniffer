"""Move synthetic samples into samples/synthetic/"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'samples'
SYN = SAMPLES / 'synthetic'
SYN.mkdir(exist_ok=True)

moved = []
for p in SAMPLES.iterdir():
    if p.is_file() and ('synthetic' in p.name.lower() or p.name.lower().startswith('synthetic_')):
        shutil.move(str(p), str(SYN / p.name))
        moved.append(p.name)

print('Moved files:')
for m in moved:
    print('-', m)

print('\nSynthetic folder contents:')
for p in SYN.iterdir():
    if p.is_file():
        print('-', p.name, p.stat().st_size)
