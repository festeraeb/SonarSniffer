#!/usr/bin/env python3
# simple_test.py - Debug where the parser hangs

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

print("Starting simple test...")

try:
    print("Step 1: Importing modules...")
    from engine_classic_varstruct import parse_rsd_records_classic
    print("✓ Import successful")
    
    print("Step 2: Checking file exists...")
    rsd_file = "126SV-UHD2-GT54.RSD"
    if os.path.exists(rsd_file):
        print(f"✓ File exists: {rsd_file} ({os.path.getsize(rsd_file)} bytes)")
    else:
        print(f"✗ File not found: {rsd_file}")
        sys.exit(1)
    
    print("Step 3: Testing parser with 1 record...")
    count = 0
    for record in parse_rsd_records_classic(rsd_file, limit_records=1):
        count += 1
        print(f"✓ Got record {count}: ofs={record.ofs}, lat={record.lat}, lon={record.lon}")
        break
    
    print(f"✓ Test completed successfully! Processed {count} record(s)")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()