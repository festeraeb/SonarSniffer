"""Bridge to a gstreamer-based encoder binary (gst_encoder).

This module provides `encode_frames_to_mp4(frames, output_path, fps=30, width=None, height=None, encoder=None)`
which spawns the `gst_encoder` binary and streams raw RGB frames to it via stdin.
"""
import os
import shutil
import subprocess
import threading
import queue
from typing import Iterable
import numpy as np

GST_ENCODER_PATH = os.environ.get("GST_ENCODER_PATH") or os.path.join("tools", "gstreamer_encoder", "target", "debug", "gst_encoder")
if os.name == 'nt' and not GST_ENCODER_PATH.lower().endswith('.exe'):
    GST_ENCODER_PATH += '.exe'


def _find_encoder_binary():
    if os.path.exists(GST_ENCODER_PATH):
        return GST_ENCODER_PATH
    # Try PATH
    p = shutil.which("gst_encoder")
    if p:
        return p
    return None


def encode_frames_to_mp4(frames: Iterable[np.ndarray], output_path: str, fps: int = 30, width: int = None, height: int = None, encoder: str = None) -> str:
    """Encode frames by launching the gst_encoder binary and streaming frames.

    frames: iterable of HxWx3 uint8 arrays (or 2D grayscale arrays)
    """
    bin_path = _find_encoder_binary()
    if not bin_path:
        raise RuntimeError("gst_encoder binary not found; build tools/gstreamer_encoder or install gst_encoder on PATH")

    # Determine frame size from first frame
    it = iter(frames)
    first = None
    for f in it:
        first = f
        break
    if first is None:
        raise RuntimeError("No frames provided for encoding")

    # Normalize to RGB uint8
    def to_rgb_bytes(frame: np.ndarray) -> bytes:
        if frame.ndim == 2:
            rgb = np.stack([frame, frame, frame], axis=-1)
        elif frame.ndim == 3 and frame.shape[2] == 3:
            rgb = frame
        else:
            raise RuntimeError("Unsupported frame shape for encoding")
        return rgb.tobytes()

    H, W = first.shape[:2]
    if height is None:
        height = H
    if width is None:
        width = W

    cmd = [bin_path, f"--width={width}", f"--height={height}", f"--fps={fps}", f"--output={output_path}"]
    if encoder:
        cmd.append(f"--encoder={encoder}")

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    exc_q: "queue.Queue[Exception]" = queue.Queue()

    def writer():
        try:
            proc.stdin.write(to_rgb_bytes(first))
            for frame in it:
                proc.stdin.write(to_rgb_bytes(frame))
            try:
                proc.stdin.close()
            except Exception:
                pass
        except Exception as e:
            exc_q.put(e)
            try:
                proc.kill()
            except Exception:
                pass

    th = threading.Thread(target=writer, daemon=True)
    th.start()

    out, err = proc.communicate()
    if not exc_q.empty():
        raise exc_q.get()
    if proc.returncode != 0:
        stderr_text = err.decode("utf-8", errors="ignore")
        # If the chosen hardware h264 encoder failed, try falling back to a software encoder x264enc
        if encoder and 'h264' in encoder.lower() and encoder.lower() not in ('x264enc', 'avenc_h264'):
            try:
                # retry with x264enc
                return encode_frames_to_mp4([first] + list(it), output_path, fps=fps, width=width, height=height, encoder='x264enc')
            except Exception:
                pass
        raise RuntimeError(f"gstreamer encoder failed: {stderr_text}")

    return output_path


def encode_frames_with_fallback(frames, output_path: str, fps: int = 30, width: int = None, height: int = None, encoder: str = None) -> str:
    """Try gstreamer encoder first, fall back to disk+gst image-seq mode, then ffmpeg as last resort."""
    try:
        return encode_frames_to_mp4(frames, output_path, fps=fps, width=width, height=height, encoder=encoder)
    except Exception as e:
        # Streaming attempt failed - try image-sequence path via gst_encoder
        try:
            from sonarsniffer.telemetry import report_runtime_error
            report_runtime_error(e, feature_used='video_export', processing_step='encoder_streaming_failed', details={'attempt': 'streaming', 'encoder': encoder, 'video_out': output_path})
        except Exception:
            pass

        # Materialize frames into a list so we can attempt image-sequence mode and fallback
        try:
            if isinstance(frames, (list, tuple)):
                frames_list = list(frames)
            else:
                frames_list = list(frames)
        except Exception:
            raise RuntimeError('Failed to materialize frames for fallback paths')

        # Try gst_encoder image-sequence mode
        try:
            return _encode_via_gst_image_sequence(frames_list, output_path, fps, width=width, height=height, encoder=encoder)
        except Exception as e2:
            try:
                from sonarsniffer.telemetry import report_runtime_error
                report_runtime_error(e2, feature_used='video_export', processing_step='encoder_image_seq_failed', details={'attempt': 'image_seq', 'encoder': encoder, 'video_out': output_path})
            except Exception:
                pass
            # Final fallback: ffmpeg
            return _encode_via_ffmpeg_from_disk(frames_list, output_path, fps)



# Fallback: if streaming encoder is not usable (Broken pipe, missing plugins, etc.),
# write frames to a temporary directory as PNGs and call ffmpeg to encode the sequence.
import tempfile
from PIL import Image
import subprocess as _sub
import shutil as _shutil


def _encode_via_ffmpeg_from_disk(frames_iter, output_path: str, fps: int):
    tmpdir = tempfile.mkdtemp(prefix="sonarsniffer_gst_fallback_")
    try:
        pattern = _shutil.os.path.join(tmpdir, "frame_%06d.png")
        # Write frames
        for i, f in enumerate(frames_iter):
            img = f
            if img.ndim == 3 and img.shape[2] == 3:
                pil = Image.fromarray(img)
            elif img.ndim == 2:
                pil = Image.fromarray(img).convert('L').convert('RGB')
            else:
                raise RuntimeError("Unsupported frame shape for disk fallback")
            pil.save(_shutil.os.path.join(tmpdir, f"frame_{i:06d}.png"))

        ffmpeg_exe = _shutil.which('ffmpeg')
        if not ffmpeg_exe:
            raise RuntimeError('ffmpeg not found on PATH; required for disk fallback')

        cmd = [ffmpeg_exe, '-y', '-framerate', str(fps), '-i', _shutil.os.path.join(tmpdir, 'frame_%06d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_path]
        proc = _sub.Popen(cmd, stdout=_sub.PIPE, stderr=_sub.PIPE)
        out, err = proc.communicate()
        if proc.returncode != 0:
            stderr_text = err.decode('utf-8', errors='ignore')
            raise RuntimeError(f'ffmpeg fallback encoding failed: {stderr_text}')
        return output_path
    finally:
        # Cleanup
        try:
            for fn in _shutil.os.listdir(tmpdir):
                _shutil.os.remove(_shutil.os.path.join(tmpdir, fn))
            _shutil.os.rmdir(tmpdir)
        except Exception:
            pass


def _encode_via_gst_image_sequence(frames_iter, output_path: str, fps: int, width: int | None = None, height: int | None = None, encoder: str | None = None):
    """Write frames to a temporary dir and invoke gst_encoder with --input_dir mode.

    Returns the path to the encoded file on success.
    """
    tmpdir = tempfile.mkdtemp(prefix="sonarsniffer_gst_seq_")
    try:
        count = 0
        first_shape = None
        for i, f in enumerate(frames_iter):
            img = f
            if img.ndim == 3 and img.shape[2] == 3:
                pil = Image.fromarray(img)
            elif img.ndim == 2:
                pil = Image.fromarray(img).convert('L').convert('RGB')
            else:
                raise RuntimeError("Unsupported frame shape for gst image sequence")
            if first_shape is None:
                first_shape = pil.size[::-1]
            pil.save(_shutil.os.path.join(tmpdir, f"frame_{i:06d}.png"))
            count += 1

        if count == 0:
            raise RuntimeError("No frames to write for gst image sequence")

        if width is None or height is None:
            if first_shape is not None:
                height = height or first_shape[0]
                width = width or first_shape[1]
            else:
                raise RuntimeError("Unable to infer frame size for gst image sequence")

        bin_path = _find_encoder_binary()
        if not bin_path:
            raise RuntimeError("gst_encoder binary not found; build tools/gstreamer_encoder or install gst_encoder on PATH")

        cmd = [bin_path, f"--input-dir={tmpdir}", f"--width={width}", f"--height={height}", f"--fps={fps}", f"--output={output_path}"]
        if encoder:
            cmd.append(f"--encoder={encoder}")

        proc = _sub.Popen(cmd, stdout=_sub.PIPE, stderr=_sub.PIPE)
        out, err = proc.communicate()
        if proc.returncode != 0:
            stderr_text = err.decode('utf-8', errors='ignore')
            # If a hardware h264 encoder failed to link to mp4mux, try an explicit gst-launch pipeline that inserts h264parse
            if encoder and 'h264' in encoder.lower():
                gst_launch = _shutil.which('gst-launch-1.0') or _shutil.which('gst-launch')
                if gst_launch:
                    try:
                        # Build gst-launch pipeline using multifilesrc -> pngdec -> videoconvert -> encoder -> h264parse -> queue -> mp4mux -> filesink
                        loc = _shutil.os.path.join(tmpdir, 'frame_%06d.png')
                        gst_pipeline = f"multifilesrc location={loc} index=0 ! pngdec ! videoconvert ! {encoder} ! h264parse ! queue ! mp4mux ! filesink location={output_path}"
                        gst_cmd = [gst_launch, gst_pipeline]
                        proc2 = _sub.Popen(gst_cmd, stdout=_sub.PIPE, stderr=_sub.PIPE, shell=False)
                        out2, err2 = proc2.communicate()
                        if proc2.returncode == 0:
                            return output_path
                        else:
                            stderr_text2 = err2.decode('utf-8', errors='ignore')
                            # If gst-launch failed, try a software-encoder fallback (x264enc) with the gst_encoder binary
                            try:
                                cmd2 = [bin_path, f"--input-dir={tmpdir}", f"--width={width}", f"--height={height}", f"--fps={fps}", f"--output={output_path}", "--encoder=x264enc"]
                                proc3 = _sub.Popen(cmd2, stdout=_sub.PIPE, stderr=_sub.PIPE)
                                out3, err3 = proc3.communicate()
                                if proc3.returncode == 0:
                                    return output_path
                                else:
                                    stderr_text3 = err3.decode('utf-8', errors='ignore')
                                    raise RuntimeError(f"gst_encoder image-sequence mode failed: {stderr_text}; gst-launch failed: {stderr_text2}; x264enc attempt failed: {stderr_text3}")
                            except Exception as ex2:
                                raise RuntimeError(f"gst_encoder image-sequence mode failed: {stderr_text}; gst-launch failed: {stderr_text2}; x264enc attempt failed: {ex2}")
                    except Exception as ex:
                        raise RuntimeError(f"gst_encoder image-sequence mode failed: {stderr_text}; additionally gst-launch attempt failed: {ex}")
            raise RuntimeError(f"gst_encoder image-sequence mode failed: {stderr_text}")
        return output_path
    finally:
        # Cleanup temporary files
        try:
            for fn in _shutil.os.listdir(tmpdir):
                _shutil.os.remove(_shutil.os.path.join(tmpdir, fn))
            _shutil.os.rmdir(tmpdir)
        except Exception:
            pass

