#!/usr/bin/env python3
"""
Recursive Real File Multi-Format Parser Test
Searches a provided root directory recursively and runs the same parser checks
as `test_real_files.py`, but allows specifying a parent directory.
"""

import os
import glob
import json
import argparse
from pathlib import Path

ROOT_DEFAULT = '..'

def find_sonar_files(root):
    extensions = ['.rsd', '.RSD', '.sl2', '.sl3', '.SL2', '.SL3',
                  '.dat', '.DAT', '.son', '.SON', '.jsf', '.JSF',
                  '.svlog', '.SVLOG']

    root_path = Path(root)
    files = []
    for ext in extensions:
        for p in root_path.rglob(f'*{ext}'):
            files.append(str(p))

    # Remove duplicates and sort by size (larger first)
    # Filter out obviously non-binary or empty files (CSV headers / zero-length)
    unique_files = list(set(files))
    filtered = []
    for f in unique_files:
        try:
            if Path(f).stat().st_size == 0:
                continue
            # Quick text sniff: if file starts with ASCII header like 'ofs,' or contains commas early, skip
            with open(f, 'rb') as fh:
                start = fh.read(256)
                if b'ofs,' in start or b',' in start[:64]:
                    # looks like CSV/text, skip for binary parser runs
                    continue
        except Exception:
            continue
        filtered.append(f)
    files_with_size = [(f, os.path.getsize(f)) for f in filtered]
    files_with_size.sort(key=lambda x: x[1], reverse=True)
    return [f[0] for f in files_with_size]


def run_tests(root):
    print(f"Searching for sonar files under: {root}")
    sonar_files = find_sonar_files(root)
    print(f"Found {len(sonar_files)} sonar files")

    # Reuse parser mapping from test_real_files.py
    parsers = [
        ('Garmin RSD', 'parsers.garmin_parser', 'GarminParser', ['.rsd', '.RSD']),
        ('Lowrance SL2/SL3', 'parsers.lowrance_parser_enhanced', 'LowranceParser', ['.sl2', '.sl3', '.SL2', '.SL3']),
        ('Humminbird DAT/SON', 'parsers.humminbird_parser', 'HumminbirdParser', ['.dat', '.son', '.DAT', '.SON']),
        ('EdgeTech JSF', 'parsers.edgetech_parser', 'EdgeTechParser', ['.jsf', '.JSF']),
        ('Cerulean SVLOG', 'parsers.cerulean_parser', 'CeruleanParser', ['.svlog', '.SVLOG'])
    ]

    results = {}
    for parser_name, module_name, class_name, extensions in parsers:
        print(f"\n== Testing {parser_name} ==")
        try:
            module = __import__(module_name, fromlist=[class_name])
            parser_class = getattr(module, class_name)
        except Exception as e:
            print(f"  Import failed for {parser_name}: {e}")
            results[parser_name] = {'import': False, 'error': str(e)}
            continue

        matching = [f for f in sonar_files if any(f.endswith(ext) for ext in extensions)]
        print(f"  Found {len(matching)} matching files")
        if not matching:
            results[parser_name] = {'import': True, 'tested': False, 'files': 0}
            continue

        parser_results = []
        for fpath in matching:
            try:
                p = parser_class(fpath)
                supported = p.is_supported()
                entry = {'file': fpath, 'supported': supported}
                if supported:
                    # Try to parse small sample
                    try:
                        count, csv_path, log_path = p.parse_records(max_records=10)
                        entry.update({'parsed': count, 'csv': csv_path})
                    except Exception as e:
                        entry.update({'parsed': 0, 'error': str(e)[:200]})
                parser_results.append(entry)
            except Exception as e:
                parser_results.append({'file': fpath, 'error': str(e)[:200]})

        results[parser_name] = {'import': True, 'tested': True, 'files': len(matching), 'results': parser_results}

    out_dir = Path('benchmark_results')
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'real_files_recursive_report.json'
    with open(out_path, 'w') as fh:
        json.dump(results, fh, indent=2)

    print(f"\nResults written to {out_path}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', '-r', default=ROOT_DEFAULT, help='Root path to search')
    args = parser.parse_args()
    run_tests(args.root)


if __name__ == '__main__':
    main()
