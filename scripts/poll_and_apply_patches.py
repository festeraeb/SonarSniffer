#!/usr/bin/env python3
"""Poll telemetry server for pending patches and optionally apply them.

This script is conservative by default; pass --auto-apply to allow magic variant
patches to be applied automatically. Code patches will always be deferred and
printed for manual review.

Example:
  python scripts/poll_and_apply_patches.py --url https://sonarsniffer.example.com/api/v1/parse_reports --token $TOKEN --auto-apply
"""

import argparse
import logging
from sonarsniffer import telemetry

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger('poll_patches')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default=None, help='Telemetry base URL')
    p.add_argument('--token', default=None, help='Bearer token')
    p.add_argument('--auto-apply', action='store_true', help='Apply safe patches automatically')
    args = p.parse_args()

    patches = telemetry.fetch_pending_patches(url=args.url, token=args.token)
    if not patches:
        LOG.info('No pending patches')
        return

    LOG.info('Found %d patches', len(patches))
    for patch in patches:
        LOG.info('Patch: id=%s type=%s created_by=%s', patch.get('id'), patch.get('type'), patch.get('created_by'))
        if patch.get('type') == 'magic_variants' and args.auto_apply:
            res = telemetry.apply_patch(patch)
            if res.get('applied'):
                LOG.info('Applied patch %s added=%s', res.get('id'), res.get('added'))
            else:
                LOG.warning('Failed to apply patch %s: %s', res.get('id'), res.get('reason'))
        else:
            LOG.info('Patch needs manual review: %s', patch.get('description'))


if __name__ == '__main__':
    main()
