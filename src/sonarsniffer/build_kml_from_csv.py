#!/usr/bin/env python3
from pathlib import Path
import argparse, csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seq-start", type=int, default=None)
    ap.add_argument("--seq-end", type=int, default=None)
    a = ap.parse_args()
    
    pts = []
    with Path(a.csv).open("r", encoding="utf-8", newline="") as fp:
        r = csv.DictReader(fp)
        for row in r:
            try:
                s = int(float(row.get("seq") or 0))
                if a.seq_start is not None and s < a.seq_start: continue
                if a.seq_end is not None and s > a.seq_end: continue
                
                lat = float(row.get("lat")) if row.get("lat") else None
                lon = float(row.get("lon")) if row.get("lon") else None
                if lat is None or lon is None: continue
                pts.append((lon, lat))
            except Exception:
                pass
    
    if not pts:
        raise SystemExit("No lat/lon points.")
        
    k = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        '<Placemark>',
        f'<name>{Path(a.csv).stem}</name>',
        '<LineString>',
        '<tessellate>1</tessellate>',
        '<coordinates>'
    ]
    
    for lon, lat in pts:
        k.append(f"{lon},{lat},0")
        
    k.extend([
        '</coordinates>',
        '</LineString>',
        '</Placemark>',
        '</Document>',
        '</kml>'
    ])
    
    Path(a.out).write_text("\n".join(k), encoding="utf-8")
    print("Wrote KML:", a.out, "points:", len(pts))

if __name__ == "__main__":
    main()