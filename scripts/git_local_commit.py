#!/usr/bin/env python3
import subprocess
import sys

branch = 'feat/pipeline-exporters'
msg = 'feat(pipeline): add canonical Scan, rsd adapter, waterfall/video exporters, pipeline CLI; telemetry/patching support (local only)'

# Ensure we are in the repo root (script run from repo root)
try:
    # Check if branch exists
    subprocess.check_call(['git', 'rev-parse', '--verify', branch], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Branch exists - checkout
    subprocess.check_call(['git', 'checkout', branch])
    print(f'Checked out existing branch {branch}')
except subprocess.CalledProcessError:
    # Branch does not exist - create it
    subprocess.check_call(['git', 'checkout', '-b', branch])
    print(f'Created branch {branch}')

# Add all changes
subprocess.check_call(['git', 'add', '-A'])
# Commit if there are changes
try:
    subprocess.check_call(['git', 'commit', '-m', msg])
    print('Committed changes')
except subprocess.CalledProcessError:
    print('Nothing to commit')

# Print head
head = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
print('HEAD', head)
