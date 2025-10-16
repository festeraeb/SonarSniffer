#!/usr/bin/env python3
# video_exporter.py — preview builder + MP4 export (stitch/align + color maps)
from __future__ import annotations
from typing import Sequence, Dict, Any, List, Tuple, Optional, Callable
import math
import numpy as np
from PIL import Image
from render_accel import VideoWorker

def _build_single_preview(
    img_paths: Sequence[str],
    cfg: Dict[str,Any],
    row_h: int,
    preview_h: int
) -> tuple[np.ndarray, Optional[int], Optional[int], float]:
    """Build preview frame for single-channel data (downscan/chirp)."""
    if not img_paths:
        return np.zeros((preview_h, 100, 3), dtype=np.uint8), None, None, 1.0

    # Load last N rows that will fit in preview
    rows_needed = math.ceil(preview_h / row_h)
    preview_paths = img_paths[-rows_needed:] if rows_needed > 0 else []
    
    # Stack and scale rows
    rows = [np.array(Image.open(p)) for p in preview_paths]
    if not rows:
        return np.zeros((preview_h, 100, 3), dtype=np.uint8), None, None, 1.0
        
    preview = np.vstack(rows)
    if preview.shape[0] > preview_h:
        preview = preview[-preview_h:]
    
    return preview, preview.shape[0], None, 1.0

def _build_sidescan_preview(
    img_paths: Sequence[str],
    cfg: Dict[str,Any],
    row_h: int,
    preview_h: int
) -> tuple[np.ndarray, Optional[int], Optional[int], float]:
    """Build preview frame for sidescan data (dual channel)."""
    if not img_paths:
        return np.zeros((preview_h, 100, 3), dtype=np.uint8), None, None, 1.0

    # Load last N rows that will fit in preview
    rows_needed = math.ceil(preview_h / row_h)
    preview_paths = img_paths[-rows_needed:] if rows_needed > 0 else []
    
    # Load and split channels
    rows = [np.array(Image.open(p)) for p in preview_paths]
    if not rows:
        return np.zeros((preview_h, 100, 3), dtype=np.uint8), None, None, 1.0
        
    preview = np.vstack(rows)
    if preview.shape[0] > preview_h:
        preview = preview[-preview_h:]
        
    # Split channels if needed
    if cfg.get('AUTO_SPLIT', True):
        h = preview.shape[0]
        mid = preview.shape[1] // 2
        left = preview[:, :mid]
        right = preview[:, mid:]
        return preview, h, h, 1.0
    
    return preview, preview.shape[0], None, 1.0

def detect_scan_type(img_path: str, cfg: Dict[str,Any]) -> str:
    """Detect scan type from first image and config."""
    if cfg.get('SCAN_TYPE', 'auto') != 'auto':
        return cfg['SCAN_TYPE']
        
    # Load first image to analyze characteristics
    img = np.array(Image.open(img_path))
    h, w = img.shape[:2]
    
    if w >= h * 8:  # Very wide image suggests sidescan
        return 'sidescan'
    elif w <= h * 2:  # Narrower image suggests downscan
        return 'downscan'
    else:
        return 'chirp'

def build_preview_frame(
    img_paths: Sequence[str],
    cfg: Dict[str,Any],
    row_h: int,
    preview_h: int,
) -> tuple[np.ndarray, Optional[int], Optional[int], float]:
    """Build a preview frame showing recent data from provided image files.
    Returns (preview frame, left channel height, right channel height, time scale)
    """
    # Detect scan type
    scan_type = detect_scan_type(img_paths[0], cfg) if img_paths else 'sidescan'
    
    # Load and process images based on scan type
    if scan_type == 'sidescan':
        # Use existing sidescan preview logic
        return _build_sidescan_preview(img_paths, cfg, row_h, preview_h)
    else:
        # Simplified preview for downscan/chirp
        return _build_single_preview(img_paths, cfg, row_h, preview_h)

def export_waterfall_mp4(img_paths: Sequence[str], cfg: Dict[str,Any], out_path: str, row_h: int, video_h: int, fps: int = 30, max_val: int = 255, log_func: Optional[Callable[[str],None]] = None) -> None:
    """Export a waterfall video from a sequence of row images."""
    # Detect scan type if not specified
    scan_type = detect_scan_type(img_paths[0], cfg)
    
    # Modify output path based on scan type
    base = out_path.rsplit('.', 1)[0]
    if scan_type != 'sidescan':
        out_path = f"{base}_{scan_type}.mp4"
    
    # Adjust configuration based on scan type
    if scan_type == 'downscan' or scan_type == 'chirp':
        cfg = cfg.copy()
        cfg['ALIGN_CHANNELS'] = False
        cfg['SHOW_SEAM'] = False
        cfg['AUTO_SPLIT'] = False

# ----------- Color maps -----------
def _hex2rgb(h: str) -> tuple[int,int,int]:
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _mk(stops: List[Tuple[int,str]]) -> np.ndarray:
    lut = np.zeros((256,3), np.uint8)
    for (p0,c0),(p1,c1) in zip(stops[:-1],stops[1:]):
        r0,g0,b0 = _hex2rgb(c0); r1,g1,b1 = _hex2rgb(c1)
        span = max(1, p1 - p0)
        t = np.linspace(0,1,span,endpoint=False,dtype=np.float32)
        lut[p0:p1,0] = (r0+(r1-r0)*t).astype(np.uint8)
        lut[p0:p1,1] = (g0+(g1-g0)*t).astype(np.uint8)
        lut[p0:p1,2] = (b0+(b1-b0)*t).astype(np.uint8)
    p,c = stops[-1]
    lut[p:] = np.array(_hex2rgb(c), np.uint8)
    return lut

_LUTS: Dict[str,np.ndarray] = {}
def _lut(name: str) -> np.ndarray:
    k = name.lower()
    if k in _LUTS: return _LUTS[k]
    maps = {
        "grayscale":[(0,"#000000"),(255,"#ffffff")],
        "amber":[(0,"#000000"),(40,"#2b1b00"),(96,"#7a3e00"),(180,"#f6a400"),(255,"#fff5cc")],
        "copper":[(0,"#000000"),(48,"#1a0e06"),(110,"#5a2e15"),(190,"#b36b2c"),(255,"#ffd29c")],
        "blue":[(0,"#000000"),(64,"#001a33"),(140,"#004c99"),(210,"#33aaff"),(255,"#d6f0ff")],
        "ice":[(0,"#000000"),(64,"#001a33"),(170,"#66b2ff"),(255,"#ffffff")],
        "purple":[(0,"#000000"),(64,"#1a0033"),(150,"#5a00a3"),(210,"#c084ff"),(255,"#ffe6ff")],
        "fire":[(0,"#000000"),(50,"#330000"),(120,"#990000"),(200,"#ff6600"),(255,"#ffff66")],
        "viridis":[(0,"#440154"),(80,"#3b528b"),(140,"#21918c"),(200,"#5ec962"),(255,"#fde725")],
        "magma":[(0,"#000004"),(90,"#3b0f70"),(150,"#8c2981"),(200,"#de4968"),(235,"#fca636"),(255,"#fcfdbf")],
        "inferno":[(0,"#000004"),(70,"#1f0c48"),(135,"#5c1e76"),(190,"#b63679"),(225,"#ee7b51"),(255,"#f6d746")]
    }
    _LUTS[k] = _mk(maps.get(k, maps["grayscale"]))
    return _LUTS[k]

def _apply(gray: np.ndarray, cmap: str) -> np.ndarray:
    # Accept grayscale uint8 or any float-ish array. Return RGB uint8.
    if gray.ndim == 3 and gray.shape[2] == 3:
        return gray
    if gray.dtype != np.uint8:
        f = gray.astype(np.float32)
        mn = np.nanmin(f); mx = np.nanmax(f)
        if not np.isfinite(mn) or not np.isfinite(mx) or mx <= mn:
            f = np.clip(f, 0, 1)
        else:
            f = np.clip((f - mn) / (mx - mn), 0, 1)
        gray = (f*255 + 0.5).astype(np.uint8)
    return _lut(cmap)[gray]

# ----------- Stitch / align helpers -----------
def _even_dims(h:int,w:int)->tuple[int,int]:
    return (math.ceil(h/2)*2, math.ceil(w/2)*2)

def _even_frame(a: np.ndarray)->np.ndarray:
    h,w = a.shape[:2]
    hp,wp = _even_dims(h,w)
    if (hp,wp)==(h,w): return a
    out = np.zeros((hp,wp,3),dtype=np.uint8) if a.ndim==3 else np.zeros((hp,wp),dtype=a.dtype)
    out[:h,:w] = a
    return out

def _pad_w(img: np.ndarray, width:int)->np.ndarray:
    h,w=img.shape[:2]
    if w==width: return img
    if w>width:  return img[:,:width] if img.ndim==2 else img[:,:width,:]
    out = np.zeros((h,width),img.dtype) if img.ndim==2 else np.zeros((h,width,img.shape[2]),img.dtype)
    out[:,:w]=img; return out

def _vstack_same_w(rows: Sequence[np.ndarray])->np.ndarray:
    maxw = max(r.shape[1] for r in rows)
    return np.vstack([_pad_w(r,maxw) for r in rows])

def _resize_h(frame: np.ndarray, target_h:int)->np.ndarray:
    if target_h<=0 or frame.shape[0]==target_h: return frame
    scale = target_h/float(frame.shape[0])
    new_w = max(2, int(round(frame.shape[1]*scale)))
    from PIL import Image as _I
    return np.array(_I.fromarray(frame).resize((new_w,target_h), resample=_I.NEAREST))

def _split_mid(row: np.ndarray):
    h,w=row.shape[:2]; mid=max(1,w//2)
    return row[:,:mid], row[:,mid:], mid

def _auto_split_valley(row: np.ndarray):
    rowm = row.mean(axis=2) if row.ndim==3 else row
    col  = rowm.mean(axis=0).astype(np.float32)
    if col.size < 64: return None
    k = max(7, col.size//150)
    sm = np.convolve(col, np.ones(k)/k, mode="same")
    w = col.size; lo=int(w*0.35); hi=int(w*0.65)
    idx = int(np.argmin(sm[lo:hi]))+lo
    if idx<int(w*0.1) or idx>int(w*0.9): return None
    L=row[:,:idx]; R=row[:,idx:]
    if L.shape[1] < 24 or R.shape[1] < 24: return None
    return L,R,idx

def _fit_half_width(img: np.ndarray, half_w:int)->np.ndarray:
    h,w=img.shape[:2]
    if w==half_w: return img
    if w>half_w:  return img[:,:half_w] if img.ndim==2 else img[:,:half_w,:]
    out=np.zeros((h,half_w),img.dtype) if img.ndim==2 else np.zeros((h,half_w,img.shape[2]),img.dtype)
    out[:,:w]=img; return out

def _phase_corr_shift(L: np.ndarray, R: np.ndarray, max_shift:int)->Tuple[int,float]:
    try:
        if L.size==0 or R.size==0: return 0,0.0
        h=min(L.shape[0], R.shape[0]); wL=L.shape[1]; wR=R.shape[1]
        if h<8 or wL<8 or wR<8: return 0,0.0
        band = slice(max(0,h//3), min(h, 2*h//3))
        A = L[band, -min(128,wL):].astype(np.float32)
        B = R[band, :min(128,wR)].astype(np.float32)
        if A.size==0 or B.size==0: return 0,0.0
        A -= A.mean() if A.size else 0; B -= B.mean() if B.size else 0
        W = 1<<int(np.ceil(np.log2(max(A.shape[1],B.shape[1])*2))) if max(A.shape[1],B.shape[1])>0 else 0
        if W<=0: return 0,0.0
        def fpad(X): out=np.zeros((X.shape[0],W),np.float32); out[:,:X.shape[1]]=X; return out
        FA=np.fft.rfft(fpad(A),axis=1); FB=np.fft.rfft(fpad(B),axis=1)
        Rsp=FA*np.conj(FB); pc=np.fft.irfft(Rsp/(np.abs(Rsp)+1e-6),axis=1)
        if pc.size==0: return 0,0.0
        prof=pc.mean(axis=0)
        if not np.isfinite(prof).any(): return 0,0.0
        peak=int(np.nanargmax(prof));  peak-= (prof.size if peak>prof.size//2 else 0)
        shift=int(np.clip(peak,-max_shift,max_shift))
        maxv=float(np.nanmax(prof)); score=float(prof[peak if peak>=0 else peak+prof.size]/(maxv+1e-6)) if np.isfinite(maxv) and maxv>0 else 0.0
        if not np.isfinite(score): score=0.0
        return shift,score
    except Exception:
        return 0,0.0

def _align_join(L: np.ndarray, R: np.ndarray, cfg: Dict[str,Any], half_w:int)->Tuple[np.ndarray,int,float]:
    flip_right=bool(cfg.get("FLIP_RIGHT",True)); swap_lr=bool(cfg.get("SWAP_LR",False)); max_shift=int(cfg.get("MAX_ALIGN_SHIFT",64))
    if flip_right: R=np.fliplr(R)
    if swap_lr: L,R=R,L
    L=_fit_half_width(L,half_w); R=_fit_half_width(R,half_w)
    s,score=_phase_corr_shift(L,R,max_shift)
    if s>0:  L=np.hstack([np.zeros((L.shape[0],s),L.dtype), L[:,:-s]])
    elif s<0: s2=-s; R=np.hstack([np.zeros((R.shape[0],s2),R.dtype), R[:,:-s2]])
    return np.hstack([L,R]), s, score

def _to8(a: np.ndarray)->np.ndarray:
    if a.dtype==np.uint8: return a
    f=a.astype(np.float32); mn,mx=f.min(),f.max()
    if mx<=mn+1e-6: return np.zeros_like(a,dtype=np.uint8)
    return ((f-mn)/(mx-mn)*255+0.5).astype(np.uint8)

def _compose_single_row(row: np.ndarray, cfg: Dict[str,Any], state: Dict[str,Optional[int]]):
    seam=None; shift=None; score=None; Lraw=None; Rraw=None
    sp=_split_mid(row) if bool(cfg.get("FORCE_SPLIT_MID",False)) else (_auto_split_valley(row) if bool(cfg.get("AUTO_SPLIT",True)) else None)
    if sp is None: return row,None,None,None,None,None
    L,R,seam=sp
    if min(L.shape[1],R.shape[1]) < 24: return row,None,None,None,None,None
    if state["HALF_W"] is None: state["HALF_W"]=int(min(L.shape[1],R.shape[1]))
    half=state["HALF_W"]; Lraw,Rraw=L,R
    if bool(cfg.get("ALIGN_CHANNELS",True)): comp,shift,score=_align_join(L,R,cfg,half)
    else: comp=np.hstack([_fit_half_width(L,half), _fit_half_width(R,half)])
    return comp,seam,shift,score,Lraw,Rraw

def _compose_window(rows: Sequence[np.ndarray], cfg: Dict[str,Any], mode:str, show_seam:bool, smooth_shift:int, shift_hist:List[int], state: Dict[str,Optional[int]], edge_pad:int=0):
    built=[]; seam=None; shift=None; score=None
    overlay=(mode=="overlay"); diff_only=(mode=="difference")
    for r in rows:
        comp,s,sh,sc,Lraw,Rraw=_compose_single_row(r,cfg,state)
        if sh is not None and smooth_shift>1:
            shift_hist.append(int(sh))
            if len(shift_hist)>smooth_shift: shift_hist.pop(0)
            sh=int(np.median(shift_hist))
        if overlay and Lraw is not None and Rraw is not None:
            h=comp.shape[0]; half=state["HALF_W"]
            L8=_to8(_fit_half_width(Lraw,half)); R8=_to8(_fit_half_width(Rraw,half))
            Rf = R8[:, ::-1] if bool(cfg.get("FLIP_RIGHT", True)) else R8
            if bool(cfg.get("SWAP_LR", False)): L8,Rf=Rf,L8
            if sh:
                if sh>0: L8=np.hstack([np.zeros((h,sh),np.uint8), L8[:,:-sh]])
                elif sh<0: s2=-sh; Rf=np.hstack([np.zeros((h,s2),np.uint8), Rf[:,:-s2]])
            over=np.zeros((h, L8.shape[1]+Rf.shape[1], 3), np.uint8)
            over[:,:L8.shape[1],0]=L8; over[:,L8.shape[1]:,1]=Rf; over[:,L8.shape[1]:,2]=Rf
            comp=over
        elif diff_only and Lraw is not None and Rraw is not None:
            half=state["HALF_W"]; L8=_to8(_fit_half_width(Lraw,half)); R8=_to8(_fit_half_width(Rraw,half))
            Rf = R8[:, ::-1] if bool(cfg.get("FLIP_RIGHT", True)) else R8
            if bool(cfg.get("SWAP_LR", False)): L8,Rf=Rf,L8
            d=np.abs(L8.astype(np.int16)-Rf.astype(np.int16)).astype(np.uint8)
            comp=np.stack([d]*3,2)
        if show_seam and s is not None and comp.ndim==3:
            x = min(max(0, s), comp.shape[1]-2)
            comp[:, x:x+2, :] = (255,255,0)
        built.append(comp)
        seam = s if s is not None else seam
        shift = sh if sh is not None else shift
        score = sc if sc is not None else score
    frame=_vstack_same_w(built)
    if edge_pad>0:
        h,w=frame.shape[:2]
        out=np.zeros((h,w+edge_pad*2,3),np.uint8); out[:,edge_pad:edge_pad+w]=frame; frame=out
    return frame, seam, shift, score

def _rows_needed(video_h:int, row_h:int)->int:
    return max(1, int(math.ceil(video_h / max(1,row_h))))

# ----------- Public API -----------
def build_preview_frame(row_paths: Sequence[str], cfg: Dict[str, Any], row_h:int, video_h:int):
    cmap=str(cfg.get("COLORMAP","amber")).lower(); mode=str(cfg.get("PREVIEW_MODE","compose")).lower()
    show_seam=bool(cfg.get("SHOW_SEAM", False)); smooth=int(cfg.get("SMOOTH_SHIFT",11)); edge_pad=int(cfg.get("EDGE_PAD",0))
    need=_rows_needed(video_h,row_h)
    window=[np.array(Image.open(p)) for p in row_paths[:need]]
    if not window: raise RuntimeError("No rows for preview")
    state={"HALF_W":None}
    gray,seam,shift,score=_compose_window(window, cfg, mode, show_seam, smooth, [], state, edge_pad=edge_pad)
    gray=_resize_h(gray, int(video_h)); rgb=_apply(gray, cmap); return _even_frame(rgb), seam, shift, score

def export_waterfall_mp4(row_paths: Sequence[str], cfg: Dict[str, Any], out_mp4: str,
                         row_height:int, video_height:int, fps:int, vmax_frames:int,
                         log_func:Optional[Callable[[str],None]]=None):
    log = log_func or (lambda m: None)
    cmap=str(cfg.get("COLORMAP","amber")).lower(); smooth=int(cfg.get("SMOOTH_SHIFT",11)); edge_pad=int(cfg.get("EDGE_PAD",0))
    need=_rows_needed(video_height,row_height); window=[]; shist=[]; state={"HALF_W":None}
    vw=VideoWorker(out_mp4, fps=fps, encoder=str(cfg.get("VIDEO_ENCODER","mp4v")), log_func=log)
    for i,p in enumerate(row_paths):
        window.append(np.array(Image.open(p)))
        if len(window)>need: window.pop(0)
        if len(window)==need:
            gray,seam,shift,score=_compose_window(window, cfg, "compose", False, smooth, shist, state, edge_pad=edge_pad)
            if shift is not None: log(f"align: shift={shift:+d}px")
            gray=_resize_h(gray, int(video_height)); rgb=_apply(gray, cmap); rgb=_even_frame(rgb)
            vw.push(rgb)
            if i>=vmax_frames: break
    vw.close()
