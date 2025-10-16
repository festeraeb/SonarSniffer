#!/usr/bin/env python3
# engine_classic_varstruct.py — classic-hard (strict CRC) + stall watchdog

import os, mmap, struct
from dataclasses import dataclass
from typing import Optional, Iterable, Callable, Dict, Any, Tuple
from core_shared import MAGIC_REC_HDR, MAGIC_REC_TRL, _parse_varstruct, _mapunit_to_deg, _read_varint_from, find_magic, set_progress_hook, _emit

@dataclass
class RSDRecord:
    """Record data from a Garmin RSD file."""
    ofs: int                # File offset where record starts
    channel_id: Optional[int]         # Channel/transducer identifier 
    seq: int               # Sequence number
    time_ms: int           # Timestamp in milliseconds
    data_size: int         # Size of the data section
    lat: Optional[float]             # Latitude in degrees
    lon: Optional[float]             # Longitude in degrees
    depth_m: Optional[float]         # Water depth in meters
    sample_cnt: Optional[int]        # Number of samples in sonar data
    sonar_ofs: Optional[int]         # Offset to sonar sample data
    sonar_size: Optional[int]        # Size of sonar sample data
    beam_deg: Optional[float] = None        # Beam angle in degrees
    pitch_deg: Optional[float] = None       # Pitch angle in degrees
    roll_deg: Optional[float] = None        # Roll angle in degrees
    heave_m: Optional[float] = None    # Heave in meters
    tx_ofs_m: Optional[float] = None   # Transmitter offset in meters
    rx_ofs_m: Optional[float] = None   # Receiver offset in meters 
    color_id: Optional[int] = None     # Color scheme ID
    extras: Dict[str,Any] = None  # Additional decoded fields
    
    def __post_init__(self):
        if self.extras is None:
            self.extras = {}

def parse_rsd_records_classic(path:str, limit_records:int=0, progress:Callable[[float,str],None]=None) -> Iterable[RSDRecord]:
    if progress: set_progress_hook(progress)
    size=os.path.getsize(path)
    with open(path,'rb') as f:
        mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
        limit = size
        mbytes = MAGIC_REC_HDR.to_bytes(4,'little')

        _emit(0.0, "Finding first sync…")
        j = find_magic(mm, mbytes, 0, limit)
        if j < 0:
            _emit(0.0, "No sync found.")
            mm.close(); return
        pos = j - 1
        _emit((pos/limit)*100.0, f"First sync at 0x{j:X}")

        count = 0
        last_magic = None
        stuck_hits = 0
        MAX_STUCK = 2

        while pos + 12 < limit:
            k = find_magic(mm, mbytes, max(pos,0), limit)
            if k < 0: break
            pos_magic = k
            _emit((pos_magic/limit)*100.0, f"Header @ 0x{pos_magic:X}")

            if pos_magic == last_magic:
                stuck_hits += 1
                if stuck_hits > MAX_STUCK:
                    pos = pos_magic + 8
                    _emit((pos/limit)*100.0, f"Skipping corrupt header @ 0x{pos_magic:X}")
                    last_magic = None
                    stuck_hits = 0
                    continue
            else:
                last_magic = pos_magic
                stuck_hits = 0

            hdr_block=None
            for back in range(1,65):
                try:
                    start = pos_magic - back
                    if start < 0: break
                    hdr, body_start = _parse_varstruct(mm, start, limit, crc_mode='strict')
                    if struct.unpack('<I', hdr.get(0,b'\x00'*4)[:4])[0] == MAGIC_REC_HDR:
                        hdr_block=(hdr,start,body_start); break
                except Exception:
                    pass
            if not hdr_block:
                pos = pos_magic + 4
                _emit((pos/limit)*100.0, f"Advancing after header parse fail @ 0x{pos_magic:X}")
                continue

            hdr,hdr_start,body_start = hdr_block
            seq     = struct.unpack('<I', hdr.get(2,b'\x00'*4)[:4])[0]
            time_ms = struct.unpack('<I', hdr.get(5,b'\x00'*4)[:4])[0]
            data_sz = struct.unpack('<H', (hdr.get(4,b'\x00\x00')[:2] or b'\x00\x00'))[0]

            lat=lon=depth=None; sample=None; ch=None; used=0
            try:
                body, body_end = _parse_varstruct(mm, body_start, limit, crc_mode='strict')
                used = max(0, body_end-body_start)
                if 0 in body: ch = int.from_bytes(body[0][:4].ljust(4,b'\x00'),'little')
                if 9 in body and len(body[9])>=4:  lat = _mapunit_to_deg(int.from_bytes(body[9][:4],'little',signed=True))
                if 10 in body and len(body[10])>=4: lon = _mapunit_to_deg(int.from_bytes(body[10][:4],'little',signed=True))
                if 1 in body:
                    try:
                        v,_ = _read_varint_from(mm[body_start:body_start+len(body[1])],0,len(body[1])); depth = v/1000.0
                    except Exception: pass
                if 7 in body: sample = int.from_bytes(body[7][:4].ljust(4,b'\x00'),'little')
            except Exception:
                pos = pos_magic + 4
                _emit((pos/limit)*100.0, f"Advancing after body parse fail @ 0x{pos_magic:X}")
                continue

            sonar_ofs = body_start + used
            sonar_len = max(0, data_sz - used) if data_sz > 0 else 0

            trailer_pos = body_start + data_sz
            if trailer_pos + 12 > limit:
                break
            tr_magic, chunk_size, tr_crc = struct.unpack('<III', mm[trailer_pos:trailer_pos+12])
            if tr_magic != MAGIC_REC_TRL or chunk_size <= 0:
                pos = pos_magic + 4
                _emit((pos/limit)*100.0, f"Advancing after trailer mismatch @ 0x{trailer_pos:X}")
                continue

            yield RSDRecord(
                ofs=hdr_start, 
                channel_id=ch, 
                seq=seq, 
                time_ms=time_ms, 
                data_size=data_sz, 
                lat=lat, 
                lon=lon, 
                depth_m=depth, 
                sample_cnt=sample,
                sonar_ofs=sonar_ofs if sonar_len>0 else None, 
                sonar_size=sonar_len if sonar_len>0 else None
            )
            count += 1
            if count % 250 == 0:
                _emit((trailer_pos/limit)*100.0, f"Records: {count}")
            if limit_records and count >= limit_records: break

            pos = hdr_start + chunk_size

        _emit(100.0, f"Done (classic). Records: {count}")
        mm.close()


def parse_rsd(rsd_path: str, out_dir: str, max_records: Optional[int] = None) -> Tuple[int, str, str]:
    """Parse RSD file and write records to CSV.
    Returns (record_count, csv_path, log_path).
    """
    # Setup output paths
    csv_path = os.path.join(out_dir, os.path.basename(rsd_path) + '.csv')
    log_path = os.path.join(out_dir, os.path.basename(rsd_path) + '.log')
    
    # Create output directory if it doesn't exist
    os.makedirs(out_dir, exist_ok=True)
    
    # Open log and CSV files for writing
    count = 0
    with open(csv_path, 'w') as csv_f, \
         open(log_path, 'w') as log_f:
        
        # Write CSV header
        fields = ['ofs', 'channel_id', 'seq', 'time_ms', 'lat', 'lon', 'depth_m',
                 'sample_cnt', 'sonar_ofs', 'sonar_size', 'beam_deg', 'pitch_deg', 'roll_deg',
                 'heave_m', 'tx_ofs_m', 'rx_ofs_m', 'color_id', 'extras']
        csv_f.write(','.join(fields) + '\n')
        
        # Parse and write records - parse_rsd_records_classic handles file opening internally
        try:
            for rec in parse_rsd_records_classic(rsd_path, limit_records=max_records):
                count += 1
                values = []
                for field in fields:
                    value = getattr(rec, field, '')
                    if value is None:
                        values.append('')
                    elif field == 'extras' and isinstance(value, dict):
                        # Convert dict to JSON string
                        import json
                        values.append(json.dumps(value) if value else '')
                    else:
                        values.append(str(value))
                csv_f.write(','.join(values) + '\n')
                
                if count % 250 == 0:
                    log_f.write(f"Parsed {count} records\n")
                    log_f.flush()
                    
        except Exception as e:
            log_f.write(f"Error during parsing: {str(e)}\n")
            raise
    
    return count, csv_path, log_path
