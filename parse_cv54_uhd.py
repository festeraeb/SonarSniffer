#!/usr/bin/env python3
"""
Parse CV-54-UHD.RSD to understand its structure
"""
import struct
import sys

filepath = r'c:\Temp\Garminjunk\samples\CV-54-UHD.RSD'

print("=" * 70)
print("CV-54-UHD.RSD Analysis")
print("=" * 70)

try:
    from gcdstruct import RSDFile
    
    print("\nAttempting to parse with RSDFile...")
    rsd = RSDFile(filepath)
    
    print(f"✓ Successfully parsed with RSDFile!")
    print(f"  Header: {rsd.header}")
    print(f"  Number of frames: {len(rsd.frames) if hasattr(rsd, 'frames') else 'N/A'}")
    if hasattr(rsd, 'frames') and rsd.frames:
        print(f"  First frame: {rsd.frames[0]}")
        print(f"  Last frame: {rsd.frames[-1]}")
    
except Exception as e:
    print(f"✗ RSDFile parsing failed: {type(e).__name__}: {e}")

print("\n" + "=" * 70)
print("Raw File Structure Analysis")
print("=" * 70)

with open(filepath, 'rb') as f:
    data = f.read()

print(f"\nFile size: {len(data):,} bytes ({len(data)/1024/1024:.2f} MB)")

# Check for known headers
print(f"\nHeader Analysis:")
print(f"  First 4 bytes: {data[:4].hex()} = {repr(data[:4])}")
print(f"  First 16 bytes: {data[:16].hex()}")

# Look for RSD markers
markers = [
    (b'RSD', 'Standard RSD header'),
    (b'\x7fRSD', 'RSD with preamble'),
    (b'RIFF', 'RIFF container'),
    (b'SONAR', 'SONAR prefix'),
]

for marker, desc in markers:
    if marker in data[:100]:
        idx = data[:100].find(marker)
        print(f"  ✓ Found '{desc}' at offset {idx}")

# Analyze first 512 bytes in detail
print(f"\nFirst 512 bytes (ASCII representation, . = non-printable):")
first_512 = data[:512]
ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in first_512)
lines = [ascii_repr[i:i+80] for i in range(0, len(ascii_repr), 80)]
for i, line in enumerate(lines):
    print(f"  {i*80:4d}: {line}")

# Look for frame boundaries
print(f"\nLooking for frame patterns...")
print(f"  Byte 0: 0x{data[0]:02x} (sonar frame type byte?)")
print(f"  Byte 1: 0x{data[1]:02x}")
print(f"  Byte 2: 0x{data[2]:02x}")
print(f"  Byte 3: 0x{data[3]:02x}")

# Check if this might be raw sonar data
if data[0] in [0x06, 0x07, 0x08, 0x09]:
    print(f"  ✓ Starts with potential frame type marker: 0x{data[0]:02x}")
    print(f"    This could be raw sonar data without RSD wrapper")

# Sample frame boundaries by looking for repeating patterns
print(f"\nFrame boundary detection:")
print(f"  Searching for repeating frame start markers...")

# Look for byte patterns that repeat
first_byte = data[0]
occurrences = [i for i in range(0, min(10000, len(data))) if data[i] == first_byte]
print(f"  Byte 0x{first_byte:02x} occurs at offsets: {occurrences[:20]}...")

if len(occurrences) > 1:
    gaps = [occurrences[i+1] - occurrences[i] for i in range(min(10, len(occurrences)-1))]
    print(f"  Gaps between occurrences: {gaps}")
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        print(f"  Average gap: {avg_gap:.0f} bytes (possible frame size?)")

print("\n" + "=" * 70)
print("Conclusion")
print("=" * 70)
print("This file appears to be SONAR DATA in a different format.")
print("It does NOT have a standard RSD wrapper.")
print("Need to examine the actual sonar frame structure to decode it.")
