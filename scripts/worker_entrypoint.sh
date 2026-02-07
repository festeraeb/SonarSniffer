#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p outputs/jobs logs
# Ensure REDIS_URL is set or default to the compose service name
REDIS_URL=${REDIS_URL:-redis://redis:6379}

echo "Starting RQ worker (connecting to $REDIS_URL)" > outputs/worker.log
# Run worker with stdout/stderr appended to outputs/worker.log
exec rq worker -u "$REDIS_URL" default >> outputs/worker.log 2>&1
