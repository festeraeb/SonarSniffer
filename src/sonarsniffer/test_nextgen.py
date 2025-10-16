#!/usr/bin/env python3
"""Test script for nextgen parser with RSD files."""

from pathlib import Path
import sys
import os

def test_nextgen_parser(rsd_path, out_dir):
    print(f"\nTesting nextgen parser on {rsd_path}")
    from engine_nextgen_syncfirst import parse_rsd
    try:
        os.makedirs(out_dir, exist_ok=True)
        # Limit to 5000 records for testing
        n, csv_path, log_path = parse_rsd(rsd_path, out_dir, max_records=5000)
        print(f"Success! Parsed {n} records")
        print(f"CSV output: {csv_path}")
        print(f"Log output: {log_path}")
        return True, n
    except Exception as e:
        print(f"Error with nextgen parser: {str(e)}")
        return False, 0

if __name__ == "__main__":
    # Get the RSD files in current directory
    test_dir = Path(__file__).parent
    rsd_files = list(test_dir.glob("*.RSD"))
    
    if not rsd_files:
        print("No RSD files found in current directory")
        sys.exit(1)
        
    total_records = 0
    
    for rsd_file in rsd_files:
        out_dir = test_dir / "test_outputs" / rsd_file.stem
        print(f"\nTesting file: {rsd_file.name}")
        print("=" * 60)
        
        success, n_records = test_nextgen_parser(str(rsd_file), str(out_dir))
        print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
        if success:
            total_records += n_records
            
    print(f"\nTotal records parsed: {total_records}")