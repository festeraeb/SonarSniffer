"""Lightweight Python fallback for sidescan waterfall generation.

If the compiled Rust acceleration module is unavailable, this module
provides a simple, pure-Python implementation of `generate_sidescan_waterfall`
that normalizes and weakly enhances the flattened sonar intensity buffer.
"""
from typing import Iterable, List
import numpy as np


def generate_sidescan_waterfall(flat_buffer: Iterable[float], width: int, height: int) -> List[int]:
    """Convert a flattened float buffer into an 8-bit waterfall image.

    Args:
        flat_buffer: Iterable of floats (0.0-1.0 or arbitrary range) with length width*height
        width: image width (samples per ping)
        height: image height (number of pings)

    Returns:
        A flat list of uint8 values length width*height suitable for reshaping
        into (height, width).
    """
    arr = np.asarray(list(flat_buffer), dtype=np.float32)
    if arr.size != width * height:
        # If lengths differ, attempt safe reshape by truncation/padding
        arr = np.resize(arr, width * height)

    # Basic normalization and contrast stretching
    lo = np.nanpercentile(arr, 2)
    hi = np.nanpercentile(arr, 98)
    if hi - lo <= 1e-6:
        scaled = np.clip(arr, 0.0, 1.0)
    else:
        scaled = (arr - lo) / (hi - lo)
        scaled = np.clip(scaled, 0.0, 1.0)

    # Apply a mild gamma to enhance darker returns
    gamma = 0.9
    scaled = np.power(scaled, gamma)

    # Convert to 8-bit
    img8 = (scaled * 255.0).astype(np.uint8)
    return img8.tolist()
