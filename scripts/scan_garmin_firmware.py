#!/usr/bin/env python3
"""Scan GARMIN firmware blobs for candidate 4-byte magic headers.

Usage:
    python scripts/scan_garmin_firmware.py <dir> [--min-count N] [--top N]

This script scans all files in the directory for 4-byte sequences and reports
those that occur frequently. It can help find alternate header magic values
present in firmware images that moved the magic bytes across generations.
"""

import os
import sys
import collections
import argparse


def scan_dir(path, min_count=50, top=20):
    counts = collections.Counter()
    for root, _, files in os.walk(path):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                with open(p, 'rb') as fh:
                    data = fh.read()
                    # Count all aligned and unaligned 4-byte windows
                    for i in range(max(0, len(data) - 4)):
                        seq = data[i:i+4]
                        counts[seq] += 1
            except Exception:
                continue
    # Filter out trivial candidates
    candidates = [(int.from_bytes(k, 'little'), v) for k, v in counts.items() if v >= min_count and k != b'\x00\x00\x00\x00']
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top]


def write_candidates_to_file(candidates, out_path):
    """Write hex candidates (one per line) to out_path in 0xHEX format."""
    with open(out_path, 'w', encoding='utf-8') as fh:
        for val, cnt in candidates:
            fh.write(f"0x{val:08X}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dir')
    p.add_argument('--min-count', type=int, default=50)
    p.add_argument('--top', type=int, default=20)
    p.add_argument('--out', type=str, default=None, help='Write candidates to a file (one 0xHEX per line)')
    args = p.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Not a directory: {args.dir}")
        sys.exit(2)

    cands = scan_dir(args.dir, args.min_count, args.top)
    if not cands:
        print("No candidate 4-byte sequences found. Try lowering --min-count.")
        return

    print("Top candidate 4-byte sequences (little-endian int, occurrences):")
    for v, cnt in cands:
        print(f"0x{v:08X}\t{cnt}")

    if args.out:
        write_candidates_to_file(cands, args.out)
        print(f"Wrote {len(cands)} candidates to {args.out}")


if __name__ == '__main__':
    main()
