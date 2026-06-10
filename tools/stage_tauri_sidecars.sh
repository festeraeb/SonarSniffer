#!/usr/bin/env bash
# Stage CLI sidecars for Tauri bundling (Linux/macOS).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${1:-release}"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-${GITHUB_ACTIONS:+${REPO_ROOT}/target}}"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$HOME/.sonarsniffer-build/target}"

cd "$REPO_ROOT"
echo "Building CLI sidecars..."
cargo build --"$PROFILE" --no-default-features --bin sonarsniffer-cli --bin parse_cli

BIN_DIR="$REPO_ROOT/desktop/src-tauri/binaries"
mkdir -p "$BIN_DIR"

cp "$CARGO_TARGET_DIR/$PROFILE/sonarsniffer-cli" "$BIN_DIR/"
cp "$CARGO_TARGET_DIR/$PROFILE/parse_cli" "$BIN_DIR/"
chmod +x "$BIN_DIR/sonarsniffer-cli" "$BIN_DIR/parse_cli"

if [[ -f "$CARGO_TARGET_DIR/$PROFILE/soundtiles" ]]; then
  cp "$CARGO_TARGET_DIR/$PROFILE/soundtiles" "$BIN_DIR/"
  chmod +x "$BIN_DIR/soundtiles"
fi

echo "Sidecars ready in desktop/src-tauri/binaries/"
