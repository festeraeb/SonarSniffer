#!/usr/bin/env python3
"""Glue to run parse engines and write CSV rows.

This simplified glue supports calling run_engine(engine, rsd_path, out_dir, ...)
and provides a small CLI wrapper for testing.
"""
import argparse
import os
import sys
from typing import Tuple


def _run_one(engine_name: str, inp: str, out_dir: str, max_records=None, progress_every=2000, 
           progress_seconds=2.0, verbose=False, scan_type="auto", channel="all") -> Tuple[int,str,str]:
    # Import engine module dynamically
    if verbose:
        print(f"[engine_glue] Starting {engine_name} parser on {inp}")
        
    if engine_name == 'classic':
        from engine_classic_varstruct import parse_rsd as engine_parse
    elif engine_name == 'nextgen':
        from engine_nextgen_syncfirst import parse_rsd as engine_parse
    else:
        raise ValueError('Unknown engine')

    os.makedirs(out_dir, exist_ok=True)
    
    # Generate CSV path
    csv_path = os.path.join(out_dir, "records.csv")
    
    # First parse the RSD file
    if verbose:
        print(f"[engine_glue] Parsing {inp} to {csv_path}...")
        
    parse_result = engine_parse(inp, out_dir, max_records=max_records)
    
    # Handle the tuple return from parse engines
    if isinstance(parse_result, tuple):
        n, result_csv, temp_log_path = parse_result
    else:
        # Legacy engines might return just the CSV path
        result_csv = parse_result
        # Count records for compatibility
        try:
            with open(result_csv, 'r') as f:
                n = sum(1 for line in f) - 1  # Subtract header
        except:
            n = 0
    
    # Create a simple log
    log_path = os.path.join(out_dir, "records.log")
    try:
        # Use temp_log_path if available from engine, otherwise create our own
        if 'temp_log_path' in locals() and temp_log_path and os.path.exists(temp_log_path):
            log_path = temp_log_path
        else:
            with open(log_path, 'w') as f:
                f.write(f"Parsed {n} records from {inp}\n")
                f.write(f"Output: {result_csv}\n")
    except:
        log_path = None
    
    # Now generate PNGs from sonar data
    if verbose:
        print(f"[engine_glue] Generating images from {result_csv}...")
    
    try:
        from render_accel import process_record_images
        img_dir = os.path.join(out_dir, 'images')
        os.makedirs(img_dir, exist_ok=True)
        process_record_images(result_csv, img_dir, scan_type=scan_type, channel=channel)
    except Exception as e:
        print(f"[engine_glue] Warning: Image generation failed: {str(e)}")
    
    return n, result_csv, log_path


def run_engine(engine: str, rsd_path: str, csv_out: str, limit_rows: int | None = None) -> list[str]:
    """Run engine and return list of output file paths for GUI compatibility."""
    # Extract output directory from csv_out path
    import os
    out_dir = os.path.dirname(csv_out)
    if not out_dir:
        out_dir = '.'
    
    # Run the engine
    n, csv_path, log_path = _run_one(engine, rsd_path, out_dir, max_records=limit_rows)
    
    # Return list of paths for GUI compatibility
    result_paths = [csv_path]
    if log_path and os.path.exists(log_path):
        result_paths.append(log_path)
    
    return result_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="RSD file or sample CSV")
    ap.add_argument("--out", required=True, help="Output folder")
    ap.add_argument("--prefer", default="auto-nextgen-then-classic", 
                   choices=["auto-nextgen-then-classic","classic","nextgen","both"],
                   help="Parser preference")
    ap.add_argument("--max", type=int, default=None, help="Optional cap for fast tests")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose debug output")
    ap.add_argument("--scan-type", default="auto", choices=["auto", "sidescan", "downscan", "chirp"],
                   help="Type of scan data to parse")
    ap.add_argument("--channel", default="all", help="Channel ID to parse (all, auto, or specific ID)")
    args = ap.parse_args()

    inp = args.input
    out_dir = args.out
    prefer = args.prefer
    scan_type = args.scan_type
    channel = args.channel

    if prefer == "auto-nextgen-then-classic":
        # Try nextgen first, fall back to classic if it fails
        try:
            if args.verbose:
                print("[engine_glue] Trying nextgen parser first...")
            n, p, l = _run_one("nextgen", inp, out_dir, args.max, verbose=args.verbose)
            total = n; paths = [p]; logs = [l]
            if args.verbose:
                print(f"[engine_glue] Nextgen parser succeeded with {n} records")
        except Exception as e:
            if args.verbose:
                print(f"[engine_glue] Nextgen parser failed: {str(e)}")
                print("[engine_glue] Falling back to classic parser...")
            n, p, l = _run_one("classic", inp, out_dir, args.max, verbose=args.verbose)
            total = n; paths = [p]; logs = [l]
    elif prefer in ("classic", "nextgen"):
        if args.verbose:
            print(f"[engine_glue] Using {prefer} parser as specified")
        n, p, l = _run_one(prefer, inp, out_dir, args.max, verbose=args.verbose)
        total = n; paths = [p]; logs = [l]
    elif prefer == "both":
        n1, p1, l1 = _run_one("classic", inp, os.path.join(out_dir, "classic"), args.max)
        n2, p2, l2 = _run_one("nextgen", inp, os.path.join(out_dir, "nextgen"), args.max)
        total = n1 + n2; paths = [p1,p2]; logs = [l1,l2]
    else:
        n2, p2, l2 = _run_one("nextgen", inp, out_dir, args.max)
        if n2 == 0:
            n1, p1, l1 = _run_one("classic", inp, out_dir, args.max)
            total = n1; paths = [p1]; logs = [l1]
        else:
            total = n2; paths = [p2]; logs = [l2]

    if total == 0:
        print("[engine_glue] ERROR: parsed 0 records. See log:", " | ".join(logs))
        sys.exit(2)

    print(f"[engine_glue] OK: wrote {total} records -> {', '.join(paths)}")
    sys.exit(0)


if __name__ == '__main__':
    main()
