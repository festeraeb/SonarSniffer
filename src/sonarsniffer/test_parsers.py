#!/usr/bin/env python3
"""Test script to verify parser behavior with RSD files."""

from pathlib import Path
import sys

def test_classic_parser(rsd_path, out_dir):
    print(f"\nTesting classic parser on {rsd_path}")
    from engine_classic_varstruct import parse_rsd
    try:
        n, csv_path, log_path = parse_rsd(rsd_path, out_dir)
        print(f"Success! Parsed {n} records")
        return True
    except Exception as e:
        print(f"Failed as expected: {str(e)}")
        return False

def test_nextgen_parser(rsd_path, out_dir):
    print(f"\nTesting nextgen parser on {rsd_path}")
    from engine_nextgen_syncfirst import parse_rsd
    try:
        n, csv_path, log_path = parse_rsd(rsd_path, out_dir)
        print(f"Success! Parsed {n} records")
        return True
    except Exception as e:
        print(f"Error with nextgen parser: {str(e)}")
        return False

if __name__ == "__main__":
    # Get the first RSD file in parent directory
    test_dir = Path(__file__).parent
    rsd_files = list(test_dir.glob("*.RSD"))
    
    if not rsd_files:
        print("No RSD files found in current directory")
        sys.exit(1)
        
    for rsd_file in rsd_files:
        out_dir = test_dir / "test_outputs" / rsd_file.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nTesting file: {rsd_file.name}")
        print("=" * 60)
        
        classic_result = test_classic_parser(str(rsd_file), str(out_dir / "classic"))
        nextgen_result = test_nextgen_parser(str(rsd_file), str(out_dir / "nextgen"))
        
        print("\nResults:")
        print(f"Classic parser: {'FAILED (expected)' if not classic_result else 'Unexpectedly succeeded'}")
        print(f"Nextgen parser: {'SUCCESS' if nextgen_result else 'FAILED'}")