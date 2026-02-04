"""Minimal FastAPI app to serve outputs and provide basic admin endpoints
"""
import os
import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure package import path when running from scripts
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

SONAR_OUT = Path(os.environ.get('SONARS_OUTPUT_DIR', str(ROOT / 'outputs')))
API_TOKEN = os.environ.get('SONARS_API_TOKEN', '')

app = FastAPI(title='SonarSniffer API', version='0.1')

# Mount outputs as static files
if (SONAR_OUT).exists():
    app.mount('/outputs', StaticFiles(directory=str(SONAR_OUT)), name='outputs')

# Mount a small built-in UI prototype if present
WEB_STATIC = Path(__file__).resolve().parents[1] / 'web_static'
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


async def run_holloway_job(job_id: str, out_dir: str):
    """Run the holloway pipeline script in background (simple wrapper)."""
    _jobs[job_id]['status'] = 'running'
    _jobs[job_id]['start'] = time.time()
    _jobs[job_id].setdefault('log_lines', [])
    try:
        # Import and run the pipeline script directly to capture stdout
        script_path = ROOT / 'scripts' / 'run_holloway_pipeline.py'
        env = os.environ.copy()
        env['HOLLOWAY_OUT'] = out_dir
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
    static_index = Path(__file__).resolve().parents[1] / 'web_static' / 'index.html'
    if static_index.exists():
        return FileResponse(str(static_index))
    # Next prefer the generated index.html if present in a standard outputs subfolder
    smoke = SONAR_OUT / 'holloway_smoke' / 'index.html'
    if smoke.exists():
        return FileResponse(str(smoke))
    # otherwise a tiny landing page
    return HTMLResponse('<html><body><h1>SonarSniffer</h1><p>Use /api/outputs to see available outputs.</p></body></html>')


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


@app.post('/api/run/holloway', dependencies=[Depends(require_token)])
async def start_holloway_run(out_dir: str | None = None):
    """Start a background Holloway pipeline run; returns a job id."""
    if not out_dir:
        out_dir = str(SONAR_OUT / 'holloway_run_api')
    job_id = f'run-{int(time.time())}'
    _jobs[job_id] = {'status': 'queued', 'out_dir': out_dir, 'created': time.time()}
    # spawn background task
    asyncio.create_task(run_holloway_job(job_id, out_dir))
    return {'job_id': job_id}


@app.get('/api/run/{job_id}')
async def get_job(job_id: str):
    j = _jobs.get(job_id)
    if not j:
        raise HTTPException(404, 'Job not found')
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
