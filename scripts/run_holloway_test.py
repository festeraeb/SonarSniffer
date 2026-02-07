import sys

sys.path.insert(0, "src")
from sonarsniffer.pipeline import export_full

if __name__ == "__main__":
    print("Starting export...")
    r = export_full(
        "data/Holloway.RSD",
        "outputs/holloway_test_fix",
        formats=["waterfall", "mp4", "tiles", "kmz", "mbtiles"],
    )
    print("Done:", r)
