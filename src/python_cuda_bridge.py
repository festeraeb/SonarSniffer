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


def encode_frames_to_mp4(frames: Iterable[np.ndarray], output_path: str, fps: int = 30, output_height: int | None = None) -> str:
    """Encode frames to MP4 using ffmpeg (software encoding).

    Args:
        frames: Iterable of numpy arrays (H x W) or (H x W x 3) uint8
        output_path: Path to write MP4 file
        fps: Frames per second
        output_height: optional output height in pixels; if provided ffmpeg will
                       scale the video to (width x output_height) during encoding

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

    # Build ffmpeg command up to reading stdin
    cmd = [
        ffmpeg_exe,
        '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'rgb24',
        '-s', f'{w}x{h}',
        '-r', str(fps),
        '-i', '-',
    ]

    # If an output height is requested and differs from input, add a scale filter
    if output_height is not None and output_height > 0 and output_height != h:
        cmd += ['-vf', f'scale={w}:{int(output_height)}']

    # Continue with audio/encoding settings
    cmd += [
        '-an',
        '-vcodec', 'libx264',
        '-pix_fmt', 'yuv420p',
        output_path,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Stream frames from a dedicated writer thread so a slow/blocked ffmpeg
    # doesn't hang the caller during large video exports. Make timeout
    # configurable via FFMPEG_ENCODE_TIMEOUT (seconds).
    import threading
    import queue
    import os

    timeout = int(os.environ.get('FFMPEG_ENCODE_TIMEOUT', '600'))
    exc_q: "queue.Queue[Exception]" = queue.Queue()

    def to_rgb_bytes(frame: np.ndarray) -> bytes:
        if frame.ndim == 2:
            rgb = np.stack([frame, frame, frame], axis=-1)
        elif frame.ndim == 3 and frame.shape[2] == 3:
            rgb = frame
        else:
            raise RuntimeError("Unsupported frame shape for encoding")
        return rgb.tobytes()

    def writer_thread_fn():
        try:
            # write the first frame we already peeked
            proc.stdin.write(to_rgb_bytes(first_frame))
            for frame in frames:
                proc.stdin.write(to_rgb_bytes(frame))
            try:
                proc.stdin.close()
            except Exception:
                pass
        except BrokenPipeError:
            # ffmpeg closed stdin (e.g., codec error). Try to capture stderr to provide a
            # more helpful message for diagnostics.
            try:
                proc.kill()
            except Exception:
                pass
            stderr_text = ''
            try:
                err = proc.stderr.read()
                if err:
                    stderr_text = err.decode('utf-8', errors='ignore')
            except Exception:
                stderr_text = ''
            msg = "ffmpeg closed stdin (broken pipe) during write"
            if stderr_text:
                msg = f"{msg}; ffmpeg stderr: {stderr_text}"
            exc_q.put(RuntimeError(msg))
        except Exception as e:
            try:
                proc.kill()
            except Exception:
                pass
            stderr_text = ''
            try:
                err = proc.stderr.read()
                if err:
                    stderr_text = err.decode('utf-8', errors='ignore')
            except Exception:
                stderr_text = ''
            if stderr_text:
                exc_q.put(RuntimeError(f"write failed: {e}; ffmpeg stderr: {stderr_text}"))
            else:
                exc_q.put(e)
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    writer = threading.Thread(target=writer_thread_fn, daemon=True)
    writer.start()

    try:
        out, err = proc.communicate(timeout=timeout)
        # If writer raised an exception, surface it here
        if not exc_q.empty():
            raise exc_q.get()
        if proc.returncode != 0:
            stderr_text = err.decode('utf-8', errors='ignore')
            raise RuntimeError(f"ffmpeg failed: {stderr_text}")

    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("ffmpeg timed out during encoding")

    return output_path
