"""
Test script to verify block processing generates multiple blocks
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from block_pipeline import BlockProcessor
import pandas as pd

def test_block_generation():
    """Test block generation with small block size"""
    
    # Check if we have test data
    csv_path = "outputs/records.csv"
    if not os.path.exists(csv_path):
        csv_path = "outputs_auto/records.csv"
    
    if not os.path.exists(csv_path):
        print("No CSV data found to test with")
        return
    
    # Check CSV contents
    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Total records: {len(df)}")
    
    if 'channel_id' in df.columns:
        channels = df['channel_id'].value_counts()
        print(f"Channel distribution:")
        for ch, count in channels.items():
            print(f"  Channel {ch}: {count} records")
    
    # Create BlockProcessor with small block size to force multiple blocks
    rsd_path = "test.rsd"  # Dummy path for testing
    processor = BlockProcessor(csv_path, rsd_path, block_size=10)  # Very small blocks
    
    print(f"\nAvailable channels: {processor.get_available_channels()}")
    
    for ch_id in processor.get_available_channels():
        blocks = processor.get_channel_blocks(ch_id)
        print(f"Channel {ch_id}: {len(blocks)} blocks")
        for i, block in enumerate(blocks):
            print(f"  Block {i}: {len(block)} records")

if __name__ == "__main__":
    test_block_generation()