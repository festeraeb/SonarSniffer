#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
. venv_gst/bin/activate
pkill -f 'uvicorn sonarsniffer.web:app' || true
sleep 0.2
export SONARS_HOST=0.0.0.0
export PYTHONPATH=./src
nohup ./venv_gst/bin/python -m uvicorn sonarsniffer.web:app --host 0.0.0.0 --port 8081 --log-level info --lifespan on > /tmp/sonar_debug.log 2>&1 &
echo $! > /tmp/sonar_debug.pid
sleep 1
ss -ltnp | egrep ':8081\s' || true
ps aux | egrep 'uvicorn' | sed -n '1,200p'
