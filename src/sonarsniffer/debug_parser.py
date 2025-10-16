#!/usr/bin/env python3
"""
Debug version of engine_classic_varstruct to identify where it hangs
"""

import mmap
import struct
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple, Any, Dict, List
from core_shared import find_magic, _parse_varstruct, _mapunit_to_deg

@dataclass
class RSDRecord:
    ofs: int = 0
    channel_id: int = 0
    seq: int = 0
    time_ms: int = 0
    lat: float = 0.0
    lon: float = 0.0
    depth_m: float = 0.0
    sample_cnt: int = 0
    sonar_ofs: int = 0
    sonar_size: int = 0
    beam_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    heave_m: float = 0.0
    tx_ofs_m: float = 0.0
    rx_ofs_m: float = 0.0
    color_id: int = 0
    extras: Dict[str, Any] = None

    def __post_init__(self):
        if self.extras is None:
            self.extras = {}

RECORD_MAGIC = 0xB7E9DA86

def debug_parse_rsd_records_classic(mm: mmap.mmap, start_ofs: int = 0x5000, limit_records: Optional[int] = None) -> Iterator[RSDRecord]:
    """Debug version with extensive logging"""
    print(f"DEBUG: Starting parse at offset {start_ofs:08x}")
    
    # Find first magic header
    print("DEBUG: Step 1 - Finding first magic header...")
    magic_ofs = find_magic(mm, struct.pack('<I', RECORD_MAGIC), start_ofs, len(mm))
    if magic_ofs is None:
        print("DEBUG: No magic header found!")
        return
    
    print(f"DEBUG: Found first magic at {magic_ofs:08x}")
    
    record_count = 0
    current_ofs = magic_ofs
    
    while current_ofs < len(mm) - 16:
        print(f"DEBUG: Processing record {record_count} at offset {current_ofs:08x}")
        
        if limit_records and record_count >= limit_records:
            print(f"DEBUG: Hit limit of {limit_records} records")
            break
            
        # Check for magic at current position
        try:
            magic_check = struct.unpack('<I', mm[current_ofs:current_ofs+4])[0]
            if magic_check != RECORD_MAGIC:
                print(f"DEBUG: No magic at {current_ofs:08x}, found {magic_check:08x}")
                break
        except Exception as e:
            print(f"DEBUG: Error reading magic at {current_ofs:08x}: {e}")
            break
            
        print("DEBUG: Magic confirmed, finding next magic...")
        
        # Find next magic to determine record size
        next_magic_ofs = find_magic(mm, struct.pack('<I', RECORD_MAGIC), current_ofs + 4, len(mm))
        if next_magic_ofs is None:
            # Last record - use remaining file size
            record_size = len(mm) - current_ofs
            print(f"DEBUG: Last record, size = {record_size}")
        else:
            record_size = next_magic_ofs - current_ofs
            print(f"DEBUG: Next magic at {next_magic_ofs:08x}, record size = {record_size}")
            
        if record_size < 16 or record_size > 0x100000:  # Sanity check
            print(f"DEBUG: Invalid record size {record_size}, breaking")
            break
            
        print("DEBUG: Attempting to parse varstruct...")
        
        # Try to parse the record
        try:
            fields, parsed_size = _parse_varstruct(mm, current_ofs + 4, crc_mode='warn')
            print(f"DEBUG: Parsed {len(fields)} fields, parsed_size = {parsed_size}")
            
            # Create record with debug info
            record = RSDRecord(ofs=current_ofs)
            
            # Quick field processing (simplified)
            for field_id, field_data in fields.items():
                if field_id == 1:  # channel_id
                    record.channel_id = field_data if isinstance(field_data, int) else 0
                elif field_id == 2:  # lat
                    record.lat = _mapunit_to_deg(field_data) if isinstance(field_data, int) else 0.0
                elif field_id == 3:  # lon
                    record.lon = _mapunit_to_deg(field_data) if isinstance(field_data, int) else 0.0
                    
            print(f"DEBUG: Created record - channel={record.channel_id}, lat={record.lat:.6f}, lon={record.lon:.6f}")
            
            yield record
            record_count += 1
            
            print(f"DEBUG: Yielded record {record_count}, moving to next...")
            
        except Exception as e:
            print(f"DEBUG: Error parsing record at {current_ofs:08x}: {e}")
            # Try to skip to next magic
            skip_ofs = find_magic(mm, struct.pack('<I', RECORD_MAGIC), current_ofs + 4, len(mm))
            if skip_ofs is None:
                print("DEBUG: No more magic found, breaking")
                break
            current_ofs = skip_ofs
            continue
            
        # Move to next record
        if next_magic_ofs is None:
            break
        current_ofs = next_magic_ofs
        
    print(f"DEBUG: Parse complete, processed {record_count} records")

if __name__ == "__main__":
    print("Testing debug parser...")
    
    rsd_path = r"C:\Users\Thoma\Desktop\Data Samples\Sonar000.RSD"
    
    try:
        with open(rsd_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                print(f"File size: {len(mm)} bytes")
                
                count = 0
                for record in debug_parse_rsd_records_classic(mm, limit_records=2):
                    count += 1
                    print(f"Got record {count}: lat={record.lat:.6f}, lon={record.lon:.6f}")
                    
                print(f"Total records processed: {count}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()