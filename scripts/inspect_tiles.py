from PIL import Image
from zipfile import ZipFile
from pathlib import Path
from io import BytesIO
import numpy as np

kmz = Path("outputs/holloway_run/Holloway.kmz")
with ZipFile(kmz) as zf:
    tiles = sorted(
        [n for n in zf.namelist() if n.startswith("tiles/") and n.endswith(".png")]
    )
    print("Found", len(tiles), "tiles; showing stats for first 6")
    for t in tiles[:6]:
        data = zf.read(t)
        img = Image.open(BytesIO(data))
        arr = np.asarray(img.convert("L"))
        h, w = arr.shape
        left = arr[:, : w // 2]
        right = arr[:, w // 2 :]
        print(
            t,
            "size",
            arr.shape,
            "left mean",
            float(left.mean()),
            "right mean",
            float(right.mean()),
        )
