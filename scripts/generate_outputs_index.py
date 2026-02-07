#!/usr/bin/env python3
"""Generate a simple `index.html` in outputs/holloway_smoke that links and previews files.

Usage: python3 scripts/generate_outputs_index.py
"""
from pathlib import Path
import sys
import time
import subprocess

try:
    from PIL import Image
except Exception:
    Image = None

OUT = Path("outputs/holloway_smoke")
if not OUT.exists():
    print("Directory outputs/holloway_smoke not found")
    sys.exit(1)

files = sorted([p for p in OUT.iterdir() if p.is_file() and p.name != "index.html"])
# classify
videos = [p for p in files if p.suffix.lower() in (".mp4", ".mov", ".mkv")]
images = [p for p in files if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")]
others = [p for p in files if p not in videos + images]

meta_lines = []
for p in files:
    sz = p.stat().st_size
    info = f"{p.name}\t{sz} bytes"
    if Image and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
        try:
            im = Image.open(p)
            info += f"\tIMAGE {im.size[0]}x{im.size[1]}"
        except Exception:
            pass
    if p.suffix.lower() in (".mp4", ".mov", ".mkv"):
        try:
            out = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_name,width,height,avg_frame_rate",
                    "-of",
                    "default=noprint_wrappers=1",
                    str(p),
                ],
                stderr=subprocess.STDOUT,
            )
            info += "\n" + out.decode().strip()
        except Exception:
            pass
    meta_lines.append(info)

# Use the shipped template index.html if present; otherwise append some dynamic entries
TEMPLATE = OUT / "index.html"
if TEMPLATE.exists():
    # update generation time placeholder
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("<!--GEN_TIME-->", time.strftime("%Y-%m-%d %H:%M:%S"))
    TEMPLATE.write_text(text, encoding="utf-8")
    print("Wrote:", TEMPLATE)
else:
    # fallback: produce a minimal index
    html = [
        "<!doctype html>",
        '<html><head><meta charset="utf-8"><title>Outputs</title></head><body>',
        "<h1>Outputs</h1>",
        "<ul>",
    ]
    for p in files:
        html.append(
            f'<li><a href="{p.name}">{p.name}</a> - {p.stat().st_size} bytes</li>'
        )
    html.append("</ul>")
    html.append("<pre>")
    html.extend(meta_lines)
    html.append("</pre></body></html>")
    TEMPLATE.write_text("\n".join(html), encoding="utf-8")
    print("Wrote fallback index:", TEMPLATE)

print("\nSummary:")
print("Videos:", ", ".join([p.name for p in videos]))
print("Images:", ", ".join([p.name for p in images]))
print("Other:", ", ".join([p.name for p in others]))
print("\nTo regenerate run: python3 scripts/generate_outputs_index.py")
