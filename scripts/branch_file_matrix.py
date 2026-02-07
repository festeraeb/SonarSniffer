import subprocess
branches = ['research/optimization-integration','master','master-archive-2025-12-04','Beta','beta-clean','cesarops-platform','installation-scripts']
files = ['src/sonarsniffer/incremental_loading.py','src/sonarsniffer/ml_pipeline.py','src/sonarsniffer/geospatial_export.py','test_sonarsniffer_cli.py','SONARSNIFFER_OPTIMIZATION_COMPLETE.md']
print('Branch file presence matrix:')
for b in branches:
    print(f'Branch: {b}')
    try:
        out = subprocess.check_output(['git','ls-tree','-r','--name-only',f'github/{b}'], stderr=subprocess.DEVNULL).decode('utf-8')
    except subprocess.CalledProcessError:
        out = ''
    for f in files:
        print('  ✓' if f in out.splitlines() else '  ✗', f)
    print('')
