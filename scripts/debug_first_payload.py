from sonarsniffer.engine_nextgen_syncfirst import parse_rsd_records_nextgen
from sonarsniffer.adapters.rsd_adapter import rsd_record_to_scan

p = 'data/Holloway.RSD'
for r in parse_rsd_records_nextgen(p, limit_records=200):
    if getattr(r, 'sonar_size', 0):
        print('Found', r.ofs, r.sonar_ofs, r.sonar_size, r.sample_cnt)
        s = rsd_record_to_scan(r, p)
        print('scan samples type:', type(s.samples), 'len' , None if s.samples is None else s.samples.size)
        break
print('done')
