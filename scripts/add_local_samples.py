"""Copy specified local data files into the repo's `samples/` folder for deterministic tests.

Usage:
    python scripts/add_local_samples.py path/to/file1 [path/to/file2 ...]

If run with no arguments it will print a list of candidate small files under `data/` and exit.
"""
import sys
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / 'samples'
DATA_DIR = REPO_ROOT / 'data'

SAMPLES_DIR.mkdir(exist_ok=True)


def list_candidates():
    print("Candidate small data files under data/:\n")
    for p in sorted(DATA_DIR.rglob('*')):
        if p.is_file() and p.suffix.lower() in ['.rsd', '.son', '.xtf', '.dat']:
            size_mb = p.stat().st_size / (1024 * 1024)
            if size_mb < 200:  # show small files for convenience
                print(f"- {p.relative_to(REPO_ROOT)} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        list_candidates()
        sys.exit(0)

    for src in sys.argv[1:]:
        srcp = Path(src)
        if not srcp.exists():
            print(f"Skipping (not found): {src}")
            continue
        dest = SAMPLES_DIR / srcp.name
        shutil.copy2(srcp, dest)
        print(f"Copied {srcp} -> {dest}")
