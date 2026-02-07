from src.sonarsniffer.pipeline import scans_to_waterfall_image
from src.sonarsniffer.canonical import Scan
import numpy as np

s1 = Scan(
    id="a",
    time_ms=0,
    lat=42.0,
    lon=-87.0,
    samples=np.linspace(0, 1, 100),
    sample_rate=1,
    sample_format="float",
    beam_deg=None,
    metadata={"seq": 1, "channel_id": 4},
)
s2 = Scan(
    id="b",
    time_ms=0,
    lat=42.0,
    lon=-87.0,
    samples=np.linspace(1, 0, 90),
    sample_rate=1,
    sample_format="float",
    beam_deg=None,
    metadata={"seq": 1, "channel_id": 5},
)
s3 = Scan(
    id="c",
    time_ms=0,
    lat=42.1,
    lon=-87.1,
    samples=np.linspace(0.2, 0.8, 80),
    sample_rate=1,
    sample_format="float",
    beam_deg=None,
    metadata={"seq": 2, "channel_id": 4},
)
out = "test_waterfall.png"
scans_to_waterfall_image([s1, s2, s3], out)
print("Wrote", out)
