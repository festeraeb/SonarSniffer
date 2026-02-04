#!/usr/bin/env python3
"""Simple shim to run SonarSniffer either with Docker (preferred) or directly for local dev.

Usage:
  python scripts/cesaropsctl.py run
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get('SONARS_DOCKER_IMAGE', 'ghcr.io/yourorg/sonarsniffer:latest')


def run_container():
    if shutil.which('docker') is None and shutil.which('podman') is None:
        print('Docker/Podman not found on PATH')
        return False
    cmd = ['docker', 'run', '--rm', '-p', '8081:8081', '-v', f'{ROOT}/outputs:/app/outputs', '--name', 'sonarsniffer_local', IMAGE]
    print('Running container:',' '.join(cmd))
    return subprocess.call(cmd) == 0


def run_local():
    # Start the app directly in-process (for dev)
    env = os.environ.copy()
    env['SONARS_OUTPUT_DIR'] = str(ROOT / 'outputs')
    print('Starting local server (python scripts/serve_web.py)')
    return subprocess.call([sys.executable, str(ROOT / 'scripts' / 'serve_web.py')], env=env)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: cesaropsctl.py run [--local]')
        sys.exit(2)
    if sys.argv[1] == 'run' and '--local' not in sys.argv:
        ok = run_container()
        if not ok:
            print('Falling back to local mode')
            sys.exit(0 if run_local() else 1)
    elif sys.argv[1] == 'run' and '--local' in sys.argv:
        sys.exit(0 if run_local() else 1)
    else:
        print('Unknown command')
        sys.exit(2)
