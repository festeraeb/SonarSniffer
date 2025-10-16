#!/usr/bin/env python3
# render_accel.py — simple OpenCV-backed VideoWriter with codec fallback
import numpy as np, cv2, os

_FALLBACKS=[("mp4v",".mp4"),("XVID",".avi"),("MJPG",".avi"),("avc1",".mp4")]

class VideoWorker:
    def __init__(self,out_path,fps=30,encoder="auto",log_func=None):
        self._base=out_path; self._fps=float(fps); self._writer=None
        self._log=log_func or (lambda m:None); self._pref=(encoder or "auto").lower()

    def _cands(self):
        if self._pref not in ("auto",""):
            # try requested first, then typical fallbacks
            for f,e in _FALLBACKS:
                if self._pref in (f.lower(),"h264","libx264","h264_nvenc","h264_qsv","h264_amf","avc1"):
                    return [(f,e)]+[(ff,ee) for (ff,ee) in _FALLBACKS if (ff,ee)!=(f,e)]
        return _FALLBACKS

    def _open(self,w,h):
        for fourcc_txt,ext in self._cands():
            out=self._base if self._base.lower().endswith(ext) else os.path.splitext(self._base)[0]+ext
            vw=cv2.VideoWriter(out,cv2.VideoWriter_fourcc(*fourcc_txt),self._fps,(w,h),True)
            if vw.isOpened():
                self._writer=vw; self._base=out; self._log(f"[VideoWriter] codec={fourcc_txt} {w}x{h} -> {out}"); return
            else:
                self._log(f"[VideoWriter] failed {fourcc_txt}, trying next…")
        raise RuntimeError("All codecs failed. Install OpenH264 for avc1/H.264 if needed.")

    def push(self,frame):
        if frame.ndim==2: frame=np.stack([frame]*3,2)
        if frame.dtype!=np.uint8: frame=np.clip(frame,0,255).astype(np.uint8)
        if self._writer is None: self._open(frame.shape[1], frame.shape[0])
        # OpenCV expects BGR
        self._writer.write(frame[:,:,::-1])

    def close(self):
        if self._writer is not None: self._writer.release(); self._writer=None

def process_record_images(csv_path, img_dir, scan_type=None, channel=None):
    """
    Stub function for processing record images from CSV data
    TODO: Implement proper image generation from sonar records
    """
    print(f"[render_accel] process_record_images called for {csv_path}")
    print(f"[render_accel] Would generate images to {img_dir}")
    # For now, just create the directory and return
    import os
    os.makedirs(img_dir, exist_ok=True)
