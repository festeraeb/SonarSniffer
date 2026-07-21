#!/usr/bin/env bash
# Production native CLI build — see docs/BUILD_FLAGS.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/data/cargo-target}"

FEATURES="${SONARSNIFFER_FEATURES:-}"
JEMALLOC="${SONARSNIFFER_JEMALLOC:-0}"
PROFILE="${SONARSNIFFER_PROFILE:-release}"

feature_args=(--no-default-features)
if [[ -n "$FEATURES" ]]; then
  feature_args+=(--features "$FEATURES")
elif [[ "$JEMALLOC" == "1" && "$(uname -s)" == "Linux" ]]; then
  feature_args+=(--features jemalloc)
fi

echo "=== SonarSniffer production build ==="
echo "CARGO_TARGET_DIR=$CARGO_TARGET_DIR"
echo "profile=$PROFILE flags: ${feature_args[*]}"
echo "RUSTFLAGS=${RUSTFLAGS:-<unset>}"

"$ROOT/tools/verify_standalone_repo.sh"

cargo build --"$PROFILE" "${feature_args[@]}" \
  --bin sonarsniffer-cli --bin parse_cli

OUT="$CARGO_TARGET_DIR/$PROFILE"
echo ""
echo "OK: $OUT/sonarsniffer-cli"
echo "OK: $OUT/parse_cli"
ls -lh "$OUT/sonarsniffer-cli" "$OUT/parse_cli"
