import json, csv, os

SRC = 'parse_ignore_results.json'
if not os.path.exists(SRC):
    print('Missing parse_ignore_results.json; run parse_ignore.py first')
    raise SystemExit(1)

data = json.load(open(SRC, 'r', encoding='utf-8'))

for fname, info in data.items():
    base = os.path.splitext(os.path.basename(fname))[0]
    outname = base + '_parsed.csv'
    recs = info.get('records', [])
    if not recs:
        print(f'No records for {fname}, skipping CSV')
        continue
    with open(outname, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        # Write all available fields from records
        w.writerow(['ofs','channel_id','seq','time_ms','lat','lon','depth_m','sample_cnt','beam_deg','pitch_deg','roll_deg','heave_m','tx_ofs_m','rx_ofs_m','color_id','hdr_crc_variant','body_crc_variant'])
        for r in recs:
            extras = r.get('extras', {}) or {}
            hdrv = extras.get('hdr_crc_variant') or extras.get('hdr_crc', '')
            bodyv = extras.get('body_crc_variant') or extras.get('body_crc', '')
            w.writerow([
                r.get('ofs',''),
                r.get('channel_id',''),
                r.get('seq',''),
                r.get('time_ms',''),
                r.get('lat',''),
                r.get('lon',''),
                r.get('depth_m',''),
                r.get('sample_cnt',''),
                r.get('beam_deg',''),
                r.get('pitch_deg',''),
                r.get('roll_deg',''),
                r.get('heave_m',''),
                r.get('tx_ofs_m',''),
                r.get('rx_ofs_m',''),
                r.get('color_id',''),
                hdrv,
                bodyv
            ])
    print(f'Wrote {outname} ({len(recs)} rows)')
print('Done')
