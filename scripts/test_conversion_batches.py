from sonarsniffer.sonar_parser import SonarParser
from sonarsniffer.canonical import to_scan
from types import SimpleNamespace

p='data/Holloway.RSD'
parser = SonarParser()
for batch in parser.parse_file_in_chunks(p, batch_size=100):
    for i, r in enumerate(batch[:10]):
        print('record type:', type(r), 'keys' if isinstance(r,dict) else r)
        if isinstance(r, dict):
            safe = {
                'ofs': r.get('ofs', 0),
                'channel_id': r.get('channel_id', 0),
                'seq': r.get('seq', 0),
                'time_ms': r.get('time_ms', 0),
                'lat': r.get('lat', 0.0) or 0.0,
                'lon': r.get('lon', 0.0) or 0.0,
                'depth_m': r.get('depth_m', 0.0) or 0.0,
                'sample_cnt': r.get('sample_cnt', 0) or 0,
                'sonar_ofs': r.get('sonar_ofs', 0) or 0,
                'sonar_size': r.get('sonar_size', 0) or 0,
                'beam_deg': r.get('beam_deg', 0.0) or 0.0,
                'extras': r.get('extras', {}),
            }
            rec=SimpleNamespace(**safe)
        else:
            rec=r
        scan=to_scan('rsd', rec, p)
        print(' -> scan.samples type', type(scan.samples), 'len', None if scan.samples is None else scan.samples.size)
    break
print('done')