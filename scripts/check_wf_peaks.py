from PIL import Image
import numpy as np

im = Image.open("outputs/holloway_run/Holloway_waterfall.png").convert("L")
arr = np.asarray(im).astype(float)
H, W = arr.shape
mid = W // 2
left = arr[:, :mid]
right = arr[:, mid : mid + (W - mid)]
print("Waterfall size WxH:", W, "x", H)
print("Left peak col", int(np.argmax(left.mean(axis=0))), "of", left.shape[1])
print("Right peak col", int(np.argmax(right.mean(axis=0))), "of", right.shape[1])
print(
    "Left max",
    float(left.mean(axis=0).max()),
    "Right max",
    float(right.mean(axis=0).max()),
)
