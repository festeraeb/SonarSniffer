#!/usr/bin/env bash
# Simple script to run an RQ worker for sonarsniffer
cd "$(dirname "$0")/.." || exit 1
. venv_gst/bin/activate
if [ -z "$REDIS_URL" ]; then
  echo 'Please set REDIS_URL environment variable, for example: redis://localhost:6379'
  exit 2
fi
exec venv_gst/bin/rq worker -u "$REDIS_URL" default
