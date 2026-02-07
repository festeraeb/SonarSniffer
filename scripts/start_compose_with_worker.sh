#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.." || exit 1

# Usage: ./scripts/start_compose_with_worker.sh [PORT]
# If PORT is provided on the command line it will be used, otherwise $SONARS_PORT
# will be honored if set, otherwise we scan for a free port starting at 8081.

# Special mode: print chosen port and exit
if [ "$1" = "--print-port" ] || [ "$1" = "-p" ]; then
  if [ -n "$SONARS_PORT" ]; then
    echo "$SONARS_PORT"
    exit 0
  fi
  RUN_DIR="${RUN_DIR:-.run}"
  if [ -f "$RUN_DIR/sonars_port" ]; then
    cat "$RUN_DIR/sonars_port"
    exit 0
  fi
  # Fallback: try to find a free port (without starting compose)
  for p in $(seq 8081 8100); do
    if python3 - <<'PY' >/dev/null 2>&1
import socket,os,sys
p=int(os.environ['p'])
s=socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
  s.bind(('0.0.0.0', p))
  s.close()
  sys.exit(0)
except Exception:
  sys.exit(1)
PY
    then
      echo "$p"
      exit 0
    fi
  done
  echo "No free port found" >&2
  exit 1
fi

PORT_ARG="$1"
if [ -n "$PORT_ARG" ]; then
  PORT=$PORT_ARG
elif [ -n "$SONARS_PORT" ]; then
  PORT=$SONARS_PORT
else
  # If a previous run wrote a chosen port, prefer it
  RUN_DIR="${RUN_DIR:-.run}"
  if [ -f "$RUN_DIR/sonars_port" ]; then
    PORT=$(cat "$RUN_DIR/sonars_port")
    echo "Using previously chosen port from $RUN_DIR/sonars_port: $PORT"
  else
  # Find a free port between 8081 and 8100
  for p in $(seq 8081 8100); do
    if CAND_PORT=$p python3 - <<'PY' >/dev/null 2>&1; then
import socket,os,sys
p=int(os.environ['CAND_PORT'])
s=socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
  s.bind(('0.0.0.0', p))
  s.close()
  sys.exit(0)
except Exception:
  sys.exit(1)
PY
      PORT=$p
      break
    fi
  done
  if [ -z "$PORT" ]; then
    echo "No free port found between 8081 and 8100. Please specify a port." >&2
    exit 1
  fi
fi

export SONARS_PORT=$PORT

# Record chosen port for external tools/CI
RUN_DIR="${RUN_DIR:-.run}"
mkdir -p "$RUN_DIR"
echo "$SONARS_PORT" > "$RUN_DIR/sonars_port"
echo "Wrote chosen port to $RUN_DIR/sonars_port"

echo "Starting docker compose with SONARS_PORT=$SONARS_PORT"
# Build and bring up services (app, redis, worker)
docker compose up -d --build

echo "Waiting for SonarSniffer to become available on http://localhost:${SONARS_PORT} ..."
for i in {1..60}; do
  if curl -sSf http://localhost:${SONARS_PORT}/ >/dev/null 2>&1; then
    echo "Server is up"
    break
  fi
  sleep 1
done

docker compose ps

echo "SonarSniffer should be running on http://localhost:${SONARS_PORT} (container)."
if docker compose ps | grep -q worker; then
  echo "Worker service is running."
fi

echo "Use ./scripts/ci_smoke_test.sh to run a short smoke test or ./scripts/run_worker.sh to start a local worker."