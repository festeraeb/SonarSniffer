#!/usr/bin/env python3
"""
Test parsing standard RSD files to find CHIRP/ClearVue channels
This will help us understand the normal encoding before tackling CV-54-UHD.RSD
"""
import sys
import os

# Test with the smaller RSD files first
test_files = [
    r'c:\Temp\Garminjunk\samples\93SV-UHD-GT56.RSD',  # 0.7 MB - smallest
    r'c:\Temp\Garminjunk\samples\CV-54-UHD.RSD',      # 3.24 MB - the mystery file
    r'c:\Temp\Garminjunk\samples\Sonar002.RSD',       # 40 MB - standard
]

print("="*70)
print("STANDARD RSD CHIRP CHANNEL ANALYSIS")
print("="*70)

for filepath in test_files:
    if not os.path.exists(filepath):
        print(f"\n✗ {filepath} not found")
        continue
    
    size_mb = os.path.getsize(filepath) / 1024 / 1024
    filename = os.path.basename(filepath)
    
    print(f"\n{'='*70}")
    print(f"File: {filename} ({size_mb:.2f} MB)")
    print(f"{'='*70}")
    
    try:
        # Try to parse with any available parser
        from src.sonarsniffer.engine_nextgen_syncfirst import RSDParser
        
        parser = RSDParser()
        records = parser.parse(filepath)
        
        print(f"✓ Successfully parsed {len(records)} records")
        
        # Group by channel
        channels = {}
        for rec in records:
            ch = rec.channel_id
            if ch not in channels:
                channels[ch] = 0
            channels[ch] += 1
        
        print(f"\nChannels found:")
        for ch in sorted(channels.keys()):
            print(f"  Channel {ch:3d}: {channels[ch]:6d} records")
        
        # Check for CHIRP-like channels (6-10)
        chirp_channels = [ch for ch in channels if 6 <= ch <= 10]
        if chirp_channels:
            print(f"\n✓ CHIRP channels detected: {chirp_channels}")
            total_chirp = sum(channels[ch] for ch in chirp_channels)
            print(f"  Total CHIRP records: {total_chirp}")
        else:
            print(f"\n✗ No CHIRP channels (6-10) found")
        
        # Show sample record from first channel
        first_channel = min(channels.keys())
        print(f"\nSample record from channel {first_channel}:")
        sample = next((r for r in records if r.channel_id == first_channel), None)
        if sample:
            print(f"  Sequence: {sample.seq}")
            print(f"  Timestamp: {sample.time_ms} ms")
            if hasattr(sample, 'lat') and sample.lat:
                print(f"  Position: {sample.lat:.6f}, {sample.lon:.6f}")
            print(f"  Depth: {sample.depth_m:.1f} m")
            print(f"  Sample count: {sample.sample_cnt}")
            print(f"  Sonar data: {sample.sonar_size} bytes")
    
    except ImportError:
        print("✗ Parser not available, trying alternative methods...")
        
        with open(filepath, 'rb') as f:
            data = f.read(4096)
            
            # Check header
            if data[:3] == b'RSD':
                print("✓ Valid RSD header found")
            else:
                print(f"? Unknown header: {data[:4].hex()}")
    
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

print("\n" + "="*70)
print("NEXT STEP: Once we have standard RSD CHIRP data structure,")
print("we can compare with CV-54-UHD.RSD to reverse-engineer the frame format")
print("="*70)
