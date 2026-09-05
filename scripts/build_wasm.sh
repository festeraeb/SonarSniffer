#!/usr/bin/env bash
# Build SonarSniffer WASM package (browser). Requires wasm-pack.
# Production flags: --release --no-default-features (see docs/BUILD_FLAGS.md).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT/dist/wasm}"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/data/cargo-target}"
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:/data/cargo-home/bin:$HOME/.cargo/bin:$PATH"

if ! command -v wasm-pack >/dev/null 2>&1; then
  echo "wasm-pack not found. Install: cargo install wasm-pack" >&2
  exit 1
fi

"$ROOT/tools/verify_standalone_repo.sh"

mkdir -p "$OUT"
cd "$ROOT"

# Optional experimental RUSTFLAGS must be set by the caller; unset by default.
echo "=== Building sonarsniffer WASM (release, no default features) ==="
echo "CARGO_TARGET_DIR=$CARGO_TARGET_DIR"
echo "RUSTFLAGS=${RUSTFLAGS:-<unset>}"

wasm-pack build \
  --target web \
  --release \
  --out-dir "$OUT/pkg" \
  --no-default-features

if [[ -f "$ROOT/index.html" ]]; then
  cp "$ROOT/index.html" "$OUT/"
fi
# Copy the GUI assets the index.html references (app.js, styles.css)
# so `python3 -m http.server -d dist/wasm` is a complete triple.
for f in app.js styles.css; do
  if [[ -f "$ROOT/$f" ]]; then
    cp "$ROOT/$f" "$OUT/"
  fi
done

echo ""
echo "WASM artifacts: $OUT/pkg/"
echo "Serve locally:  python3 -m http.server -d $OUT 8080"
