#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

# Build and start compose stack
echo "Bringing up compose stack (this may take a minute)..."
docker compose up -d --build

# Wait for API
echo "Waiting for API at http://localhost:8081/ ..."
for i in $(seq 1 60); do
  if curl -sSf http://localhost:8081/ >/dev/null 2>&1; then
    echo "API is responding"
    break
  fi
  sleep 1
done

TOKEN="${SONARS_API_TOKEN:-}"
AUTH_HEADER=()
if [ -n "$TOKEN" ]; then
  AUTH_HEADER=(-H "X-Token: $TOKEN")
fi

# Trigger a run and capture job id
echo "Triggering holloway run via API..."
RESPONSE=$(curl -s -X POST "http://localhost:8081/api/run/holloway" "${AUTH_HEADER[@]}")
echo "API response: $RESPONSE"
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
BACKEND=$(echo "$RESPONSE" | jq -r '.backend')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
  echo "Failed to obtain job id from API"
  docker compose logs sonarsniffer || true
  exit 2
fi

echo "Submitted job $JOB_ID (backend=$BACKEND). Polling for completion..."

for i in $(seq 1 180); do
  STATUS=$(curl -s "http://localhost:8081/api/job/$JOB_ID" | jq -r '.status') || STATUS=""
  echo "[$i] status=$STATUS"
  if [ "$STATUS" = "success" ]; then
    echo "Job succeeded"
    break
  elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
    echo "Job failed: $STATUS"
    docker compose logs --tail=200 sonarsniffer || true
    docker compose logs --tail=200 worker || true
    exit 3
  fi
  sleep 2
done

# Show outputs
echo "Listing outputs/ (sample):"
docker compose exec -T sonarsniffer bash -lc 'ls -la /app/outputs | sed -n "1,200p"' || true

echo "Smoke test finished. If job succeeded, outputs should be available under ./outputs on the host (mounted)."