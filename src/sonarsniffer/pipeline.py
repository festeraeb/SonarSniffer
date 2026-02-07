#!/usr/bin/env python3
"""High-level pipeline to export waterfall, video, KML, and other artifacts
from a sonar file using canonical Scan objects.
"""
from typing import Iterable, List
import os
from pathlib import Path
import numpy as np
from .sonar_parser import SonarParser
# rsd_video_core may live at package level (src/rsd_video_core.py) or inside package
try:
    from .rsd_video_core import generate_sidescan_waterfall
except Exception:
    try:
        from rsd_video_core import generate_sidescan_waterfall
    except Exception:
        raise
# Encoder bridge (ffmpeg) may also be top-level. We also support a gstreamer-based encoder binary.
VIDEO_ENCODER = os.environ.get('VIDEO_ENCODER', '').lower()
encode_frames_to_mp4 = None
if VIDEO_ENCODER == 'gstreamer':
    try:
        from .gstreamer_bridge import encode_frames_with_fallback as encode_frames_to_mp4  # type: ignore
    except Exception:
        try:
            from gstreamer_bridge import encode_frames_with_fallback as encode_frames_to_mp4  # type: ignore
        except Exception:
            encode_frames_to_mp4 = None
# If not configured, fall back to python_cuda_bridge (ffmpeg-based)
if encode_frames_to_mp4 is None:
    try:
        from .python_cuda_bridge import encode_frames_to_mp4  # type: ignore
    except Exception:
        try:
            from python_cuda_bridge import encode_frames_to_mp4  # type: ignore
        except Exception:
            encode_frames_to_mp4 = None

from .canonical import Scan
from PIL import Image


# Palette mapping helper
def apply_palette(arr: np.ndarray, palette: str) -> np.ndarray:
    """Map a 2D uint8 grayscale array to an RGB uint8 array according to named palette."""
    a = np.asarray(arr, dtype=np.uint8)
    v = a.astype(np.float32) / 255.0
    h, w = a.shape
    # Default grayscale
    if not palette:
        return np.stack([a, a, a], axis=-1)
    p = palette.lower()
    if p == "amber":
        r = a
        g = np.clip((a.astype(np.float32) * 0.75), 0, 255).astype(np.uint8)
        b = np.zeros_like(a, dtype=np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p == "blue":
        r = np.clip((v * 0.20 * 255.0), 0, 255).astype(np.uint8)
        g = np.clip((v * 0.60 * 255.0), 0, 255).astype(np.uint8)
        b = np.clip((v * 1.00 * 255.0), 0, 255).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p == "green":
        r = np.clip((v * 0.20 * 255.0), 0, 255).astype(np.uint8)
        g = np.clip((v * 1.00 * 255.0), 0, 255).astype(np.uint8)
        b = np.clip((v * 0.20 * 255.0), 0, 255).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p == "yellow":
        r = np.clip((v * 1.00 * 255.0), 0, 255).astype(np.uint8)
        g = np.clip((v * 0.90 * 255.0), 0, 255).astype(np.uint8)
        b = np.clip((v * 0.10 * 255.0), 0, 255).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p in ("pink", "purple-pink"):
        r = np.clip((v * 1.00 * 255.0), 0, 255).astype(np.uint8)
        g = np.clip((v * 0.30 * 255.0), 0, 255).astype(np.uint8)
        b = np.clip((v * 0.90 * 255.0), 0, 255).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p in ("red", "orange", "copper"):
        r = np.clip((v * 1.00 * 255.0), 0, 255).astype(np.uint8)
        g = np.clip((v * 0.40 * 255.0), 0, 255).astype(np.uint8)
        b = np.clip((v * 0.10 * 255.0), 0, 255).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)
    if p in ("classic", "multi", "classic multi"):
        # low->blue, mid->green, high->red gradient
        c0 = np.array([0, 0, 255], dtype=np.float32)
        c1 = np.array([0, 255, 0], dtype=np.float32)
        c2 = np.array([255, 0, 0], dtype=np.float32)
        t = v * 2.0
        t0 = np.clip(t, 0.0, 1.0)
        t1 = np.clip(t - 1.0, 0.0, 1.0)
        col = np.zeros((h, w, 3), dtype=np.float32)
        col += (1.0 - t0)[..., None] * c0
        col += t0[..., None] * (1.0 - t1)[..., None] * c1
        col += t1[..., None] * c2
        return np.clip(col, 0, 255).astype(np.uint8)
    if p in ("night", "inverted"):
        inv = (255 - a).astype(np.uint8)
        return apply_palette(inv, "classic")
    # fallback grayscale
    return np.stack([a, a, a], axis=-1)


def scans_to_waterfall_image(
    scans: Iterable[Scan],
    output_path: str,
    width: int = None,
    color: str | None = "amber",
    merge_channels: bool = True,
    channel_gap: int = 16,
    pairing_debug: bool = False,
    alignment_mode: str = "auto",
    debug_out: str | None = None,
    beam_gain: bool = False,
    nadir_mask: int = 0,
):
    """Build a vertical waterfall image from Scan objects and save PNG.

    If `color=='amber'` the grayscale waterfall will be mapped to an amber
    RGB palette to improve contrast for visual inspection and video outputs.

    When `merge_channels=True` and consecutive scans share the same `seq` but
    different `channel_id`, they will be merged horizontally into a single
    row by placing the higher channel id on the left and flipping it horizontally
    (this matches common port/starboard conventions for Garmin RSD files).
    """
    # Convert iterable to list of Scan to allow lookahead grouping
    scans_list = list(scans)
    rows = []
    max_width = 0

    # Preprocess scans (beam-angle gain compensation, nadir masking)
    def _preprocess_scan(s: Scan):
        arr = None
        if s.samples is None:
            return None
        arr = np.asarray(s.samples, dtype=np.float32).copy()
        applied_gain = 1.0
        masked = 0
        # Beam-angle gain correction (normalize amplitude vs beam angle)
        if beam_gain and s.beam_deg is not None:
            try:
                import math

                theta = math.radians(float(s.beam_deg) or 0.0)
                cosv = max(0.2, abs(math.cos(theta)))
                # divide by cos to compensate for spreading loss (capped)
                applied_gain = 1.0 / cosv
                # Avoid extreme amplification
                applied_gain = min(applied_gain, 4.0)
                arr = arr * (1.0 / applied_gain)
            except Exception:
                applied_gain = 1.0
        # Nadir masking: zero out central samples to remove near-transducer artifact
        if nadir_mask and nadir_mask > 0:
            mid = arr.size // 2
            lo = max(0, int(mid - nadir_mask))
            hi = min(arr.size, int(mid + nadir_mask))
            arr[lo:hi] = 0
            masked = hi - lo
        # store debug metrics in metadata for later use
        s.metadata = dict(s.metadata or {})
        s.metadata.update(
            {
                "applied_gain": float(applied_gain),
                "nadir_masked": int(masked),
                "peak_pos": int(np.argmax(arr)) if arr.size > 0 else None,
                "mean": float(np.mean(arr)) if arr.size > 0 else 0.0,
            }
        )
        return arr

    # If requested, first group by sequence id and compose pairs using a
    # seam-minimization heuristic. This is more robust than only checking
    # immediate neighbors and handles interleaved or non-adjacent channel records.
    def _compose_pairwise(group: list) -> list:
        out_rows = []
        for items in group:
            if len(items) == 1:
                s = items[0]
                if s.samples is None:
                    continue
                pr = _preprocess_scan(s)
                if pr is None:
                    continue
                out_rows.append(pr)
                continue
            # Select two channels (if more than two, take first two after sorting by channel_id)
            try:
                items_sorted = sorted(
                    items, key=lambda x: x.metadata.get("channel_id", 0)
                )
            except Exception:
                items_sorted = items[:2]
            # Apply preprocessing to both channels so beam/nadir corrections are consistent
            pa = _preprocess_scan(items_sorted[0])
            pb = _preprocess_scan(items_sorted[1])
            # Fallback to raw samples if preprocessing returned None
            a = (
                pa
                if pa is not None
                else np.asarray(items_sorted[0].samples, dtype=np.float32)
            )
            b = (
                pb
                if pb is not None
                else np.asarray(items_sorted[1].samples, dtype=np.float32)
            )
            L = max(a.size, b.size)
            if a.size < L:
                a = np.concatenate([a, np.zeros(L - a.size, dtype=a.dtype)])
            else:
                a = a[:L]
            if b.size < L:
                b = np.concatenate([b, np.zeros(L - b.size, dtype=b.dtype)])
            else:
                b = b[:L]
            # Try both orders and flips and pick the one minimizing seam discontinuity
            # Add a small horizontal gap between channels to avoid seam overlap
            gap_arr = np.zeros(channel_gap, dtype=a.dtype)
            candidates = []
            # order (a left, b right)
            candidates.append((np.concatenate([a[::-1], gap_arr, b]), "a_reversed_b"))
            candidates.append((np.concatenate([a, gap_arr, b]), "a_b"))
            candidates.append((np.concatenate([b[::-1], gap_arr, a]), "b_reversed_a"))
            candidates.append((np.concatenate([b, gap_arr, a]), "b_a"))

            def seam_error(arr):
                # measure absolute difference at seam region (16 pixels)
                mid = arr.size // 2
                left_tail = arr[mid - 8 : mid]
                right_head = arr[mid : mid + 8]
                return float(np.sum(np.abs(left_tail - right_head)))

            # Score candidates and pick best; optionally use alignment preference
            scored = [(cand, label, seam_error(cand)) for (cand, label) in candidates]
            if alignment_mode and alignment_mode != "auto":
                # compute peak distance-from-center metric for each candidate
                metrics = []
                for cand, label, seam in scored:
                    arr = np.asarray(cand, dtype=np.float32)
                    mid = arr.size // 2
                    peak = int(np.argmax(arr))
                    dist = abs(peak - mid)
                    metrics.append((cand, label, seam, dist))
                if alignment_mode == "outer":
                    # prefer larger distance from center; tiebreak with lower seam
                    chosen = max(metrics, key=lambda x: (x[3], -x[2]))
                else:
                    # inner -> prefer closer to center then lower seam
                    chosen = min(metrics, key=lambda x: (x[3], x[2]))
                best = (chosen[0], chosen[1], float(chosen[2]))
            else:
                best = min(scored, key=lambda x: x[2])
            out_rows.append(best[0])
            if pairing_debug and debug_out is not None:
                try:
                    from pathlib import Path
                    import csv

                    dbgdir = Path(debug_out) / "pairing_debug"
                    dbgdir.mkdir(parents=True, exist_ok=True)
                    csvf = dbgdir / "pairing_debug.csv"
                    write_header = not csvf.exists()
                    with csvf.open("a", newline="") as fh:
                        w = csv.writer(fh)
                        if write_header:
                            w.writerow(
                                [
                                    "seq_key",
                                    "chosen_label",
                                    "seam",
                                    "left_len",
                                    "right_len",
                                ]
                            )
                        seq_key = None
                        try:
                            seq_key = (
                                items[0].metadata.get("seq")
                                if isinstance(items[0].metadata, dict)
                                else None
                            )
                        except Exception:
                            seq_key = None
                        left_len = a.size
                        right_len = b.size
                        # include preprocessing info if available
                    peak = None
                    applied_gain = None
                    nadir_masked = None
                    try:
                        # peek into the input Scan objects
                        left_meta = (
                            items_sorted[0].metadata
                            if hasattr(items_sorted[0], "metadata")
                            else {}
                        )
                        right_meta = (
                            items_sorted[1].metadata
                            if hasattr(items_sorted[1], "metadata")
                            else {}
                        )
                        # prefer the combined candidate's peak if available
                        peak = left_meta.get("peak_pos") or right_meta.get("peak_pos")
                        applied_gain = left_meta.get("applied_gain") or right_meta.get(
                            "applied_gain"
                        )
                        nadir_masked = left_meta.get("nadir_masked") or right_meta.get(
                            "nadir_masked"
                        )
                    except Exception:
                        pass
                    w.writerow(
                        [
                            str(seq_key),
                            best[1],
                            float(best[2]),
                            int(left_len),
                            int(right_len),
                            peak,
                            applied_gain,
                            nadir_masked,
                        ]
                    )
                    # Save a small thumbnail for first few pairs with overlay
                    thumb_count_file = dbgdir / ".count"
                    count = 0
                    if thumb_count_file.exists():
                        try:
                            count = int(thumb_count_file.read_text())
                        except Exception:
                            count = 0
                    if count < 50:
                        # Normalize composite to uint8 for thumbnail
                        comp = best[0]
                        mn = float(comp.min())
                        mx = float(comp.max())
                        rng = mx - mn if mx != mn else 1.0
                        norm = ((comp - mn) / rng * 255.0).astype(np.uint8)
                        imt = Image.fromarray(norm).convert("RGB")
                        try:
                            from PIL import ImageDraw, ImageFont

                            draw = ImageDraw.Draw(imt)
                            wdt = imt.width
                            hgt = imt.height
                            # mark seam center
                            cx = wdt // 2
                            draw.line([(cx, 0), (cx, hgt)], fill=(255, 0, 0), width=1)
                            # mark peak if available
                            if peak is not None:
                                px = int(peak)
                                if px >= 0 and px < wdt:
                                    draw.line(
                                        [(px, 0), (px, hgt)], fill=(0, 255, 0), width=1
                                    )
                            # annotate gain/mask
                            text = (
                                f"gain={applied_gain:.2f}"
                                if applied_gain is not None
                                else ""
                            )
                            if nadir_masked is not None:
                                text += f" mask={nadir_masked}"
                            if text:
                                draw.text((4, 4), text, fill=(255, 255, 0))
                        except Exception:
                            pass
                        Image.fromarray(np.asarray(imt)).save(
                            str(dbgdir / f"pair_{seq_key}_{count}.png")
                        )
                        thumb_count_file.write_text(str(count + 1))
                except Exception:
                    pass
        return out_rows

    # Build groups by seq preserving original order of sequences
    from collections import OrderedDict, defaultdict

    groups = OrderedDict()
    for s in scans_list:
        if s.samples is None:
            continue
        seq = s.metadata.get("seq") if isinstance(s.metadata, dict) else None
        key = seq if seq is not None else f"_single_{s.id}"
        groups.setdefault(key, []).append(s)

    composed_rows = _compose_pairwise(list(groups.values()))

    for arr in composed_rows:
        # Normalize sample length if needed
        if width is not None:
            if arr.size < width:
                pad = np.zeros(width - arr.size, dtype=arr.dtype)
                arr = np.concatenate([arr, pad])
            elif arr.size > width:
                arr = arr[:width]
        max_width = max(max_width, arr.size)
        rows.append(arr)

    if not rows:
        raise RuntimeError("No valid scan samples to build waterfall")

    # If width not provided, use max_width and pad rows
    W = width or max_width
    H = len(rows)
    flat = np.zeros(W * H, dtype=np.float32)
    for i, r in enumerate(rows):
        if r.size < W:
            r2 = np.resize(r, W)
        else:
            r2 = r[:W]
        flat[i * W : (i + 1) * W] = r2

    img8 = np.asarray(generate_sidescan_waterfall(flat.tolist(), W, H), dtype=np.uint8).reshape((H, W))
    im = Image.fromarray(img8, mode='L')

    # Apply color mapping if requested
    arr = np.asarray(im, dtype=np.uint8)
    if color and color.lower() != "grayscale":
        rgb = apply_palette(arr, color)
        Image.fromarray(rgb, mode="RGB").save(output_path)
    else:
        im.save(output_path)
    return output_path


def scans_to_video(
    scans: Iterable[Scan],
    output_path: str,
    fps: int = 5,
    width: int = None,
    color: str | None = "amber",
    merge_channels: bool = True,
    height: int = 256,
    scans_per_frame: int = 1,
    channel_gap: int = 16,
    pairing_debug: bool = False,
    alignment_mode: str = "auto",
    debug_out: str | None = None,
    beam_gain: bool = False,
    nadir_mask: int = 0,
):
    # Build frames as RGB by stretching grayscale into 3 channels (or map to color)
    # Build a rolling waterfall buffer so each frame shows a moving window of recent pings
    H = height
    buffer = []  # list of 1D arrays (latest appended at end)
    frames = []
    W = width

    # Helper to pad existing rows in buffer when W grows
    def _pad_buffer_rows(new_W: int):
        for idx, row in enumerate(buffer):
            if row.size < new_W:
                buffer[idx] = np.concatenate(
                    [row, np.zeros(new_W - row.size, dtype=row.dtype)]
                )

    # Compose scans into rows similar to waterfall (including merge of channel pairs)
    scans_list = list(scans)
    # Build groups by seq preserving original order of sequences
    from collections import OrderedDict

    groups = OrderedDict()
    for s in scans_list:
        if s.samples is None:
            continue
        seq = s.metadata.get("seq") if isinstance(s.metadata, dict) else None
        key = seq if seq is not None else f"_single_{s.id}"
        groups.setdefault(key, []).append(s)

    # Reuse the same compose heuristic used by waterfall: try simple orders and flips
    def _compose_item(items):
        if len(items) == 1:
            s = items[0]
            pr = _preprocess_scan(s)
            return pr if pr is not None else np.asarray(s.samples, dtype=np.float32)
        try:
            items_sorted = sorted(items, key=lambda x: x.metadata.get("channel_id", 0))
        except Exception:
            items_sorted = items[:2]
        a = np.asarray(items_sorted[0].samples, dtype=np.float32)
        b = np.asarray(items_sorted[1].samples, dtype=np.float32)
        L = max(a.size, b.size)
        if a.size < L:
            a = np.concatenate([a, np.zeros(L - a.size, dtype=a.dtype)])
        else:
            a = a[:L]
        if b.size < L:
            b = np.concatenate([b, np.zeros(L - b.size, dtype=b.dtype)])
        else:
            b = b[:L]
        gap_arr = np.zeros(channel_gap, dtype=a.dtype)
        candidates = [
            (np.concatenate([a[::-1], gap_arr, b]), "a_reversed_b"),
            (np.concatenate([a, gap_arr, b]), "a_b"),
            (np.concatenate([b[::-1], gap_arr, a]), "b_reversed_a"),
            (np.concatenate([b, gap_arr, a]), "b_a"),
        ]

        def seam_err(arr):
            mid = arr.size // 2
            left_tail = arr[mid - 8 : mid]
            right_head = arr[mid : mid + 8]
            return float(np.sum(np.abs(left_tail - right_head)))

        scored = [(cand, label, seam_err(cand)) for (cand, label) in candidates]
        # Apply alignment mode preference (outer/inner/auto)
        if alignment_mode and alignment_mode != "auto":
            metrics = []
            for cand, label, seam in scored:
                arr = np.asarray(cand, dtype=np.float32)
                mid = arr.size // 2
                peak = int(np.argmax(arr))
                dist = abs(peak - mid)
                metrics.append((cand, label, seam, dist))
            if alignment_mode == "outer":
                chosen = max(metrics, key=lambda x: (x[3], -x[2]))
            else:
                chosen = min(metrics, key=lambda x: (x[3], x[2]))
            best = (chosen[0], chosen[1], float(chosen[2]))
        else:
            best = min(scored, key=lambda x: x[2])

        # Optionally write pairing debug info
        if pairing_debug and debug_out is not None:
            try:
                from pathlib import Path
                import csv

                dbgdir = Path(debug_out) / "pairing_debug"
                dbgdir.mkdir(parents=True, exist_ok=True)
                csvf = dbgdir / "pairing_debug_video.csv"
                write_header = not csvf.exists()
                with csvf.open("a", newline="") as fh:
                    w = csv.writer(fh)
                    if write_header:
                        w.writerow(
                            ["seq_key", "chosen_label", "seam", "left_len", "right_len"]
                        )
                    seq_key = None
                    try:
                        seq_key = (
                            items[0].metadata.get("seq")
                            if isinstance(items[0].metadata, dict)
                            else None
                        )
                    except Exception:
                        seq_key = None
                    left_len = a.size
                    right_len = b.size
                    w.writerow(
                        [
                            str(seq_key),
                            best[1],
                            float(best[2]),
                            int(left_len),
                            int(right_len),
                        ]
                    )
            except Exception:
                pass

        return best[0]

    processed = 0
    # Iterate composed rows and build frames
    for key in groups.keys():
        arr = _compose_item(groups[key])

        if W is None:
            W = arr.size
        elif arr.size > W:
            old_W = W
            W = arr.size
            _pad_buffer_rows(W)
        if arr.size < W:
            arr = np.concatenate([arr, np.zeros(W - arr.size, dtype=arr.dtype)])
        else:
            arr = arr[:W]

        # Append to rolling buffer
        buffer.append(arr)
        if len(buffer) > H:
            buffer.pop(0)

        processed += 1
        # Only produce a frame every `scans_per_frame` processed sequences
        if processed % scans_per_frame != 0:
            continue

        # Build a HxW array where rows are the recent scans
        mat = np.zeros((H, W), dtype=np.float32)
        rows_to_fill = len(buffer)
        # Place newest scans at the bottom for natural scrolling (top=old, bottom=new)
        for j, row in enumerate(buffer):
            mat[H - rows_to_fill + j, :] = row
        # Normalize / map to uint8 via generate_sidescan_waterfall which expects flat list
        img8 = np.asarray(
            generate_sidescan_waterfall(mat.flatten().tolist(), W, H), dtype=np.uint8
        ).reshape((H, W))
        frame = img8
        # Apply color mapping if requested
        if color and color.lower() != "grayscale":
            frame_rgb = apply_palette(frame, color)
        else:
            frame_rgb = np.stack([frame, frame, frame], axis=-1)
        frames.append(frame_rgb)

    # Use ffmpeg encoder with fallback to PNG-sequence + ffmpeg if encoding fails
    try:
        return encode_frames_to_mp4(iter(frames), output_path, fps=fps)
    except Exception as e:
        # Fallback: write frames to a temporary dir and run ffmpeg on the image sequence
        import tempfile
        import subprocess

        td = tempfile.mkdtemp(prefix="sonar_frames_")
        for i, f in enumerate(frames):
            Image.fromarray(f).save(os.path.join(td, f"frame_{i:05d}.png"))
        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            os.path.join(td, "frame_%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
        try:
            subprocess.check_call(cmd)
            return output_path
        except subprocess.CalledProcessError as ce:
            raise RuntimeError(f"fallback ffmpeg encoding failed: {ce}") from e


def export_full(input_path: str, out_dir: str, formats: List[str] = None, batch_size: int = 1000):
    p = SonarParser()
    formats = formats or ['waterfall']
    os.makedirs(out_dir, exist_ok=True)
    # Convert parser records to canonical Scan objects using registered adapters
    parsed = p.parse_file(input_path)
    records = parsed.get("records", [])
    from .canonical import to_scan

    # Ensure adapters are imported so they register themselves
    try:
        from .adapters import rsd_adapter  # noqa: F401
    except Exception:
        try:
            import sonarsniffer.adapters.rsd_adapter as rsd_adapter  # noqa: F401
        except Exception:
            pass
    scans = [to_scan("rsd", r, input_path) for r in records]

    results = {}
    if 'waterfall' in formats:
        out = os.path.join(out_dir, Path(input_path).stem + '_waterfall.png')
        scans_to_waterfall_image(scans, out)
        results['waterfall'] = out
    if 'mp4' in formats:
        out = os.path.join(out_dir, Path(input_path).stem + '.mp4')
        scans_to_video(scans, out)
        results['mp4'] = out

    # KML exporter: generate simple KML linking to the waterfall PNG
    if 'kml' in formats:
        from typing import Tuple

        def _compute_bounds(scans) -> Tuple[float, float, float, float]:
            # Group by seq and average lat/lon per sequence for more robust bounds when
            # dual-channel records are present. Falls back to individual records if
            # seq metadata is absent.
            from collections import defaultdict

            groups = defaultdict(list)
            for s in scans:
                if s.lat is None or s.lon is None:
                    continue
                seq = s.metadata.get("seq") if isinstance(s.metadata, dict) else None
                key = seq if seq is not None else f"_single_{s.id}"
                groups[key].append((s.lat, s.lon))
            if not groups:
                return (0.0, 0.0, 0.0, 0.0)
            latitudes = []
            longitudes = []
            for k, vals in groups.items():
                lats = [v[0] for v in vals]
                lons = [v[1] for v in vals]
                latitudes.append(sum(lats) / len(lats))
                longitudes.append(sum(lons) / len(lons))
            return (min(latitudes), max(latitudes), min(longitudes), max(longitudes))

        out_png = results.get('waterfall')
        if out_png:
            bounds = _compute_bounds(scans)
            out_kml = os.path.join(out_dir, Path(input_path).stem + '.kml')
            scans_to_kml(out_png, bounds, out_kml)
            results['kml'] = out_kml

    # GeoTIFF exporter: create simple georeferenced image and worldfile fallback
    if 'geotiff' in formats:
        out_png = results.get('waterfall')
        if out_png:
            out_tiff = os.path.join(out_dir, Path(input_path).stem + '.tif')
            scans_to_geotiff(out_png, out_tiff, scans)
            results['geotiff'] = out_tiff

    if 'tiles' in formats:
        out_png = results.get('waterfall')
        if out_png:
            tiles_dir = os.path.join(out_dir, Path(input_path).stem + '_tiles')
            scans_to_tiles(out_png, tiles_dir, tile_size=256, max_zoom=4)
            results['tiles'] = tiles_dir

    if 'mosaic' in formats:
        # Simple mosaic: build from waterfall and any pngs in out_dir
        imgs = []
        for f in os.listdir(out_dir):
            if f.lower().endswith('.png'):
                imgs.append(os.path.join(out_dir, f))
        if imgs:
            out_mosaic = os.path.join(out_dir, Path(input_path).stem + '_mosaic.png')
            create_mosaic_from_images(imgs, out_mosaic, mode='average')
            results['mosaic'] = out_mosaic

    # MBTiles export: pack tiles into an MBTiles SQLite database (v1 schema)
    if 'mbtiles' in formats:
        tiles_dir = results.get('tiles')
        if tiles_dir:
            mb_path = os.path.join(out_dir, Path(input_path).stem + '.mbtiles')
            tiles_to_mbtiles(tiles_dir, mb_path, metadata={"name": Path(input_path).stem, "format": "png"})
            results['mbtiles'] = mb_path

    # KMZ (super-overlay) export: create KMZ containing tiles and KML overlays
    if 'kmz' in formats:
        out_png = results.get('waterfall')
        tiles_dir = results.get('tiles')
        if out_png and tiles_dir:
            bounds = None
            # Compute bounds from scans grouping by seq and averaging lat/lon per sequence
            try:
                from collections import defaultdict

                groups = defaultdict(list)
                for s in scans:
                    if s.lat is None or s.lon is None:
                        continue
                    seq = (
                        s.metadata.get("seq") if isinstance(s.metadata, dict) else None
                    )
                    key = seq if seq is not None else f"_single_{s.id}"
                    groups[key].append((s.lat, s.lon))
                if groups:
                    latitudes = []
                    longitudes = []
                    for vals in groups.values():
                        lats = [v[0] for v in vals]
                        lons = [v[1] for v in vals]
                        latitudes.append(sum(lats) / len(lats))
                        longitudes.append(sum(lons) / len(lons))
                    bounds = (
                        min(latitudes),
                        max(latitudes),
                        min(longitudes),
                        max(longitudes),
                    )
            except Exception:
                bounds = None

            if bounds:
                out_kmz = os.path.join(out_dir, Path(input_path).stem + '.kmz')
                generate_superoverlay_kmz(out_png, tiles_dir, bounds, out_kmz)
                results['kmz'] = out_kmz

    return results


def scans_to_kml(waterfall_png_path: str, bounds: tuple, output_kml_path: str):
    """Generate a minimal KML with GroundOverlay referencing the waterfall PNG.

    bounds: (min_lat, max_lat, min_lon, max_lon)
    """
    min_lat, max_lat, min_lon, max_lon = bounds
    name = Path(waterfall_png_path).stem
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <GroundOverlay>
      <name>{name} waterfall</name>
      <Icon>
        <href>{Path(waterfall_png_path).name}</href>
      </Icon>
      <LatLonBox>
        <north>{max_lat}</north>
        <south>{min_lat}</south>
        <east>{max_lon}</east>
        <west>{min_lon}</west>
      </LatLonBox>
    </GroundOverlay>
  </Document>
</kml>'''
    # Write alongside the image so relative link works
    out_dir = os.path.dirname(output_kml_path)
    os.makedirs(out_dir, exist_ok=True)
    # Copy PNG to output dir if needed
    import shutil
    dst_png = os.path.join(out_dir, Path(waterfall_png_path).name)
    if os.path.abspath(waterfall_png_path) != os.path.abspath(dst_png):
        try:
            shutil.copy(waterfall_png_path, dst_png)
        except Exception:
            pass
    with open(output_kml_path, 'w', encoding='utf-8') as fh:
        fh.write(kml)
    return output_kml_path


def scans_to_geotiff(waterfall_png_path: str, out_tiff_path: str, scans: List[Scan]):
    """Attempt to write a GeoTIFF; fallback to PNG+worldfile (TFW) if rasterio not available.

    Note: This is a lightweight fallback that writes a TFW with approximate values when
    precise georeferencing is not available.
    """
    try:
        import rasterio
        from rasterio.transform import from_origin
        img = Image.open(waterfall_png_path)
        arr = np.array(img)
        # Compute simple transform using scan bounds
        min_lat = min((s.lat for s in scans if s.lat), default=0.0)
        max_lat = max((s.lat for s in scans if s.lat), default=0.0)
        min_lon = min((s.lon for s in scans if s.lon), default=0.0)
        max_lon = max((s.lon for s in scans if s.lon), default=0.0)
        if min_lat == max_lat or min_lon == max_lon:
            # fallback: set an arbitrary geotransform with pixel size 1
            transform = from_origin(0, 0, 1, 1)
        else:
            h, w = arr.shape[:2]
            xres = (max_lon - min_lon) / float(w)
            yres = (max_lat - min_lat) / float(h)
            transform = from_origin(min_lon, max_lat, xres, yres)
        # Write GeoTIFF (single band if grayscale; else write RGB)
        if arr.ndim == 2:
            count = 1
            dtype = arr.dtype
            with rasterio.open(out_tiff_path, 'w', driver='GTiff', height=arr.shape[0], width=arr.shape[1], count=1, dtype=dtype, transform=transform, crs='EPSG:4326') as dst:
                dst.write(arr, 1)
        else:
            # RGB
            count = 3
            dtype = arr.dtype
            with rasterio.open(out_tiff_path, 'w', driver='GTiff', height=arr.shape[0], width=arr.shape[1], count=3, dtype=dtype, transform=transform, crs='EPSG:4326') as dst:
                for i in range(3):
                    dst.write(arr[:, :, i], i + 1)
        return out_tiff_path
    except Exception:
        # Fallback: write PNG copy and a simplistic TFW (worldfile)
        img = Image.open(waterfall_png_path)
        out_png = str(Path(out_tiff_path).with_suffix('.png'))
        img.save(out_png)
        # Approximate georef values
        min_lat = min((s.lat for s in scans if s.lat), default=0.0)
        max_lat = max((s.lat for s in scans if s.lat), default=0.0)
        min_lon = min((s.lon for s in scans if s.lon), default=0.0)
        max_lon = max((s.lon for s in scans if s.lon), default=0.0)
        h, w = img.size[1], img.size[0]
        if w == 0 or h == 0:
            px_x = 1.0
            px_y = 1.0
        else:
            px_x = (max_lon - min_lon) / float(w) if max_lon != min_lon else 1.0
            px_y = (max_lat - min_lat) / float(h) if max_lat != min_lat else 1.0
        # World file: A D B E C F where A = pixel size in x, E = -pixel size in y
        tfw = f"{px_x}\n0.0\n0.0\n{-px_y}\n{min_lon}\n{max_lat}\n"
        with open(str(Path(out_tiff_path).with_suffix('.tfw')), 'w', encoding='utf-8') as fh:
            fh.write(tfw)
        # Write a simple meta file describing provenance
        with open(str(Path(out_tiff_path).with_suffix('.meta')), 'w', encoding='utf-8') as fh:
            fh.write(f"source_image={out_png}\nmin_lat={min_lat}\nmax_lat={max_lat}\nmin_lon={min_lon}\nmax_lon={max_lon}\n")
        return out_png


def scans_to_tiles(waterfall_png_path: str, out_tiles_dir: str, tile_size: int = 256, max_zoom: int = 4):
    """Generate simple tile pyramid (z/x/y.png) from an image.

    This is a lightweight super-overlay style generator (not Google-specific),
    producing tiles for zoom levels 0..max_zoom where 0 is lowest resolution.
    """
    os.makedirs(out_tiles_dir, exist_ok=True)
    img = Image.open(waterfall_png_path).convert('RGBA')
    w, h = img.size

    for z in range(0, max_zoom + 1):
        scale = 2 ** (max_zoom - z)
        # Downscale source to level z resolution
        target_w = max(1, w // scale)
        target_h = max(1, h // scale)
        resized = img.resize((target_w, target_h), resample=Image.LANCZOS)
        cols = (target_w + tile_size - 1) // tile_size
        rows = (target_h + tile_size - 1) // tile_size
        for x in range(cols):
            for y in range(rows):
                left = x * tile_size
                upper = y * tile_size
                right = min(left + tile_size, target_w)
                lower = min(upper + tile_size, target_h)
                tile = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
                region = resized.crop((left, upper, right, lower))
                tile.paste(region, (0, 0))
                tile_dir = os.path.join(out_tiles_dir, str(z), str(x))
                os.makedirs(tile_dir, exist_ok=True)
                tile_path = os.path.join(tile_dir, f"{y}.png")
                tile.save(tile_path)
    return out_tiles_dir


def create_mosaic_from_images(image_paths: List[str], output_path: str, mode: str = 'average'):
    """Create a simple mosaic by overlaying images. Mode can be 'average' or 'max'."""
    imgs = [Image.open(p).convert('RGBA') for p in image_paths]
    if not imgs:
        raise RuntimeError('No images provided')
    # Determine max canvas size
    max_w = max(im.size[0] for im in imgs)
    max_h = max(im.size[1] for im in imgs)
    canvas = Image.new('RGBA', (max_w, max_h), (0, 0, 0, 0))
    if mode == 'max':
        # For each pixel take max value across images
        import numpy as np
        arrs = [np.array(im, dtype=np.uint8) for im in imgs]
        stacked = np.maximum.reduce(arrs)
        out = Image.fromarray(stacked.astype(np.uint8))
        out.save(output_path)
        return output_path
    else:
        # Average overlay
        import numpy as np
        acc = np.zeros((max_h, max_w, 4), dtype=np.float32)
        count = np.zeros((max_h, max_w, 1), dtype=np.float32)
        for im in imgs:
            arr = np.array(im, dtype=np.float32)
            h, w = im.size[1], im.size[0]
            acc[:h, :w, :] += arr
            count[:h, :w, 0] += (arr[:, :, 3] > 0).astype(np.float32)
        # Avoid divide by zero
        count[count == 0] = 1.0
        avg = (acc / count)
        avg = np.clip(avg, 0, 255).astype(np.uint8)
        out = Image.fromarray(avg)
        out.save(output_path)
        return output_path


def tiles_to_mbtiles(tiles_dir: str, mbtiles_path: str, metadata: dict = None):
    """Create a simple MBTiles (v1) file from a tile directory structure z/x/y.png.

    This implementation writes tiles in PNG format and stores metadata in the metadata table.
    It streams tile files to sqlite without loading entire tile sets into memory.
    """
    import sqlite3
    metadata = metadata or {}
    # Remove existing file if present
    if os.path.exists(mbtiles_path):
        os.remove(mbtiles_path)
    conn = sqlite3.connect(mbtiles_path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE metadata (name text, value text);')
    cur.execute('CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob);')
    cur.execute('CREATE UNIQUE INDEX name ON metadata (name);')
    cur.execute('CREATE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);')
    # Insert metadata
    cur.executemany('INSERT INTO metadata (name,value) VALUES (?,?)', [(k, str(v)) for k, v in metadata.items()])
    conn.commit()
    # Walk tiles structure
    for z in os.listdir(tiles_dir):
        zdir = os.path.join(tiles_dir, z)
        if not os.path.isdir(zdir):
            continue
        zi = int(z)
        for x in os.listdir(zdir):
            xdir = os.path.join(zdir, x)
            if not os.path.isdir(xdir):
                continue
            xi = int(x)
            for yfn in os.listdir(xdir):
                if not yfn.lower().endswith('.png'):
                    continue
                yi = int(os.path.splitext(yfn)[0])
                tile_path = os.path.join(xdir, yfn)
                with open(tile_path, 'rb') as fh:
                    blob = fh.read()
                # MBTiles uses TMS tile scheme with flipped Y
                tms_y = (2 ** zi - 1) - yi
                cur.execute('INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?,?,?,?)', (zi, xi, tms_y, sqlite3.Binary(blob)))
        conn.commit()
    conn.close()
    return mbtiles_path


def generate_superoverlay_kmz(waterfall_png: str, tiles_dir: str, bounds: tuple, out_kmz_path: str, tile_size: int = 256, max_zoom: int = 4):
    """Create a KMZ (zip) containing KML GroundOverlays for tiles and the tiles themselves.

    bounds: (min_lat, max_lat, min_lon, max_lon)
    """
    import zipfile
    min_lat, max_lat, min_lon, max_lon = bounds
    out_dir = os.path.dirname(out_kmz_path)
    name = os.path.splitext(os.path.basename(out_kmz_path))[0]
    # Build doc.kml content incrementally and write into KMZ
    kmz_temp = out_kmz_path + '.tmp'
    with zipfile.ZipFile(kmz_temp, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Add tiles
        for root, dirs, files in os.walk(tiles_dir):
            for fn in files:
                if not fn.lower().endswith('.png'):
                    continue
                absf = os.path.join(root, fn)
                rel = os.path.relpath(absf, tiles_dir)
                zf.write(absf, arcname=os.path.join('tiles', rel))
        # Generate a KML with GroundOverlay entries for each tile at highest zoom (for simplicity)
        entries = []
        for z in range(max_zoom + 1):
            zdir = os.path.join(tiles_dir, str(z))
            if not os.path.isdir(zdir):
                continue
            # Determine scaled target size at this zoom level
            for x in os.listdir(zdir):
                xdir = os.path.join(zdir, x)
                if not os.path.isdir(xdir):
                    continue
                for yfn in os.listdir(xdir):
                    if not yfn.lower().endswith('.png'):
                        continue
                    y = int(os.path.splitext(yfn)[0])
                    xi = int(x)
                    # Compute bounds for this tile using linear mapping
                    # Determine number of tiles at this zoom
                    cols = sum(1 for _ in os.listdir(zdir))
                    # Estimate tile grid width/height by listing one column
                    anyx = next(iter(os.listdir(zdir)), None)
                    if anyx is None:
                        continue
                    rows = len(os.listdir(os.path.join(zdir, anyx)))
                    # Compute pixel fraction
                    left_frac = xi / cols
                    right_frac = (xi + 1) / cols
                    top_frac = y / rows
                    bottom_frac = (y + 1) / rows
                    west = min_lon + left_frac * (max_lon - min_lon)
                    east = min_lon + right_frac * (max_lon - min_lon)
                    # Pixel Y increases downward; map to lat accordingly
                    north = max_lat - top_frac * (max_lat - min_lat)
                    south = max_lat - bottom_frac * (max_lat - min_lat)
                    href = f"tiles/{z}/{xi}/{yfn}"
                    entries.append((href, north, south, east, west))
        # Build KML
        kml = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n  <Document>\n'
        for href, north, south, east, west in entries:
            kml += f'''    <GroundOverlay>\n      <Icon>\n        <href>{href}</href>\n      </Icon>\n      <LatLonBox>\n        <north>{north}</north>\n        <south>{south}</south>\n        <east>{east}</east>\n        <west>{west}</west>\n      </LatLonBox>\n    </GroundOverlay>\n'''
        kml += '  </Document>\n</kml>'
        # Write doc.kml at root of KMZ
        zf.writestr('doc.kml', kml)
    # Rename temp kmz to final
    os.replace(kmz_temp, out_kmz_path)
    return out_kmz_path
