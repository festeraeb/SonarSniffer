#!/usr/bin/env python3
# engine_classic_varstruct.py — classic-hard (strict CRC) + stall watchdog

import os, mmap, struct
from dataclasses import dataclass
from typing import Optional, Iterable, Callable
from core_shared import MAGIC_REC_HDR, MAGIC_REC_TRL, _parse_varstruct, _mapunit_to_deg, _read_varint_from, find_magic, set_progress_hook, _emit

@dataclass
class RSDRecord:
    ofs:int; channel_id:Optional[int]; seq:int; time_ms:int; data_size:int
    lat:Optional[float]; lon:Optional[float]; depth_m:Optional[float]
    sample_cnt:Optional[int]; sonar_ofs:Optional[int]; sonar_size:Optional[int]

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

            yield RSDRecord(hdr_start, ch, seq, time_ms, data_sz, lat, lon, depth, sample,
                            sonar_ofs if sonar_len>0 else None, sonar_len if sonar_len>0 else None)
            count += 1
            if count % 250 == 0:
                _emit((trailer_pos/limit)*100.0, f"Records: {count}")
            if limit_records and count >= limit_records: break

            pos = hdr_start + chunk_size

        _emit(100.0, f"Done (classic). Records: {count}")
        mm.close()
