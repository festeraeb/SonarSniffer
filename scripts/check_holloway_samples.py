#!/usr/bin/env python3
"""Count how many records in Holloway.RSD include sonar samples and show sample stats."""
from sonarsniffer.engine_nextgen_syncfirst import parse_rsd_records_nextgen

PATH = 'data/Holloway.RSD'

cnt = 0
cnt_with_payload = 0
sample_cnt_total = 0
first_with_payload = None

for i, r in enumerate(parse_rsd_records_nextgen(PATH, limit_records=0)):
    cnt += 1
    if getattr(r, 'sonar_size', 0) and getattr(r, 'sonar_cnt', getattr(r, 'sample_cnt', 0)):
        cnt_with_payload += 1
        sample_cnt_total += getattr(r, 'sample_cnt', 0) or 0
        if first_with_payload is None:
            first_with_payload = (i, r.ofs, r.sonar_ofs, r.sonar_size, r.sample_cnt)
    if i and i % 20000 == 0:
        print('processed', i, 'records')

print('Total records scanned:', cnt)
print('Records with sonar payload:', cnt_with_payload)
print('Total sample count (sum):', sample_cnt_total)
if first_with_payload:
    print('First payload at index/rec/ofs/sonar_ofs/sonar_size/sample_cnt:', first_with_payload)
else:
    print('No payloads found in file according to parser heuristics.')
