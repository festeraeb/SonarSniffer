#!/usr/bin/env python3
"""Submit a patch JSON to the telemetry server for review.

Example:
  python scripts/submit_patch.py --file my_patch.json --url https://sonarsniffer.example.com/api/v1/parse_reports --token $TOKEN
"""

import argparse
import json
from sonarsniffer import telemetry


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', required=True, help='Patch JSON file')
    p.add_argument('--url', default=None, help='Telemetry base URL')
    p.add_argument('--token', default=None, help='Bearer token')
    args = p.parse_args()

    with open(args.file, 'r', encoding='utf-8') as fh:
        patch = json.load(fh)

    res = telemetry.submit_patch(patch, url=args.url, token=args.token)
    if res is None:
        print('Submit failed or returned non-2xx')
    else:
        print('Server response:')
        print(json.dumps(res, indent=2))

if __name__ == '__main__':
    main()
