"""FFmpeg-based video encoding bridge with graceful fallback.

Provides a minimal `encode_frames_to_mp4` function that accepts an
iterator/list of numpy uint8 frames (H x W x 3 or H x W grayscale) and
encodes them to MP4 via ffmpeg subprocess. If a GPU bridge is available
it should provide the same function signature and be used instead.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Iterable
import numpy as np


def encode_frames_to_mp4(frames: Iterable[np.ndarray], output_path: str, fps: int = 30) -> str:
    """Encode frames to MP4 using ffmpeg (software encoding).

    Args:
        frames: Iterable of numpy arrays (H x W) or (H x W x 3) uint8
        output_path: Path to write MP4 file
        fps: Frames per second

    Returns:
        Path to written file (string)

    Raises:
        RuntimeError: if ffmpeg is not available or encoding fails
    """
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        raise RuntimeError("ffmpeg not found on PATH; install ffmpeg to enable video export")

    output_path = str(Path(output_path))

    # Prepare a pipe-based ffmpeg command that reads raw frames (rgb24)
    # Convert frames to rgb24 if grayscale
    import io

    # Use first frame to determine size
    first_frame = None
    for f in frames:
        first_frame = f
        break
    if first_frame is None:
        raise RuntimeError("No frames provided for encoding")

    h, w = first_frame.shape[:2]

    # Build ffmpeg command
    cmd = [
        ffmpeg_exe,
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'rgb24',
        '-s', f'{w}x{h}',
        '-r', str(fps),
        '-i', '-',
        '-an',
        '-vcodec', 'libx264',
        '-pix_fmt', 'yuv420p',
        output_path,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # Write first frame and remaining frames to stdin
        def to_rgb_bytes(frame: np.ndarray) -> bytes:
            if frame.ndim == 2:
                rgb = np.stack([frame, frame, frame], axis=-1)
            elif frame.ndim == 3 and frame.shape[2] == 3:
                rgb = frame
            else:
                raise RuntimeError("Unsupported frame shape for encoding")
            return rgb.tobytes()

        proc.stdin.write(to_rgb_bytes(first_frame))
        for frame in frames:
            proc.stdin.write(to_rgb_bytes(frame))

        proc.stdin.close()
        out, err = proc.communicate(timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {err.decode('utf-8', errors='ignore')}" )

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("ffmpeg timed out during encoding")

    return output_path
