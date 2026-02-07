import zipfile
from pathlib import Path

kmz = Path("outputs/holloway_run/Holloway.kmz")
if not kmz.exists():
    print("KMZ not found")
    raise SystemExit(1)
with zipfile.ZipFile(kmz, "r") as zf:
    print("Files in kmz:", zf.namelist()[:20])
    kml = zf.read("doc.kml").decode("utf-8")
    print("doc.kml head:\n", "\n".join(kml.splitlines()[:40]))
    # show a sample tile entry
    tiles = [n for n in zf.namelist() if n.startswith("tiles/") and n.endswith(".png")]
    print("Sample tiles:", tiles[:5])
    if tiles:
        info = zf.getinfo(tiles[0])
        print("Sample tile size:", info.file_size)
