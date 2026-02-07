from PIL import Image
import numpy as np
from pathlib import Path

wf = Path("outputs/holloway_run/Holloway_waterfall.png")
if not wf.exists():
    print("Waterfall not found")
    raise SystemExit(1)

im = Image.open(wf).convert("L")
arr = np.asarray(im)
H, W = arr.shape
print("Waterfall size:", H, W)
# Split in middle
mid = W // 2
left = arr[:, :mid]
right = arr[:, mid : mid + (W - mid)]
# Resize to same width if odd
if left.shape[1] != right.shape[1]:
    minw = min(left.shape[1], right.shape[1])
    left = left[:, :minw]
    right = right[:, :minw]

# Compute per-row correlation
corrs = []
from scipy.stats import pearsonr

for i in range(H):
    l = left[i].astype(np.float32)
    r = right[i].astype(np.float32)
    # skip constant rows
    if l.std() < 1e-3 or r.std() < 1e-3:
        corrs.append(0.0)
        continue
    corrs.append(pearsonr(l, r)[0])

print("Mean correlation left/right (pearson):", float(np.nanmean(corrs)))
# Cross-correlation of entire halves
l_flat = left.ravel().astype(np.float32)
r_flat = right.ravel().astype(np.float32)
# Normalize
l_flat = (l_flat - l_flat.mean()) / (l_flat.std() + 1e-9)
r_flat = (r_flat - r_flat.mean()) / (r_flat.std() + 1e-9)
xc = np.correlate(l_flat, r_flat, mode="full")
lag = np.argmax(xc) - (len(l_flat) - 1)
print("Cross-correlation peak lag:", int(lag), "peak value:", float(xc.max()))

# Seam test: compute vertical seam between half boundary
seam_diff = np.abs(arr[:, mid - 1].astype(np.float32) - arr[:, mid].astype(np.float32))
print("Seam diff stats: mean", float(seam_diff.mean()), "max", int(seam_diff.max()))

# Check for duplicate halves (identical)
identical = np.all(left == right)
print("Left and right identical:", bool(identical))

# Save small debug images
Image.fromarray(left).save("outputs/holloway_run/debug_left.png")
Image.fromarray(right).save("outputs/holloway_run/debug_right.png")
print("Wrote debug images: debug_left.png, debug_right.png")
