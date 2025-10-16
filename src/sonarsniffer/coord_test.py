#!/usr/bin/env python3
"""
Test coordinate extraction from RSD file
"""

import mmap
import struct
from core_shared import find_magic, _mapunit_to_deg

RECORD_MAGIC = 0xB7E9DA86

def test_coordinate_extraction(rsd_path: str):
    """Test coordinate extraction with broader range"""
    
    with open(rsd_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            
            # Find first few headers
            magic_bytes = struct.pack('<I', RECORD_MAGIC)
            headers = []
            current_pos = 0x5000
            
            for _ in range(5):
                magic_pos = find_magic(mm, magic_bytes, current_pos, len(mm))
                if magic_pos is None:
                    break
                headers.append(magic_pos)
                current_pos = magic_pos + 4
            
            print(f"Found {len(headers)} headers")
            
            for i, header_pos in enumerate(headers):
                print(f"\nHeader {i} at {header_pos:08x}")
                
                # Get record size
                if i + 1 < len(headers):
                    record_size = headers[i + 1] - header_pos
                else:
                    record_size = min(len(mm) - header_pos, 0x1000)
                
                print(f"Record size: {record_size}")
                
                data_start = header_pos + 4
                data_end = header_pos + record_size
                
                # Look for potential coordinates anywhere in the record
                found_coords = []
                
                for offset in range(data_start, data_end - 8, 4):
                    try:
                        val1 = struct.unpack('<i', mm[offset:offset+4])[0]
                        val2 = struct.unpack('<i', mm[offset+4:offset+8])[0]
                        
                        lat = _mapunit_to_deg(val1)
                        lon = _mapunit_to_deg(val2)
                        
                        # Check for any reasonable geographic coordinates
                        if (-90 <= lat <= 90) and (-180 <= lon <= 180):
                            # Also check if they look like a real location (not 0,0 or close)
                            if abs(lat) > 0.1 and abs(lon) > 0.1:
                                found_coords.append((offset - data_start, lat, lon))
                        
                    except Exception:
                        continue
                
                print(f"Found {len(found_coords)} potential coordinate pairs:")
                for rel_offset, lat, lon in found_coords:
                    print(f"  +{rel_offset:3d}: {lat:8.5f}, {lon:8.5f}")

if __name__ == "__main__":
    test_coordinate_extraction("126SV-UHD2-GT54.RSD")