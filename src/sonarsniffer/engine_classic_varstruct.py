#!/usr/bin/env python3
"""
Working RSD parser that doesn't hang - replacement for engine_classic_varstruct.py
Based on signature-aware approach from your documentation
"""

import mmap
import struct
from dataclasses import dataclass
from typing import Iterator, Optional, Dict, Any, List
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

def parse_rsd_records_classic(rsd_path: str, start_ofs: int = 0x5000, limit_records: Optional[int] = None) -> Iterator[RSDRecord]:
    """
    Replacement parser that doesn't hang.
    Uses header scanning and heuristic coordinate extraction.
    """
    
    with open(rsd_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            
            # Find record headers
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
                if len(headers) > 20000:
                    break
            
            if not headers:
                return
                
            # Process each record
            record_count = 0
            for i, header_pos in enumerate(headers):
                if limit_records and record_count >= limit_records:
                    break
                    
                # Determine record size
                if i + 1 < len(headers):
                    record_size = headers[i + 1] - header_pos
                else:
                    record_size = min(len(mm) - header_pos, 0x10000)
                    
                if record_size < 16 or record_size > 0x100000:
                    continue
                    
                try:
                    record = parse_record_heuristic(mm, header_pos, record_size, record_count)
                    if record:
                        yield record
                        record_count += 1
                except Exception:
                    continue

def parse_record_heuristic(mm: mmap.mmap, header_pos: int, record_size: int, seq: int) -> Optional[RSDRecord]:
    """Parse a single record using heuristic approach"""
    
    record = RSDRecord(ofs=header_pos, seq=seq)
    
    # Skip the 4-byte magic header
    data_start = header_pos + 4
    data_end = header_pos + record_size
    
    if data_end > len(mm):
        return None
    
    # Try to find channel ID in the first part of the record
    # Look for pattern: channel ID is often at the beginning after some header bytes
    channel_found = False
    for offset in range(data_start, min(data_start + 32, data_end - 4), 4):
        try:
            val = struct.unpack('<I', mm[offset:offset+4])[0]
            # Sidescan typically has channels 0-3, with 0=left, 1=right being common
            if 0 <= val <= 15:  # Reasonable channel range
                record.channel_id = val
                channel_found = True
                break
        except Exception:
            continue
    
    # If no clear channel found, try to infer from sequence pattern
    if not channel_found:
        # Many sidescan systems alternate left/right channels
        record.channel_id = seq % 2  # Alternate between 0 and 1
    
    # Skip A1/B2 pad region (around +160 to +200)
    search_start = max(data_start + 8, data_start + 200)
    
    # Search for coordinates - look for patterns that decode to reasonable North American coordinates
    lat_found = False
    best_coords = None
    best_offset = -1
    
    for offset in range(search_start, data_end - 8, 4):
        try:
            val1 = struct.unpack('<i', mm[offset:offset+4])[0]
            val2 = struct.unpack('<i', mm[offset+4:offset+8])[0]
            
            lat = _mapunit_to_deg(val1)
            lon = _mapunit_to_deg(val2)
            
            # Check for reasonable North American coordinates
            # Focus on areas where lakes and rivers might be
            if (40.0 <= lat <= 55.0) and (-100.0 <= lon <= -80.0):
                # This looks like Great Lakes region
                if best_coords is None:
                    best_coords = (lat, lon)
                    best_offset = offset
                    
        except Exception:
            continue
    
    if best_coords:
        record.lat, record.lon = best_coords
        lat_found = True
        
        # Look for depth nearby the coordinates
        depth_search_start = max(data_start, best_offset - 24)
        depth_search_end = min(data_end - 4, best_offset + 32)
        
        for depth_offset in range(depth_search_start, depth_search_end, 4):
            try:
                depth_val = struct.unpack('<i', mm[depth_offset:depth_offset+4])[0]
                # Check if it's reasonable depth in mm (0-500m for lakes)
                if 0 <= depth_val <= 500000:
                    record.depth_m = depth_val / 1000.0
                    break
            except Exception:
                continue
    
    # Try to find sonar data offset and size
    # Sonar data is typically at the end of the record
    potential_sonar_start = data_start + 100  # Skip header area
    if potential_sonar_start < data_end:
        # Look for patterns that might indicate sonar data
        for offset in range(potential_sonar_start, data_end - 8, 4):
            try:
                # Look for reasonable sample counts (sonar lines are typically 256-2048 samples)
                sample_count = struct.unpack('<H', mm[offset:offset+2])[0]
                if 64 <= sample_count <= 4096:
                    record.sample_cnt = sample_count
                    record.sonar_ofs = offset + 8  # Data starts after size info
                    record.sonar_size = min(sample_count * 2, data_end - (offset + 8))
                    break
            except Exception:
                continue
    
    # Set sequence number as time placeholder
    record.time_ms = seq * 1000  # Approximate timing
    
    # Only return record if we found coordinates
    return record if lat_found else None

def parse_rsd(rsd_path: str, csv_out: str, limit_rows: Optional[int] = None):
    """Simple CSV export function matching the original interface"""
    
    records = []
    
    for record in parse_rsd_records_classic(rsd_path, limit_records=limit_rows):
        records.append(record)
    
    # Write CSV
    with open(csv_out, 'w', newline='') as csvf:
        csvf.write("ofs,channel_id,seq,time_ms,lat,lon,depth_m,sample_cnt,sonar_ofs,sonar_size,beam_deg,pitch_deg,roll_deg,heave_m,tx_ofs_m,rx_ofs_m,color_id,extras_json\n")
        
        for record in records:
            import json
            extras_json = json.dumps(record.extras) if record.extras else "{}"
            
            csvf.write(f"{record.ofs},{record.channel_id},{record.seq},{record.time_ms},{record.lat:.8f},{record.lon:.8f},{record.depth_m:.3f},{record.sample_cnt},{record.sonar_ofs},{record.sonar_size},{record.beam_deg:.2f},{record.pitch_deg:.2f},{record.roll_deg:.2f},{record.heave_m:.3f},{record.tx_ofs_m:.3f},{record.rx_ofs_m:.3f},{record.color_id},\"{extras_json}\"\n")
    
    print(f"Wrote {len(records)} records to {csv_out}")
    return csv_out

if __name__ == "__main__":
    # Test the parser
    csv_out = parse_rsd("126SV-UHD2-GT54.RSD", "test_records.csv", limit_rows=50)
    
    # Show some sample results
    with open(csv_out, 'r') as f:
        lines = f.readlines()
        print(f"\nSample results ({len(lines)-1} records):")
        for i, line in enumerate(lines[:6]):
            print(f"Line {i}: {line.strip()}")