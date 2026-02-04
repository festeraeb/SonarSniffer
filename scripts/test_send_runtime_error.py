import os, time
os.environ['SONARSNIFFER_TELEMETRY_URL'] = os.environ.get('SONARSNIFFER_TELEMETRY_URL', 'http://localhost:7071/api/runtime-error')
from sonarsniffer.telemetry import report_runtime_error

try:
    raise RuntimeError('TEST: simulated encoding failure')
except Exception as e:
    report_runtime_error(e, feature_used='video_export', processing_step='frame_encoding', details={'note': 'test run', 'timestamp': time.time()})
    print('Reported (fire-and-forget)')
