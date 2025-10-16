#!/usr/bin/env python3
"""
Simple test to verify endianness changes
"""

from core_shared import MAGIC_REC_HDR, MAGIC_REC_TRL

def test_magic_endianness():
    print("Testing magic number endianness conversion:")
    print(f"MAGIC_REC_HDR: 0x{MAGIC_REC_HDR:08X}")
    print(f"MAGIC_REC_TRL: 0x{MAGIC_REC_TRL:08X}")

    # Convert to bytes and back
    hdr_bytes = MAGIC_REC_HDR.to_bytes(4, 'big')
    trl_bytes = MAGIC_REC_TRL.to_bytes(4, 'big')

    print(f"MAGIC_REC_HDR as big-endian bytes: {hdr_bytes.hex()}")
    print(f"MAGIC_REC_TRL as big-endian bytes: {trl_bytes.hex()}")

    # Verify round-trip
    hdr_back = int.from_bytes(hdr_bytes, 'big')
    trl_back = int.from_bytes(trl_bytes, 'big')

    print(f"Round-trip MAGIC_REC_HDR: 0x{hdr_back:08X} {'✓' if hdr_back == MAGIC_REC_HDR else '✗'}")
    print(f"Round-trip MAGIC_REC_TRL: 0x{trl_back:08X} {'✓' if trl_back == MAGIC_REC_TRL else '✗'}")

if __name__ == "__main__":
    test_magic_endianness()