#!/usr/bin/env python3
"""
Script to inspect Garmin RSD file structure and dump all fields
"""

import os, mmap, struct
from core_shared import MAGIC_REC_HDR, MAGIC_REC_TRL, _parse_varstruct, find_magic

def inspect_rsd(path: str):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        limit = size
        mbytes = MAGIC_REC_HDR.to_bytes(4, 'big')

        print(f"Inspecting {path}")
        print(f"File size: {size} bytes")
        print(f"Looking for magic: 0x{MAGIC_REC_HDR:08X} (big-endian)")

        j = find_magic(mm, mbytes, 0, limit)
        if j < 0:
            print("No magic found")
            mm.close()
            return

        print(f"Found magic at offset 0x{j:08X}")

        # Try to parse the first record
        pos_magic = j
        for back in range(1, 65):
            try:
                start = pos_magic - back
                if start < 0: break
                hdr, body_start = _parse_varstruct(mm, start, limit, crc_mode='warn')
                if struct.unpack('>I', hdr.get(0, b'\x00'*4)[:4])[0] == MAGIC_REC_HDR:
                    print(f"Header found at 0x{start:08X}, body at 0x{body_start:08X}")
                    print("Header fields:")
                    for k, v in hdr.items():
                        if len(v) <= 8:
                            print(f"  Field {k}: {v.hex()} (len {len(v)})")
                        else:
                            print(f"  Field {k}: {v[:8].hex()}... (len {len(v)})")

                    print("Body fields:")
                    body, body_end = _parse_varstruct(mm, body_start, limit, crc_mode='warn')
                    for k, v in body.items():
                        if len(v) <= 8:
                            print(f"  Field {k}: {v.hex()} (len {len(v)})")
                        else:
                            print(f"  Field {k}: {v[:8].hex()}... (len {len(v)})")

                    # Also show raw body data
                    body_size = min(100, body_end - body_start)
                    raw_body = bytes(mm[body_start:body_start + body_size])
                    print(f"Raw body data ({body_size} bytes): {raw_body.hex()}")

                    break
            except Exception as e:
                print(f"Back {back}: {e}")
                continue

        mm.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python inspect_rsd.py <rsd_file>")
        sys.exit(1)
    inspect_rsd(sys.argv[1])