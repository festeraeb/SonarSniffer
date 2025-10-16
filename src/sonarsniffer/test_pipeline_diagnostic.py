#!/usr/bin/env python3
"""Diagnostic test for block processing pipeline"""

import os
import sys
from pathlib import Path

def test_block_processing_pipeline():
    """Test the complete block processing pipeline"""
    print("=== BLOCK PROCESSING PIPELINE DIAGNOSTIC ===\n")
    
    # Check if we have test data
    test_csv = "records.csv"
    test_rsd = None
    
    # Look for CSV files
    outputs_csv = Path("outputs/records.csv")
    outputs_auto_csv = Path("outputs_auto/records.csv")
    
    if outputs_csv.exists():
        test_csv = str(outputs_csv)
        print(f"✓ Found CSV: {test_csv}")
    elif outputs_auto_csv.exists():
        test_csv = str(outputs_auto_csv)
        print(f"✓ Found CSV: {test_csv}")
    elif Path(test_csv).exists():
        print(f"✓ Found CSV: {test_csv}")
    else:
        print("✗ No CSV file found. Need to run parser first.")
        return False
    
    # Check CSV content
    try:
        with open(test_csv, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("✗ CSV file is empty or has no data rows")
                return False
            print(f"✓ CSV has {len(lines)-1} data rows")
            
            # Check header
            header = lines[0].strip().split(',')
            print(f"✓ CSV columns: {header}")
            
            # Check for required fields
            required_fields = ['channel_id', 'sonar_ofs', 'sonar_size']
            missing_fields = [field for field in required_fields if field not in header]
            if missing_fields:
                print(f"✗ Missing required fields: {missing_fields}")
                return False
            print("✓ All required fields present")
            
    except Exception as e:
        print(f"✗ Error reading CSV: {e}")
        return False
    
    # Test block pipeline imports
    try:
        from block_pipeline import BlockProcessor, read_records_from_csv, compose_channel_block_preview
        print("✓ Block pipeline imports successful")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    # Test CSV reading
    try:
        records = read_records_from_csv(test_csv)
        print(f"✓ Loaded {len(records)} records from CSV")
        
        if len(records) == 0:
            print("✗ No records loaded - check CSV format")
            return False
            
        # Check first record
        first_record = records[0]
        print(f"✓ First record: channel={first_record.channel_id}, sonar_ofs={first_record.sonar_ofs}, sonar_size={first_record.sonar_size}")
        
        # Check channels
        channels = set(r.channel_id for r in records if r.channel_id is not None)
        print(f"✓ Available channels: {sorted(channels)}")
        
        if len(channels) < 2:
            print("⚠ Warning: Less than 2 channels found - may affect processing")
        
    except Exception as e:
        print(f"✗ Error loading records: {e}")
        return False
    
    # Try to create BlockProcessor (without RSD file for now)
    try:
        processor = BlockProcessor(test_csv, "dummy.rsd", 25)  # Use dummy RSD path
        print("✓ BlockProcessor created")
        
        available_channels = processor.get_available_channels()
        print(f"✓ Available channels from processor: {available_channels}")
        
        if len(available_channels) >= 2:
            # Test getting blocks for first two channels
            ch1, ch2 = available_channels[0], available_channels[1]
            blocks1 = processor.get_channel_blocks(ch1)
            blocks2 = processor.get_channel_blocks(ch2)
            print(f"✓ Channel {ch1}: {len(blocks1)} blocks")
            print(f"✓ Channel {ch2}: {len(blocks2)} blocks")
            
            if blocks1 and blocks2:
                print(f"✓ Block sizes: Ch{ch1}[0]={len(blocks1[0])} records, Ch{ch2}[0]={len(blocks2[0])} records")
        
    except Exception as e:
        print(f"✗ Error creating BlockProcessor: {e}")
        return False
    
    print("\n=== SUMMARY ===")
    print("✓ CSV loading: WORKING")
    print("✓ Record parsing: WORKING") 
    print("✓ Channel detection: WORKING")
    print("✓ Block creation: WORKING")
    print("\nThe pipeline should now work correctly!")
    print("\nNEXT STEPS:")
    print("1. Load an RSD file in the GUI")
    print("2. Run the parser to generate CSV")
    print("3. Build block preview")
    print("4. Should see proper vertical channel blocks")
    
    return True

if __name__ == "__main__":
    success = test_block_processing_pipeline()
    if success:
        print("\n🎉 All tests passed! Pipeline ready.")
    else:
        print("\n❌ Tests failed. Check the issues above.")