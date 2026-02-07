"""Minimal FastAPI app to serve outputs and provide basic admin endpoints
"""
import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Header,
    BackgroundTasks,
    UploadFile,
    File,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure package import path when running from scripts
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

SONAR_OUT = Path(os.environ.get('SONARS_OUTPUT_DIR', str(ROOT / 'outputs')))
SONAR_IN = Path(os.environ.get("SONARS_INPUT_DIR", str(ROOT / "data")))
API_TOKEN = os.environ.get('SONARS_API_TOKEN', '')

app = FastAPI(title='SonarSniffer API', version='0.1')

# Initialize Sentry (optional)
try:
    import sentry_sdk

    SENTRY_DSN = os.environ.get("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(SENTRY_DSN, traces_sample_rate=0.0)
except Exception:
    # don't fail if sentry isn't available
    sentry_sdk = None
    SENTRY_DSN = None

# Ensure standard directories exist
SONAR_OUT.mkdir(parents=True, exist_ok=True)
SONAR_IN.mkdir(parents=True, exist_ok=True)

# Mount outputs as static files
if (SONAR_OUT).exists():
    app.mount('/outputs', StaticFiles(directory=str(SONAR_OUT)), name='outputs')

# Mount inputs as static files too
if (SONAR_IN).exists():
    app.mount("/inputs", StaticFiles(directory=str(SONAR_IN)), name="inputs")

# Mount a small built-in UI prototype if present
WEB_STATIC = Path(__file__).resolve().parents[0] / "web_static"
if WEB_STATIC.exists():
    app.mount('/ui', StaticFiles(directory=str(WEB_STATIC)), name='ui')

# In-memory job store
_jobs: Dict[str, Dict[str, Any]] = {}
# WebSocket subscriber mapping: job_id -> set of WebSocket connections
_ws_subscribers: Dict[str, set] = {}


async def _broadcast_job_line(job_id: str, line: str):
    """Send a log line to all websocket subscribers for the job_id."""
    subs = _ws_subscribers.get(job_id)
    if not subs:
        return
    to_remove = []
    for ws in list(subs):
        try:
            await ws.send_text(line)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        subs.discard(ws)


async def run_holloway_job(
    job_id: str,
    out_dir: str,
    source: str | None = None,
    color: str | None = None,
    video: str | None = None,
    video_fps: int | None = None,
    video_height: int | None = None,
    scans_per_frame: int | None = None,
    channel_gap: int | None = None,
    pairing_debug: bool | None = None,
    alignment_mode: str | None = None,
    beam_gain: bool | None = None,
    nadir_mask: int | None = None,
    gen_mp4: int | None = None,
    gen_kmz: int | None = None,
    gen_mbtiles: int | None = None,
):
    """Run the holloway pipeline script in background (simple wrapper).

    Additional options are passed to the pipeline via environment variables so
    both local and RQ worker runs behave the same.
    """
    _jobs[job_id]['status'] = 'running'
    _jobs[job_id]['start'] = time.time()
    _jobs[job_id].setdefault('log_lines', [])
    try:
        # Import and run the pipeline script directly to capture stdout
        script_path = ROOT / 'scripts' / 'run_holloway_pipeline.py'
        env = os.environ.copy()
        env['HOLLOWAY_OUT'] = out_dir
        if source:
            env["HOLLOWAY_SOURCE"] = source
        if color:
            env["HOLLOWAY_COLOR"] = color
        if video is not None:
            env["HOLLOWAY_VIDEO"] = (
                "1" if str(video).lower() in ("1", "true", "yes", "y") else "0"
            )
        if video_fps is not None:
            env["HOLLOWAY_VIDEO_FPS"] = str(video_fps)
        if video_height is not None:
            env["HOLLOWAY_VIDEO_HEIGHT"] = str(video_height)
        if scans_per_frame is not None:
            env["HOLLOWAY_SCANS_PER_FRAME"] = str(scans_per_frame)
        if channel_gap is not None:
            env["HOLLOWAY_CHANNEL_GAP"] = str(channel_gap)
        if pairing_debug is not None:
            env["HOLLOWAY_PAIRING_DEBUG"] = "1" if pairing_debug else "0"
        if alignment_mode is not None:
            env["HOLLOWAY_ALIGNMENT_MODE"] = str(alignment_mode)
        if beam_gain is not None:
            env["HOLLOWAY_BEAM_GAIN"] = "1" if beam_gain else "0"
        if nadir_mask is not None:
            env["HOLLOWAY_NADIR_MASK"] = str(nadir_mask)
        # generation flags from UI
        if gen_mp4 is not None:
            env["HOLLOWAY_GEN_MP4"] = str(gen_mp4)
        if gen_kmz is not None:
            env["HOLLOWAY_GEN_KMZ"] = str(gen_kmz)
        if gen_mbtiles is not None:
            env["HOLLOWAY_GEN_MBTILES"] = str(gen_mbtiles)

        proc = await asyncio.create_subprocess_exec(sys.executable, str(script_path), env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        _jobs[job_id]['pid'] = proc.pid
        output = []
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode('utf-8', errors='ignore').rstrip('\n')
            output.append(text)
            _jobs[job_id]['last_log'] = text
            _jobs[job_id]['log_lines'].append(text)
            # Keep log tail bounded
            if len(_jobs[job_id]['log_lines']) > 500:
                _jobs[job_id]['log_lines'] = _jobs[job_id]['log_lines'][-500:]
            # Broadcast to any WS listeners (best-effort)
            try:
                await _broadcast_job_line(job_id, text)
            except Exception:
                pass
        rc = await proc.wait()
        _jobs[job_id]['status'] = 'success' if rc == 0 else 'failed'
        _jobs[job_id]['rc'] = rc
        _jobs[job_id]['output'] = '\n'.join(output[-200:])
    except Exception as e:
        _jobs[job_id]['status'] = 'error'
        _jobs[job_id]['error'] = str(e)
        # Report to Sentry if available
        try:
            if sentry_sdk is not None:
                sentry_sdk.capture_exception(e)
        except Exception:
            pass
    finally:
        _jobs[job_id]['end'] = time.time()


# Simple token dependency
async def require_token(x_token: str | None = Header(default=None)):
    if API_TOKEN:
        if not x_token or x_token != API_TOKEN:
            raise HTTPException(status_code=401, detail='Unauthorized')


@app.get('/', response_class=HTMLResponse)
async def ui_index():
    # Prefer a built-in UI prototype if present
    static_index = Path(__file__).resolve().parents[0] / "web_static" / "index.html"
    if static_index.exists():
        return FileResponse(str(static_index))
    # Next prefer the generated index.html if present in a standard outputs subfolder
    smoke = SONAR_OUT / 'holloway_smoke' / 'index.html'
    if smoke.exists():
        return FileResponse(str(smoke))
    # otherwise a tiny landing page
    return HTMLResponse('<html><body><h1>SonarSniffer</h1><p>Use /api/outputs to see available outputs.</p></body></html>')


@app.get('/health/liveness')
async def liveness():
    """Liveness probe endpoint (returns 200 when the process is alive)."""
    return JSONResponse({"status": "ok"})


@app.get('/health/ready')
async def readiness():
    """Readiness probe endpoint. Returns 200 when required resources are available.

    Checks:
    - Outputs directory exists
    - If REDIS_URL is configured, check Redis connectivity
    """
    out = SONAR_OUT
    if not out.exists():
        raise HTTPException(503, 'Outputs directory not available')
    REDIS_URL = os.environ.get('REDIS_URL')
    if REDIS_URL:
        try:
            from redis import Redis

            r = Redis.from_url(REDIS_URL)
            r.ping()
        except Exception:
            raise HTTPException(503, 'Redis not reachable')
    return JSONResponse({"status": "ready"})


@app.get('/api/outputs')
async def list_outputs():
    """List outputs available under SONAR_OUT with basic metadata."""
    out = SONAR_OUT
    if not out.exists():
        raise HTTPException(404, 'Outputs directory not found')
    res = []
    for p in sorted(out.glob('**/*')):
        if p.is_file():
            item = {
                'path': str(p.relative_to(out)),
                'size': p.stat().st_size,
                'mtime': p.stat().st_mtime,
            }
            res.append(item)
    return JSONResponse(res)


@app.get("/api/inputs")
async def list_inputs():
    """List input files available under SONAR_IN with basic metadata."""
    inp = SONAR_IN
    if not inp.exists():
        raise HTTPException(404, "Inputs directory not found")
    res = []
    for p in sorted(inp.rglob("**/*")):
        if p.is_file():
            item = {
                "path": str(p.relative_to(inp)),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
            res.append(item)
    return JSONResponse(res)


@app.get("/api/token_required")
async def token_required():
    """Return whether an API token is required for protected endpoints."""
    return JSONResponse({"required": bool(API_TOKEN)})


@app.post('/api/outputs/regenerate', dependencies=[Depends(require_token)])
async def regenerate_index(background_tasks: BackgroundTasks):
    """Regenerate the index HTML for outputs/holloway_smoke via existing script."""
    script = ROOT / 'scripts' / 'generate_outputs_index.py'
    if not script.exists():
        raise HTTPException(404, 'Generator script not found')
    # Run in background
    job_id = f'gen-{int(time.time())}'

    async def _job():
        await asyncio.create_subprocess_exec(sys.executable, str(script))

    background_tasks.add_task(_job)
    return {'job_id': job_id, 'status': 'scheduled'}


@app.post("/api/upload", dependencies=[Depends(require_token)])
async def upload_input(upload_file: UploadFile = File(...)):
    """Upload a file into the server inputs directory (SONAR_IN)."""
    filename = Path(upload_file.filename).name
    dest = SONAR_IN / filename
    # ensure destination directory exists
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return {"filename": filename, "path": str(dest.relative_to(SONAR_IN))}


@app.post('/api/run/holloway', dependencies=[Depends(require_token)])
async def start_holloway_run(
    out_dir: str | None = None,
    source: str | None = None,
    color: str | None = None,
    video: bool | None = None,
    video_fps: int | None = None,
    video_height: int | None = None,
    scans_per_frame: int | None = None,
    channel_gap: int | None = None,
    pairing_debug: bool | None = None,
    alignment_mode: str | None = None,
    beam_gain: bool | None = None,
    nadir_mask: int | None = None,
    gen_mp4: int | None = None,
    gen_kmz: int | None = None,
    gen_mbtiles: int | None = None,
):
    """Start a background Holloway pipeline run; returns a job id.

    Accepts UI/run-time options and forwards them to the pipeline via env vars or RQ arguments:
      - video_fps, video_height, scans_per_frame, channel_gap
      - pairing_debug (bool), alignment_mode (auto|outer|inner)
    """
    # If caller didn't specify, pick a default out dir
    if not out_dir:
        out_dir = str(SONAR_OUT / 'holloway_run_api')

    # Resolve provided source relative to inputs dir
    if source:
        src_path = SONAR_IN / source
        if not src_path.exists():
            raise HTTPException(404, "Specified source not found")
        source = str(src_path)

    REDIS_URL = os.environ.get("REDIS_URL")
    if REDIS_URL:
        # Lazy import to avoid hard Redis dependency when not used
        try:
            from redis import Redis
            from rq import Queue
            from sonarsniffer.job_runner import run_holloway_sync
        except Exception as e:
            raise HTTPException(500, f"Redis/RQ support not available: {e}")
        redis = Redis.from_url(REDIS_URL)
        q = Queue("default", connection=redis)
        job = q.enqueue(
            run_holloway_sync,
            out_dir,
            source,
            color,
            "1" if video else "0",
            video_fps,
            video_height,
            scans_per_frame,
            channel_gap,
            pairing_debug,
            alignment_mode,
            beam_gain,
            nadir_mask,
            gen_mp4,
            gen_kmz,
            gen_mbtiles,
        )
        return {"job_id": job.get_id(), "backend": "redis"}

    # Fallback: enqueue in-process task
    job_id = f'run-{int(time.time())}'
    _jobs[job_id] = {
        "status": "queued",
        "out_dir": out_dir,
        "created": time.time(),
        "source": source,
        "color": color,
        "video": bool(video),
        "video_fps": video_fps,
        "video_height": video_height,
        "scans_per_frame": scans_per_frame,
        "channel_gap": channel_gap,
        "pairing_debug": pairing_debug,
        "alignment_mode": alignment_mode,
        "beam_gain": beam_gain,
        "nadir_mask": nadir_mask,
    }
    asyncio.create_task(
        run_holloway_job(
            job_id,
            out_dir,
            source,
            color,
            "1" if video else "0",
            video_fps,
            video_height,
            scans_per_frame,
            channel_gap,
            pairing_debug,
            alignment_mode,
            beam_gain,
            nadir_mask,
            gen_mp4,
            gen_kmz,
            gen_mbtiles,
        )
    )
    return {"job_id": job_id, "backend": "local"}


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Return status for a job_id. If Redis is configured, check RQ for job status first."""
    REDIS_URL = os.environ.get("REDIS_URL")
    if REDIS_URL:
        try:
            from redis import Redis
            from rq.job import Job

            redis = Redis.from_url(REDIS_URL)
            job = Job.fetch(job_id, connection=redis)
            return {
                "id": job.get_id(),
                "status": job.get_status(),
                "result": job.result,
            }
        except Exception as e:
            # Fall through to local job store check
            pass
    j = _jobs.get(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return JSONResponse(j)


@app.get('/api/run/{job_id}')
async def get_job(job_id: str):
    j = _jobs.get(job_id)
    if not j:
        raise HTTPException(404, 'Job not found')
    # If local job has an out_dir, provide a relative path to SONAR_OUT when possible
    try:
        outdir = j.get("out_dir")
        if outdir:
            p = Path(str(outdir))
            if str(p).startswith(str(SONAR_OUT)):
                j = dict(j)
                j["out_dir_rel"] = str(p.relative_to(SONAR_OUT))
    except Exception:
        pass
    return JSONResponse(j)


@app.get('/api/logs/{name}')
async def get_log(name: str):
    p = SONAR_OUT / name
    if not p.exists() or not p.is_file():
        raise HTTPException(404, 'Log not found')
    return FileResponse(str(p))


from fastapi import WebSocket, WebSocketDisconnect


@app.websocket('/ws/logs/{job_id}')
async def ws_logs(websocket: WebSocket, job_id: str):
    """WebSocket endpoint to stream logs for a given job id."""
    await websocket.accept()
    subs = _ws_subscribers.setdefault(job_id, set())
    subs.add(websocket)
    try:
        # Send current backlog if present
        j = _jobs.get(job_id)
        if j and 'log_lines' in j:
            for l in j['log_lines'][-200:]:
                await websocket.send_text(l)
        # Keep connection alive and listen for ping messages (no-op)
        while True:
            msg = await websocket.receive_text()
            if msg == 'ping':
                await websocket.send_text('pong')
    except WebSocketDisconnect:
        subs.discard(websocket)
    except Exception:
        subs.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
