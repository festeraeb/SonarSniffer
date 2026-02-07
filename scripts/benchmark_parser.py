#!/usr/bin/env python3
"""Benchmark parser throughput (MB/s) for Python and Rust parsers.

Outputs a JSON report with timings.
"""
import argparse
import os
import time
import json

from sonarsniffer.sonar_parser import SonarParser


def time_parse(path, repeat=1):
    p = SonarParser()
    start = time.time()
    count = 0
    for _ in range(repeat):
        r = p.parse_file(path)
        count += len(r.get('records', []))
    dur = time.time() - start
    size_mb = os.path.getsize(path) / (1024.0 * 1024.0)
    return {'records': count, 'duration_s': dur, 'size_mb': size_mb, 'mb_per_s': (size_mb * repeat) / dur if dur>0 else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--repeat', type=int, default=1)
    ap.add_argument('--out', default='benchmark-report.json')
    args = ap.parse_args()
    report = {}
    report['python'] = time_parse(args.file, repeat=args.repeat)
    # Try rust parser path via import; if exists we can time it similarly
    try:
        import rsd_parser_rust as rustp
        import time as _t
        start = _t.time()
        recs = list(rustp.parse_rsd_records(args.file, 0))
        dur = _t.time() - start
        size_mb = os.path.getsize(args.file) / (1024.0 * 1024.0)
        report['rust'] = {'records': len(recs), 'duration_s': dur, 'size_mb': size_mb, 'mb_per_s': size_mb / dur if dur>0 else 0}
    except Exception as ex:
        report['rust'] = {'error': str(ex)}

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2)
    print('Wrote', args.out)

if __name__ == '__main__':
    main()
