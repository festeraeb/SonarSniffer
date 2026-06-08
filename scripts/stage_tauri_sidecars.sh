#!/usr/bin/env bash
# Stage CLI + soundtiles binaries for Tauri externalBin (required before cargo check/tauri build).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_DIR="$REPO/desktop/src-tauri"

# Bundled curvelet library — must exist in-repo (never crates.io).
if [[ ! -f "$REPO/nauticuvs/Cargo.toml" ]]; then
  echo "missing vendored nauticuvs at $REPO/nauticuvs" >&2
  exit 1
fi
BIN_DIR="$TAURI_DIR/binaries"
HOST="$(rustc -vV | awk '/^host: / {print $2}')"

ext=""
if [[ "$HOST" == *windows* ]]; then
  ext=".exe"
fi

mkdir -p "$BIN_DIR"

echo "[sidecars] host=$HOST"

cd "$REPO"
cargo build --release --no-default-features --bin sonarsniffer-cli --bin parse_cli
cargo build --release -p soundtiles

for name in sonarsniffer-cli parse_cli soundtiles; do
  src="$REPO/target/release/${name}${ext}"
  dst="$BIN_DIR/${name}-${HOST}${ext}"
  if [[ ! -f "$src" ]]; then
    echo "missing $src" >&2
    exit 1
  fi
  cp -f "$src" "$dst"
  echo "[sidecars] $dst"
done
