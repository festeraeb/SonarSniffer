#!/usr/bin/env python3
"""
Simple signature-aware RSD parser based on your documentation
"""

import mmap
import struct
from dataclasses import dataclass
from typing import Iterator, Optional, Dict, Any
from core_shared import find_magic, _mapunit_to_deg

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

def parse_rsd_heuristic(mm: mmap.mmap, start_ofs: int = 0x5000, limit_records: Optional[int] = None) -> Iterator[RSDRecord]:
    """
    Signature-aware parser based on your documentation.
    Uses header scanning and heuristic field detection.
    """
    
    # 1) Header sweep: scan for record magic
    magic_bytes = struct.pack('<I', RECORD_MAGIC)
    headers = []
    
    current_pos = start_ofs
    while current_pos < len(mm) - 16:
        magic_pos = find_magic(mm, magic_bytes, current_pos, len(mm))
        if magic_pos is None:
            break
        headers.append(magic_pos)
        current_pos = magic_pos + 4
        
        # Limit header search for performance
        if len(headers) > 10000:
            break
    
    if not headers:
        return
        
    print(f"Found {len(headers)} record headers")
    
    # 2) Process each record using header boundaries
    for i, header_pos in enumerate(headers):
        if limit_records and i >= limit_records:
            break
            
        # Determine record size
        if i + 1 < len(headers):
            record_size = headers[i + 1] - header_pos
        else:
            record_size = min(len(mm) - header_pos, 0x10000)  # Cap at 64KB for last record
            
        if record_size < 16 or record_size > 0x100000:
            continue
            
        try:
            record = parse_record_heuristic(mm, header_pos, record_size)
            if record:
                yield record
        except Exception as e:
            print(f"Error parsing record at {header_pos:08x}: {e}")
            continue

def parse_record_heuristic(mm: mmap.mmap, header_pos: int, record_size: int) -> Optional[RSDRecord]:
    """
    Heuristic record parsing based on your documentation patterns:
    - Float block near +96..+128 from header
    - Skip A1/B2 pad runs near +160..+200
    - Search for MapUnits (lat/lon pairs)
    - Hunt for depth_mm nearby
    """
    
    record = RSDRecord(ofs=header_pos)
    
    # Skip the 4-byte magic header
    data_start = header_pos + 4
    data_end = header_pos + record_size
    
    if data_end > len(mm):
        return None
    
    # Look for float block near +96..+128
    float_block_start = data_start + 92  # +96 from original header
    if float_block_start + 32 <= data_end:
        try:
            floats = []
            for offset in range(float_block_start, min(float_block_start + 32, data_end - 4), 4):
                float_val = struct.unpack('<f', mm[offset:offset+4])[0]
                floats.append(float_val)
            
            # Store float block in extras
            record.extras['float_block'] = floats
            
        except Exception:
            pass
    
    # Skip A1/B2 pad region (~+160 to +200)
    search_start = max(data_start + 8, data_start + 200)  # Skip pad region
    
    # Search for MapUnits (lat/lon pairs) - two consecutive int32s that decode to plausible coordinates
    # Holloway Reservoir area: 48.47-48.51°N, -92.57°W
    lat_found = False
    
    for offset in range(search_start, data_end - 8, 4):
        try:
            # Read two consecutive int32s
            val1 = struct.unpack('<i', mm[offset:offset+4])[0]
            val2 = struct.unpack('<i', mm[offset+4:offset+8])[0]
            
            lat = _mapunit_to_deg(val1)
            lon = _mapunit_to_deg(val2)
            
            # Check if coordinates are plausible - broader range for North America
            if (25.0 <= lat <= 75.0) and (-180.0 <= lon <= -50.0):
                record.lat = lat
                record.lon = lon
                lat_found = True
                
                # Look for depth nearby (±24 bytes)
                depth_search_start = max(data_start, offset - 24)
                depth_search_end = min(data_end - 4, offset + 32)
                
                for depth_offset in range(depth_search_start, depth_search_end, 4):
                    try:
                        depth_val = struct.unpack('<i', mm[depth_offset:depth_offset+4])[0]
                        # Check if it's reasonable depth in mm (0-150m)
                        if 0 <= depth_val <= 150000:
                            record.depth_m = depth_val / 1000.0
                            break
                    except Exception:
                        continue
                        
                break
                
        except Exception:
            continue
    
    # Try to find channel_id in early part of record
    for offset in range(data_start, min(data_start + 64, data_end - 4), 4):
        try:
            val = struct.unpack('<I', mm[offset:offset+4])[0]
            if 0 <= val <= 255:  # Reasonable channel ID
                record.channel_id = val
                break
        except Exception:
            continue
    
    # Only return record if we found coordinates
    if lat_found:
        return record
    else:
        return None

def parse_rsd(rsd_path: str, csv_out: str, limit_rows: Optional[int] = None):
    """Simple CSV export function"""
    
    records = []
    
    with open(rsd_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for record in parse_rsd_heuristic(mm, limit_records=limit_rows):
                records.append(record)
    
    # Write CSV
    with open(csv_out, 'w', newline='') as csvf:
        csvf.write("ofs,channel_id,seq,time_ms,lat,lon,depth_m,sample_cnt,sonar_ofs,sonar_size,beam_deg,pitch_deg,roll_deg,heave_m,tx_ofs_m,rx_ofs_m,color_id,extras_json\n")
        
        for record in records:
            import json
            extras_json = json.dumps(record.extras) if record.extras else "{}"
            
            csvf.write(f"{record.ofs},{record.channel_id},{record.seq},{record.time_ms},{record.lat:.8f},{record.lon:.8f},{record.depth_m:.3f},{record.sample_cnt},{record.sonar_ofs},{record.sonar_size},{record.beam_deg:.2f},{record.pitch_deg:.2f},{record.roll_deg:.2f},{record.heave_m:.3f},{record.tx_ofs_m:.3f},{record.rx_ofs_m:.3f},{record.color_id},\"{extras_json}\"\n")
    
    return csv_out

if __name__ == "__main__":
    rsd_path = "126SV-UHD2-GT54.RSD"
    csv_out = "heuristic_test.csv"
    
    print("Testing heuristic parser...")
    
    result = parse_rsd(rsd_path, csv_out, limit_rows=20)
    print(f"Results written to: {result}")
    
    # Show some results
    with open(csv_out, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:5]):
            print(f"Line {i}: {line.strip()}")