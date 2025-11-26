#!/usr/bin/env python3
"""
Deep dive into CV-54-UHD.RSD frame structure
"""
import struct

filepath = r'c:\Temp\Garminjunk\samples\CV-54-UHD.RSD'

print("=" * 70)
print("CV-54-UHD.RSD Frame Structure Analysis")
print("=" * 70)

with open(filepath, 'rb') as f:
    data = f.read()

print(f"\nFile size: {len(data):,} bytes")
print(f"Total frames (0x06 markers): {data.count(b'\x06')}")

# Analyze frame boundaries
print("\n" + "=" * 70)
print("Frame Boundaries (0x06 markers)")
print("=" * 70)

frame_starts = [i for i in range(len(data)) if data[i:i+1] == b'\x06']
print(f"\nFound {len(frame_starts)} frames (0x06 markers)")

# Show first 10 frame boundaries
print(f"\nFirst 10 frame start positions:")
for i, pos in enumerate(frame_starts[:10]):
    if i < len(frame_starts) - 1:
        frame_size = frame_starts[i+1] - pos
    else:
        frame_size = len(data) - pos
    
    # Show frame header
    frame_header = data[pos:min(pos+32, len(data))]
    print(f"  Frame {i:2d}: offset {pos:7d}, size {frame_size:6d} bytes, header: {frame_header[:16].hex()}")

# Analyze frame size distribution
print(f"\n" + "=" * 70)
print("Frame Size Distribution")
print("=" * 70)

frame_sizes = []
for i in range(len(frame_starts)-1):
    size = frame_starts[i+1] - frame_starts[i]
    frame_sizes.append(size)

# Last frame
last_frame_size = len(data) - frame_starts[-1]
frame_sizes.append(last_frame_size)

print(f"\nFrame sizes:")
print(f"  Min: {min(frame_sizes)} bytes")
print(f"  Max: {max(frame_sizes)} bytes")
print(f"  Avg: {sum(frame_sizes) / len(frame_sizes):.1f} bytes")
print(f"  Unique sizes: {len(set(frame_sizes))}")

# Check if sizes are consistent
size_counts = {}
for size in frame_sizes:
    size_counts[size] = size_counts.get(size, 0) + 1

print(f"\nSize frequency:")
for size in sorted(size_counts.keys())[:10]:
    print(f"  {size:6d} bytes: {size_counts[size]:4d} frames")

# Deep dive into first frame
print(f"\n" + "=" * 70)
print("First Frame Detailed Analysis")
print("=" * 70)

frame1_start = frame_starts[0]
frame1_end = frame_starts[1] if len(frame_starts) > 1 else len(data)
frame1_data = data[frame1_start:frame1_end]

print(f"\nFrame 0: {len(frame1_data)} bytes at offset {frame1_start}")
print(f"\nFrame header (first 64 bytes):")
print(f"  Raw hex: {frame1_data[:64].hex()}")

# Parse frame header
print(f"\n  Frame type byte: 0x{frame1_data[0]:02x}")
print(f"  Byte 1-2:        0x{frame1_data[1:3].hex()}")
print(f"  Byte 3-4:        0x{frame1_data[3:5].hex()}")

# Try to parse as little-endian integers
try:
    val_u16_be = struct.unpack('>H', frame1_data[1:3])[0]
    val_u16_le = struct.unpack('<H', frame1_data[1:3])[0]
    print(f"  Bytes 1-2 as BE u16: {val_u16_be}")
    print(f"  Bytes 1-2 as LE u16: {val_u16_le}")
    
    val_u32_be = struct.unpack('>I', frame1_data[1:5])[0]
    val_u32_le = struct.unpack('<I', frame1_data[1:5])[0]
    print(f"  Bytes 1-4 as BE u32: {val_u32_be}")
    print(f"  Bytes 1-4 as LE u32: {val_u32_le}")
except:
    pass

# Show raw bytes with ASCII
print(f"\n  First 128 bytes (hex | ASCII):")
for offset in range(0, min(128, len(frame1_data)), 16):
    hex_part = frame1_data[offset:offset+16].hex()
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in frame1_data[offset:offset+16])
    print(f"    {offset:04d}: {hex_part:32s} | {ascii_part}")

# Analyze what comes after the frame type byte
print(f"\n" + "=" * 70)
print("Frame Type and Structure Patterns")
print("=" * 70)

# Count frame types
frame_types = {}
for pos in frame_starts:
    ftype = data[pos:pos+1].hex()
    if ftype not in frame_types:
        frame_types[ftype] = 0
    frame_types[ftype] += 1

print(f"\nFrame type markers found:")
for ftype in sorted(frame_types.keys()):
    print(f"  0x{ftype}: {frame_types[ftype]} occurrences")

# Look at what follows frame markers in other frames
print(f"\nPatterns after 0x06 markers (next 4 bytes):")
pattern_counts = {}
for pos in frame_starts[:100]:  # Check first 100
    pattern = data[pos:pos+5].hex()
    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

for pattern in sorted(pattern_counts.keys(), key=lambda x: -pattern_counts[x])[:10]:
    print(f"  {pattern}: {pattern_counts[pattern]} times")

print("\n" + "=" * 70)
print("Hypothesis")
print("=" * 70)
print("""
This file contains RAW SONAR FRAMES (not RSD wrapped).

Each frame:
- Starts with 0x06 (frame type marker)
- Followed by variable-length data (200-400 bytes typically)
- Multiple frames concatenated without RSD container

This appears to be a STREAMING FORMAT (like what would come from
the sonar device directly) rather than the standard RSD container format.

This is consistent with:
- Garmin UHD format raw export
- Real-time sonar stream capture
- Alternative data format specification

Need to determine:
1. What the next bytes mean (0x04, 0x7c, 0x4b in frame 0)
2. Where the payload data starts/ends
3. What the GT54 transducer metadata is
""")
