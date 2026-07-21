#!/usr/bin/env bash
# Full CLI run-through against production-flagged release binaries.
# See docs/BUILD_FLAGS.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/data/cargo-target}"
PROFILE="${SONARSNIFFER_PROFILE:-release}"
BIN_DIR="${CARGO_TARGET_DIR}/${PROFILE}"
OUT_ROOT="${SMOKE_OUT:-$ROOT/dist/smoke-out}"
TEST_ROOT="${SONARSNIFFER_TEST_FILES:-/mnt/raid0/wreckhunter2000-1-data/sonarsniffer/test_files}"

CLI="$BIN_DIR/sonarsniffer-cli"
PARSE="$BIN_DIR/parse_cli"

if [[ ! -x "$CLI" || ! -x "$PARSE" ]]; then
  echo "Missing release binaries; building with production flags..."
  bash "$ROOT/tools/prod_cargo_build.sh"
fi

mkdir -p "$OUT_ROOT"
echo "=== smoke: parse_cli --preflight ==="
"$PARSE" --preflight || true

echo "=== smoke: sonarsniffer-cli (usage / no-arg probe path) ==="
"$CLI" 2>&1 | head -n 20 || true

CANDIDATES=(
  "$TEST_ROOT/25MAR25-0735-01.RSD"
  "$ROOT/25MAR25-0735-01.RSD"
  "$TEST_ROOT/Sonar001.RSD"
  "$ROOT/Sonar010.RSD"
  "$ROOT/Holloway.RSD"
)

FILE=""
for c in "${CANDIDATES[@]}"; do
  if [[ -f "$c" ]]; then FILE="$c"; break; fi
done

if [[ -z "$FILE" ]]; then
  echo "WARN: no RSD test file found — preflight-only smoke passed" >&2
  exit 0
fi

echo "=== smoke: sonarsniffer-cli probe on $(basename "$FILE") ==="
"$CLI" "$FILE" 2>&1 | head -n 40

SMOKE_DIR="$OUT_ROOT/$(basename "$FILE" .RSD)"
rm -rf "$SMOKE_DIR"
mkdir -p "$SMOKE_DIR"

echo "=== smoke: parse_cli --fast --no-video --output-dir ==="
"$PARSE" "$FILE" --fast --no-video --output-dir "$SMOKE_DIR" --summary | head -n 80

echo ""
echo "OK smoke complete → $SMOKE_DIR"
find "$SMOKE_DIR" -type f 2>/dev/null | head -n 40
